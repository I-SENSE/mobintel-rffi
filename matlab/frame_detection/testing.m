clear; clc;

input_dir = '/Users/stepanmazokha/Desktop/wisig_raw_rffi_dataset/node1-1_wifi_2021_03_08/';
output_dir = '/Users/stepanmazokha/Desktop/wisig_frames_rffi_dataset/node1-1_wifi_2021_03_08/';

main_detect_frames('node1-1', input_dir, output_dir);

% path = '/Users/stepanmazokha/Downloads/received_samples.dat';
% x = read_complex_binary(path);
% 
% t = 1:12800000;
% 
% figure;
% plot(t, x(t));