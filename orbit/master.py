# This is a master script. It performs a complete suite of tasks to configure nodes,
# transmit and receive samples, ans so forth. The objective of this script is to 
# perform the entire process of data capture completely automatically, without 
# any involvement of an operator.

import os
import tx_udp_master
import tx_probe_master
import rx_master
import threading
import queue
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

AP_NODE = "node2-5"
RX_NODES = ["node1-1", "node1-20", "node20-1", "node20-20"]
TX_TRAINING_NODES = ['node5-1', 'node7-10', 'node7-14', 'node2-19', 'node5-5', 'node19-1', 'node20-20', 'node1-10', 'node8-20', 'node11-17', 
                     'node2-6', 'node1-12', 'node4-1', 'node3-13', 'node1-16', 'node8-8', 'node8-18', 'node1-19', 'node1-18', 'node11-7', 
                     'node20-12', 'node4-10', 'node11-4', 'node8-3', 'node4-11', 'node3-18', 'node14-7', 'node10-17', 'node10-11']
TX_TESTING_NODES = ['node12-20', 'node17-11', 'node20-19', 'node20-1', 'node20-15', 'node14-10', 'node16-16', 'node15-1', 'node14-7', 'node16-1']

TX_INTERVAL = "0.01" # Interval (in seconds) between injected probe requests
TX_SSID = "smazokha" # Name of the SSID which we'll use in the probe requests (irrelevant)
TX_MAC = "11:22:33:44:55:66" # Spoofed MAC address we'll use in our probe requests
TX_CHANNEL = 11 # Channel ID on which we'll be sending our probes [1 -- 13]

CONFIG_BATCH_SIZE = 5
CAPTURE_DURATION_SEC = 20

EXPERIMENT_DIR = '/Users/stepanmazokha/Desktop/orbit_experiment/'

# Performs simultaneous signal capture on all specified RX devices
# - tx_node_id: identifier of the transmitting node (format: X-Y)
# - rx_node_id: identifier of the receiving node (format: X-Y)
# - target_dir: directory where the signal should be stored
# - start_event, stop_event: thread events to control task execution
def command_rx(tx_node_id, rx_node_id, target_dir, start_event, stop_event):
    print(f"RX: {tx_node_id} -> {rx_node_id}: Starting...")
    try:
        # Wait for the start signal
        start_event.wait()

        print(f"RX: {tx_node_id} -> {rx_node_id}: Running...")

        rx_master.node_capture(tx_node_id, rx_node_id, target_dir)

        # Wait for the stop signal (optional)
        print(f"RX: {tx_node_id} -> {rx_node_id}: Done, waiting...")
        stop_event.wait()

        print(f"RX: {tx_node_id} -> {rx_node_id}: Completed.")
    except Exception as e:
        print(f"Something went wrong: {str(e)}")

# Performs configuration of a given device:
# - node_id: identifier of the configured node (format: X-Y)
# - node_type: type of the node [AP, TX-probe, TX-udp, RX]
def command_config(node_id, node_type, channel):
    print(f"Config: {node_id}, {node_type} started")
    try:
        if node_type == 'AP': # only relevant in case we're sending UDP traffic
            tx_udp_master.node_configure_ap(node_id, driver_name=tx_udp_master.WIFI_DRIVER_ATHEROS_10k, channel=channel)
        elif node_type == 'TX-probe':
            tx_probe_master.node_configure(node_id, driver_name=tx_probe_master.WIFI_DRIVER_ATHEROS_MAIN, channel=channel)
        elif node_type == 'TX-udp':
            tx_udp_master.node_configure_tx(node_id, driver_name=tx_udp_master.WIFI_DRIVER_ATHEROS_MAIN, channel=channel)
        elif node_type == 'RX':
            rx_master.node_configure(node_id)
        else: 
            print("Invalid node type.")

        print(f"Config: {node_id} ({node_type}) finished")
    except Exception as e:
        print(f"Something went wrong ({node_id}, {node_type}): {str(e)}")

# Runs configuration of all relevant nodes for the experiment
# - tx_node_ids: list of TX
# - rx_node_ids: list of RX nodes
# - ap_node_ids: list of AP nodes (either one entry or empty)
# - tx_mode: type of TX traffic to be sent [probe | udp]
def run_config(tx_node_ids, rx_node_ids, ap_node_ids, tx_mode, batch_size, tx_channel):
    config_queue = queue.Queue()
    [config_queue.put((node_id, 'RX')) for node_id in rx_node_ids]
    [config_queue.put((node_id, 'TX-' + tx_mode)) for node_id in tx_node_ids]
    [config_queue.put((node_id, 'AP')) for node_id in ap_node_ids]

    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = []
        while not config_queue.empty():
            if len(futures) < batch_size:
                node_id, node_type = config_queue.get()
                future = executor.submit(command_config, node_id, node_type, tx_channel)
                futures.append(future)
            else:
                # Check and remove completed futures
                for future in as_completed(futures):
                    futures.remove(future)
                    break  # Only remove one future per iteration to maintain the batch size

        # Ensure all remaining futures are completed
        for future in as_completed(futures):
            pass

