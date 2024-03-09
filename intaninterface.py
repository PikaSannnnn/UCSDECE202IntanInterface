import socket
from intanutils import *
from time import sleep
import numpy as np
import matplotlib.pyplot as plt

HOST = '127.0.0.1'
PORT = 5001
BUFFERSIZE = 200000
FRAMES_PER_BLOCK = 128 

class IntanInterface:
    def __init__(self, cmdAddrPort, waveAddrPort):
        # Connect to TCP command server - default home IP address at port 5000.
        print('Connecting to TCP command server...')
        self.cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cmd.connect(cmdAddrPort)

        # Connect to TCP waveform server - default home IP address at port 5001.
        print('Connecting to TCP waveform server...')
        self.wave = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.wave.connect(waveAddrPort)
    
    def setup(self, **kwargs):
        """
        Opt Inputs:
            numChannels: number of recording channels
            recordtime: recording time; this will be used for calibration
        """
        self.numChannels = 1 if 'numChannels' not in kwargs else kwargs['numChannels']
        recordtime = 1 if 'recordtime' not in kwargs else kwargs['recordtime']
        
        ## Setup Intan Software
        # Query runmode from RHX software.
        self.cmd.sendall(b'get runmode')
        commandReturn = str(self.cmd.recv(BUFFERSIZE), "utf-8")
        
        # If controller is running, stop it.
        if commandReturn != "Return: RunMode Stop":
            self.cmd.sendall(b'set runmode stop')
            # Allow time for RHX software to accept this command before the next.
            sleep(0.1)

        # Query sample rate from RHX software.
        self.cmd.sendall(b'get sampleratehertz')
        commandReturn = str(self.cmd.recv(BUFFERSIZE), "utf-8")
        expectedReturnString = "Return: SampleRateHertz "
        # Look for "Return: SampleRateHertz N" where N is the sample rate.
        if commandReturn.find(expectedReturnString) == -1:
            raise GetSampleRateFailure(
                'Unable to get sample rate from server.'
            )
        
        self.timestep = 1 / float(commandReturn[len(expectedReturnString):])
        
        self.calibrate(recordtime=recordtime)

    def calibrate(self, recordtime=1):
        """Time for calibration **per** action, i.e. if recordtime=5, it is 5 seconds for resting and 5 seconds for flexing
        
        recordtime: Time for calibration per action; thus, total calibration recordtime is recordtime * 2 (+ 16 seconds buffer/prep)
        
        Returns: 
        """
        self.stds = {}
        modes = ["Resting", "Flexing"]
        
        # Run controller for 10 seconds for calibration
        for mode in modes:
            print(f"Running {mode} calibration for {recordtime} seconds. Please begin {mode}.")
            print("Beginning in 5 seconds...")
            sleep(1)
            for i in range(4, 0, -1):
                print(f"{i}...")
                sleep(1)
            print("Calibrating...")
            
            # run for `recordtime` amount of seconds
            self.record(recordtime)
            print("Finished...")
            sleep(2)
            
            # Read waveform
            timestamps, data = self.readWaveform(recordtime)
            
            # Plot the data that was read
            # plt.plot(timestamps, data)
            # plt.title('Amplifier Data')
            # plt.xlabel('Time (s)')
            # plt.ylabel('Voltage (uV)')
            # plt.show()
            
            # absdata = np.abs(data)
            # potential = np.mean(absdata)
            # self.stds[mode] = np.std(np.abs(data))
            self.stds[mode] = np.std(data)
            # print(f"{mode} Mean Potential: {potential}")
            print(f"{mode} Std. Dev. Potential: {self.stds[mode]}")
            abs_emg_signal = data
            # abs_emg_signal = np.abs(data)

            # Windowing: Divide the signal into windows (here, each window contains 3 samples)
            window_size = 3
            num_windows = len(data) // window_size

            # Amplitude Calculation: Find the maximum absolute value in each window
            window_amplitudes = [np.max(abs_emg_signal[i*window_size:(i+1)*window_size]) for i in range(num_windows)]

            # Average Calculation: Compute the average amplitude
            average_amplitude = np.mean(window_amplitudes)

            print("Average Amplitude:", average_amplitude)
            sleep(3)

        threshold_diff = (self.stds['Flexing'] - self.stds['Resting']) * 0.1
        self.flexThresh = self.stds['Resting'] + threshold_diff
        print(f"FlexThreshold: {self.flexThresh}")

    def detectFlexing(self, timeframe=0.5):
        timestamps, data = self.recordRead(timeframe)
        std = np.std(data)
        # std = np.std(np.abs(data))
        print(std)

        return std > self.flexThresh

    def recordRead(self, recordtime):
        self.record(recordtime)
        return self.readWaveform(recordtime)

    def record(self, recordtime):
        self.cmd.sendall(b'set runmode run')
        sleep(recordtime)
        self.cmd.sendall(b'set runmode stop')
    
    def readWaveform(self, recordtime):
        waveformBytesPerFrame = 4 + (2 * self.numChannels)
        waveformBytesPerBlock = FRAMES_PER_BLOCK * waveformBytesPerFrame + 4    # 4 bytes = magic number;
        
        # Read waveform data
        rawData = self.wave.recv(self.numChannels * BUFFERSIZE * (recordtime + 1))
        print(len(rawData)) # Note: Each second at 30Hz = 129696 data points
        print(waveformBytesPerBlock)
        if len(rawData) % waveformBytesPerBlock != 0:
            raise InvalidReceivedDataSize(
                'An unexpected amount of data arrived that is not an integer '
                'multiple of the expected data size per block.'
            )
        numBlocks = int(len(rawData) / waveformBytesPerBlock)
        print(numBlocks)

        # Index used to read the raw data that came in through the TCP socket.
        rawIndex = 0

        # List used to contain scaled timestamp values in seconds.
        amplifierTimestamps = []

        # List used to contain scaled amplifier data in microVolts.
        amplifierData = []

        for _ in range(numBlocks):
            # Expect 4 bytes to be TCP Magic Number as uint32.
            # If not what's expected, raise an exception.
            magicNumber, rawIndex = readUint32(rawData, rawIndex)
            if magicNumber != 0x2ef07a08:
                raise InvalidMagicNumber('Error... magic number incorrect')

            # Each block should contain 128 frames of data - process each
            # of these one-by-one
            for _ in range(FRAMES_PER_BLOCK):
                # Expect 4 bytes to be timestamp as int32.
                rawTimestamp, rawIndex = readInt32(rawData, rawIndex)

                # Multiply by 'timestep' to convert timestamp to seconds
                amplifierTimestamps.append(rawTimestamp * self.timestep)

                # Expect 2 bytes of wideband data.
                rawSample, rawIndex = readUint16(rawData, rawIndex)

                # Scale this sample to convert to microVolts
                amplifierData.append(0.195 * (rawSample - 32768))
                
        return amplifierTimestamps, amplifierData

if __name__ == "__main__":
    interface = IntanInterface(('127.0.0.1', 5000), ('127.0.0.1', 5001))
    interface.setup(recordtime=5, numChannels=1)
    for _ in range(0, 4):
        print(interface.detectFlexing(5))