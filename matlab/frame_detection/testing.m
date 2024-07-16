close all; clear; clc;

% DIR_IN = '/Users/stepanmazokha/Desktop/orbit_dataset_1rx/our_raw_rffi_dataset/';
% DIR_OUT = '/Users/stepanmazokha/Desktop/orbit_dataset_1rx/orbit_frames_rffi_dataset/';

% filename_silent = '/Users/stepanmazokha/Desktop/orbit_dataset_1rx/our_raw_rffi_dataset/training_tx{node_empty_channel}_rx{node_node1-1+rxFreq_2462e6+rxGain_10+capLen_2+rxSampRate_25e6}.dat';
% 
% dir_list = dir(DIR_IN);
% for idx = 3:length(dir_list)
%     if dir_list(idx).isdir
%         dir_name = dir_list(idx).name;
%         full_dir_in = [DIR_IN, dir_name, '/'];
%         full_dir_out = [DIR_OUT, dir_name, '/'];
%         disp(dir_name);
% 
%         main_detect_frames('node1-1', filename_silent, full_dir_in, full_dir_out);
%     end
% end

% main_detect_frames('node1-1', filename_silent, [DIR_IN 'training_2024-07-13_06-53-20/'], [DIR_OUT 'training_2024-07-13_06-53-20/'])
% main_detect_frames('node1-1', filename_silent, [DIR_IN 'epoch_2024-07-13_07-40-21/'], [DIR_OUT 'epoch_2024-07-13_07-40-21/'])

DIR_IN = '/Users/stepanmazokha/Desktop/orbit_dataset/';

% plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-16_05-34-07', 'udp-2sec'));
% plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-16_05-53-51', 'silent-5sec'));
plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-16_05-56-20', 'probes'));
plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-16_06-07-02', 'probes'));
plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-16_06-11-47', 'silent'));
plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-16_06-19-38', 'probes'));

% plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-13_08-38-59', 'tx{node_node20-15}_rx{node_node1-1+rxFreq_2462e6+rxGain_10+capLen_2+rxSampRate_25e6}'));
% plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-13_08-51-04', 'tx{node_node20-19}_rx{node_node1-1+rxFreq_2462e6+rxGain_10+capLen_2+rxSampRate_25e6}'));
% plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-13_09-02-07', 'tx{node_node16-16}_rx{node_node1-1+rxFreq_2462e6+rxGain_10+capLen_2+rxSampRate_25e6}'));
% plot_iq(get_file_path(DIR_IN, 'epoch_2024-07-13_09-31-48', 'tx{node_node12-20}_rx{node_node1-1+rxFreq_2462e6+rxGain_10+capLen_2+rxSampRate_25e6}'));

function[] = plot_iq(fullpath)
    x = read_complex_binary(fullpath);

    x = x(1:floor(length(x)));
    
    t = (1:floor(length(x)));
    
    figure;
    plot(t, x(t));
%     ylim([-0.05, 0.05]);
end

function[fullpath] = get_file_path(dir_in, epoch, file)
    fullpath = [dir_in epoch '/' file '.dat'];
end