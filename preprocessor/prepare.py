import os
import numpy as np
import re
import h5py
import json
from collections import defaultdict
import boto3
from tqdm import tqdm
import matlab.engine
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client('s3')

ROOT_DIR = '/home/smazokha2016/Desktop'
# ROOT_DIR = '/Users/stepanmazokha/Desktop'

MATLAB_OFDM_DECODER = ROOT_DIR + '/mobintel-rffi/preprocessor/frame_mac_detection'
TEMP_IQ_DIRECTORY = ROOT_DIR + '/orbit_processor_temp/'
NODE_MACS = 'experiment_device_macs.json'
S3_BUCKET_NAME = "mobintel-orbit-dataset"
S3_EXPERIMENT_NAME = "orbit_experiment_jul_19"
S3_EPOCH_PREFIX = "epoch_"
S3_TRAINING_PREFIX = "training_"
RFFI_DATASET_TARGET_DIR = f'{ROOT_DIR}/{S3_BUCKET_NAME}_h5/'
FRAME_COUNT = 400

# Extracts signal configs from a file name in a dataset
# - filename: name of the .dat file (without the route)
def parse_dat_name(filename):
    # Extract node_tx
    node_tx_match = re.search(r'tx\{node_(.*?)\}', filename)
    node_tx = node_tx_match.group(1) if node_tx_match else None

    # Extract node_rx
    node_rx_match = re.search(r'rx\{node_(.*?)[\+\}]', filename)
    node_rx = node_rx_match.group(1) if node_rx_match else None

    # Extract samp_rate
    samp_rate_match = re.search(r'rxSampRate_(\d+e\d+)', filename)
    samp_rate = int(float(samp_rate_match.group(1))) if samp_rate_match else None

    return {
        "node_tx": node_tx,
        "node_rx": node_rx,
        "samp_rate": samp_rate
    }

# Reads a JSON file containing MAC addresses of devices
def get_device_macs(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)

    return data

class TqdmCallback:
    def __init__(self, total_size):
        self.progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading', bar_format='{desc}: {percentage:3.0f}% |{bar}| {n_fmt}/{total_fmt} [{elapsed}/{remaining}]', ascii=' █')

    def __call__(self, bytes_amount):
        self.progress_bar.update(bytes_amount)

def download_file_with_progress(bucket_name, s3_key, local_path):
    s3 = boto3.client('s3')

    # Get the total size of the object
    response = s3.head_object(Bucket=bucket_name, Key=s3_key)
    total_size = response['ContentLength']

    # Ensure the local directory exists
    local_dir = os.path.dirname(local_path)
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    # Start the download and show the progress
    callback = TqdmCallback(total_size)
    s3.download_file(bucket_name, s3_key, local_path, Callback=callback)
    callback.progress_bar.close()

def s3_list_subdirs(bucket_name, prefix):
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
    
    subdirs = []
    for path in response['CommonPrefixes']:
        subdirs.append(os.path.basename(os.path.normpath(path['Prefix'])))
    return subdirs

def s3_list_files(bucket_name, prefix):
    # Initialize the paginator
    paginator = s3.get_paginator('list_objects_v2')

    # Create a PageIterator from the Paginator
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    # List to store all file keys
    filenames = []

    # Iterate through each page
    for page in page_iterator:
        if 'Contents' in page:
            for obj in page['Contents']:
                filename = os.path.basename(os.path.normpath(obj['Key']))
                if filename[-4:] == '.dat':
                    filenames.append(filename)

    return filenames

# Create a dictionary which contains IDs (1--400) and (X-Y) of all sensors physically present
# in the Orbit testbed facility. This is later used to produce unique labels for the sensor 
# fingerprinting model.
def generate_node_ids():
    ids = {}
    node_i = 0
    for i in np.arange(1, 21):
        for j in np.arange(1, 21):
            ids[str(i) + "-" + str(j)] = node_i
            node_i = node_i + 1
    return ids

# Save an h5 dataset file containing labels & data for a given set of devices
def save_dataset_h5(file_target, label, data):
    print('Saving', file_target)
    with h5py.File(file_target, 'w') as h5file:
        h5file.create_dataset('label', data=label, dtype='float64')
        h5file.create_dataset('data', data=data, dtype='float64')  

