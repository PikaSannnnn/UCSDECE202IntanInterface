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
    arms['right'] = IntanInterface(('127.0.0.1', 5000), ('127.0.0.1', 5001), debug=debug)
    print("Setting up right arm")
    arms['right'].setup(recordtime=5, channel=23)
    
    arms['left'] = IntanInterface(('127.0.0.1', 5002), ('127.0.0.1', 5003), debug=debug)
    print("Setting up left arm")
    arms['left'].setup(recordtime=3, channel=23)

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