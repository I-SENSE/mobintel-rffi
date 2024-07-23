function [state,psdu,cfgRx,res] = recoverEHT(rxPacket,preEHTChanEst,preEHTNoiseEst,chanBW,lsigLength,cfgDataRec)
%recoverEHT Recovers EHT users and performs measurements
%   [STATE,PSDU,CFGRX,RES] = recoverEHT(RXPACKET,PREEHTCHANEST,PREEHTNOISEEST,CHANBW,LSIGLENGTH,FORMAT,CFGDATAREC)
%   recovers the PSDU from an EHT packet and performs measurements.
%
%   STATE is a structure containing two fields:
%     nextState: The next processing state.
%     status: The previous state processing status.
%
%   PSDU is a cell array were each element is an int8 column vector
%   containing the recovered bits for a recovered user.
%
%   CFGRX is an array of recovered wlanEHTRecoveryConfig objects for each
%   user.
%
%   RES is a structure containing signal analysis.
%
%   RXPACKET is the received and synchronized time-domain packet. It is a
%   Ns-by-Nr matrix of real or complex values, where Ns represents the
%   number of time-domain samples in the packet, and Nr represents the
%   number of receive antennas.
%
%   PREEHTCHANEST is the estimated channel at data and pilot subcarriers
%   based on the L-LTF, L-SIG and RL-SIG. It is a real or complex array of
%   size Nst-by-1-by-Nr, where Nst represents the total number of occupied
%   subcarriers. The singleton dimension corresponds to the single
%   transmitted stream in the pre-EHT fields which includes the combined
%   cyclic shifts if multiple transmit antennas are used.
%
%   PREEHTNOISEEST is the noise variance estimate. It is a real,
%   nonnegative scalar.
%
%   CHANBW is the channel bandwidth and must be 'CBW20', 'CBW40', 'CBW80',
%   'CBW160', or 'CBW320'.
%
%   LSIGLENGTH is the recovered length field from L-SIG.
%
%   CFGDATAREC is an object of type trackingRecoveryConfig.

%   Copyright 2023 The MathWorks, Inc.

    state = struct;
    state.status = "Success";
    state.nextState = "EHT-Headers";

    % Create recovery config now we have decoded L-SIG successfully
    cfgRx = wlanEHTRecoveryConfig('ChannelBandwidth',chanBW);
    cfgRx.LSIGLength = lsigLength;

    % Create default result structure
    res = struct;
    res.PHYConfig = cfgRx;

    res.USIG = struct;
    res.EHTSIG = struct;

    res.EHTPreamble = struct;
    res.EHTPreamble.Processed = false;
    res.EHTPreamble.EHTSTFPower = nan;
    res.EHTPreamble.EHTLTFPower = nan;
    res.EHTPreamble.RU = repmat(struct('Power',nan),1,0);

    res.EHTData = struct;
    res.EHTData.Processed = false;
    res.EHTData.Power = nan;
    res.EHTData.RU = repmat(struct('Power',nan),1,0);
    res.EHTData.User = repmat(struct('Power',nan),1,0);

    psdu = [];

    while all(state.nextState~=["RxError" "A-MPDU" "RxSuccess"])
        switch state.nextState
          case "EHT-Headers"

            [status,resEHTHeader] = processEHTHeaders(rxPacket,preEHTChanEst,preEHTNoiseEst,cfgRx);

            cfgRx = resEHTHeader.PHYConfig; % Return from function updated PHY configuration
            res.PHYConfig = cfgRx;
            res.USIG = resEHTHeader.USIG;
            res.EHTSIG = resEHTHeader.EHTSIG;

            state.status = status;
            if any(strcmp(status,"Success"))
                state.nextState = "EHT-Preamble";
            else
                state.nextState = "RxError";
            end

          case {"EHT-Preamble"}

            users = resEHTHeader.PHYConfig;
            indexEHT = wlanFieldIndices(users(1));
            res.EHTPreamble = processEHTPreamble(rxPacket,users,indexEHT);

            % Apply AGC (EHT-STF) to whole packet
            rxPacket(indexEHT.EHTSTF(1):end,:) = rxPacket(indexEHT.EHTSTF(1):end,:)./sqrt(res.EHTPreamble.EHTSTFPower);

            if isempty(indexEHT.EHTData) || indexEHT.EHTData(2)<indexEHT.EHTData(1)
                % NDP therefore no data field
                state.nextState = "RxSuccess";
            else
                state.nextState = "EHT-Data";
            end

          case "EHT-Data"

            [psdu, res.EHTData] = processEHTData(rxPacket, res.PHYConfig,res.EHTPreamble.RU,cfgDataRec, indexEHT);

            % Adjust measured power to account for EHT-STF AGC scaling
            res.EHTData.Power = res.EHTData.Power*res.EHTPreamble.EHTSTFPower;
            for r = 1:numel(res.EHTPreamble.RU)
                res.EHTData.RU(r).Power = res.EHTData.RU(r).Power*res.EHTPreamble.EHTSTFPower;
            end
            for u = 1:numel(res.EHTData.User)
                res.EHTData.User(u).Power = res.EHTData.User(u).Power*res.EHTPreamble.EHTSTFPower;
            end

            state.nextState = "A-MPDU";
        end
    end

