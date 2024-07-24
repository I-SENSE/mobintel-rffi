% This source code is a slightly refactored and simplified
% version of the 802.11 waveform recovery & analysis demo:
% Ref: https://www.mathworks.com/help/wlan/ug/recover-and-analyze-packets-in-802-11-waveform.html

close all; clear; clc;

% TX_NODE = '00:60:b3:ac:a1:cb';
% TX_NODE = '00:60:b3:25:c0:2f';
TX_NODE = '00:60:b3:ac:a1:cb';

% X_path = '/Users/stepanmazokha/Desktop/node19-19_25msps.dat';
X_path = '/Users/stepanmazokha/Desktop/orbit_processor_temp/tx{node_node1-10}_rx{node_node1-1+rxFreq_2462e6+rxGain_10+capLen_10+rxSampRate_20e6}.dat';

T = find_tx_frames(X_path, 'CBW20', 20e6, TX_NODE, 400);

fprintf('Captured UDP frames: %i', length(T.('preamble_bounds')));

plot_recognized_frames(X, T.('preamble_bounds'));