import time
import subprocess
from openai_client import OpenAIClient

TX_INTERVAL = "0.01" # Interval (in seconds) between injected probe requests
TX_SSID = "smazokha" # Name of the SSID which we'll use in the probe requests (irrelevant)
TX_MAC = "11:22:33:44:55:66" # Spoofed MAC address we'll use in our probe requests
TX_CHANNEL = 11 # Channel ID on which we'll be sending our probes [1 -- 13]
TX_INTERFACE = "wlp6s8" # Default name of the interface we'll set in monitor mode
LLM_MAX_ATTEMPTS = 6 # How many times we'll use LLM to attempt node connection
WIFI_DRIVER_ATHEROS_MAIN = 'ath5k' # this driver applies to all other WiFi nodes (Atheros 5212 chipset)

JUMP_NODE_GRID = "smazokha@grid.orbit-lab.org" # Node via which we're connecting to the Grid

def send_command(needsJump, node, command, capture_response=False):
    if needsJump: 
        cmd = "ssh -o StrictHostKeyChecking=no -J %s root@%s \"%s\"" % (JUMP_NODE_GRID, node, command)
    else: 
        cmd = "ssh -o StrictHostKeyChecking=no %s \"%s\"" % (node, command)

    print(f"[{node}] {cmd}")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    stdout_lines = []

    while True:
        stdout_line = process.stdout.readline()

        if not stdout_line: 
            break

        if stdout_line:
            print(f"[{node}] {stdout_line}", end='')
            if capture_response:
                stdout_lines.append(stdout_line)
        
    if capture_response:
        stdout, _ = process.communicate()
        stdout_lines.append(stdout)    
        return ''.join(stdout_lines)
    else: return None

def node_configure(node_id, driver_name=WIFI_DRIVER_ATHEROS_MAIN):
    send_command(False, JUMP_NODE_GRID, "omf tell -a offh -t " + node_id)
    send_command(False, JUMP_NODE_GRID, "omf load -i baseline-5.4.1.ndz -t " + node_id)
    send_command(False, JUMP_NODE_GRID, "omf tell -a on -t " + node_id)

    attempts = 0
    while attempts < LLM_MAX_ATTEMPTS:
        print('Sleeping for 30 seconds before attempting to connect.')
        time.sleep(30)
        
        attempts += 1

        can_proceed = OpenAIClient().prompt_is_ls_successful(send_command(True, node_id, "ls /root/", capture_response=True))

        if can_proceed:
            break
        
        if attempts == LLM_MAX_ATTEMPTS:
            print("This was the last attempt. Node is dead. Quitting.")
            return

    send_command(True, node_id, "sudo apt update -y")
    send_command(True, node_id, "sudo apt-get -y update")
    send_command(True, node_id, "sudo apt-get -y install network-manager net-tools hostapd wireless-tools tmux python3-pip aircrack-ng git")
    send_command(True, node_id, "pip3 install scapy")
    send_command(True, node_id, f"modprobe {driver_name}")
    send_command(True, node_id, "rfkill block wlan")
    send_command(True, node_id, "cd /root && git clone https://github.com/FanchenBao/probe_request_injection")

    print('Configured.')

def node_emit_start(node_id, channel=TX_CHANNEL, mac=TX_MAC, ssid=TX_SSID, interval=TX_INTERVAL):
    send_command(True, node_id, "rfkill unblock wlan")

    time.sleep(2)

    command_response = send_command(True, node_id, "iwconfig", capture_response=True)
    if command_response.__contains__(TX_INTERFACE):
        interface = TX_INTERFACE
    else:
        interface = OpenAIClient().prompt_find_wifi_interface(command_response)
        if interface == 'NONE':
            interface = input("Which interface should we use?")
        
    send_command(True, node_id, f"airmon-ng start {interface}") # airmon ads postfix 'mon' to the newly created interface
    send_command(True, node_id, "tmux kill-session -t emit")
    send_command(True, node_id, f"/root/probe_request_injection/emit/emit.sh -i {interface}mon -c {channel} --mac {mac} --interval {interval} --ssid {ssid}")

    return interface

def node_emit_stop(node_id, interface):
    send_command(True, node_id, f"airmon-ng stop {interface}mon")
    send_command(True, node_id, "tmux kill-session -t emit")
    send_command(True, node_id, "rfkill block wlan")

def node_emit(node_id, channel=TX_CHANNEL, mac=TX_MAC, ssid=TX_SSID, interval=TX_INTERVAL):
    send_command(True, node_id, "rfkill unblock wlan")
    time.sleep(2)
    command_response = send_command(True, node_id, "iwconfig", capture_response=True)
    if command_response.__contains__(TX_INTERFACE):
        interface = TX_INTERFACE
    else:
        interface = OpenAIClient().prompt_find_wifi_interface(command_response)
        if interface == 'NONE':
            interface = input("Which interface should we use?")
        
    send_command(True, node_id, f"airmon-ng start {interface}") # airmon ads postfix 'mon' to the newly created interface
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

    input("Hit enter to stop.")
    send_command(True, node_id, f"airmon-ng stop {interface}mon")
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
        tx_type = input("What should we do? [config one | emit one] ")
        if tx_type == 'config one':
            node_id = input('TX node ID: ')
            mode_config([node_id])
        elif tx_type == 'emit one':
            node_id = input('TX node ID: ')
            mode_emit([node_id])
        else: print("Wrong command.")
        
if __name__ == "__main__":
    main()