import socket

from intanutil.header import (read_header,
                              header_to_result)
from intanutil.data import (calculate_data_size,
                            read_all_data_blocks,
                            check_end_of_file,
                            parse_data,
                            data_to_result)
from intanutil.filter import apply_notch_filter

HOST = '127.0.0.1'
PORT = 5001
BUFFERSIZE = 200000
FRAMES_PER_BLOCK = 128  

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
    
    waveformBytesPerFrame = 4 + 2
    waveformBytesPerBlock = FRAMES_PER_BLOCK * waveformBytesPerFrame + 4
    
    timestep = 1 / float(commandReturn[len(expectedReturnString):])
    
    # Read waveform data
    rawData = intan.recv(BUFFERSIZE)
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
            amplifierTimestamps.append(rawTimestamp * timestep)

            # Expect 2 bytes of wideband data.
            rawSample, rawIndex = readUint16(rawData, rawIndex)

            # Scale this sample to convert to microVolts
            amplifierData.append(0.195 * (rawSample - 32768))

    # If using matplotlib to plot is not desired,
    # the following plot lines can be removed.
    # Data is still accessible at this point in the amplifierTimestamps
    # and amplifierData.
    plt.plot(amplifierTimestamps, amplifierData)
    plt.title('A-010 Amplifier Data')
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (uV)')
    plt.show()
    
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