### Mobintel RFFI Project

More details coming soon...

Don't forget to calibrate the USRP before starting reception!
Ref: https://files.ettus.com/manual/page_calibration.html

Commands:

`uhd_cal_rx_iq_balance --verbose --args="addr=192.168.10.2"`
`uhd_cal_tx_iq_balance --verbose --args="addr=192.168.10.2"`
`uhd_cal_tx_dc_offset --verbose --args="addr=192.168.10.2"`