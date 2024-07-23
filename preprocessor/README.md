This is a heavily refactored version of the WiSig dataset prep code.

Here's the original repo: [link](https://github.com/WiSig-dataset/wisig-process-raw/)

How does it work:

1. Launch frame_detection
2. Launch frame_equalization
3. Launch pkl_creation notebook


How to run prepare.py:

1. Launch Matlab on your device
2. Share Matlab engine:

    1. Check if there's an engine already: `matlab.engine.engineName`
    2. If the engine isn't shared, create share: `matlab.engine.shareEngine('mobintel_engine')`

3. Launch the pre-processing script: `python3 prepare.py`

    1. Specify the preamble length: `400 for 25 Msps, 320 for 20 Msps`
    2. Specify the Matlab engine: `mobintel_engine`