from intaninterface import IntanInterface
import multiprocessing as mp
from time import time
import os

def multiprocess_arm(interface, timeframe, arm, q):
    measure = interface.detectFlexing(timeframe=timeframe)
    
    q.put((arm, measure))

if __name__ == "__main__":
    debug=False
    arms = {}
    
    # Intro
    print("##########################################")
    print("# Welcome to Intan Control Interface.")
    print("# ECE202 W24 Group 7")
    print()
    print("This interface requires two electrodes/channels for EMG recording, one for each arm")
    
    # Connect Right Arm
    print("\033[91mPlease turn on RIGHT Arm's Intan TCP Control with \033[93m\033[1mCommands to 127.0.0.1:5000\033[91m and \033[93m\033[1mOutput to 127.0.0.1:5001\033[0m")
    input("Press ENTER when ready to connect.")
    arms['right'] = IntanInterface(('127.0.0.1', 5000), ('127.0.0.1', 5001), debug=debug)
    
    # Connect Left Arm
    print("\033[91mPlease turn on LEFT Arm's Intan TCP Control with \033[93m\033[1mCommands to 127.0.0.1:5002\033[91m and \033[93m\033[1mOutput to 127.0.0.1:5003\033[0m")
    input("Press ENTER when ready to connect.")
    arms['left'] = IntanInterface(('127.0.0.1', 5002), ('127.0.0.1', 5003), debug=debug)
    print()
    
    # Get Channel Numbers
    rightchannel = int(input("Please input left arm's channel number (e.g. 23): "))
    leftchannel = int(input("Please input right arm's channel number (e.g. 23): "))
    
    # Setup and Calibration
    input("Electrodes must be calibrated. When ready press ENTER to begin calibration of both arms")
    print("\033[96mCalibrating RIGHT arm...\033[0m")
    arms['right'].setup(recordtime=5, channel=rightchannel)
    print("\033[96mCalibrating LEFT arm...\033[0m")
    arms['left'].setup(recordtime=3, channel=leftchannel)

    processes = []
    timeframe=0.5
    # Repeat until quit
    start = time()
    controlqueue = []
    while True:
        outputs = mp.Queue()
        
        # Start thread of both arms
        for arm , interface in arms.items():
            p = mp.Process(target=multiprocess_arm, args=(interface, timeframe, arm, outputs))
            processes.append(p)
            p.start()

        # Rejoin thread
        for p in processes:
            p.join()
            
        controls = {}
        # Check thread output (if arm was flexed or not)
        for _ in range(0, 2):
            arm, flex = outputs.get(False)
            controls[arm] = flex
            
        controlqueue.append(f"{controls['left']}, {controls['right']}")
        
        if not os.path.exists('control.csv'):
            with open('control.csv', 'w') as file:
                file.write(controlqueue.pop(0))
        
    print("Elapsed:", time() - start)