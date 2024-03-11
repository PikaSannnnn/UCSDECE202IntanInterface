import socket
from intanutils import *
from time import sleep
import numpy as np
import pywt
import matplotlib.pyplot as plt

HOST = '127.0.0.1'
PORT = 5001

class IntanInterface:
    def __init__(self, cmdAddrPort, waveAddrPort, focusFreq=25, debug=False):
        self.__debug = debug
        self.focusFreq = focusFreq

        # Connect to TCP command server - default home IP address at port 5000.
        print('Connecting to TCP command server...')
        self.cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cmd.connect(cmdAddrPort)

        # Connect to TCP waveform server - default home IP address at port 5001.
        print('Connecting to TCP waveform server...')
        self.wave = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.wave.connect(waveAddrPort)
        
        # Init any constant vars NOTE: Change here to reflect to all objects
        self.buffersize = 200000
        self.frames_per_block = 128
        self.wavelet = 'mexh'
        self.threshRatio = 0.75
    
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
        commandReturn = str(self.cmd.recv(self.buffersize), "utf-8")
        
        # If controller is running, stop it.
        if commandReturn != "Return: RunMode Stop":
            self.cmd.sendall(b'set runmode stop')
            # Allow time for RHX software to accept this command before the next.
            sleep(0.1)

        # Query sample rate from RHX software.
        self.cmd.sendall(b'get sampleratehertz')
        commandReturn = str(self.cmd.recv(self.buffersize), "utf-8")
        expectedReturnString = "Return: SampleRateHertz "
        # Look for "Return: SampleRateHertz N" where N is the sample rate.
        if commandReturn.find(expectedReturnString) == -1:
            raise GetSampleRateFailure(
                'Unable to get sample rate from server.'
            )
        
        self.timestep = 1 / float(commandReturn[len(expectedReturnString):])
        
        self.calibrations = []
        for _ in range(0, self.numChannels):
            self.calibrations.append(self.calibrate(recordtime=recordtime))

    def calibrate(self, recordtime=1):
        """Time for calibration **per** action, i.e. if recordtime=5, it is 5 seconds for resting and 5 seconds for flexing
        
        recordtime: Time for calibration per action; thus, total calibration recordtime is recordtime * 2 (+ 16 seconds buffer/prep)
        
        Returns: 
        """
        calibrations = {}
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
            
            # Comptue CWT
            coef, freq = self.computeCWT(data)

            # Comput mean at object's freq
            mean = np.mean(np.abs(coef[self.focusFreq]))
            print("Mean Power: ", mean)
            calibrations[mode] = mean
            
            # Debug view CWT Spectrogram
            if self.__debug:
                self.viewCWT(coef)

        threshDiff = (calibrations['Flexing'] - calibrations['Resting']) * self.threshRatio
        self.flexThresh = calibrations['Resting'] + threshDiff
        print("FlexThres: ", self.flexThresh)

    def detectFlexing(self, timeframe=1):
        timestamps, data = self.recordRead(timeframe)

        # Comptue CWT
        coef, freq = self.computeCWT(data)

        # Comput mean at object's freq
        mean = np.mean(np.abs(coef[self.focusFreq]))

        return mean > self.flexThresh

    def recordRead(self, recordtime):
        self.record(recordtime)
        return self.readWaveform(recordtime)

    def record(self, recordtime):
        self.cmd.sendall(b'set runmode run')
        sleep(recordtime)
        self.cmd.sendall(b'set runmode stop')
    
    def readWaveform(self, recordtime):
        waveformBytesPerFrame = 4 + (2 * self.numChannels)
        waveformBytesPerBlock = self.frames_per_block * waveformBytesPerFrame + 4    # 4 bytes = magic number;
        
        # Read waveform data
        rawData = self.wave.recv(self.numChannels * self.buffersize * (int(recordtime + 1)))
        # print(len(rawData)) # Note: Each second at 30Hz = 129696 data points
        # print(waveformBytesPerBlock)
        if len(rawData) % waveformBytesPerBlock != 0:
            raise InvalidReceivedDataSize(
                'An unexpected amount of data arrived that is not an integer '
                'multiple of the expected data size per block.'
            )
        numBlocks = int(len(rawData) / waveformBytesPerBlock)
        # print(numBlocks)

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
            for _ in range(self.frames_per_block):
                # Expect 4 bytes to be timestamp as int32.
                rawTimestamp, rawIndex = readInt32(rawData, rawIndex)

                # Multiply by 'timestep' to convert timestamp to seconds
                amplifierTimestamps.append(rawTimestamp * self.timestep)

                # Expect 2 bytes of wideband data.
                rawSample, rawIndex = readUint16(rawData, rawIndex)

                # Scale this sample to convert to microVolts
                amplifierData.append(0.195 * (rawSample - 32768))
                
        return np.array(amplifierTimestamps), np.array(amplifierData)

    def computeCWT(self, data):
        scales = np.arange(1, 128, 4)

        return pywt.cwt(data, scales, self.wavelet)
    
    def viewCWT(self, coefs):
        plt.figure(figsize=(12, 6))
        plt.imshow(np.abs(coefs),
                aspect='auto', cmap='jet', origin='lower')
        plt.colorbar(label='Wavelet Power')
        plt.xlabel('Time (s)')
        plt.ylabel('Frequency (Hz)')
        plt.title(f'{self.wavelet} Wavelet Power Spectrum of EMG Signal')
        plt.show()
        
    
    def switchChannel(self, channelNum):
        # Clear all outputs
        self.cmd.sendall(b'execute clearalldataoutputs')
        sleep(0.1)
        
        # Activate channel to switch to
        fullCmd = f"set a-%03.f.tcpdataoutputenabled true" % channelNum
        self.cmd.sendall(bytes(fullCmd, 'utf-8'))
        sleep(0.1)

if __name__ == "__main__":
    interface = IntanInterface(('127.0.0.1', 5000), ('127.0.0.1', 5001), debug=True)
    interface.setup(recordtime=3, numChannels=1)

    measured = []
    for i in range(0, 80):
        measure = interface.detectFlexing(timeframe=0.25)
        print(measure)
        measured.append(measure)
        sleep(0.5)