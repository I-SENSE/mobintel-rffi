function [failCRC,cfgUsers,bitsUsers,eqUserSym,failInterpretation] = heSIGBUserFieldDecode(rx,chanEst,noiseVar,cfgRx,varargin)
%heSIGBUserFieldDecode Decode HE-SIG-B user field
%
%   [FAILCRC,CFGUSERS] =
%   heSIGBUserFieldDecode(RX,CHANEST,NOISEVAR,CFGUSERS) decode the HE-SIG-B
%   user field given the HE-SIG-B field samples, RX, channel estimate,
%   CHANEST, noise variance, NOISEVAR, and recovery configuration object
%   CFGRX.
%
%   FAILCRC represents the result of the CRC for each user. It is true if
%   the user fails the CRC. It is a logical row vector of size
%   1-by-NumUsers.
%
%   Returned CFGUSERS is a cell array of size 1-by-NumUsers. CFGUSERS is
%   the updated format configuration object after HE-SIG-B user field
%   decoding, of type <a href="matlab:help('wlanHERecoveryConfig')">wlanHERecoveryConfig</a>. The updated format
%   configuration object CFGUSERS is only returned for the users who pass
%   the CRC.
%
%   RX are the HE-SIG-B field samples.
%
%   CHANEST is a complex Nst-by-1-by-Nr array containing the estimated
%   channel at data and pilot subcarriers, where Nst is the number of
%   occupied subcarriers and Nr is the number of receive antennas.
%
%   NOISEVAR is the noise variance estimate, specified as a nonnegative
%   scalar.
%
%   The input CFGRX is the format configuration object of type
%   <a href="matlab:help('wlanHERecoveryConfig')">wlanHERecoveryConfig</a>, which specifies the parameters for the HE-MU format.
%
%   [...,FAILINTERPRETATION] = heSIGBUserFieldDecode(...,SUPPRESSERROR)
%   controls the behavior of the function due to an unexpected value of the
%   interpreted HE-SIG-B user field bits. SUPPRESSERROR is logical. When
%   SUPPRESSERROR is true and the function cannot interpret the recovered
%   HE-SIG-B user field bits due to an unexpected value, the function
%   returns FAILINTERPRETATION as true and the returned object is unchanged
%   for the user. When SUPPRESSERROR is false and the function cannot
%   interpret the recovered HE-SIG-B user field bits due to an unexpected
%   value, an exception is issued and the function does not return. The
%   default is false.

%   Copyright 2018-2023 The MathWorks, Inc.

    suppressError = false; % Control the validation of the interpreted HE-SIG-B user field bits
    failInterpretation = false;
    if nargin>4
        suppressError = varargin{1};
    end
    chanBW = cfgRx.ChannelBandwidth;

    % Demodulate HE-SIGB field
    demodUserFieldData = wlanHEDemodulate(rx,'HE-SIG-B',chanBW);

    % Estimate and correct common phase error
    preheInfo = wlanHEOFDMInfo('HE-SIG-B',chanBW);
    demodUserFieldData = wlanHETrackPilotError(demodUserFieldData,chanEst(preheInfo.PilotIndices,:,:),cfgRx,'HE-SIG-B');

    % Extract data symbols
    demodUserData = demodUserFieldData(preheInfo.DataIndices,:,:);

    % Perform equalization
    if matches(packetFormat(cfgRx),'HE-MU')
        % For code generation of wlanHEEqualize with cfgRx of type
        % wlanHERecoveryConfig
        field = 'HE-SIG-B';
    else
        field = '';
        error("Packet format is not of type 'HE-MU'.");
    end
    [eqUserSym,csi] = wlanHEEqualize(demodUserData,chanEst(preheInfo.DataIndices,:,:),noiseVar,cfgRx,field);

    % Return a cell array of objects each representing a user
    if suppressError
        [bitsUsers,failCRC] = wlanHESIGBUserBitRecover(eqUserSym,noiseVar,csi,cfgRx);
        [cfgUsers,failInterpretation] = interpretHESIGBUserBits(cfgRx,bitsUsers,failCRC);
    else
        [bitsUsers,failCRC,cfgUsers] = wlanHESIGBUserBitRecover(eqUserSym,noiseVar,csi,cfgRx);
    end

end
