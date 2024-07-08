import os
import numpy as np
from gnuradio import gr

MAX_SAMP_PER_RECORD = 20e6 * 2 # store 2 seconds per stream

class blk(gr.sync_block):
    def __init__(self, save_enabled=0, directory="/root/rec", usrp_1="24-5_A.bin", usrp_2="24-5_B.bin", usrp_3="24-6_A.bin", usrp_4="24-6_B.bin", usrp_5="24-7_A.bin", usrp_6="24-7_B.bin", usrp_7="24-8_A.bin", usrp_8="24-8_B.bin"):
        gr.sync_block.__init__(self,
                               name="custom_block",
                               in_sig=[np.complex64, np.complex64, np.complex64, np.complex64, np.complex64, np.complex64, np.complex64, np.complex64],
                               out_sig=None)

        self.save_enabled = save_enabled
        self.directory = directory
        self.file_names = [usrp_1, usrp_2, usrp_3, usrp_4, usrp_5, usrp_6, usrp_7, usrp_8]
        self.file_paths = [os.path.join(self.directory, usrp) for usrp in self.file_names]
        self.file_handles = [None] * 8
        self.file_check_counter = 0

        self.sample_counter = [0] * 8 # we'll keep track of how many samples are we saving, to stop when >= MAX_SAMP_PER_RECORD

        self.open_files()

    def open_files(self, force_reopen=False):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
    
        for i, file_path in enumerate(self.file_paths):
            if force_reopen or not os.path.exists(file_path):
                if self.file_handles[i] is not None:
                    self.file_handles[i].close()
                self.file_handles[i] = open(file_path, 'ab')

    def write_samples(self, input_items, index):
        self.sample_counter[index] = self.sample_counter[index] + len(input_items[index])
        if self.file_handles[index] is not None:
            self.file_handles[index].write(input_items[index].tobytes())

    def work(self, input_items, output_items):
        if self.save_enabled:
            if self.file_check_counter % 1000 == 0:
                print("Check")
                self.open_files(force_reopen=False)

            self.file_check_counter += 1

            for i in range(8):
                self.write_samples(input_items, i)
                
            if self.sample_counter[0] >= MAX_SAMP_PER_RECORD:
                self.save_enabled = 0
                self.sample_counter = [0] * 8
                print("2 seconds of samples recorded. Done.")
                self.file_check_counter = 0

        return len(input_items[0])

    def __del__(self):
        for f in self.file_handles:
            if f:
                f.close()