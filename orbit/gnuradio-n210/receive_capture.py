#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Receive Capture
# GNU Radio version: 3.10.9.2

from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time




class receive_capture(gr.top_block):

    def __init__(self, cap_len=0.512, device="addr=192.168.10.2", output_file="/root/received_samples.dat", rx_freq=2462e6, rx_gain=0.5, rx_lo_off=10e6, rx_samp_rate=25e6, skip=2):
        gr.top_block.__init__(self, "Receive Capture", catch_exceptions=True)

        ##################################################
        # Parameters
        ##################################################
        self.cap_len = cap_len
        self.device = device
        self.output_file = output_file
        self.rx_freq = rx_freq
        self.rx_gain = rx_gain
        self.rx_lo_off = rx_lo_off
        self.rx_samp_rate = rx_samp_rate
        self.skip = skip

        ##################################################
        # Blocks
        ##################################################

        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(('args', "")),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_samp_rate(rx_samp_rate)
        # No synchronization enforced.

        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(rx_freq,rx_lo_off), 0)
        self.uhd_usrp_source_0.set_gain(rx_gain, 0)
        self.blocks_skiphead_0 = blocks.skiphead(gr.sizeof_gr_complex*1, (int(skip*rx_samp_rate)))
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, (int(cap_len*rx_samp_rate)))
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex*1, output_file, False)
        self.blocks_file_sink_0.set_unbuffered(True)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_head_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.blocks_skiphead_0, 0), (self.blocks_head_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_skiphead_0, 0))


    def get_cap_len(self):
        return self.cap_len

    def set_cap_len(self, cap_len):
        self.cap_len = cap_len
        self.blocks_head_0.set_length((int(self.cap_len*self.rx_samp_rate)))

    def get_device(self):
        return self.device

    def set_device(self, device):
        self.device = device

    def get_output_file(self):
        return self.output_file

    def set_output_file(self, output_file):
        self.output_file = output_file
        self.blocks_file_sink_0.open(self.output_file)

    def get_rx_freq(self):
        return self.rx_freq

    def set_rx_freq(self, rx_freq):
        self.rx_freq = rx_freq
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.rx_freq,self.rx_lo_off), 0)

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.uhd_usrp_source_0.set_gain(self.rx_gain, 0)

    def get_rx_lo_off(self):
        return self.rx_lo_off

    def set_rx_lo_off(self, rx_lo_off):
        self.rx_lo_off = rx_lo_off
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.rx_freq,self.rx_lo_off), 0)

    def get_rx_samp_rate(self):
        return self.rx_samp_rate

    def set_rx_samp_rate(self, rx_samp_rate):
        self.rx_samp_rate = rx_samp_rate
        self.blocks_head_0.set_length((int(self.cap_len*self.rx_samp_rate)))
        self.uhd_usrp_source_0.set_samp_rate(self.rx_samp_rate)

    def get_skip(self):
        return self.skip

    def set_skip(self, skip):
        self.skip = skip



def argument_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "--cap-len", dest="cap_len", type=eng_float, default=eng_notation.num_to_str(float(0.512)),
        help="Set cap_len [default=%(default)r]")
    parser.add_argument(
        "--device", dest="device", type=str, default="addr=192.168.10.2",
        help="Set device [default=%(default)r]")
    parser.add_argument(
        "--output-file", dest="output_file", type=str, default="/root/received_samples.dat",
        help="Set /root/received_samples.dat [default=%(default)r]")
    parser.add_argument(
        "--rx-freq", dest="rx_freq", type=eng_float, default=eng_notation.num_to_str(float(2462e6)),
        help="Set rx_freq [default=%(default)r]")
    parser.add_argument(
        "--rx-gain", dest="rx_gain", type=eng_float, default=eng_notation.num_to_str(float(0.5)),
        help="Set rx_gain [default=%(default)r]")
    parser.add_argument(
        "--rx-lo-off", dest="rx_lo_off", type=eng_float, default=eng_notation.num_to_str(float(10e6)),
        help="Set rx_lo_off [default=%(default)r]")
    parser.add_argument(
        "--rx-samp-rate", dest="rx_samp_rate", type=eng_float, default=eng_notation.num_to_str(float(25e6)),
        help="Set rx_samp_rate [default=%(default)r]")
    parser.add_argument(
        "--skip", dest="skip", type=eng_float, default=eng_notation.num_to_str(float(2)),
        help="Set skip [default=%(default)r]")
    return parser


def main(top_block_cls=receive_capture, options=None):
    if options is None:
        options = argument_parser().parse_args()
    tb = top_block_cls(cap_len=options.cap_len, device=options.device, output_file=options.output_file, rx_freq=options.rx_freq, rx_gain=options.rx_gain, rx_lo_off=options.rx_lo_off, rx_samp_rate=options.rx_samp_rate, skip=options.skip)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    tb.wait()


if __name__ == '__main__':
    main()
