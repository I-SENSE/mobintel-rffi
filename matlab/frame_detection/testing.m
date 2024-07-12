close all; clear; clc;

DIR_IN = '/Users/stepanmazokha/Desktop/debug/';
DIR_OUT = '/Users/stepanmazokha/Desktop/orbit_frames_rffi_dataset/epoch_2024-07-11_14-12-23/';

file1_in = get_file_path(DIR_IN, 'silent', 'samples');
file2_in = get_file_path(DIR_IN, 'udp', 'samples');
file3_in = get_file_path(DIR_IN, 'probes', 'samples');

file_out = DIR_OUT;

% WiSig Data
% main_detect_frames('node1-1', [DIR_IN 'node1-1_wifi_2021_03_01/'], file_out); 

% Our Data: Silent
% main_detect_frames('node1-1', [DIR_IN 'epoch_2024-07-11_14-14-01/'], file_out);

% Out Data: With Signal
% main_detect_frames('node1-1', [DIR_IN 'epoch_2024-07-11_14-12-23/'], file_out);

plot_iq(file1_in);
plot_iq(file2_in);
plot_iq(file3_in);

function[] = plot_iq(fullpath)
    x = read_complex_binary(fullpath);
    
    t = (1:floor(length(x)));
    
    figure;
    plot(t, x(t));
    ylim([-0.05, 0.05]);
end

function[fullpath] = get_file_path(dir_in, epoch, file)
    fullpath = [dir_in epoch '/' file '.dat'];
end