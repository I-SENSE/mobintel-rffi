#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Receive Capture
# Generated: Fri Jan  8 14:11:14 2021
##################################################

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import time


class receive_capture(gr.top_block):

    def __init__(self, args="addr=192.168.10.2", cap_len=1, fname="received_samples.dat", rx_freq=915e6, rx_gain=0.8, rx_lo_off=1e6, rx_samp_rate=1e6, skip=1):
        gr.top_block.__init__(self, "Receive Capture")

        ##################################################
        # Parameters
        ##################################################
        self.args = args
        self.cap_len = cap_len
        self.fname = fname
        self.rx_freq = rx_freq
        self.rx_gain = rx_gain
        self.rx_lo_off = rx_lo_off
        self.rx_samp_rate = rx_samp_rate
        self.skip = skip

        ##################################################
        # Blocks
        ##################################################
        self.uhd_usrp_source_0 = uhd.usrp_source(
        	",".join((args, "")),
        	uhd.stream_args(
        		cpu_format="fc32",
        		channels=range(1),
        	),
        )
        self.uhd_usrp_source_0.set_samp_rate(rx_samp_rate)
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(rx_freq,rx_lo_off), 0)
        self.uhd_usrp_source_0.set_normalized_gain(rx_gain, 0)
        self.uhd_usrp_source_0.set_auto_dc_offset(True, 0)
        self.uhd_usrp_source_0.set_auto_iq_balance(True, 0)
        self.blocks_skiphead_0 = blocks.skiphead(gr.sizeof_gr_complex*1, int(skip*rx_samp_rate))
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, int(cap_len*rx_samp_rate))
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex*1, fname, False)
        self.blocks_file_sink_0.set_unbuffered(True)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_head_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.blocks_skiphead_0, 0), (self.blocks_head_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_skiphead_0, 0))

    def get_args(self):
        return self.args

    def set_args(self, args):
        self.args = args

    def get_cap_len(self):
        return self.cap_len

    def set_cap_len(self, cap_len):
        self.cap_len = cap_len
        self.blocks_head_0.set_length(int(self.cap_len*self.rx_samp_rate))

    def get_fname(self):
        return self.fname

    def set_fname(self, fname):
        self.fname = fname
        self.blocks_file_sink_0.open(self.fname)

    def get_rx_freq(self):
        return self.rx_freq

    def set_rx_freq(self, rx_freq):
        self.rx_freq = rx_freq
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.rx_freq,self.rx_lo_off), 0)

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.uhd_usrp_source_0.set_normalized_gain(self.rx_gain, 0)


    def get_rx_lo_off(self):
        return self.rx_lo_off

    def set_rx_lo_off(self, rx_lo_off):
        self.rx_lo_off = rx_lo_off
        self.uhd_usrp_source_0.set_center_freq(uhd.tune_request(self.rx_freq,self.rx_lo_off), 0)

    def get_rx_samp_rate(self):
        return self.rx_samp_rate

    def set_rx_samp_rate(self, rx_samp_rate):
        self.rx_samp_rate = rx_samp_rate
        self.uhd_usrp_source_0.set_samp_rate(self.rx_samp_rate)
        self.blocks_head_0.set_length(int(self.cap_len*self.rx_samp_rate))

    def get_skip(self):
        return self.skip

    def set_skip(self, skip):
        self.skip = skip


def argument_parser():
    parser = OptionParser(usage="%prog: [options]", option_class=eng_option)
    parser.add_option(
        "", "--args", dest="args", type="string", default="addr=192.168.10.2",
        help="Set args [default=%default]")
    parser.add_option(
        "", "--cap-len", dest="cap_len", type="eng_float", default=eng_notation.num_to_str(1),
        help="Set cap_len [default=%default]")
    parser.add_option(
        "", "--fname", dest="fname", type="string", default="received_samples.dat",
        help="Set received_samples.dat [default=%default]")
    parser.add_option(
        "", "--rx-freq", dest="rx_freq", type="eng_float", default=eng_notation.num_to_str(915e6),
        help="Set rx_freq [default=%default]")
    parser.add_option(
        "", "--rx-gain", dest="rx_gain", type="eng_float", default=eng_notation.num_to_str(0.8),
        help="Set rx_gain [default=%default]")
    parser.add_option(
        "", "--rx-lo-off", dest="rx_lo_off", type="eng_float", default=eng_notation.num_to_str(1e6),
        help="Set rx_lo_off [default=%default]")
    parser.add_option(
        "", "--rx-samp-rate", dest="rx_samp_rate", type="eng_float", default=eng_notation.num_to_str(1e6),
        help="Set rx_samp_rate [default=%default]")
    parser.add_option(
        "", "--skip", dest="skip", type="eng_float", default=eng_notation.num_to_str(1),
        help="Set skip [default=%default]")
    return parser


def main(top_block_cls=receive_capture, options=None):
    if options is None:
        options, _ = argument_parser().parse_args()

    tb = top_block_cls(args=options.args, cap_len=options.cap_len, fname=options.fname, rx_freq=options.rx_freq, rx_gain=options.rx_gain, rx_lo_off=options.rx_lo_off, rx_samp_rate=options.rx_samp_rate, skip=options.skip)
    tb.start()
    tb.wait()


if __name__ == '__main__':
    main()
