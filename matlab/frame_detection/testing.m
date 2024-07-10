close all; clear; clc;

% input_dir = '/Users/stepanmazokha/Desktop/wisig_raw_rffi_dataset/node1-1_wifi_2021_03_08/';
% output_dir = '/Users/stepanmazokha/Desktop/wisig_frames_rffi_dataset/node1-1_wifi_2021_03_08/';
% 
% main_detect_frames('node1-1', input_dir, output_dir);

plot_iq('1interval-005_gain-05');
plot_iq('2interval-005_gain-15');
plot_iq('3interval-05_gain-15');

function[] = plot_iq(epoch)
    path = '/Users/stepanmazokha/Desktop/debug/';
    file = '/samples.dat';
    fullpath = [path epoch file];
    x = read_complex_binary(fullpath);
    
    t = (1:length(x))';
    
    figure;
    plot(t, x);
    title(epoch);
end