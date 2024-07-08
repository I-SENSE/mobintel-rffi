import os
import time
import subprocess
from multiprocessing import Process
from collections import deque

JUMP_NODE_GRID = "smazokha@grid.orbit-lab.org"
JUMP_NODE_OUTDOOR = "smazokha@outdoor.orbit-lab.org"

def get_ceiling_emitters():
    # NOTE: this table has inverse indexing (i.e., index 0 -> 19, 1 -> 18, etc)
    # NOTE: node naming is done as follows: node[row]-[col], for example top left node is node20-20
    grid = [
        [1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1], # corner #2 (this is where I'm sitting)
        [1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
        [1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 1],
        [1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1]] # corner #3
    
    # Convert available nodes into a queue (and convert indexes into node names)
    queue = deque()

    for row in range(len(grid)):
        for col in range(len(grid[0])):
            node_i = 20-row
            node_j = 20-col

            isNodeLive = grid[row][col]
            if isNodeLive == 1:
                nodeName = "node%s-%s" % (str(node_i), str(node_j))
                queue.append(nodeName)

    return queue

def send_command(needsJump, node, command, isGrid):
    cmd = ""
    if needsJump: cmd = "ssh -J %s root@%s \"%s\"" % (JUMP_NODE_GRID if isGrid else JUMP_NODE_OUTDOOR, node, command)
    else: cmd = "ssh %s \"%s\"" % (node, command)
    print(cmd)
    os.system(cmd)

def omf_on(node, isGrid):
    print("Enabling the node...")
    send_command(False, JUMP_NODE_GRID if isGrid else JUMP_NODE_OUTDOOR, "omf tell -a on -t " + node, isGrid)
    print("Please wait 1-2 mins for the node to become available to run more commands.")

def omf_offh(node, isGrid):
    print("Enabling the node...")
    send_command(False, JUMP_NODE_GRID if isGrid else JUMP_NODE_OUTDOOR, "omf tell -a offh -t " + node, isGrid)
    print("Please wait 1-2 mins for the node to become available to run more commands.")

def configure(node, isGrid):
    print("Configuring the wireless...")

    send_command(True, node, "apt update", isGrid)
    send_command(True, node, "apt install -y uhd-host net-tools xter", isGrid)
    send_command(True, node, "apt install -y wireless-tools bcmwl-kernel-source", isGrid)
    send_command(True, node, "apt install -y rfkill", isGrid)
    send_command(True, node, "apt install -y network-manager", isGrid)
    send_command(True, node, "rfkill unblock wlan", isGrid)
    
    configScript = os.path.join(os.getcwd(), 'scripts/network_installer.sh')

    # Upload the script to the node
    os.system("scp -o ProxyJump=%s %s root@%s:/root/network_installer.sh" % (JUMP_NODE_GRID, configScript, node))
    send_command(True, node, "chmod +x /root/network_installer.sh", isGrid)
    send_command(True, node, "/root/network_installer.sh", isGrid)

def connect(node, isGrid):
    print("Connecting to WiFi...")
    send_command(True, node, "rfkill unblock wlan", isGrid)
    send_command(True, node, "nmcli radio wifi on", isGrid)
    send_command(True, node, "nmcli connection up mobloc", isGrid)

def transmit(node, isGrid):
    print("Sending data...")

    # send_command(True, "node4-5", "tmux new-session -d -s random_session 'netcat -lu 192.168.16.1 55554 > random_data.dat'", False)
    # time.sleep(1)
    # send_command(True, node, "tmux new-session -d -s random_session 'cat /dev/urandom | netcat -u 192.168.16.1 55554'", isGrid)
    send_command(True, node, "tmux new-session -d -s random_session 'ping 192.168.16.1 -i 0.1'", isGrid)

    input("Say when to stop (press any key)")

    send_command(True, "node4-5", "tmux kill-server", False)
    send_command(True, "node4-5", "rm -rf /root/random_data.dat", False)
    send_command(True, node, "tmux kill-server", isGrid)
    
    print("Stopped")

def disconnect(node, isGrid):
    print("Disconnecting from WiFi, killing RF")
    send_command(True, node, "nmcli connection down mobloc", isGrid)
    send_command(True, node, "nmcli radio wifi off", isGrid)
    send_command(True, node, "rfkill block wlan", isGrid)

def mode_radiomap():
    print("Working in radiomap mode.")
    emitterQueue = get_ceiling_emitters()

    input("Ready to start? (hit any key) ")
    currNode = emitterQueue.popleft()
    while True:
        instruction = input("[%s | 192.168.16.2] What should we do? [omf_on | omf_offh | configure | connect | transmit | disconnect | next (node)] " % (currNode))
        
        if instruction == 'omf_on':
            omf_on(currNode, True)
        elif instruction == 'omf_offh':
            omf_offh(currNode, True)
        elif instruction == 'configure':
            configure(currNode, True)
        elif instruction == 'connect':
            connect(currNode, True)
        elif instruction == 'transmit':
            transmit(currNode, True)
        elif instruction == 'disconnect':
            disconnect(currNode, True)
        elif instruction == 'next':
            if emitterQueue:
                currNode = emitterQueue.popleft()
            else: 
                break
        else: print("Invalid command.")

    print("Done with all nodes.")

def mode_mobile():
    print("Working in mobile mode.")

    input("Ready to start? (hit any key) ")
    currNode = "node2-5"

    while True:
        instruction = input("[%s | 192.168.16.1] What should we do? [omf_on | connect | transmit | disconnect | done] " % currNode)
        
        if instruction == 'omf_on':
            omf_on(currNode, False)
        elif instruction == 'omf_offh':
            omf_offh(currNode, False)
        elif instruction == 'connect':
            connect(currNode, False)
        elif instruction == 'transmit':
            transmit(currNode, False)
        elif instruction == 'disconnect':
            disconnect(currNode, False)
        elif instruction == 'done':
            break
        else: print("Invalid command.")

    print("Done with mobile mode.")

def main():
    print("Welcome, Stephan. Let's get started.")
    while True:
        tx_type = input("Which mode are we in? [mobile | radiomap] ")
        if tx_type == 'mobile':
            mode_mobile()
            return
        elif tx_type == 'radiomap':
            mode_radiomap()
            return
        else: print("Wrong command.")
        

if __name__ == "__main__":
    main()