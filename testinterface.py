from intaninterface import IntanInterface
import multiprocessing as mp

def multiprocess_arm(interface, timeframe, arm, q):
    measure = interface.detectFlexing(timeframe=timeframe)
    
    q.put((arm, measure))

if __name__ == "__main__":
    arms = []
    arms['right'] = IntanInterface(('127.0.0.1', 5000), ('127.0.0.1', 5001), debug=True)
    print("Setting up right arm")
    arms['right'].setup(recordtime=5, channel=23)
    arms['left'] = IntanInterface(('127.0.0.1', 5002), ('127.0.0.1', 5003), debug=True)
    print("Setting up left arm")
    arms['left'].setup(recordtime=3, channel=23)

    processes = []
    timeframe=0.25

    # Repeat until quit
    for _ in range(0, 80):  # 0.25 * 80 = 20s
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
outputs = [('left', True), ('right', False)]
arm_bits = {'left':0x10, 'right':0x01}
# Check thread output (if arm was flexed or not)
for arm, flex in outputs:
    if flex:
        print(arm_bits[arm])
        flex_bits |= arm_bits[arm]
        
print(flex_bits)