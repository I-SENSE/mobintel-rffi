close all; clear; clc;

DIR_IN = '/Users/stepanmazokha/Desktop/our_raw_rffi_dataset/';
DIR_OUT = '/Users/stepanmazokha/Desktop/orbit_frames_rffi_dataset/epoch_2024-07-11_14-12-23/';

file1_in = get_file_path(DIR_IN, 'test1', 'samples');
file2_in = get_file_path(DIR_IN, 'test2', 'samples');
file3_in = get_file_path(DIR_IN, 'test3', 'samples');
file4_in = get_file_path(DIR_IN, 'test4', 'samples');

file_out = DIR_OUT;

% WiSig Data
% main_detect_frames('node1-1', [DIR_IN 'node1-1_wifi_2021_03_01/'], file_out); 

% Our Data: Silent
% main_detect_frames('node1-1', [DIR_IN 'epoch_2024-07-11_14-14-01/'], file_out);

% Out Data: With Signal
% main_detect_frames('node1-1', [DIR_IN 'epoch_2024-07-11_14-12-23/'], file_out);

% main_detect_frames('node1-1', [DIR_IN 'epoch_3/'], file_out);

plot_iq(file1_in);
plot_iq(file2_in);
plot_iq(file3_in);
plot_iq(file4_in);

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