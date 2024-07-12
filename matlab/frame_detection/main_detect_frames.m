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
        transmitter = node_name(5:end);
    
        fprintf('Processing %d of %d: node%s\n', fi, length(fileList), transmitter);
    
        x = read_complex_binary([input_dir, fileList(fi).name]);

        % TODO: remove (this makes debugging a little faster)
        x = x(1:floor(length(x) / 5));

        % Identify all frames in the signal, as well as accompanied attributes
        energies=[]; % average energy for each frame
        maxs=[]; % absolute max value of real (or imag) samples for each frame
        endpoints=[]; % frame start & end indexes
        lengths=[]; % how many samples each frame takes

        % Find the first significant event in the signal
        en = find_beginning(x, 1);
        frame_count = 0;
        while en < length(x)
            % Identify next frame (using a threshold, set inside the fun)
            % Note: modify internal threshold if it doesn't work
            [st, en] = split(x, en);
            if en >= length(x) || en == -1 || st == -1
                break;
            end

            % Extract frame amplitudes of the identified frame
            y = real(x(st:en));

            % Use VAD to trim out unnecessary sections of the frame
            [s, f] = myVAD(y);
    
            % Calculate length of the frame
            lengths(end + 1) = f - s + 1;
            
            % Calculate average energy & absolute max value of the frame
            [energies(end + 1), maxs(end + 1)] = signal_energy(y(s:f));

            % Calculate start & end indexes of the resulting frame
            endpoints(end + 1) = complex(s + st, f + st);

            frame_count = frame_count + 1;
        end

        % Normalize frame lengths
        lengths = abs((lengths-mean(lengths))./std(lengths));
    
        figure;
        hold on;
        plot(1:length(x), real(x), 'black');

        % Analyze & filter out all identified frames
        packet_log = {};
        for frame_idx = 1:frame_count
            % Extract frame coordinates
            s = real(endpoints(frame_idx));
            f = imag(endpoints(frame_idx));

            disp('Max:    ' + string(maxs(frame_idx)));
            disp('Energy: ' + string(energies(frame_idx)));
            disp('Length: ' + string(lengths(frame_idx)))
            disp('Pair l: ' + string(pair_length(endpoints(frame_idx))));
            disp('Pair r: ' + string(pair_length(endpoints(frame_idx))));
            disp('-----------------------');

            max = maxs(frame_idx);
            energy = energies(frame_idx);
            len = lengths(frame_idx);
            pair = pair_length(endpoints(frame_idx));

            % Note: modify these thresholds if the filtering doesn't work
            check_maxs = max <= 0.02;
            check_energies = 0.002 <= energy;
            check_lenghts = 0.01 <= len && len <= 5;
            check_pair = 2000 <= pair;

            if check_lenghts && check_maxs && check_energies && check_pair
                packet_log{end+1}=x(s:f);
                plot(s:f, real(x(s:f)), 'green');
            else
                plot(s:f, real(x(s:f)), 'blue');
            end
        end

        hold off;
       
        if ~exist([output_dir, 'packets/'], 'dir')
            mkdir([output_dir, 'packets/']);
        end
        save([output_dir, 'packets/', 'packets_', transmitter, '.mat'], 'packet_log');
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Calculates difference between imaginary and real parts of a value
function p = pair_length(value)
    p = imag(value) - real(value);
end

% Locates beginning of a significant event in IQ signal, beginning with a
% start index. 
function [e] = find_beginning(signal, start)
    x = signal(start:end);
    
    threshold = 0.005;
    n = 100;
    
    i = start;
    j = i + n;
    while i <= length(x)
        count = 0;
        while i <= j && i <= length(x)
            if real(x(i)) < threshold && imag(x(i)) < threshold
                count = count + 1;
            end
            i = i + 1;
        end
        if n <= count
            e = max((j + j - n)/2, 0);
            break;
        end
        j=j+n;
    end
    
    e = e + start;
end

% Estimates energy of a given series of IQ samples
% - s: average energy of the given signal
% - m: maximum absolute value of real (or imag) parts of the signal
function [s, m] = signal_energy(signal)
    s = 0;
    m = -1;
    
    for i = 1:length(signal)
       m = max(m, abs(real(signal(i))));
       m = max(m, abs(imag(signal(i))));
       s = s + abs(signal(i));
    end
    
    s = s / length(signal);
end

% This function aims to identify two points in a given signal:
% - s: position where the signal first exceeds a threshold
% - e: ending point where signal drops below the threshold for a certain
% number of consecutive samples
function [s, e] = split(signal, start)
    x = signal;
    
    threshold = 0.001; % threshold for real & imaginary parts
    n = 100; % segment length
    
    i = start + 1;
    j = i + n;

    % Find the first segment where the signal exceeds the threshold
    s = -1; % initialize start index
    while i <= length(x)
        yn = 0; % flag to indicate threshold crossing
        while i <= j && i <= length(x)
            if real(x(i)) > threshold || imag(x(i)) > threshold
                s = (i + i - n) / 2;
                yn = 1;
                break;
            end
            i = i + 1;
        end

        % Did we cross the threshold? Let's stop searching
        if yn == 1
            break;
        end
        j = j + n;
    end 
    
    j = i + n; % Reset j for the second loop
    
    e = -1; % Initialize the end index
    
    % Finds the first segment after the start index where the signal falls 
    % below the threshold for n consecutive samples
    while i <= length(x)
        count = 0; % counter for samples below threshold
        while i<=j && i<=length(x)
            if real(x(i)) < threshold && imag(x(i)) < threshold
                count = count + 1;
            end
            i=i+1;
        end
        if count >= n
            e = (j + j - n) / 2; % set end index
            break;
        end
        j = j + n;
    end
end