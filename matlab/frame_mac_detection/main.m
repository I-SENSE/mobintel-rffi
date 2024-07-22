% This source code is a slightly refactored and simplified
% version of the 802.11 waveform recovery & analysis demo:
% Ref: https://www.mathworks.com/help/wlan/ug/recover-and-analyze-packets-in-802-11-waveform.html

close all; clear; clc;

% TX_NODE_1_10 = '00:60:b3:ac:a1:cb';
TX_NODE_1_11 = '00:60:b3:25:c0:2f';

X = read_iq('/Users/stepanmazokha/Desktop/node19-19_25msps.dat');

[preamble_bounds, preamble_iq] = find_tx_frames(X, 'CBW20', 25e6, TX_NODE_1_11, 400);

fprintf('Captured UDP frames: %i', length(preamble_bounds));

plot_recognized_frames(X, preamble_bounds);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function [preamble_bounds, preamble_iq] = find_tx_frames(X, bw, samp_rate, search_mac_tx, preamble_len)
    % 1. Analyze the waveform
    analyzer = WaveformAnalyzer();
    process(analyzer, X, bw, samp_rate);
    
    % 2. Extract MAC info for a given frame
    preamble_bounds = {};
    preamble_iq = {};
    
    fprintf('Searching for %s\n', search_mac_tx);
    printout_counter = 0;
    for mac_i = 1:size(analyzer.Results, 2)
        mac_summary = macSummary(analyzer, mac_i, false);
        if isempty(mac_summary)
            continue;
        end
    
        % frame_rx_mac = parseMacAddress(mac_summary{1, 1}); % MAC address of the AP
        frame_tx_mac = parseMacAddress(mac_summary{1, 2}); % MAC address of the emitter
    
        % Filter frames based on the TX MAC address
        if strcmp(frame_tx_mac, search_mac_tx)
            fprintf('.');
            printout_counter = printout_counter + 1;
            if printout_counter == 40
                printout_counter = 0;
                fprintf('\n');
            end
    
            % Extract start & end indexes for the frame preamble
            x = analyzer.Results{mac_i};
    
            preamble_start = x.PacketOffset;
            preamble_end = preamble_start + preamble_len - 1;

            % If you need a full frame:
            % frame_end = frame_start + x.NumRxSamples;
    
            preamble_bounds{end+1} = [preamble_start, preamble_end];
            preamble_iq{end+1} = X(preamble_start:preamble_end);
        end
    end
    fprintf('\n');
end

function [] = plot_recognized_frames(X, frame_bounds)
    figure;
    hold on;
    plot(real(X), 'black');
    for i = 1:length(frame_bounds)
        bounds = frame_bounds{i};

        frame_start = bounds(1);
        frame_end = bounds(2);
    
        plot(frame_start:frame_end, real(X(frame_start:frame_end)), 'green');
    end
    hold off;
end

function [X] = read_iq(filename, count)
    m = nargchk (1,2,nargin);
    if (m)
        usage(m);
    end
    
    if (nargin < 2)
        count = Inf;
    end
    
    f = fopen (filename, 'rb');
    if (f < 0)
        X = 0;
    else
        t = fread(f, [2, count], 'float');
        fclose (f);
        X = t(1,:) + t(2,:) * i;
        [r, c] = size(X);
        X = reshape(X, c, r);
    end
end

function [formattedMac] = parseMacAddress(mac)
    macAddress = sprintf('%s', mac);

    % Validate the input
    if strlength(macAddress) ~= 12
        formattedMac = macAddress;
        return;
    end
    
    % Convert to lowercase
    macAddress = lower(macAddress);
    
    % Insert colons to separate octets
    formattedMac = sprintf('%s:%s:%s:%s:%s:%s', ...
        macAddress(1:2), macAddress(3:4), macAddress(5:6), ...
        macAddress(7:8), macAddress(9:10), macAddress(11:12));
end