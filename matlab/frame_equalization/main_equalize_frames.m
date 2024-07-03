% This function takes as input a root directory of the RX device, and then processes each of the packets, leaving a new batch of processed packets.
function [] = main_equalize_frames(input_dir, output_dir, min_frame_limit)
    tx_nodes = dir([input_dir, 'packets/']);

    % Skip first two entries ('.' and '..')
    for tx_node = 3 : length(tx_nodes)
        fl = tx_nodes(tx_node).name;

        load([input_dir, 'packets/', fl]);

        packet_log_in = packet_log;

        fprintf(sprintf('Node %d of %d: %s (%d packets)\n' , tx_node, length(tx_nodes), fl, length(packet_log_in))); 

        % Only process the emitter if there are at least min_frame_limit from
        % it (we need more, but this is the min bar)
        if length(packet_log_in) < min_frame_limit
            disp('Not enough packets available.');
            continue;
        end

        packet_log_op = {};
        for pkt_i=1:length(packet_log_in)
            pkt = packet_log_in{pkt_i};
            [preamble_clean, preamble_equalized] = process_frame(pkt);
            if ~isempty(preamble_clean) 
                packet_log_op{end+1} = [preamble_clean, preamble_equalized];
            end
        end

        % Only process the emitter if there are at least min_frame_limit from
        % it (we need more, but this is the min bar)
        if length(packet_log_op) < min_frame_limit
            disp('Not enough packets available.');
            continue;
        end

        packet_log=packet_log_op;
        if ~isempty(packet_log)
            if ~exist([output_dir, 'equalized_packets/'])
                mkdir([output_dir, 'equalized_packets/']);
            end
            save([input_dir, 'equalized_packets/', fl], 'packet_log')
        end
    end
end

function [preamble_clean_up, preamble_equalized_up] = process_frame(pkt)
    nht = wlanNonHTConfig;

    % Downsample from 25 Msps to 20 Msps
    pkt = resample(pkt,4,5);
    pkt = [zeros(20,1); pkt];

    % Find start of the packet, abandon if failed
    strt_indx = wlanPacketDetect(pkt,'CBW20');
    if isempty(strt_indx)
        preamble_clean_up = [];
        preamble_equalized_up = [];
        return
    end 
    if strt_indx+800> length(pkt)
        preamble_clean_up = [];
        preamble_equalized_up = [];
        return
    end

    % Keep only the first 800 samples (we'll need even less)
    pkt = pkt(strt_indx:strt_indx+800);
    
    % Somewhat redundantly, extract preamble from the raw IQ samples
    preamble_clean = extract_preamble(pkt, 0.8, nht);

    % Perform CFO removal & equalization
    preamble_equalized = equalize(pkt, nht);

    % Perform upsampling (20 -> 25 Msps, 320 samples -> 400 samples)
    preamble_clean_up = resample(preamble_clean, 5, 4);
    preamble_equalized_up = resample(preamble_equalized, 5, 4);
end

% Estimate CSI and equalize the frame
function [pkt_stf_ltf_fo] = equalize(pkt, nht)
    % Determine indexes of STF and LTF sequences
    stf_ind = wlanFieldIndices(nht,'L-STF');
    ltf_ind = wlanFieldIndices(nht,'L-LTF');
    pkt_stf = pkt(stf_ind(1):stf_ind(2));

    freqOffsetEst1 = wlanCoarseCFOEstimate(pkt_stf,'CBW20');
    pkt = pkt.*exp(1j*(1:length(pkt))'/20e6*2*pi*-freqOffsetEst1 );
    pkt_ltf = pkt(ltf_ind(1):ltf_ind(2));

    freqOffsetEst2 = wlanFineCFOEstimate(pkt_ltf,'CBW20');

    pkt = pkt.*exp(1j*(1:length(pkt))'/20e6*2*pi*-freqOffsetEst2);

    % Specify indexes of null & pilot subcarriers
    datIndx= [39:64 2:27];

    % Get IQ samples of the STF sequence
    pkt_stf = pkt(stf_ind(1):stf_ind(2));

    % Get IQ samples of the LTF sequence
    pkt_ltf = pkt(ltf_ind(1):ltf_ind(2));

    % Demodulate LTF, estimate noise, CSI
    demodSig = wlanLLTFDemodulate(pkt_ltf,nht);
    nVar = helperNoiseEstimate(demodSig, nht.ChannelBandwidth, 1);
    
    % Merge the preamble, reshape into a (64x5) array, run FFT
    pkt_stf_ltf = [pkt_stf; pkt_ltf];
    pkt_stf_ltf_resh = reshape(pkt_stf_ltf,64,5);
    pkt_stf_ltf_freq = fft(pkt_stf_ltf_resh,64);
    pkt_stf_ltf_freq = pkt_stf_ltf_freq(datIndx,:);

    % Estimate CSI, perform equalization of the preamble
    h1 = wlanLLTFChannelEstimate(demodSig,nht);
    pkt_stf_ltf_freq_eq = pkt_stf_ltf_freq.*conj(h1)./(conj(h1).*h1+nVar);

    pkt_stf_ltf_freq_eq_all = zeros(64,5);
    pkt_stf_ltf_freq_eq_all(datIndx,:) = pkt_stf_ltf_freq_eq;
    pkt_stf_ltf_eq = ifft(pkt_stf_ltf_freq_eq_all,64);
    pkt_stf_ltf_eq = pkt_stf_ltf_eq(:);
    
    pkt_stf_ltf_fo = pkt_stf_ltf_eq .*exp(1j*(1:length(pkt_stf_ltf_eq))'/20e6*2*pi*(freqOffsetEst1+freqOffsetEst2));
end

% Extract preamble from the frame
% This method somewhat does refundant work. We could simply use indexes
% from stf_ind & ltf_ind to get our preamble. But as a sanity check, we're
% going to do it from scratch using cross-correlation.
function [preamble] = extract_preamble(X, sensitivity, nht)
    % Determine indexes of STF and LTF sequences
    stf_ind = wlanFieldIndices(nht,'L-STF');
    ltf_ind = wlanFieldIndices(nht,'L-LTF');
    pkt_stf = X(stf_ind(1):stf_ind(2));
    pkt_ltf = X(ltf_ind(1):ltf_ind(2));
    preamble = [pkt_stf; pkt_ltf];

%     % Generate the reference LTF sequence
%     % The function wlanLLTF generates the L-LTF time domain signal for 802.11n
%     ltfSequence = wlanLLTF(nht);
%     stfSequence = wlanLSTF(nht);
%     
%     % Perform correlation
%     [correlationLTF, lagLTF] = xcorr(X, ltfSequence);
%     [correlationSTF, lagSTF] = xcorr(X, stfSequence);
%     
%     correlationLTF = abs(correlationLTF);
%     correlationSTF = abs(correlationSTF);
%     
%     % Find peaks in the correlation
%     [~, locsLTF] = findpeaks(correlationLTF, 'MinPeakHeight', max(correlationLTF) * sensitivity, 'MinPeakDistance', length(ltfSequence));
%     [~, locsSTF] = findpeaks(correlationSTF, 'MinPeakHeight', max(correlationSTF) * sensitivity, 'MinPeakDistance', length(stfSequence));
%     
%     tLTF = lagLTF(locsLTF);
%     tSTF = lagSTF(locsSTF);
% 
%     % STF (16 * 10) + LTF (32 + 64 + 64) = 320 IQ samples
%     preamble = X(tSTF : tSTF + 320 - 1);
end