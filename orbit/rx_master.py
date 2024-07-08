import os
import time

JUMP_NODE_GRID = "smazokha@grid.orbit-lab.org"

CORE_LOCAL_FOLDER = "/Users/stepanmazokha/Desktop/"
CORE_REC_FOLDER = "/root/rec/"

MIMO_RACKS = [ # this array stores file naming for each of the MIMO antenna racks (indexing of array corresponds to 0-based corner indexing in the room)
    # ["24-15_A.bin", "24-15_B.bin", "24-16_A.bin", "24-16_B.bin", "24-17_A.bin", "24-17_B.bin", "24-18_A.bin", "24-18_B.bin"],
    ["24-17_A.bin", "24-17_B.bin", "24-18_A.bin", "24-18_B.bin"],
    # ["24-5_A.bin", "24-5_B.bin", "24-6_A.bin", "24-6_B.bin", "24-7_A.bin", "24-7_B.bin", "24-8_A.bin", "24-8_B.bin"],
    ["24-7_A.bin", "24-7_B.bin", "24-8_A.bin", "24-8_B.bin"],
    # ["23-5_A.bin", "23-5_B.bin", "23-6_A.bin", "23-6_B.bin", "23-7_A.bin", "23-7_B.bin", "23-8_A.bin", "23-8_B.bin"],
    ["23-5_A.bin", "23-5_B.bin", "23-6_A.bin", "23-6_B.bin"],
    # ["23-15_A.bin", "23-15_B.bin", "23-16_A.bin", "23-16_B.bin", "23-17_A.bin", "23-17_B.bin", "23-18_A.bin", "23-18_B.bin"]
    ["23-17_A.bin", "23-17_B.bin", "23-18_A.bin", "23-18_B.bin"]
]

# These are the routes to servers for each of the MIMO racks (in order [1, 2, 3, 4])
MIMO_RACK_SERVERS = ["root@node21-1", "root@node21-4", "root@node21-2", "root@node21-6"]

def send_command(node, command):
    cmd = "ssh -J %s %s \"%s\"" % (JUMP_NODE_GRID, node, command)
    print(cmd)
    os.system(cmd)

def local_create_dir(newdir):
    if not os.path.exists(newdir):
        os.mkdir(newdir)

def delete_rec_dir(nodes):
    for node in nodes:
        nodeRoute = MIMO_RACK_SERVERS[node]
        print("Deleting " + CORE_REC_FOLDER + " directory.")
        send_command(nodeRoute, "rm -rf " + CORE_REC_FOLDER)

def download_recordings(mimo_racks, destination_path):
    # mimo_racks: array of MIMO indexes (0-based), non-empty
    # destination_path: full destination path for the SCP command
    for rack in mimo_racks:
        print(rack)
        rackRoute = MIMO_RACK_SERVERS[rack]
        for item in MIMO_RACKS[rack]:
            cmd = "scp -J %s %s:%s %s" % (JUMP_NODE_GRID, rackRoute, os.path.join(CORE_REC_FOLDER, item), destination_path)
            print(cmd)
            os.system(cmd)

def mode_mobile(rootFolder):
    print("Working in mobile mode.")
    rootFolder = os.path.join(rootFolder, "mobile")

    if not os.path.exists(rootFolder):
        print("Mobile folder doesn't exist. We'll create one.")
        os.mkdir(rootFolder)

    # Loop for creating emitter folder
    while True:
        instruction = input("Ready to start? (back | any key to proceed) ")

        if instruction == 'back':
            return
        else:
            rootFolderOriginal = rootFolder

            # Select emitter to save this to
            emitter_X = input("What location is this (X coord): ")
            emitter_Y = input("What location is this (Y coord): ")
            emitter_coord = "location-%s_%s" % (emitter_X, emitter_Y)
            rootFolder = os.path.join(rootFolder, emitter_coord)

            if os.path.exists(rootFolder):
                print("Such location exists. Saving here: " + rootFolder)
            else: # attempt is correct
                print("Creating folder for this attempt: " + rootFolder)
                os.mkdir(rootFolder)

            # Create timestamped folder to download data
            rootFolder = os.path.join(rootFolder, str(int(time.time() * 1000)))
            print("Final folder for data: " + rootFolder)
            os.mkdir(rootFolder)

            # Loop for executing relevant commands
            sub_mode_instruction(rootFolder)

            rootFolder = rootFolderOriginal