end

function [status, res] = processEHTHeaders(rxPacket,preEHTChanEst,NEstNonHT,cfgRx)
% Process U-SIG and EHT-SIG

    persistent BPSKEVM
    persistent EVM
    if isempty(BPSKEVM)
        BPSKEVM = comm.EVM('ReferenceSignalSource','Estimated from reference constellation', ...
                           'MaximumEVMOutputPort',true, ...
                           'AveragingDimensions',[1 2], ...
                           'ReferenceConstellation',wlanReferenceSymbols('BPSK'));
    end
    if isempty(EVM)
        EVM = comm.EVM('ReferenceSignalSource','Estimated from reference constellation', ...
                       'AveragingDimensions',[1 2],...
                       'MaximumEVMOutputPort',true);
    end

    % Update field indices after packet format detection
    chanBW = cfgRx.ChannelBandwidth;
    indexEHT = wlanFieldIndices(cfgRx);

    rxUSIG = rxPacket(indexEHT.USIG(1):indexEHT.USIG(2),:);
    usigDemod = wlanEHTDemodulate(rxUSIG,'U-SIG',cfgRx);
    [usigDemod,cpe] = wlanEHTTrackPilotError(usigDemod,preEHTChanEst,cfgRx,'U-SIG');

    % Equalize data carrying subcarriers, merging 20 MHz subchannels
    preehtInfo = wlanEHTOFDMInfo('U-SIG',cfgRx);
    [eqUSIGSymComb,csi] = wlanEHTEqualize(usigDemod(preehtInfo.DataIndices,:,:), ...
                                         preEHTChanEst(preehtInfo.DataIndices,:,:), ...
                                         NEstNonHT,cfgRx,'U-SIG'); % Without combining
    % Equalize without combining for EVM measurement
    eqUSIGSym = ofdmEqualize(usigDemod(preehtInfo.DataIndices,:,:),preEHTChanEst(preehtInfo.DataIndices,:,:),NEstNonHT);

    % Recover U-SIG bits
    [rxUSIGBits,failCRC] = wlanUSIGBitRecover(eqUSIGSymComb,NEstNonHT,csi);

    [EVMRMSComb,EVMMaxComb] = BPSKEVM(eqUSIGSymComb);
    [EVMRMS,EVMMax] = BPSKEVM(eqUSIGSym);

    res = struct;
    res.PHYConfig = cfgRx;

    % Store U-SIG results
    res.USIG = struct;
    res.USIG.Processed = true;
    res.USIG.EQDataSym = eqUSIGSym;
    res.USIG.Bits = rxUSIGBits;
    res.USIG.FailCRC = failCRC;
    res.USIG.CPE = cpe;
    res.USIG.Power = mean(rxUSIG(:).*conj(rxUSIG(:)));
    res.USIG.EVMRMS = 20*log10(mean(EVMRMS)/100);
    res.USIG.EVMMax = 20*log10(mean(EVMMax)/100);
    res.USIG.EVMRMSCombined = 20*log10(EVMRMSComb/100);
    res.USIG.EVMMaxCombined = 20*log10(EVMMaxComb/100);
    res.USIG.EVMMax = 20*log10(mean(EVMMax)/100);

    % Initialize EHT-SIG results
    res.EHTSIG = struct;
    res.EHTSIG.Processed = false;
    res.EHTSIG.Power = nan;
    res.EHTSIG.User = struct;
    res.EHTSIG.User.Processed = false;

    if all(failCRC)
        % If every 80 MHz subblock fails then stop processing
        status = "U-SIG FailCRC";
        return
    end

    % Update PHY configuration now U-SIG decoded
    [cfgRx,failInterp] = interpretUSIGBits(cfgRx,rxUSIGBits,failCRC);
    if failInterp
        status = "Invalid U-SIG contents";
        return
    end
    res.PHYConfig = cfgRx;

    if ~strcmp(cfgRx.ChannelBandwidth,chanBW)
        % Likely captured a packet which has a larger or smaller bandwidth
        % than we are capturing, therefore stop processing
        status = "Unexpected channel bandwidth decoded";
        return
    end

    % Setup EHT-SIG EVM measurement
    release(EVM);
    switch cfgRx.EHTSIGMCS
        case 0
            ehtsigmod = 'BPSK';
        case 1
            ehtsigmod = 'QPSK';
        case 3
            ehtsigmod = '16QAM';
        case 15
            ehtsigmod = 'BPSK'; % BPSK-DCM
    end
    EVM.ReferenceConstellation = wlanReferenceSymbols(ehtsigmod);

    % EHT-SIG common processing
    res.EHTSIG.Processed = true;

    % Update field indices
    indexEHT = wlanFieldIndices(cfgRx);

    % Get EHT-SIG field symbols
    rxEHTSIG = rxPacket(indexEHT.EHTSIG(1):indexEHT.EHTSIG(2),:);

    % Demodulate EHT-SIG field
    ehtsigDemod = wlanEHTDemodulate(rxEHTSIG,'EHT-SIG',cfgRx);

    % Estimate and correct common phase error
    ehtsigDemod = wlanEHTTrackPilotError(ehtsigDemod,preEHTChanEst(preehtInfo.PilotIndices,:,:),cfgRx,'EHT-SIG');

    % Extract data symbols
    ehtsigDemodData = ehtsigDemod(preehtInfo.DataIndices,:,:);

    % Equalize and merge subchannel within an 80 MHz subchannels
    [eqEHTSIGSymComb,csiData] = wlanEHTEqualize(ehtsigDemodData,preEHTChanEst(preehtInfo.DataIndices,:,:),NEstNonHT,cfgRx,'EHT-SIG'); % With combining
    eqEHTSIGSym = ofdmEqualize(ehtsigDemodData,preEHTChanEst(preehtInfo.DataIndices,:,:),NEstNonHT); % Without combining

    % Decode EHT-SIG common field
    [commonBits,failCRC] = wlanEHTSIGCommonBitRecover(eqEHTSIGSymComb,NEstNonHT,csiData,cfgRx);
    [cfgRx,failInterp] = interpretEHTSIGCommonBits(cfgRx,commonBits,failCRC);
    res.EHTSIG.UsersSignaledInSingleSubblock = cfgRx.UsersSignaledInSingleSubblock;

    % Update PHY configuration
    res.PHYConfig = cfgRx;
    
    % Set power and EVM measure for EHT-SIG field
    res.EHTSIG.EQDataSym = eqEHTSIGSym;
    res.EHTSIG.EQDataSymCombined = eqEHTSIGSymComb;
    res.EHTSIG.Power = mean(rxEHTSIG(:).*conj(rxEHTSIG(:)));
    [EVMRMS,EVMMax] = EVM(res.EHTSIG.EQDataSym);
    res.EHTSIG.EVMRMS = 20*log10(EVMRMS/100);
    res.EHTSIG.EVMMax = 20*log10(EVMMax/100);
    [EVMRMSComb,EVMMaxComb] = EVM(res.EHTSIG.EQDataSymCombined);
    res.EHTSIG.EVMRMSCombined = 20*log10(EVMRMSComb/100);
    res.EHTSIG.EVMMaxCombined = 20*log10(EVMMaxComb/100);

    % Check if EHT Common field CRC fails
    if all(failCRC,'all') && failInterp
        status = "EHT-SIG Common Fail";
        return
    else
        if cfgRx.PPDUType==wlan.type.EHTPPDUType.ndp && ~failCRC
            status = "Success"; % EHT Sounding NDP
            return
        elseif cfgRx.PPDUType==wlan.type.EHTPPDUType.dl_ofdma && any(failCRC,'All')
            status = "EHT-SIG Common Fail";
            return
        end
    end

    % Recover user bits
    [userBits,failCRC] = wlanEHTSIGUserBitRecover(eqEHTSIGSymComb,NEstNonHT,cfgRx,csi);
    [cfgUsers,failInterp] = interpretEHTSIGUserBits(cfgRx,userBits,failCRC);

    res.EHTSIG.User = struct;
    res.EHTSIG.User.Processed = true;
    res.EHTSIG.User.FailCRC = failCRC;
    res.EHTSIG.User.FailInterp = failInterp;
    res.EHTSIG.User.Bits = userBits;

    % CRC on EHT-SIG (user field)
    if all(~failCRC) && all(~failInterp)
        % All users pass CRC and interpreted successfully
        res.EHTSIG.NumUsers = sum(cfgRx.NumUsersPerContentChannel);
        res.EHTSIG.User.Status = "Success";
    elseif all(failCRC)
        % Discard the packet if all users fail the CRC
        status = "EHT-SIG User Fail";
        res.EHTSIG.NumUsers = nan;
        res.EHTSIG.User.Status = 'EHT-SIG CRC failed for all users';
        return
    elseif all(failInterp)
        % Discard the packet if all users cannot be interpreted
        status = "EHT-SIG User Fail";
        res.EHTSIG.NumUsers = nan;
        res.EHTSIG.User.Status = 'EHT-SIG unexpected value or CRC fail for all users';
        return
    elseif all(~failInterp)
        % Some users failed CRC, but passing ones all interpreted
        % Only process users with valid CRC and can be interpreted
        res.EHTSIG.NumUsers = numel(cfgUsers);
        res.EHTSIG.User.Status = 'EHT-SIG CRC failed for at least one user';
    elseif all(~failCRC)
        % All users passed CRC, but some failed interpretation
        % Only process users which can be interpreted
        res.EHTSIG.NumUsers = numel(cfgUsers);
        res.EHTSIG.User.Status = 'EHT-SIG unexpected value for at least one user';
    else % any(failInterp)
        % Some users failed CRC, and some passing ones failed interpretation
        % Only process users with valid CRC and can be interpreted
        res.EHTSIG.NumUsers = numel(cfgUsers);
        res.EHTSIG.User.Status = 'EHT-SIG unexpected value or CRC failed for at least one user';
    end

    res.PHYConfig = cellfun(@(x)x,cfgUsers,'UniformOutput',true); % Convert cell array to object array
    status = "Success";
