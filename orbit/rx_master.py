import os
import time

#                    1         2         3         4         5         6         7         8         9         10        11        12        13
OFDM_CENTER_FREQ = ["2412e6", "2417e6", "2422e6", "2427e6", "2432e6", "2437e6", "2442e6", "2447e6", "2452e6", "2457e6", "2462e6", "2467e6", "2472e6"]

JUMP_NODE_GRID = "smazokha@grid.orbit-lab.org" # node via which we're connecting to the Grid
# JUMP_NODE_GRID = "smazokha@sb3.orbit-lab.org"

CORE_LOCAL_FOLDER = "/Users/stepanmazokha/Desktop/"
CORE_RX_FILE = "/root/samples.dat"
RX_NODES = ["node1-1"]

RX_CHANNEL_IDX = 11 # 1-based value, according to 802.11 standard
RX_USRP_IP = "addr=192.168.10.2"
RX_FREQ = OFDM_CENTER_FREQ[RX_CHANNEL_IDX - 1]
RX_GAIN = "10" # Chx Gain Value, Absolute (dB), range (for SBX): 0 - 31.5 dB
RX_SAMP_RATE = "25e6" # Sampling rate, should be at least 20 Msps
RX_SKIP = "1" # How many samples (N) do we skip, where N = RX_SKIP * RX_SAMP_RATE
# RX_CAP_LEN = "0.512"
RX_CAP_LEN = "2" # How many samples (N) do we capture, where N = RX_CAP_LEN * RX_SAMP_RATE
# RX_LO_OFF = "10e6"
RX_LO_OFF = "0" # If the center freq is crowded, we can optionally tune it up (WiSig had it at 10 MHz)

def generate_dir_name():
    return time.strftime("epoch_%Y-%m-%d_%H-%M-%S", time.localtime())

def send_command(needsJump, node, command):
    if needsJump: 
        cmd = "ssh -J %s root@%s \"%s\"" % (JUMP_NODE_GRID, node, command)
    else: 
        cmd = "ssh %s \"%s\"" % (node, command)

    print(cmd)
    os.system(cmd)

def node_configure(node_id):
    send_command(False, JUMP_NODE_GRID, "omf tell -a offh -t " + node_id)
    send_command(False, JUMP_NODE_GRID, "omf load -i baseline.ndz -t " + node_id)
    send_command(False, JUMP_NODE_GRID, "omf tell -a on -t " + node_id)

    while True:
        input('Hit enter when ready to proceed')
        send_command(True, node_id, "ls /root/")

        instruction = input("Were you able to get a response? [Y/n]")
        if instruction == 'Y':
            break

    send_command(True, node_id, "sudo add-apt-repository ppa:gnuradio/gnuradio-releases")
    send_command(True, node_id, "apt update")
    send_command(True, node_id, "sudo apt install uhd-host net-tools wireless-tools git python3-pip gnuradio gir1.2-gtk-3.0 rfkill")
    send_command(True, node_id, "rfkill block wlan")
    send_command(True, node_id, "uhd_find_devices")
    send_command(True, node_id, "iwconfig")

    while True:
        instruction = input("Do we need to configure IP address to USRP? [Y/n]")

        if instruction == 'Y':
            interface = input("Which interface should we use? (eth2 or DATA2 recommended)")
            send_command(True, node_id, f"ifconfig {interface} 192.168.10.1 netmask 255.255.255.0 up")
            send_command(True, node_id, "uhd_find_devices")

            instruction = input("Did it work? [Y/any key]")
            if instruction == 'Y': break
            else: continue
        elif instruction == 'n':
            break
        else: print("Invalid command")

    send_command(True, node_id, f'/usr/lib/uhd/examples/test_pps_input --args=\"{RX_USRP_IP}\" --source external')

    send_command(True, node_id, "cd /root/ && git clone https://github.com/i-sense/mobintel-rffi && mv /root/mobintel-rffi/orbit/gnuradio-n210 /root/ && rm -rf /root/mobintel-rffi")

    # These commands take a long time to run, but are paramount for reducing background noise, etc
    send_command(True, node_id, 'uhd_cal_rx_iq_balance --verbose --args="addr=192.168.10.2"')
    send_command(True, node_id, 'uhd_cal_tx_iq_balance --verbose --args="addr=192.168.10.2"')
    send_command(True, node_id, 'uhd_cal_tx_dc_offset --verbose --args="addr=192.168.10.2"')

    print('Configure done')