def mode_radiomap(rootFolder):
    # Mode radiomap:
    # - create .../radiomap folder
    # - create .../radiomap/emitter_X_Y folder
    # - create .../radiomap/emitter_X_Y/timestamp folder
    # - download selected data and/or delete /root/rec folder

    print("Working in radiomap mode.")
    rootFolder = os.path.join(rootFolder, "radiomap")

    if not os.path.exists(rootFolder):
        print("Radiomap folder doesn't exist. We'll create one.")
        os.mkdir(rootFolder)

    # Loop for creating emitter folder
    while True:
        instruction = input("Ready to start? (back | any key to proceed) ")

        if instruction == 'back':
            return
        else:
            rootFolderOriginal = rootFolder

            # Select emitter to save this to
            emitter_X = input("What emitter is this (X coord): ")
            emitter_Y = input("What emitter is this (Y coord): ")
            emitter_coord = "emitter-%s_%s" % (emitter_X, emitter_Y)
            rootFolder = os.path.join(rootFolder, emitter_coord)

            if os.path.exists(rootFolder):
                print("Such emitter exists. Saving here: " + rootFolder)
            else: # attempt is correct
                print("Creating folder for this attempt: " + rootFolder)
                os.mkdir(rootFolder)

            # Create timestamped folder to download data
            rootFolder = os.path.join(rootFolder, str(int(time.time() * 1000)))
            print("Final folder for data: " + rootFolder)
            os.mkdir(rootFolder)

            # Loop for executing relevant commands
            sub_mode_instruction(rootFolder)

            rootFolder = rootFolderOriginal

def sub_mode_instruction(rootFolder):
    nodes = None
    while True:
        instruction = input("Which node should we deal with? [1 | 2 | 3 | 4 | all] ")

        if instruction == 'all':
            nodes = [0, 1, 2, 3]
            break
        elif instruction == '1' or instruction == '2' or instruction == '3' or instruction == '4':
            nodes = [int(instruction)-1]
            break
        else: print("Wrong command.")

    if not nodes: return

    while True:
        instruction = input("[%s] Action? [download | delete_rec_dir | back] " % str(nodes))

        if instruction == 'delete_rec_dir':
            delete_rec_dir(nodes)
        elif instruction == 'download':
            download_recordings(nodes, rootFolder)
            print("Deleting files from server...")
            delete_rec_dir(nodes)
        elif instruction == 'back':
            return
        else: print("Wrong command.")

def mode_calibration(rootFolder):
    # Mode calibration:
    # - create .../calibration folder
    # - create .../calibration/wired-X folder
    # - download selected data and/or delete /root/rec folder

    print("Working in calibration mode.")
    rootFolder = os.path.join(rootFolder, "calibration")

    if not os.path.exists(rootFolder):
        print("Calibration folder doesn't exist. We'll create one.")
        os.mkdir(rootFolder)

    input("Ready to start? (hit any key) ")

    # Loop for creating an attempt folder
    while True:
        attempt = input("What attempt is this? (1...1000 | back) ")

        if attempt == 'back':
            return
        else:
            rootFolderOriginal = rootFolder

            attempt = "wired-" + attempt
            if not os.path.exists(os.path.join(rootFolder, attempt)):
                print("Creating attempt folder.")
                rootFolder = os.path.join(rootFolder, attempt)
                os.mkdir(rootFolder)
            
            # Get into sub mode to run as many commands as you need and then come back
            sub_mode_instruction(rootFolder)

            rootFolder = rootFolderOriginal

def main():
    print("Welcome, Stephan. Let's get started.")

    rootFolder = input("Where should we store experiments of this run? (the folder MUST exist) ")
    if rootFolder == "": rootFolder = "debug"
    rootFolder = os.path.join(CORE_LOCAL_FOLDER, rootFolder)

    if not os.path.exists(rootFolder):
        print("Root folder doesn't exist. We'll create one.")
        os.mkdir(rootFolder)

    print("OK, we'll work here: " + rootFolder)

    while True:
        rx_type = input("Which mode are we in? [mobile | radiomap | calibration] ")
        if rx_type == 'mobile':
            mode_mobile(rootFolder)
        elif rx_type == 'radiomap':
            mode_radiomap(rootFolder)
        elif rx_type == 'calibration':
            mode_calibration(rootFolder)
        else: print("Wrong command.")

if __name__ == "__main__":
    main()