import os
import time
import subprocess
import llm
from multiprocessing import Process
from collections import deque

# TX command: cat /dev/urandom | netcat -u 192.168.16.1 55555
# RX command: rm -rf /root/temp_node.dat && netcat -lu  192.168.16.1 55555 > "/root/temp_node.dat"

JUMP_NODE_GRID = "smazokha@sb3.orbit-lab.org" # Node via which we're connecting to the Grid
JUMP_NODE_OUTDOOR = "smazokha@sb3.orbit-lab.org"
# JUMP_NODE_GRID = "smazokha@sb3.orbit-lab.org"

TX_INTERVAL = "0.01" # Interval (in seconds) between injected probe requests
TX_SSID = "smazokha" # Name of the SSID which we'll use in the probe requests (irrelevant)
TX_MAC = "11:22:33:44:55:66" # Spoofed MAC address we'll use in our probe requests
TX_CHANNEL = 11 # Channel ID on which we'll be sending our probes [1 -- 13]
TX_INTERFACE = "wlp6s8mon" # Default name of the interface we'll set in monitor mode

AP_NODE = "node1-2"
LLM_MAX_ATTEMPTS = 6

TX_NODES_TRAIN = ["node7-10", "node7-11", "node7-14", "node1-10", "node1-12", "node8-3", "node1-16", "node1-18",
                "node1-19", "node8-8", "node2-6", "node8-18", "node8-20", "node2-19", "node3-13", "node3-18",
                "node10-7", "node4-1", "node10-11", "node10-17", "node4-10", "node4-11", "node11-1", "node11-4",
                "node11-7", "node5-1", "node5-5", "node11-17", "node6-1", "node6-15"]
                
TX_NODES_TEST = ["node20-12", "node19-1", "node17-10", "node14-7", "node17-11", "node16-1", "node14-10", 
                 "node20-15", "node12-20", "node20-19", "node13-3", "node15-1", "node19-19", "node16-16", "node20-1"]

def send_command(jump, node, command, capture_response=False):
    if jump == None:
        cmd = "ssh %s \"%s\"" % (node, command)
    elif jump == 'grid':
        cmd = "ssh -J %s root@%s \"%s\"" % (JUMP_NODE_GRID, node, command)
    elif jump == 'outdoor':
        cmd = "ssh -J %s root@%s \"%s\"" % (JUMP_NODE_OUTDOOR, node, command)
    else:
        return

    print(cmd)

    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    stdout_lines = []

    while True:
        stdout_line = process.stdout.readline()

        if not stdout_line: 
            break

        if stdout_line:
            print(stdout_line, end='')
            if capture_response:
                stdout_lines.append(stdout_line)
        
    if capture_response:
        stdout, _ = process.communicate()
        stdout_lines.append(stdout)    
        return ''.join(stdout_lines)
    else: return None

def node_configure_ap(node_id, driver_name="ath5k"):
    send_command(None, JUMP_NODE_OUTDOOR, "omf tell -a offh -t " + node_id)
    send_command(None, JUMP_NODE_OUTDOOR, "omf load -i baseline.ndz -t " + node_id)
    send_command(None, JUMP_NODE_OUTDOOR, "omf tell -a on -t " + node_id)

    attempts = 0
    while attempts < LLM_MAX_ATTEMPTS:
        print('Sleeping for 30 seconds before attempting to connect.')
        time.sleep(30)
        
        attempts += 1

        can_proceed = llm.prompt_is_ls_successful(send_command('outdoor', node_id, "ls /root/", capture_response=True))

        if can_proceed:
            break
        
        if attempts == LLM_MAX_ATTEMPTS:
            print("This was the last attempt. Node is dead. Quitting.")
            return

    send_command('outdoor', node_id, "sudo apt-get update -y")
    send_command('outdoor', node_id, "sudo apt-get install -y network-manager wireless-tools net-tools hostapd wireless-tools tmux rfkill socat")
    send_command('outdoor', node_id, f"modprobe {driver_name}")

    interface = llm.prompt_find_wifi_interface(send_command('outdoor', node_id, "iwconfig", capture_response=True))
    if interface == 'NONE':
        interface = input("Which interface should we use?")

    command_hostapd = f"""
sudo bash -c 'cat <<EOF > /etc/hostapd/hostapd.conf
interface={interface}
driver=nl80211
ssid=mobloc_wlan
hw_mode=g
channel={TX_CHANNEL}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=P@ssw0rd123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF'
"""
    send_command('outdoor', node_id, command_hostapd)
    send_command('outdoor', node_id, 'DAEMON_CONF="/etc/hostapd/hostapd.conf"')
    send_command('outdoor', node_id, "systemctl unmask hostapd && systemctl enable hostapd")

    command_default_hostapd = """
sudo bash -c 'cat <<EOF > /etc/default/hostapd
# Defaults for hostapd initscript
#
# See /usr/share/doc/hostapd/README.Debian for information about alternative
# methods of managing hostapd.
#
# Uncomment and set DAEMON_CONF to the absolute path of a hostapd configuration
# file and hostapd will be started during system boot. An example configuration
# file can be found at /usr/share/doc/hostapd/examples/hostapd.conf.gz
#
DAEMON_CONF=\\"/etc/hostapd/hostapd.conf\\"

# Additional daemon options to be appended to hostapd command:-
#       -d   show more debug messages (-dd for even more)
#       -K   include key data in debug messages
#       -t   include timestamps in some debug messages
#
# Note that -B (daemon mode) and -P (pidfile) options are automatically
# configured by the init.d script and must not be added to DAEMON_OPTS.
#
#DAEMON_OPTS=""
EOF'
"""
    send_command('outdoor', node_id, command_default_hostapd)
    send_command('outdoor', node_id, "systemctl restart hostapd")
    send_command('outdoor', node_id, f"ifconfig {interface} 192.168.16.1 netmask 255.255.255.0")
    send_command('outdoor', node_id, f"sudo iwconfig {interface} txpower 20")

    print("AP setup complete.")

