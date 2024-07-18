import time
import subprocess
from openai_client import OpenAIClient

TX_CHANNEL = 11 # Channel ID on which we'll be sending our probes [1 -- 13]
LLM_MAX_ATTEMPTS = 6 # How many times we'll use LLM to attempt node connection
WIFI_DRIVER_ATHEROS_MAIN = 'ath5k' # this driver applies to all other WiFi nodes (Atheros 5212 chipset)
WIFI_DRIVER_ATHEROS_10k = 'ath10k_pci' # this driver applies only to outdoor node 2-5

JUMP_NODE_GRID = "smazokha@grid.orbit-lab.org" # grid.orbit-lab.org
JUMP_NODE_OUTDOOR = "smazokha@outdoor.orbit-lab.org" # outdoor.orbit-lab.org

def send_command(jump, node, command, capture_response=False):
    if jump == None:
        cmd = "ssh -o StrictHostKeyChecking=no %s \"%s\"" % (node, command)
    elif jump == 'grid':
        cmd = "ssh -o StrictHostKeyChecking=no -J %s root@%s \"%s\"" % (JUMP_NODE_GRID, node, command)
    elif jump == 'outdoor':
        cmd = "ssh -o StrictHostKeyChecking=no -J %s root@%s \"%s\"" % (JUMP_NODE_OUTDOOR, node, command)
    else:
        return

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

def node_configure_ap(node_id, driver_name=WIFI_DRIVER_ATHEROS_10k, channel=TX_CHANNEL):
    openai_client = OpenAIClient()

    send_command(None, JUMP_NODE_OUTDOOR, "omf tell -a offh -t " + node_id)
    send_command(None, JUMP_NODE_OUTDOOR, "omf load -i baseline-5.4.1.ndz -t " + node_id)
    send_command(None, JUMP_NODE_OUTDOOR, "omf tell -a on -t " + node_id)

    attempts = 0
    while attempts < LLM_MAX_ATTEMPTS:
        print('Sleeping for 30 seconds before attempting to connect.')
        time.sleep(30)
        
        attempts += 1

        can_proceed = openai_client.prompt_is_ls_successful(send_command('outdoor', node_id, "ls /root/", capture_response=True))

        if can_proceed:
            break
        
        if attempts == LLM_MAX_ATTEMPTS:
            print("This was the last attempt. Node is dead. Quitting.")
            return

    send_command('outdoor', node_id, "sudo apt update -y")
    send_command('outdoor', node_id, "sudo apt-get update -y")
    send_command('outdoor', node_id, "sudo apt-get install -y network-manager wireless-tools net-tools hostapd tmux rfkill socat")
    send_command('outdoor', node_id, f"modprobe {driver_name}")

    interface = openai_client.prompt_find_wifi_interface(send_command('outdoor', node_id, "iwconfig", capture_response=True))
    if interface == 'NONE':
        interface = input("Which interface should we use?")

    command_hostapd = f"""
sudo bash -c 'cat <<EOF > /etc/hostapd/hostapd.conf
interface={interface}
driver=nl80211
ssid=mobloc_wlan
hw_mode=g
channel={channel}
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

def node_configure_tx(node_id, driver_name=WIFI_DRIVER_ATHEROS_MAIN):
    openai_client = OpenAIClient()

    send_command(None, JUMP_NODE_GRID, "omf tell -a offh -t " + node_id)
    send_command(None, JUMP_NODE_GRID, "omf load -i baseline-5.4.1.ndz -t " + node_id)
    send_command(None, JUMP_NODE_GRID, "omf tell -a on -t " + node_id)

    attempts = 0
    while attempts < LLM_MAX_ATTEMPTS:
        print('Sleeping for 30 seconds before attempting to connect.')
        time.sleep(30)
        
        attempts += 1

        can_proceed = openai_client.prompt_is_ls_successful(send_command('grid', node_id, "ls /root/", capture_response=True))

        if can_proceed:
            break
        
        if attempts == LLM_MAX_ATTEMPTS:
            print("This was the last attempt. Node is dead. Quitting.")
            return

    send_command('grid', node_id, "sudo apt update -y")
    send_command('grid', node_id, "sudo apt-get -y update")
    send_command('grid', node_id, "sudo apt-get -y install net-tools network-manager hostapd wireless-tools rfkill tmux socat")
    send_command('grid', node_id, f"modprobe {driver_name}")

    interface = openai_client.prompt_find_wifi_interface(send_command('grid', node_id, "iwconfig", capture_response=True))

    if interface == 'NONE':
        interface = input("Which interface should we use?")

    send_command('grid', node_id, f"ip link set {interface} up")
    send_command('grid', node_id, "systemctl start network-manager")
    send_command('grid', node_id, f"nmcli connection add type wifi con-name mobloc ifname {interface} mac \$(cat /sys/class/net/{interface}/address) ssid mobloc_wlan mode infra ip4 192.168.16.12/24")
    send_command('grid', node_id, "nmcli con modify mobloc 802-11-wireless-security.key-mgmt wpa-psk  wifi-sec.psk P@ssw0rd123")
    send_command('grid', node_id, "rfkill block wlan")
    print("TX setup complete.")
    
def node_transmission_start(tx_node_id, ap_node_id):
    send_command('grid', tx_node_id, "rfkill unblock wlan")
    time.sleep(2)
    send_command('grid', tx_node_id, 'nmcli dev wifi | grep "mobloc_wlan"')

    # while True:
    #     # input("Hit when you're ready to check for WiFi availability...")
    #     send_command('grid', tx_node_id, 'nmcli dev wifi | grep "mobloc_wlan"')
    #     answer = input("Do you see WiFi network 'mobloc_wlan'? [hit/n]")
    #     if answer is not 'n':
    #         break

    send_command('grid', tx_node_id, "nmcli connection up mobloc")
    send_command('grid', tx_node_id, "ping 192.168.16.1 -c 1")
    send_command('outdoor', ap_node_id, "tmux new-session -d -s receive 'socat - UDP-RECV:55555 > \"/root/temp_node.dat\"'")
    time.sleep(2) # let AP set up the receival
    send_command('grid', tx_node_id, "tmux new-session -d -s emit 'cat /dev/urandom | socat - UDP-SENDTO:192.168.16.1:55555'")

def node_transmission_stop(tx_node_id, ap_node_id):
    send_command('outdoor', ap_node_id, "tmux kill-session -t receive")
    send_command('grid', tx_node_id, "tmux kill-session -t emit")
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
            # Use this code when AP is an Outdoor node
            node_id = input(f"AP node ID [{WIFI_DRIVER_ATHEROS_10k}]: ")
            node_configure_ap(node_id, driver_name=WIFI_DRIVER_ATHEROS_10k) # use when AP is in outdoor env

            # Use this code when AP is an SB3 node
            # node_id = input(f"AP node ID [{WIFI_DRIVER_ATHEROS_MAIN}]: ")
            # node_configure_ap(node_id) # use when AP has our main Atheros driver

        elif tx_type == "emit one":
            tx_node_id = input("TX node ID: ")
            ap_node_id = input("AP node ID: ")

            input("Ready to start transmission?")

            node_transmission_start(tx_node_id, ap_node_id)
            input("Transmission is in progress. Start reception. Hit to stop.")
            node_transmission_stop(tx_node_id, ap_node_id)

        else: print("Wrong command.")
        
if __name__ == "__main__":
    main()