end

function res = processEHTPreamble(rxPacket,cfgUser,indexEHT)
% Process EHT-STF and EHT-LTF

% EHT-STF AGC - apply to remaining packet
    rxEHTSTF = rxPacket((indexEHT.EHTSTF(1):indexEHT.EHTSTF(2)),:);
    ehtSTFPower = mean(rxEHTSTF(:).*conj(rxEHTSTF(:)));
    rxPacket(indexEHT.EHTSTF(1):end,:) = rxPacket(indexEHT.EHTSTF(1):end,:)./sqrt(ehtSTFPower);

    rxEHTLTF = rxPacket((indexEHT.EHTLTF(1):indexEHT.EHTLTF(2)),:);
    ehtltfPower = mean(rxEHTLTF(:).*conj(rxEHTLTF(:)));
    
    isOFDMA = false;
    if cfgUser(1).PPDUType==wlan.type.EHTPPDUType.dl_ofdma
        allocInfo = wlan.internal.ehtAllocationParams(cfgUser(1).AllocationIndex);
        isOFDMA = true;
    else
        allocInfo = struct('NumRUs',1,'RUSizes',cfgUser(1).RUSize,'RUIndices',cfgUser(1).RUIndex);
    end

    % Create a numRU-by-numUsers logical matrix indicating which users are associated with an RU
    numUsers = numel(cfgUser);
    userInd = false(allocInfo.NumRUs,numUsers);
    if isOFDMA
        if numel(cell2mat(allocInfo.RUSizes)) > numel(allocInfo.RUSizes)
            % Contains MRU
            ruSizePerUser = zeros(1,numUsers); % RU size and index for each user
            ruIndexPerUSer = zeros(1,numUsers);
            for indUser = 1:numUsers
                ruSizePerUser(indUser) = sum(cfgUser(indUser).RUSize);
                ruIndexPerUSer(indUser) = sum(cfgUser(indUser).RUIndex);
            end
            for r = 1:allocInfo.NumRUs
                userInd(r,:) = all([sum(cell2mat(allocInfo.RUSizes(r))); sum(cell2mat(allocInfo.RUIndices(r)))]==[ruSizePerUser;ruIndexPerUSer],1);
            end
        else
            % Not Containing MRU
            for r = 1:allocInfo.NumRUs
                userInd(r,:) = all([cell2mat(allocInfo.RUSizes(r)); cell2mat(allocInfo.RUIndices(r))]==[[cfgUser.RUSize];[cfgUser.RUIndex]],1);
            end
        end
    else
        % Non-OFDMA, always a single RU
        ruIndex = 1;
        if numel(allocInfo.RUSizes) > allocInfo.NumRUs
            % Contains MRU
            ruSizePerUser = zeros(1,numUsers); % RU size and index for each user
            ruIndexPerUSer = zeros(1,numUsers);
            for indUser = 1:numUsers
                ruSizePerUser(indUser) = sum(cfgUser(indUser).RUSize);
                ruIndexPerUSer(indUser) = sum(cfgUser(indUser).RUIndex);
            end
            userInd(ruIndex,:) = all([sum(allocInfo.RUSizes); sum(allocInfo.RUIndices)]==[ruSizePerUser;ruIndexPerUSer],1);
        else
            userInd(ruIndex,:) = all([allocInfo.RUSizes(ruIndex); allocInfo.RUIndices(ruIndex)]==[[cfgUser.RUSize];[cfgUser.RUIndex]],1);
        end
    end

    % Per-RU processing of LTF
    ehtltfRU = struct('RUSize',0,'RUIndex',0,'UserNumbers',[],'UserIndices',[],'ChanEst',[],'PilotEst',[],'Power',0);
    ehtltfRU = repmat(ehtltfRU,1,allocInfo.NumRUs);
    for r = 1:allocInfo.NumRUs
        if isOFDMA
            ehtltfRU(r).RUSize = cell2mat(allocInfo.RUSizes(r));
            ehtltfRU(r).RUIndex = cell2mat(allocInfo.RUIndices(r));
        else
            ehtltfRU(r).RUSize = allocInfo.RUSizes; % Could be MRU
            ehtltfRU(r).RUIndex = allocInfo.RUIndices;
        end
        ehtltfRU(r).UserIndices = userInd(r,:);
        ehtltfRU(r).UserNumbers = find(userInd(r,:));

        if isempty(ehtltfRU(r).UserNumbers)
            % If no user can be decoded in RU then skip RU
            continue;
        end

        uidx = ehtltfRU(r).UserNumbers(1); % Get a user for the RU for channel estimation (which one doesn't matter)

        % EHT-LTF demodulation
        ehtltfDemod = wlanEHTDemodulate(rxEHTLTF,'EHT-LTF',cfgUser(uidx));

        % Channel estimate
        [ehtltfRU(r).ChanEst,ehtltfRU(r).PilotEst] = wlanEHTLTFChannelEstimate(ehtltfDemod,cfgUser(uidx));

        % Measure power of an RU
        measuredRUPower = mean(abs(ehtltfDemod(:).*conj(ehtltfDemod(:))));
        ehtltfRU(r).Power = measuredRUPower*ehtSTFPower; % Normalize as scaled by EHT-STF AGC
    end

    res = struct;
    res.Processed = true;
    res.EHTSTFPower = ehtSTFPower;
    res.EHTLTFPower = ehtltfPower*ehtSTFPower; % Normalize as scaled by EHT-STF AGC
    res.RU = ehtltfRU;

end

function [rxPSDU, resData] = processEHTData(rxPacket,users,RU,cfgDataRec,indexEHT)
% Process EHT-Data field for all users

% Extract data portion from packet
    rxEHTData = rxPacket(indexEHT.EHTData(1):end,:);

    % Calculate the number of OFDM symbols in the data field
    ehtOFDMInfo = wlanEHTOFDMInfo('EHT-Data',users(1));
    symLen = ehtOFDMInfo.FFTLength+ehtOFDMInfo.CPLength;
    numOFDMSym = (double(indexEHT.EHTData(2)-indexEHT.EHTData(1))+1)/symLen;

    resData = struct;
    resData.Processed = true;
    resData.Power = mean(rxEHTData(:).*conj(rxEHTData(:)));

    numRUs = numel(RU);
    numUsers = numel(users);

    % Form a matrix indicating which users are on which RU
    ruUserMatrix = false(numRUs,numUsers);
    for r = 1:numRUs
        ruUserMatrix(r,:) = RU(r).UserIndices;
    end

    % Initialize storage
    rxPSDU = cell(1,numel(users));
    resUser = struct;
    resUser.Processed = true;
    resUser.NoiseEst = 0;
    resUser.rxPSDU = [];
    resUser.EQDataSym = [];
    resUser.EQPilotSym = [];
    resUser.CPE = [];
    resUser.PEG = [];
    resUser.PilotGain = [];
    resUser.rxPSDU = [];
    resUser.EVMRMS =0;
    resUser.EVMMax = 0;
    resUser.Power = 0;
    resUser.RUNumber = 0;
    resUser = repmat(resUser,1,numel(users));

    % Demodulation and decoding for each user
    for u = 1:numUsers
        ruNum = ruUserMatrix(:,u); % Get the index of the RU containing the user

        [rxPSDU{u},resUser(u)] = processEHTDataUser(rxEHTData,users(u), ...
                                                   RU(ruNum).ChanEst,RU(ruNum).PilotEst,numOFDMSym,cfgDataRec);
        resUser(u).RUNumber = find(ruNum);
    end
    resData.User = resUser;

    % Store per-RU results
    ehtDataRU = struct('RUSize',0,'RUIndex',0,'UserNumbers',[],'NoiseEst',0,'Power',0);
    ehtDataRU = repmat(ehtDataRU,1,numRUs);
    for r = 1:numRUs
        u = find(ruUserMatrix(r,:),1);
        if isempty(u)
            % No user can be decoded in this RU
            continue
        end
        ehtDataRU(r).RUSize = users(u).RUSize;
        ehtDataRU(r).RUIndex = users(u).RUIndex;
        ehtDataRU(r).UserNumbers = RU(r).UserNumbers;
        ehtDataRU(r).Power = resUser(u).Power;
        ehtDataRU(r).NoiseEst = resUser(u).NoiseEst;
    end
    resData.RU = ehtDataRU;

end

function [rxPSDU,res] = processEHTDataUser(rxData,user,chanEst,pilotEst,numOFDMSym,cfgDataRec)
% Process EHT-Data field for a user

    persistent DataEVM

    if isempty(DataEVM)
        % Average over symbols and subcarriers
        DataEVM = comm.EVM('ReferenceSignalSource','Estimated from reference constellation', ...
                           'AveragingDimensions',[1 2],...
                           'MaximumEVMOutputPort',true);
    end

    res = struct;
    ehtOFDMInfo = wlanEHTOFDMInfo('EHT-Data',user);

    % Joint demodulation and tracking
    [demodSym,res.CPE,res.PEG,res.PilotGain] = helperTrackingOFDMDemodulate(rxData,chanEst,numOFDMSym,user,cfgDataRec);

    % Estimate noise power in EHT fields
    demodPilotSym = demodSym(ehtOFDMInfo.PilotIndices,:,:);
    res.NoiseEst = wlanEHTDataNoiseEstimate(demodPilotSym,pilotEst,user);

    % Equalize
    if strcmp(cfgDataRec.EqualizationMethod,'ZF')
        nEstEQ = 0;
    else
        nEstEQ = res.NoiseEst;
    end
    [res.EQDataSym,csiData] = wlanEHTEqualize(demodSym(ehtOFDMInfo.DataIndices,:,:),chanEst(ehtOFDMInfo.DataIndices,:,:),nEstEQ,user,'EHT-Data');
    % Equalize pilots separately
    res.EQPilotSym = ofdmEqualize(demodSym(ehtOFDMInfo.PilotIndices,:,:),chanEst(ehtOFDMInfo.PilotIndices,:,:),nEstEQ);

    % Demap and decode bits
    rxPSDU = wlanEHTDataBitRecover(res.EQDataSym,res.NoiseEst,csiData,user,'LDPCDecodingMethod',cfgDataRec.LDPCDecodingMethod);
    res.rxPSDU = rxPSDU;

    % Measure EVM per spatial stream, averaged over subcarriers and symbols
    release(DataEVM);
    DataEVM.ReferenceConstellation = wlanReferenceSymbols(user);
    [EVMRMS,EVMMax] = step(DataEVM,res.EQDataSym);
    res.EVMRMS = 20*log10(squeeze(EVMRMS)/100);
    res.EVMMax = 20*log10(squeeze(EVMMax)/100);

    % Measure power of an RU using the pilots as the average power of the
    % constellation is 1.
    res.Power = mean(abs(demodPilotSym(:).*conj(demodPilotSym(:))));

    res.RUNumber = nan; % Will be set externally
    res.Processed = true;

end