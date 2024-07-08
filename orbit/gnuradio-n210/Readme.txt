Running this script requires using gnuradio 3.7

This is the command



capLen=0.512
rxFreq=2462e6
rxGain=0.5
rxLoOff=10e6
rxSampRate=25e6
skip=2
fname=filename
mmip=192.168.10.2


python receive_capture.py --cap-len $capLen --rx-freq $rxFreq --rx-gain $rxGain --rx-lo-off $rxLoOff --rx-samp-rate $rxSampRate --skip $skip --fname $fname --args addr=$mmip #> /dev/null 2>&1 
