% This function performs detection of OFDM frames from raw IQ traffic and
% saves them in another given directory. Each resulting file corresponds to
% a single transmitter, and contains IQ samples for a single frame preamble
% (400 samples long, with 25 Msps - would be 320 samples w 20 Msps) in both
% equalized and non-equalized forms.
%
% Input directory must contain .dat files for a single receiver (expect
% naming like:
% tx{node/node14-9}_rx{node/node1-1-rxFreq/2462e6-rxGain/0.5-capLen/0.512-rxSampRate/25e6}
%
% Output directory must exist and should be empty.
function [] = main_detect_frames(node_name, input_dir, output_dir)
    fileList = dir([input_dir, '/*.dat']);

    for fi = 1:length(fileList)
        transmitter=regexp(fileList(fi).name, ['\d+-\d+(?=:*}_rx{node:' , node_name, '-rxFreq:2462e6-rxGain:0\.5-capLen:0\.512-rxSampRate:25e6}\.dat)'], 'match');
    
        transmitter=transmitter{1};
    
        fprintf('Processing %d of %d: node%s\n',fi,length(fileList),transmitter);
    
        packet_log = {};
        packet_log_filename = strcat('packets_', transmitter, '.mat');
    
        x = read_complex_binary([input_dir, fileList(fi).name]);

        % Optionally, demonstrate STF / LTF sequence starts
        % show_stf_ltf(x, 800000, 0.8)

        en=find_beg(x,1);
    
        final = length(x)-find_beg(flip(x),1);
    
        x_r = real(x);  
        xx=x_r;
    
        energies=[];
        maxs=[];
        endpoints=[];
        lengths=[];
    
        filter = zeros(length(x), 1);

        tt=0;

        while en<final
            tt = tt +1;
            [st,en]=split(x,en);
            if en>=final || en==-1 || st==-1
                break;
            end
            y=x_r(st:en);

            [s,f]=myVAD(y, 0.0000001, 0.0000001);
    
            lengths(end+1)=f-s+1;
            [energies(end+1), maxs(end+1)] = signal_energy(y(s:f));
    
            s=s+st;
            f=f+st;

            endpoints(end+1) = complex(s,f);
        end

        if ~exist([output_dir, 'statistics/'], 'dir')
           mkdir([output_dir, 'statistics/']);
        end
        save([output_dir, 'statistics/', transmitter], 'endpoints','lengths','energies','maxs');

        sd=std(lengths);
        zs=(lengths-mean(lengths))./sd;
    
        num=1;
    
        for pi=1:length(energies)
            
            endpoint=endpoints(pi);
            s=real(endpoint);
            f=imag(endpoint);
            xx(s:f)=0;
            if pi < length(energies) && abs(zs(pi)) < 5 && maxs(pi) < 0.5 && energies(pi) < 0.25 && energies(pi) > 0.001 && pair_length(endpoints(pi)) >= 1000  && pair_length(endpoints(pi+1)) <= 2000 % && energies(i+1) > 0.4
                xx(s:f)=0;
                filter(s:f)=1;
    
                packet_log{end+1}=x(s:f);
                num=num+1;
    
            end
    
            if pi == length(energies) && abs(zs(pi)) < 5 && maxs(pi) < 0.5 && energies(pi) < 0.25 && energies(pi) > 0.001 && (f-s >= 1000)
                xx(s:f)=0;
                filter(s:f)=1;
    
                packet_log{end+1}=x(s:f);       
                num=num+1;
    
            end
        end
       
        if ~exist([output_dir, 'packets/'], 'dir')
            mkdir([output_dir, 'packets/']);
        end
        save([output_dir, 'packets/', packet_log_filename], 'packet_log');
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% This function can be used to show the starting indexes for the STF and
% LTF sequences in the raw signal.
%
% Suggested values:
% x_len: 800000
% sensitivity: 0.8 (the lower the bar - the more you'll find)
function [] = show_stf_ltf(X, x_len, sensitivity)
    X = X(1:x_len);
    
    % Create a configuration object for an 802.11n packet
    cfgHT = wlanNonHTConfig;
    
    % Generate the reference LTF sequence
    % The function wlanLLTF generates the L-LTF time domain signal for 802.11n
    ltfSequence = wlanLLTF(cfgHT);
    stfSequence = wlanLSTF(cfgHT);
    
    % Perform correlation
    [correlationLTF, lagLTF] = xcorr(X, ltfSequence);
    [correlationSTF, lagSTF] = xcorr(X, stfSequence);
    
    correlationLTF = abs(correlationLTF);
    correlationSTF = abs(correlationSTF);
    
    % Find peaks in the correlation
    [~, locsLTF] = findpeaks(correlationLTF, 'MinPeakHeight', max(correlationLTF) * sensitivity, 'MinPeakDistance', length(ltfSequence));
    [~, locsSTF] = findpeaks(correlationSTF, 'MinPeakHeight', max(correlationSTF) * sensitivity, 'MinPeakDistance', length(stfSequence));
    
    startIndicesLTF = lagLTF(locsLTF);
    startIndicesSTF = lagSTF(locsSTF);
    
    % Optional: Plot the IQ samples and mark the LTF start points
    figure;
    plot(1:length(X), real(X));
    hold on;
    plot(startIndicesLTF, zeros(size(startIndicesLTF, 1)), 'r.');
    plot(startIndicesSTF, zeros(size(startIndicesSTF, 1)), 'g.');
    title('IQ Samples with LTF Start Points');
    xlabel('Sample Index');
    ylabel('Amplitude');
    grid on;
    hold off;
    disp('');
end