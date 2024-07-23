% input_dir = '/Users/stepanmazokha/Desktop/wisig_frames_rffi_dataset/node1-1_wifi_2021_03_08/';
% output_dir = '/Users/stepanmazokha/Desktop/wisig_frames_rffi_dataset/node1-1_wifi_2021_03_08/';
% 
% main_equalize_frames(input_dir, output_dir, 500);

DIR_IN = '/Users/stepanmazokha/Desktop/orbit_frames_rffi_dataset/';
DIR_OUT = '/Users/stepanmazokha/Desktop/orbit_frames_rffi_dataset/';

% input_dir = '/Users/stepanmazokha/Desktop/orbit_frames_rffi_dataset/epoch_2024-07-11_14-12-23/';
% output_dir = '/Users/stepanmazokha/Desktop/orbit_frames_rffi_dataset/epoch_2024-07-11_14-12-23/';

% main_equalize_frames(input_dir, output_dir, 100);

dir_list = dir(DIR_IN);
for idx = 3:length(dir_list)
    if dir_list(idx).isdir
        dir_name = dir_list(idx).name;
        full_dir_in = [DIR_IN, dir_name, '/'];
        full_dir_out = [DIR_OUT, dir_name, '/'];
        disp(dir_name);

        main_equalize_frames(full_dir_in, full_dir_out, 400);
    end
end