# Runs signal capture across specified RX nodes
# - rx_node_ids: identifiers of the RX nodes that are capturing signal
# - tx_node_id: identifier of the TX node that emits signal (for file naming only)
# - target_dir: directory where we'll save the file with IQ samples
# - capture_duration_sec: how long we'll wait for signal to be captured
def run_rx(tx_node_id, rx_node_ids, target_dir, capture_duration_sec):
    start_event = threading.Event()
    stop_event = threading.Event()

    # 1. Configure and start all threads
    threads = []
    for rx_node_id in rx_node_ids:
        thread = threading.Thread(target=command_rx, args=(tx_node_id, rx_node_id, target_dir, start_event, stop_event))
        thread.start()
        threads.append(thread)

    # 2. Launch signal capture on all threads simultaneously
    start_event.set()

    # 3. Wait for N seconds for the capture to be completed
    time.sleep(capture_duration_sec)

    # 4. Stop all threads simultaneously and wait for them to finish
    stop_event.set()
    for thread in threads:
        thread.join()

# Runs a single transmission task, probe request mode
def run_capture_probes(tx_node_id, rx_node_ids, channel, mac, ssid, interval, target_dir, capture_duration_sec):
    # Start transmission
    wifi_interface = tx_probe_master.node_emit_start(tx_node_id, channel, mac, ssid, interval)
    time.sleep(5) # wait while the tmux session starts on TX device

    # Perform capture
    run_rx(tx_node_id, rx_node_ids, target_dir, capture_duration_sec)

    # Stop transmission
    tx_probe_master.node_emit_stop(tx_node_id, wifi_interface)

# Runs a single transmission task, udp mode
def run_capture_udp(tx_node_id, ap_node_id, rx_node_ids, target_dir, capture_duration_sec):
    # Start transmission
    tx_udp_master.node_transmission_start(tx_node_id, ap_node_id)
    time.sleep(5) # wait while the tmux session starts on TX device

    # Perform capture
    run_rx(tx_node_id, rx_node_ids, target_dir, capture_duration_sec)

    # Stop transmission
    tx_udp_master.node_transmission_stop(tx_node_id, ap_node_id)

# Runs a full experiment in udp mode
def run_full_experiment_udp(tx_node_ids_train, tx_node_ids_test, rx_node_ids, ap_node_id, experiment_dir, capture_duration_sec, epochs):
    # 1. Perform data capture for the training devices
    target_dir = rx_master.prepare_target_dir(experiment_dir, 'training_')
    os.mkdir(target_dir)
    for tx_node_id in tx_node_ids_train:
        run_capture_udp(tx_node_id, ap_node_id, rx_node_ids, target_dir, capture_duration_sec)

    print("================ TRAINING CAPTURE COMPLETE ================")

    # 2. Run testing data capture for a given number of epochs
    for epoch_i in epochs:
        print(f"Running epoch #{epoch_i + 1}")

        target_dir = rx_master.prepare_target_dir(experiment_dir, 'epoch_')
        os.mkdir(target_dir)
        for tx_node_id in tx_node_ids_test:
            run_capture_udp(tx_node_id, ap_node_id, rx_node_ids, target_dir, capture_duration_sec)

        print(f"================ EPOCH #{epoch_i + 1} CAPTURE COMPLETE ================")

def main():
    while True:
        instruction = input("What should we do? [config [probe | udp] | emit [probe | udp]] | run experiment [probe | udp]")

        if instruction == 'config probe':
            run_config(tx_node_ids=(TX_TRAINING_NODES + TX_TESTING_NODES), rx_node_ids=RX_NODES, ap_node_ids=[], tx_mode='probe', batch_size=CONFIG_BATCH_SIZE, tx_channel=TX_CHANNEL)
        elif instruction == 'config udp':
            run_config(tx_node_ids=(TX_TRAINING_NODES + TX_TESTING_NODES), rx_node_ids=RX_NODES, ap_node_ids=[AP_NODE], tx_mode='udp', batch_size=CONFIG_BATCH_SIZE, tx_channel=TX_CHANNEL)
        elif instruction == 'emit probe':
            tx_node_id = input('TX node ID: ') # 'node14-7'
            target_dir = rx_master.prepare_target_dir(EXPERIMENT_DIR, '')

            if not os.path.exists(target_dir): os.mkdir(target_dir)

            run_capture_probes(tx_node_id, RX_NODES, TX_CHANNEL, TX_MAC, TX_SSID, TX_SSID, target_dir, CAPTURE_DURATION_SEC)

        elif instruction == 'emit udp':
            tx_node_id = input('TX node ID: ') # 'node14-7'
            ap_node_id = input('AP node ID: ') # AP_NODE
            target_dir = rx_master.prepare_target_dir(EXPERIMENT_DIR, '')

            if not os.path.exists(target_dir): os.mkdir(target_dir)

            run_capture_udp(tx_node_id, ap_node_id, RX_NODES, target_dir, CAPTURE_DURATION_SEC)

        elif instruction == 'run experiment probe':
            print('Work in progress')
        elif instruction == 'run experiment udp':
            epochs = int(input('How many epochs? (int only please): '))
            run_full_experiment_udp(TX_TRAINING_NODES, TX_TESTING_NODES, RX_NODES, AP_NODE, EXPERIMENT_DIR, CAPTURE_DURATION_SEC, epochs)
        else: print('Invalid command.')

if __name__ == "__main__":
    main()