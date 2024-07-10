import os
import time
import subprocess
from multiprocessing import Process
from collections import deque

JUMP_NODE_GRID = "smazokha@grid.orbit-lab.org" # Node via which we're connecting to the Grid
# JUMP_NODE_GRID = "smazokha@sb3.orbit-lab.org"

TX_INTERVAL = "0.5" # Interval (in seconds) between injected probe requests
TX_SSID = "smazokha" # Name of the SSID which we'll use in the probe requests (irrelevant)
TX_MAC = "11:22:33:44:55:66" # Spoofed MAC address we'll use in our probe requests
TX_CHANNEL = 5 # Channel ID on which we'll be sending our probes [1 -- 13]
TX_INTERFACE = "wlp6s8mon" # Default name of the interface we'll set in monitor mode

TX_NODES_TRAIN = ["node7-10", "node7-11", "node7-14", "node1-10", "node1-12", "node8-3", "node1-16", "node1-18",
                "node1-19", "node8-8", "node2-6", "node8-18", "node8-20", "node2-19", "node3-13", "node3-18",
                "node10-7", "node4-1", "node10-11", "node10-17", "node4-10", "node4-11", "node11-1", "node11-4",
                "node11-7", "node5-1", "node5-5", "node11-17", "node6-1", "node6-15"]
                
TX_NODES_TEST = ["node20-12", "node19-1", "node17-10", "node14-7", "node17-11", "node16-1", "node14-10", 
                 "node20-15", "node12-20", "node20-19", "node13-3", "node15-1", "node19-19", "node16-16", "node20-1"]

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

    send_command(True, node_id, "apt update")
    send_command(True, node_id, "apt install network-manager net-tools hostapd wireless-tools tmux python3-pip aircrack-ng git")
    send_command(True, node_id, "pip3 install scapy")
    send_command(True, node_id, "modprobe ath5k")
    send_command(True, node_id, "rfkill block wlan")
    send_command(True, node_id, "cd /root && git clone https://github.com/FanchenBao/probe_request_injection")

    print('Configured.')

def node_emit(node_id, interface=TX_INTERFACE, channel=TX_CHANNEL, mac=TX_MAC, ssid=TX_SSID, interval=TX_INTERVAL):
    send_command(True, node_id, "rfkill unblock wlan")
    
    while True:
        send_command(True, node_id, "iwconfig")
        interface = input("What interface should we use?")

        send_command(True, node_id, f"airmon-ng start {interface}")
        send_command(True, node_id, "tmux kill-session -t emit")

        # Note #1: probe emission code has been developed by Fanchen for one of our previous projects. 
        #          But this code provides an easy interface for emitting probe requests. 
        #          Importantly, the probes will be emitted for as long as the tmux sesh is running. 
        #          So, that's why we need to kill the session once we captured our data on the RX side.
        # 
        # Note #2: The TX power functionality of the Fanchen's repo is not applicable in our case. We 
        #          cannot change TX power on the grid, because the Atheros chipsets we can use has the
        #          regional power limits written in EEPROM. Therefore, any attempts to change the TX 
        #          power won't work.
        #          Ref: https://wiki.archlinux.org/title/Network_configuration/Wireless#:~:text=However%2C%20setting%20the,maximum%20of%2030dBm
        # 
        # TODO:    Determine most optimal interval for probe emission. Update the matlab IQ parser accordingly.
        send_command(True, node_id, f"/root/probe_request_injection/emit/emit.sh -i {interface}mon -c {channel} --mac {mac} --interval {interval} --ssid {ssid}")

        command = input("What now? [emit/enter (to stop)]")

        if command == 'emit':
            continue
        else: 
            send_command(True, node_id, f"airmon-ng stop {interface}mon")
            break

    send_command(True, node_id, "tmux kill-session -t emit")
    send_command(True, node_id, "rfkill block wlan")

def mode_emit(tx_nodes):
    if len(tx_nodes) == 0:
        print('No nodes to emit from.')
        return

    node_idx = 0
    while node_idx < len(tx_nodes):
        node_id = tx_nodes[node_idx]
        instruction = input('Ready to emit from ' + node_id + "? [Y/skip]")

        if instruction == 'Y':
            node_emit(node_id)
            
            instruction = input('Emission is over. Move to next device? [Y/n]')
            if instruction == 'Y':
                node_idx = node_idx + 1
            
        elif instruction == 'skip':
            node_idx = node_idx + 1
        else: print('Invalid command.')

    print('Done')

def mode_config(nodes):
    if len(nodes) == 0:
        print('No nodes to emit from.')
        return
    
    node_idx = 0
    while node_idx < len(nodes):
        node_id = nodes[node_idx]

        instruction = input('Ready to configure ' + node_id + "? [Y/skip/done]")

        if instruction == 'Y':
            node_configure(node_id)
            node_idx = node_idx + 1
        elif instruction == 'skip':
            node_idx = node_idx + 1
        elif instruction == 'done':
            break
        else: 
            print('Invalid command')

def main():
    print("Welcome!. Let's get started.")
    while True:
        tx_type = input("What should we do? [config | config one | emit train | emit test | emit one] ")
        if tx_type == 'config':
            mode_config(TX_NODES_TRAIN + TX_NODES_TEST)
        elif tx_type == 'config one':
            node_id = input('Type node ID (nodeX-Y): ')
            mode_config([node_id])
        elif tx_type == 'emit train':
            mode_emit(TX_NODES_TRAIN)
        elif tx_type == 'emit test':
            mode_emit(TX_NODES_TEST)
        elif tx_type == 'emit one':
            node_id = input('Type node ID (nodeX-Y): ')
            mode_emit([node_id])
        else: print("Wrong command.")
        
if __name__ == "__main__":
    main()