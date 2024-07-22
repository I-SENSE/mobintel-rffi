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
function [] = main_detect_frames(rx_node_id, filepath_silent, dir_signal, dir_output)
    X_silent = read_complex_binary(filepath_silent);

    % Identify all .dat files & process each one of them
    file_list = dir([dir_signal, '/*.dat']);
    for fi = 1:length(file_list)
        filename = file_list(fi).name;
        pattern = 'tx\{node_(.*?)\}_rx';
        matches = regexp(filename, pattern, 'tokens');

        if ~isempty(matches)
            transmitter = matches{1}{1};
        else
            transmitter = rx_node_id(10:end);
        end
        
        fprintf('Processing %d of %d: %s\n', fi, length(file_list), transmitter);

        X_signal = read_complex_binary([dir_signal, filename]);

        packet_log = process_file(X_silent, X_signal, num2str(fi));

        if ~exist([dir_output, 'packets/'], 'dir')
            mkdir([dir_output, 'packets/']);
        end
        save([dir_output, 'packets/', 'packets_', transmitter, '.mat'], 'packet_log');
    end
end

function [frame_log] = process_file(X_silent, X_signal, transmitter)
    rng(123);

    % Find frames in both silent & signal samples
    [endpoints_silent, features_silent] = find_frames(X_silent);
    [endpoints_signal, features_signal] = find_frames(X_signal);

    % Cluster frames in silent samples, identify frames we need to drop (i.e., alien frames)
    silent_cluster_count = 5;
    [labels_silent, centroids_silent] = kmeans(features_silent, silent_cluster_count, 'Replicates', 5);
%     plot_labeled_frames(real(X_silent), endpoints_silent, labels_silent, lines(silent_cluster_count), "Silent IQ Clusters");

    thresholds = [1000, 0.1, 0.5, 1000, 1000];
%     allowed_centroids = [2, 3];
    allowed_centroids = [3];
    alien_label = 2;

    is_frame_alien = find_alien_frames(features_signal, centroids_silent, thresholds, allowed_centroids, alien_label);
%     plot_labeled_frames(real(X_signal), endpoints_signal, is_frame_alien, lines(2), label);
    
    % Update the lists of signal endpoints & features, drop alien frames
    endpoints_signal = endpoints_signal(:, is_frame_alien == 1);
    features_signal = features_signal(is_frame_alien == 1, :);
%     plot_labeled_frames(real(X_signal), endpoints_signal, ones(size(endpoints_signal, 2), 1), lines(1), label);

    % Run k-means on the remaining frames and see which ones we can keep
    rng(123);
    remaining_k = 10;
    remaining_colors = lines(remaining_k);
    [labels_filtered, ~] = kmeans(features_signal, remaining_k, 'Replicates', 5);

    % Count the number of frames in each cluster
    cluster_counts = histcounts(labels_filtered, remaining_k);
    [sorted_counts, sorted_indices] = sort(cluster_counts, 'descend');

    sorted_counts = sorted_counts(1:6);
    sorted_indices = sorted_indices(1:6);

%     plot_labeled_frames(real(X_signal), endpoints_signal, labels_filtered, remaining_colors, label);

%     screenSize = get(0, 'ScreenSize');
%     width = screenSize(3);  % Full width of the screen
%     height = screenSize(4) / 4;  % 1/4th height of the screen
%     figure('Position', [1, 1, width, height]);
%     
%     hold on;
%     plot(1:length(X_signal), real(X_signal), 'black');
%     h = gobjects(remaining_k, 1);
%     for i = 1:length(endpoints_signal)
%         s = real(endpoints_signal(i));
%         f = imag(endpoints_signal(i));
% 
%         label = labels_filtered(i);
% 
%         if ismember(label, sorted_indices)
%     %         plot(s:f, real(X(s:f)), 'Color', colors(label, :));
%             h(label) = plot(s:f, real(X_signal(s:f)), 'Color', remaining_colors(label, :), 'LineWidth', 2);
%         end
%     end
%     hold off;
%     title(label);

%     legend(h, [arrayfun(@(x) ['Cluster ' num2str(sorted_indices(x)) ' -- ' num2str(sorted_counts(x))], 1:remaining_k, 'UniformOutput', false), 'Silent Mode'], 'LineWidth', 2);
    
    frame_log = {};

%     screenSize = get(0, 'ScreenSize');
%     width = screenSize(3);  % Full width of the screen
%     height = screenSize(4) / 4;  % 1/4th height of the screen
%     figure('Position', [1, 1, width, height]);
%     hold on;
%     plot(1:length(X_signal), real(X_signal), 'black');

    for i = 1:length(endpoints_signal)
        s = real(endpoints_signal(i));
        f = imag(endpoints_signal(i));

        label = labels_filtered(i);

        if ismember(label, sorted_indices)
%             plot(s:f, real(X_signal(s:f)), 'blue');
            frame_log{end+1} = X_signal(s:f);
        end
    end
%     hold off;
%     title(label);

    disp(strcat("Transmitter: ", transmitter, ". Frames: ", num2str(sum(sorted_counts))));
%     drawnow;
end

function [] = plot_labeled_frames(X, endpoints, labels, colors, name)
    % Display the cluster labels for each frame
    screenSize = get(0, 'ScreenSize');
    width = screenSize(3);  % Full width of the screen
    height = screenSize(4) / 4;  % 1/4th height of the screen
    figure('Position', [1, 1, width, height]);
    
    hold on;
    plot(1:length(X), real(X), 'black');

    for i = 1:length(endpoints)
        s = real(endpoints(i));
        f = imag(endpoints(i));

        label = labels(i);

        plot(s:f, real(X(s:f)), 'Color', colors(label, :));
    end
    hold off;
    title(name);
end

function [is_frame_alien] = find_alien_frames(features_signal, centroids, thresholds, allowed_centroids, alien_label)
    is_frame_alien = ones(size(features_signal, 1), 1);

    for centroid_idx = allowed_centroids
        centroid = centroids(centroid_idx);
        threshold = thresholds(centroid_idx);

        distances = zeros(size(features_signal, 1), 1);
        for frame_idx = 1:size(features_signal, 1)
            distances(frame_idx) = norm(features_signal(frame_idx, 1) - centroid);
            if distances(frame_idx) <= threshold
                is_frame_alien(frame_idx) = alien_label;
            end
        end
    
%         figure;
%         scatter(1:length(distances), distances);
%         title("Centroid distances");
    end
end

function [endpoints, features] = find_frames(x)
    % Identify all frames in the signal, as well as accompanied attributes
    % - energies: average energy for each frame
    % - maxs: absolute max value of real (or imag) samples for each frame
    % - endpoints: % frame start & end indexes
    % - lengths: how many samples each frame takes
    % - pairs
    energies = [];
    maxs = [];
    endpoints = [];
    lengths = [];
    pairs = [];

    % Find the first significant event in the signal
    en = find_beginning(x, 1);
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

        pairs(end + 1) = pair_length(complex(s + st, f + st));
    end

    % Normalize frame lengths
%     lengths_a = abs((lengths-mean(lengths))./std(lengths));

    features = [maxs; energies; lengths; pairs]';
%     features = [maxs; energies; lengths]';

    features = normalize(features, 1, 'range', [0 1]);
end

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