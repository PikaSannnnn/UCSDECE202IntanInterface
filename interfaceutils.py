#########################################
#   Interface Utils (User Defined)
#

class SetupReplaceReject(Exception):
    """Exception returned when an IntanInterface object was already setup and locked
    to a channel, but setup is being called again to override without specifying
    to override.
    
    This is a warning error that is thrown as it'll greatly affect recording.
    """
    
class ChannelChangeReject(Exception):
    """Exception returned when an IntanInterface object is attempting to change or reactivate a channel
    while locked to another. Normally, changing should not occur unless self.__channel was changed externally.
    
    This is a warning error that is thrown as it'll greatly affect recording.
    """

#########################################
#   Intan Utils (Defined by Intan Software)
#

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