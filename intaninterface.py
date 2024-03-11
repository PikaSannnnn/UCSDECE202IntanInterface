import socket
from interfaceutils import *
from time import sleep
import numpy as np
import pywt
import matplotlib.pyplot as plt

HOST = '127.0.0.1'
PORT = 5001

class IntanInterface:
    def __init__(self, cmdAddrPort, waveAddrPort, timeout=5, debug=False):
        # Init immutable constants.
        self.__debug = debug
        self.__setup_lock = False
        
        # Init any mutable constant vars NOTE: Change here to reflect to all objects, or change externally for single object
        self.buffersize = 200000
        self.frames_per_block = 128
        self.wavelet = 'mexh'
        self.threshRatio = 0.75

        # Connect to TCP command server - default home IP address at port 5000.
        print('Connecting to TCP command server...')
        try: 
            self.cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd.settimeout(timeout)  # Set connection timeout
            self.__debugOut(f"Attempting to connect to {cmdAddrPort}. Timeout = 5s")
            self.cmd.connect(cmdAddrPort)
        except socket.timeout:
            print("Connection timeout. Please make sure TCP command port is connected on Intan")
            exit(1)
        except Exception as e:
            print(f"Some error occured: {e}.\nPlease check your TCP waveform port on Intan.")
            exit(1)
        print(f"Connected to {cmdAddrPort[0]}:{cmdAddrPort[1]}")

        # Connect to TCP waveform server - default home IP address at port 5001.
        print('Connecting to TCP waveform server...')
        try:
            self.wave = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.wave.settimeout(timeout)  # Set connection timeout
            self.__debugOut(f"Attempting to connect to {waveAddrPort}. Timeout = 5s")
            self.wave.connect(waveAddrPort)
        except socket.timeout:
            print("Connection timeout. Please make sure TCP waveform port is connected on Intan.")
            exit(1)
        except Exception as e:
            print(f"Some error occured: {e}.\nPlease check your TCP waveform port on Intan.")
            exit(1)
        print(f"Connected to {cmdAddrPort[0]}:{cmdAddrPort[1]}")
    
    def setup(self, **kwargs):
        """
        Opt Inputs:
            channel: channel number
            recordtime: recording time; this will be used for calibration
        """
        override = False if 'override' not in kwargs else kwargs['override']
        if self.__setup_lock and not override:
            self.__debugOut("Re-setup blocked by __setup_lock. To re-setup, use override=True.")
            raise SetupReplaceReject(
                'Reject action to re-setup/calibrate an IntanInterface object.'
            )
        
        recordtime = 1 if 'recordtime' not in kwargs else kwargs['recordtime']
        self.__channel = 0 if 'channel' not in kwargs else kwargs['channel']
        self.focusfreq = 25 if 'focusfreq' not in kwargs else kwargs['focusfreq']
        self.__debugOut(f"Setup: recordtime={recordtime}, channel={self.__channel}, focusfreq={self.focusfreq}")
        
        ## Setup Intan Software
        # Query runmode from RHX software.
        self.cmd.sendall(b'get runmode')
        commandReturn = str(self.cmd.recv(self.buffersize), "utf-8")
        
        # If controller is running, stop it.
        if commandReturn != "Return: RunMode Stop":
            self.__debugOut("Stopping controller...")
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
        
        # Activate Channel
        self.activateChannel()
        
        # Calibrate electrode 
        self.calibrate(recordtime=recordtime)
        
        self.__setup_lock = True

    def calibrate(self, **kwargs):
        """Time for calibration **per** action, i.e. if recordtime=5, it is 5 seconds for resting and 5 seconds for flexing
        
        recordtime: Time for calibration per action; thus, total calibration recordtime is recordtime * 2 (+ 16 seconds buffer/prep)
        
        Returns: 
        """
        override = False if 'override' not in kwargs else kwargs['override']
        if self.__setup_lock and not override:
            self.__debugOut("Re-calibration blocked by __setup_lock. To re-calibrate, use override=True.")
            raise ChannelChangeReject(
                'Reject action to change channel.'
            )
            
        recordtime = 1 if 'recordtime' not in kwargs else kwargs['recordtime']
        self.__debugOut(f"Calibration: recordtime={recordtime}, threshRatio={self.threshRatio}")
        
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
            print("Finished.")
            sleep(2)
            
            # Read waveform
            timestamps, data = self.readWaveform(recordtime)
            
            # Comptue CWT
            coef, freq = self.computeCWT(data)

            # Comput mean at object's freq
            mean = np.mean(np.abs(coef[self.focusfreq]))
            self.__debugOut(f"Mean {mode} Power: ", mean)
            calibrations[mode] = mean
            
            # Debug view CWT Spectrogram
            if self.__debug:
                self.viewCWT(coef)

        threshDiff = (calibrations['Flexing'] - calibrations['Resting']) * self.threshRatio
        self.flexThresh = calibrations['Resting'] + threshDiff
        print("Threshold for Flexing classification: ", self.flexThresh)

    def detectFlexing(self, timeframe=1):
        timestamps, data = self.recordRead(timeframe)

        # Comptue CWT
        coef, freq = self.computeCWT(data)

        # Comput mean at object's freq
        mean = np.mean(np.abs(coef[self.focusfreq]))
        self.__debugOut(f"Sample Mean Power: {mean}")

        return mean > self.flexThresh

    def recordRead(self, recordtime):
        self.record(recordtime)
        return self.readWaveform(recordtime)

    def record(self, recordtime):
        self.__debugOut("Start recording")
        self.cmd.sendall(b'set runmode run')
        sleep(recordtime)
        self.__debugOut("Stop recording")
        self.cmd.sendall(b'set runmode stop')
    
    def readWaveform(self, recordtime):
        waveformBytesPerFrame = 4 + 2
        waveformBytesPerBlock = self.frames_per_block * waveformBytesPerFrame + 4    # 4 bytes = magic number;
        
        # Read waveform data
        rawData = self.wave.recv(self.buffersize * (int(recordtime + 1)))
        self.__debugOut("Raw data length:", len(rawData)) # Note: Each second at 30Hz = 129696 data points
        self.__debugOut("Waveform Bytes Per Block:", waveformBytesPerBlock)
        if len(rawData) % waveformBytesPerBlock != 0:
            raise InvalidReceivedDataSize(
                'An unexpected amount of data arrived that is not an integer '
                'multiple of the expected data size per block.'
            )
        numBlocks = int(len(rawData) / waveformBytesPerBlock)
        self.__debugOut("# Blocks:", numBlocks)

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
        self.__debugOut("Scale:", scales)

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
        
    
    def activateChannel(self, override=False):
        if self.__setup_lock and not override:
            raise ChannelChangeReject(
                'Reject action to re-active/change channel. Doing this does not re-setup/calibrate.\nIf you are sure of this, use override=True.'
            )
        
        # Clear all outputs
        self.__debugOut("Clearing All Data Outputs")
        self.cmd.sendall(b'execute clearalldataoutputs')
        sleep(0.1)
        
        # Activate channel to switch to this object's channel
        fullCmd = f"set a-%03.f.tcpdataoutputenabled true" % self.__channel
        self.cmd.sendall(bytes(fullCmd, 'utf-8'))
        sleep(0.1)
        
        print(f"Activated channel A-%03.f" % self.__channel)
        
    def __debugOut(self, *args):
        if self.__debug:
            print("[DEBUG]", *args)

if __name__ == "__main__":
    interface = IntanInterface(('127.0.0.1', 5000), ('127.0.0.1', 5001), debug=True)
    interface.setup(recordtime=3, channel=23)

    measured = []
    for i in range(0, 80):
        measure = interface.detectFlexing(timeframe=0.25)
        measured.append(measure)
        sleep(0.5)
    print(measured)