This is a heavily refactored version of the WiSig dataset prep code.

Here's the original repo: [link](https://github.com/WiSig-dataset/wisig-process-raw/)

How does it work:

1. Launch frame_detection
2. Launch frame_equalization
3. Launch pkl_creation notebook


How to run prepare.py:

On macOS: 

1. Ensure that you can launch matlab in Terminal: `alias matlab="/Applications/MATLAB_R2024a.app/bin/matlab"`

    Optionally, add it to ~/.bash_profile, and then run `source ~/.bash_profile` 

2. In multiple terminal windows, open N matlab sessions: `matlab -nodesktop -r "matlab.engine.shareEngine('mobintel_session_M')"`

    * N would need to be changed to the index of your session
    * Start as many sessions as you specified in the `MATLAB_SESSION_NAMES` list in the script



1. Launch Matlab on your device
2. Share Matlab engine:

    1. Check if there's an engine already: `matlab.engine.engineName`
    2. If the engine isn't shared, create share: `matlab.engine.shareEngine('mobintel_engine')`

3. Launch the pre-processing script: `python3 prepare.py`

    1. Specify the preamble length: `400 for 25 Msps, 320 for 20 Msps`
    2. Specify the Matlab engine: `mobintel_engine`