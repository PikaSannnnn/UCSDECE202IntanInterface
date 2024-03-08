import socket
from time import sleep
import numpy as np
import matplotlib.pyplot as plt

HOST = '127.0.0.1'
PORT = 5001
BUFFERSIZE = 200000
FRAMES_PER_BLOCK = 128  

def readUint32(array, arrayIndex):
    """Reads 4 bytes from array as unsigned 32-bit integer.
    """
    variableBytes = array[arrayIndex: arrayIndex + 4]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=False)
    arrayIndex = arrayIndex + 4
    return variable, arrayIndex


def readInt32(array, arrayIndex):
    """Reads 4 bytes from array as signed 32-bit integer.
    """
    variableBytes = array[arrayIndex: arrayIndex + 4]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=True)
    arrayIndex = arrayIndex + 4
    return variable, arrayIndex


def readUint16(array, arrayIndex):
    """Reads 2 bytes from array as unsigned 16-bit integer.
    """
    variableBytes = array[arrayIndex: arrayIndex + 2]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=False)
    arrayIndex = arrayIndex + 2
    return variable, arrayIndex

def calibrate(socket, time=5, numChannels=1):
    """Time for calibration **per** action, i.e. if time=5, it is 5 seconds for resting and 5 seconds for flexing
    
    time: Time for calibration per action; thus, total calibration time is time * 2 (+ 16 seconds buffer/prep)
    
    Returns: 
    """
    calibrations = []
    modes = ["Resting", "Flexing"]
    
    # Run controller for 10 seconds for calibration
    for mode in modes:
        print(f"Running {mode} calibration for {time} seconds")
        print("Beginning in 5 seconds...")
        sleep(1)
        print("4...")
        sleep(1)
        print("3...")
        sleep(1)
        print("2...")
        sleep(1)
        print("1...")
        sleep(1)
        print("Calibrating...")
        
        # socket.recv(BUFFERSIZE * (recordtime + 1))  # Clear Buffer
        scommand.sendall(b'set runmode run')
        sleep(recordtime)
        scommand.sendall(b'set runmode stop')
        print("Finished...")
        sleep(2)
        timestamps, data = readWaveform(socket, time, numChannels)
        
        plt.plot(timestamps, data)
        plt.title('Amplifier Data')
        plt.xlabel('Time (s)')
        plt.ylabel('Voltage (uV)')
        plt.show()
        
        potential = np.mean(np.abs(data))
        print(f"{mode} Potential +/-:", potential)
        sleep(3)
    
def readWaveform(socket, recordtime, numChannels):
    # Read waveform data
    rawData = socket.recv(numChannels * BUFFERSIZE * (recordtime + 1))
    print(len(rawData)) # Note: Each second at 30Hz = 129696 data points
    print(waveformBytesPerBlock)
    if len(rawData) % (numChannels * waveformBytesPerBlock) != 0:
        raise InvalidReceivedDataSize(
            'An unexpected amount of data arrived that is not an integer '
            'multiple of the expected data size per block.'
        )
    numBlocks = int(len(rawData) / (numChannels * waveformBytesPerBlock))
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
            amplifierTimestamps.append(rawTimestamp * timestep)

            # Expect 2 bytes of wideband data.
            rawSample, rawIndex = readUint16(rawData, rawIndex)

            # Scale this sample to convert to microVolts
            amplifierData.append(0.195 * (rawSample - 32768))
            
    return amplifierTimestamps, amplifierData

class GetSampleRateFailure(Exception):
    """Exception returned when the TCP socket failed to yield the sample rate
    as reported by the RHX software.
    """

class InvalidMagicNumber(Exception):
    """Exception returned when the first 4 bytes of a data block are not the
    expected RHX TCP magic number (0x2ef07a08).
    """

class InvalidReceivedDataSize(Exception):
    """Exception returned when the amount of data received on the TCP socket
    is not an integer multiple of the excepted data block size.
    """

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as intan:
    intan.connect((HOST, PORT))
    print(f"Connected to {HOST}:{PORT}")
    
    print('Connecting to TCP command server...')
    scommand = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scommand.connect(('127.0.0.1', 5000))
    
    ## Setup Intan Software
    # Query runmode from RHX software.
    scommand.sendall(b'get runmode')
    commandReturn = str(scommand.recv(BUFFERSIZE), "utf-8")
    
    # If controller is running, stop it.
    if commandReturn != "Return: RunMode Stop":
        scommand.sendall(b'set runmode stop')
        # Allow time for RHX software to accept this command before the next.
        sleep(0.1)

    # Query sample rate from RHX software.
    scommand.sendall(b'get sampleratehertz')
    commandReturn = str(scommand.recv(BUFFERSIZE), "utf-8")
    expectedReturnString = "Return: SampleRateHertz "
    # Look for "Return: SampleRateHertz N" where N is the sample rate.
    if commandReturn.find(expectedReturnString) == -1:
        raise GetSampleRateFailure(
            'Unable to get sample rate from server.'
        )
    
    waveformBytesPerFrame = 4 + 2   
    waveformBytesPerBlock = FRAMES_PER_BLOCK * waveformBytesPerFrame + 4    # 4 bytes = magic number;
    
    timestep = 1 / float(commandReturn[len(expectedReturnString):])
    recordtime = 1
    
    calibrate(intan, recordtime, 2)

    # If using matplotlib to plot is not desired,
    # the following plot lines can be removed.
    # Data is still accessible at this point in the amplifierTimestamps
    # and amplifierData.
    
    # intan.bind((HOST, PORT))
    # intan.listen()
    # print(f"Listening for connections on {HOST}:{PORT}")
    
    # input_socket, input_addr = intan.accept()
    # print(f"Received connection from {input_addr}")
    
    # while True:
    #     data = input_socket.recv(1024)
    #     if not data:
    #         break
        
    #     print(data)
        
        
    # print("Closed connection")