# Package & store epoch infromation in h5 file (ready for RFFI)
def epoch_save(node_ids_dict, target_dir, epoch_preambles, session_name, preamble_len):
    for rx_name in epoch_preambles.keys():
        rx_epochs = epoch_preambles[rx_name]

        # Data shape: (epochs x frames, samples x 2)
        # All frames/samples from all emitters are stitched together
        h5_data = np.zeros((len(rx_epochs) * FRAME_COUNT, preamble_len * 2), dtype='float64')
        # Labels shape: (epochs x frames, 1)
        h5_labels = np.zeros((len(rx_epochs) * FRAME_COUNT, 1), dtype='float64')

        h5_idx = 0
        for rx_epoch in rx_epochs:
            preambles = rx_epoch['preambles']
            tx_node_name = rx_epoch['node_tx']
            for preamble_i in np.arange(0, preambles.shape[0]):
                h5_data[h5_idx, 0::2] = np.real(preambles[preamble_i, :])
                h5_data[h5_idx, 1::2] = np.imag(preambles[preamble_i, :])

                h5_labels[h5_idx] = node_ids_dict[tx_node_name]

                h5_idx = h5_idx + 1

        dataset_filepath = os.path.join(target_dir, f'node{rx_name}_{session_name}.h5')
        save_dataset_h5(dataset_filepath, h5_labels, h5_data)

def is_session_valid(session_name):
    return session_name[0:6] == 'epoch_' or session_name[0:9] == 'training_'

def request_preamble_len():
    try:
        return int(input("What should be preamble length? [400] "))
    except:
        return 400

def main():
    preamble_len = request_preamble_len()

    # Check if a directory to store final dataset exists and create if not
    if not os.path.exists(RFFI_DATASET_TARGET_DIR):
        os.makedirs(RFFI_DATASET_TARGET_DIR)

    # Set up the MATLAB environment before starting
    matlab_engine_name = input('Matlab engine name to connect to [mobintel_engine]: ')
    if len(matlab_engine_name) == 0: matlab_engine_name = 'mobintel_engine'
    mateng = matlab.engine.connect_matlab(matlab_engine_name)
    mateng.cd(MATLAB_OFDM_DECODER, nargout=0)

    # Load a JSON file with device MAC addresses from S3 experiment folder
    device_macs_local_path = os.path.join(RFFI_DATASET_TARGET_DIR, NODE_MACS)
    download_file_with_progress(S3_BUCKET_NAME, f"{S3_EXPERIMENT_NAME}/{NODE_MACS}", device_macs_local_path)
    device_macs = get_device_macs(device_macs_local_path)

    # Generate a dictionary of node IDs
    node_ids = generate_node_ids()

    # Obtain a list of epochs in the experiment
    sessions = s3_list_subdirs(S3_BUCKET_NAME, S3_EXPERIMENT_NAME + '/')

    # Process each session (aka epoch)
    for session_name in sessions:
        if not is_session_valid(session_name):
            print("Skipping session", session_name)
            continue

        print("Processing session ", session_name)
        session_dat_files = s3_list_files(S3_BUCKET_NAME, S3_EXPERIMENT_NAME + "/" + session_name + "/")

        # Prepare a dictionary to store preambles for this epoch
        epoch_preambles = defaultdict(list)
        rx_nodes = set()

        # 3. Process each .dat file
        for dat_file in session_dat_files:
            print(f"- {dat_file}")

            # 3.1. Download the file from S3
            s3_filepath = f"{S3_EXPERIMENT_NAME}/{session_name}/{dat_file}"
            local_filepath = os.path.join(TEMP_IQ_DIRECTORY, dat_file)
            print(f'Downloading {dat_file}...')
            download_file_with_progress(S3_BUCKET_NAME, s3_filepath, local_filepath)

            # 3.2. Extract signal info from its name
            dat_config = parse_dat_name(dat_file)
            tx_name = dat_config['node_tx'][4:]
            rx_name = dat_config['node_rx'][4:]
            samp_rate = dat_config['samp_rate']

            rx_nodes.add(rx_name)

            # 3.3. Retrieve node MAC address
            tx_mac = device_macs[tx_name]['mac']

            # 3.2. Decode the file via MATLAB script, extract preambles
            response = mateng.find_tx_frames(local_filepath, 'CBW20', samp_rate, tx_mac, preamble_len)
            # preamble_bounds = np.array(response['preamble_bounds']).squeeze()
            preamble_iq = np.array(response['preamble_iq']).squeeze()

            if preamble_iq.shape[0] < FRAME_COUNT:
                print(f"Insufficient frames captured: {dat_file}")
                continue
            else:
                # 3.3. Store information from a current dat file
                epoch_preambles[rx_name].append({
                    'preambles': preamble_iq[0:FRAME_COUNT, :],
                    'node_tx': tx_name,
                    'node_rx': rx_name,
                    'node_mac': tx_mac
                })

            # 3.4. Remove local file afer the processing is completed
            print(f"Deleting local file {local_filepath}")
            os.remove(local_filepath)

        epoch_save(node_ids, RFFI_DATASET_TARGET_DIR, epoch_preambles, session_name, preamble_len)

if __name__ == "__main__":
    main()