def node_capture(tx_node_id, rx_node_id, local_dir):
    # 0. Remove any residual files, if any
    send_command(True, rx_node_id, f"rm -rf {CORE_RX_FILE}")

    # 1. Launch capture
    send_command(True, rx_node_id, f'/root/gnuradio-n210/receive_capture.py --device=\"{RX_USRP_IP}\" --cap-len={RX_CAP_LEN} --output-file=\"{CORE_RX_FILE}\" --rx-freq={RX_FREQ} --rx-gain={RX_GAIN} --rx-lo-off={RX_LO_OFF} --rx-samp-rate={RX_SAMP_RATE} --skip={RX_SKIP}')

    # 2. Download file to local device
    filename = f"tx{{node_{tx_node_id}}}_rx{{node_{rx_node_id}+rxFreq_{RX_FREQ}+rxGain_{RX_GAIN}+capLen_{RX_CAP_LEN}+rxSampRate_{RX_SAMP_RATE}}}.dat"
    path_local = os.path.join(local_dir, filename)
    command = f"scp -J {JUMP_NODE_GRID} root@{rx_node_id}:{CORE_RX_FILE} {path_local}"
    print(command)
    os.system(command)

    # 3. Delete file on the node
    send_command(True, rx_node_id, f"rm -rf {CORE_RX_FILE}")
    print('Capture done')

def mode_rx(node_ids, local_folder, tx_node_id):
    if len(node_ids) == 0:
        print('No nodes to emit from.')
        return

    node_idx = 0
    while node_idx < len(node_ids):
        rx_node_id = node_ids[node_idx]

        instruction = input(f"Ready to RX on {rx_node_id}? [Y/skip/done]")

        if instruction == 'Y':
            node_capture(tx_node_id, rx_node_id, local_folder)
            node_idx = node_idx + 1
        elif instruction == 'skip':
            node_idx = node_idx + 1
        elif instruction == 'done':
            break
        else: print('Invalid command')

    print('Done')

def mode_config(node_ids):
    if len(node_ids) == 0:
        print('No nodes to emit from.')
        return
    
    node_idx = 0

    while node_idx < len(node_ids):
        node_id = node_ids[node_idx]

        instruction = input(f"Ready to configure {node_id}? [Y/skip/done]")

        if instruction == 'Y':
            node_configure(node_id)
            node_idx = node_idx + 1
        elif instruction == 'skip':
            node_idx = node_idx + 1
        elif instruction == 'done':
            break
        else: print('Invalid command')

    print('Done')

def main():
    print("Welcome! Let's get started.")

    rootFolder = input("Where should we store experiments of this run? (the folder MUST exist) ")
    if rootFolder == "": rootFolder = "debug"
    rootFolder = os.path.join(CORE_LOCAL_FOLDER, rootFolder)

    if not os.path.exists(rootFolder):
        print("Root folder doesn't exist. We'll create it.")
        os.mkdir(rootFolder)

    rootFolder = os.path.join(rootFolder, generate_dir_name())

    os.mkdir(rootFolder)

    print("OK, we'll work here: " + rootFolder)

    # tx_node_id = input("Which node are we emitting from? [nodeX-Y]")

    while True:
        instruction = input("What should we do? [config | config one | rx | rx one]")

        if instruction == 'config':
            mode_config(RX_NODES)
        elif instruction == 'config one':
            node_id = input("Which node should we configure? [nodeX-Y]")
            mode_config([node_id])
        elif instruction == 'rx':
            temp = input(f"Which node are we emitting from? [nodeX-Y | enter to use {tx_node_id}]")
            if len(temp) > 0:
                print(f"OK, TX = {tx_node_id}")
                tx_node_id = temp
            mode_rx(RX_NODES, rootFolder, tx_node_id)
        elif instruction == 'rx one':
            # temp = input(f"Which node are we emitting from? [nodeX-Y | enter to use {tx_node_id}]")
            tx_node_id = input("TX node ID: ")
            # rx_node_id = input("RX node ID: ")
            rx_node_id = "node1-1"
            mode_rx([rx_node_id], rootFolder, tx_node_id)
        else: print("Wrong command.")

if __name__ == "__main__":
    main()