% This source code is a slightly refactored and simplified
% version of the 802.11 waveform recovery & analysis demo:
% Ref: https://www.mathworks.com/help/wlan/ug/recover-and-analyze-packets-in-802-11-waveform.html

close all; clear; clc;

% TX_NODE_1_10 = '00:60:b3:ac:a1:cb';
TX_NODE_1_11 = '00:60:b3:25:c0:2f';

X_path = '/Users/stepanmazokha/Desktop/node19-19_25msps.dat';

T = find_tx_frames(X_path, 'CBW20', 25e6, TX_NODE_1_11, 400);

fprintf('Captured UDP frames: %i', length(preamble_bounds));

plot_recognized_frames(X, preamble_bounds);