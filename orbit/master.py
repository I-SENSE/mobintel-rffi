# This is a master script. It performs a complete suite of tasks to configure nodes,
# transmit and receive samples, ans so forth. The objective of this script is to 
# perform the entire process of data capture completely automatically, without 
# any involvement of an operator.

import tx_udp_master
import rx_master

AP_NODE = "node2-5"
RX_NODES = ["node1-1", "node1-20", "node20-1", "node20-20"]
TX_TRAINING_NODES = ['5-1', '7-10', '7-14', '2-19', '5-5', '19-1', '20-20', '1-10', '8-20', '11-17', 
                     '2-6', '1-12', '4-1', '3-13', '1-16', '8-8', '8-18', '1-19', '1-18', '11-7', 
                     '20-12', '4-10', '11-4', '8-3', '4-11', '3-18', '14-7', '10-17', '10-11']
TX_TESTING_NODES = ['12-20', '17-11', '20-19', '20-1', '20-15', '14-10', '16-16', '15-1', '14-7', '16-1']

def main():
    while True:
        instruction = input("Which mode should we use? [config ap | config rx | config tx | ]")

        if instruction == 'config one':
            node_id = input("RX node ID: ")
            mode_config([node_id])
        elif instruction == 'rx one':
            node_id = input('RX node ID: ')
            mode_rx([node_id])
        else: print("Wrong command.")

if __name__ == "__main__":
    main()