def node_configure_tx(node_id):
    send_command(None, JUMP_NODE_GRID, "omf tell -a offh -t " + node_id)
    send_command(None, JUMP_NODE_GRID, "omf load -i baseline.ndz -t " + node_id)
    send_command(None, JUMP_NODE_GRID, "omf tell -a on -t " + node_id)

    attempts = 0
    while attempts < LLM_MAX_ATTEMPTS:
        print('Sleeping for 30 seconds before attempting to connect.')
        time.sleep(30)
        
        attempts += 1

        can_proceed = llm.prompt_is_ls_successful(send_command('grid', node_id, "ls /root/", capture_response=True))

        if can_proceed:
            break
        
        if attempts == LLM_MAX_ATTEMPTS:
            print("This was the last attempt. Node is dead. Quitting.")
            return

    send_command('grid', node_id, "sudo apt-get -y update")
    send_command('grid', node_id, "sudo apt-get -y install net-tools network-manager hostapd wireless-tools rfkill tmux socat")
    send_command('grid', node_id, "modprobe ath5k")

    interface = llm.prompt_find_wifi_interface(send_command('grid', node_id, "iwconfig", capture_response=True))

    if interface == 'NONE':
        interface = input("Which interface should we use?")

    send_command('grid', node_id, f"ip link set {interface} up")
    send_command('grid', node_id, "systemctl start network-manager")
    send_command('grid', node_id, f"nmcli connection add type wifi con-name mobloc ifname {interface} mac \$(cat /sys/class/net/{interface}/address) ssid mobloc_wlan mode infra ip4 192.168.16.12/24")
    send_command('grid', node_id, "nmcli con modify mobloc 802-11-wireless-security.key-mgmt wpa-psk  wifi-sec.psk P@ssw0rd123")
    send_command('grid', node_id, "rfkill block wlan")
    print("TX setup complete.")
    
def node_transmit(tx_node_id, ap_node_id):
    send_command('grid', tx_node_id, "rfkill unblock wlan")
    time.sleep(2)

    while True:
        # input("Hit when you're ready to check for WiFi availability...")
        send_command('grid', tx_node_id, 'nmcli dev wifi | grep "mobloc_wlan"')
        answer = input("Do you see WiFi network 'mobloc_wlan'? [hit/n]")
        if answer is not 'n':
            break

    send_command('grid', tx_node_id, "nmcli connection up mobloc")
    send_command('grid', tx_node_id, "ping 192.168.16.1 -c 2")

    input("Ready to start transmission?")
    
    # command_tx_start = "tmux new-session -d -s emit 'cat /dev/urandom | netcat -u 192.168.16.1 55555'"
    # command_ap_start = "tmux new-session -d -s receive 'netcat -lu  192.168.16.1 55555 > \"/root/temp_node.dat\"'"

    command_tx_start = "tmux new-session -d -s emit 'cat /dev/urandom | socat - UDP-SENDTO:192.168.16.1:55555'"
    command_ap_start = "tmux new-session -d -s receive 'socat - UDP-RECV:55555 > \"/root/temp_node.dat\"'"

    command_tx_stop = "tmux kill-session -t emit"
    command_ap_stop = "tmux kill-session -t receive"

    # send_command('outdoor', ap_node_id, "rm -rf /root/temp_node.dat")
    # send_command('outdoor', ap_node_id, command_ap_stop)
    # send_command('grid', tx_node_id, command_tx_stop)

    send_command('outdoor', ap_node_id, command_ap_start)
    time.sleep(2) # let AP set up the receival
    send_command('grid', tx_node_id, command_tx_start)

    input("Transmission is in progress. Start reception. Hit to stop.")
    send_command('outdoor', ap_node_id, command_ap_stop)
    send_command('grid', tx_node_id, command_tx_stop)
    send_command('grid', tx_node_id, "rfkill block wlan")
    send_command('outdoor', ap_node_id, "rm -rf /root/temp_node.dat")

    print("Transmission complete.")

def main():
    print("Welcome!. Let's get started.")
    while True:
        tx_type = input("What should we do? [config tx | config ap | emit one] ")

        if tx_type == "config tx":
            node_id = input("TX node ID: ")
            node_configure_tx(node_id)

        elif tx_type == "config ap":
            # node_id = "node2-5"
            # node_configure_ap(node_id, driver_name="ath10k_pci") # use when AP is in outdoor env

            node_id = input("AP node ID: ")
            node_configure_ap(node_id) # use when AP has our main Atheros driver

        elif tx_type == "emit one":
            tx_node_id = input("TX node ID: ")
            # ap_node_id = input("AP node ID: ")
            ap_node_id = "node2-5"
            node_transmit(tx_node_id, ap_node_id)

        else: print("Wrong command.")
        
if __name__ == "__main__":
    main()