from intaninterface import IntanInterface
import multiprocessing as mp
from time import time

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
    # while True:
    for _ in range(0, 40):  # 0.5 * 80 = 20s
        outputs = mp.Queue()
        
        # Start thread of both armsuu
        for arm , interface in arms.items():
            p = mp.Process(target=multiprocess_arm, args=(interface, timeframe, arm, outputs))
            processes.append(p)
            p.start()

        # Rejoin thread
        for p in processes:
            p.join()
            
        flex_bits = 0x00
        arm_bits = {'left': 0x10, 'right': 0x01}
        # Check thread output (if arm was flexed or not)
        for _ in range(0, 2):
            arm, flex = outputs.get(False)
            if flex:
                flex_bits |= arm_bits[arm]
                
        # Game Commands
        print("---")
        if flex_bits & 0x01 == 0x01:
            print("Move")
        if flex_bits & 0x10 == 0x10:
            print("Click")
            
    print("Elapsed:", time() - start)