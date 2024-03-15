from intaninterface import IntanInterface
from time import time, sleep
import os

if __name__ == "__main__":
    debug=False
    arms = {}
    
    # Intro
    print("##########################################")
    print("# Welcome to Intan Control Interface.")
    print("# ECE202 W24 Group 7")
    print()
    print("This interface requires one electrodes/channels for EMG recording")
    
    # Connect Right Arm
    print("\033[91mPlease turn on the Intan TCP Control with \033[93m\033[1mCommands to 127.0.0.1:5000\033[91m and \033[93m\033[1mOutput to 127.0.0.1:5001\033[0m")
    input("Press ENTER when ready to connect.")
    interface = IntanInterface(('127.0.0.1', 5000), ('127.0.0.1', 5001), debug=debug)
    
    # Get Channel Numbers
    rightchannel = int(input("Please input arm's channel number (e.g. 23): "))
    
    # Setup and Calibration
    input("Electrodes must be calibrated. When ready press ENTER to begin calibration.")
    print("\033[96mCalibrating arm...\033[0m")
    interface.setup(recordtime=3, channel=rightchannel)

    processes = []
    timeframe=0.2
    # Repeat until quit
    start = time()
    while True:
        measure = interface.detectFlexing(timeframe=timeframe)
        print(measure)    
        
        with open('control.csv', 'w') as file:
            file.write(str(measure))
        sleep(0.2)
        
    print("Elapsed:", time() - start)