import os
import sys
import serial

# Internal parameters
BAUDRATE = 2000000
MESSAGE_PATH = r"burunyu.gif"
KEY_PATH = r"blake2s_key.txt"
DIGEST_SIZE_BYTES = 32
USE_KEY = True

# Constants
MAX_KEY_LENGTH = 32
BLOCK_SIZE = 64


# Next two functions are utility functions.
def exit_with_error(error_msg):
    print(error_msg)
    sys.exit("Exiting the program")


def read_key():
    key_file_size = os.stat(KEY_PATH).st_size
    if key_file_size > MAX_KEY_LENGTH:
        exit_with_error("Key is too long. Remember: key can be up to 32 bytes in length")
    elif key_file_size == 0:
        exit_with_error(
            "Key file is empty. Either disable the keyed_hashing option or type something into the key file")

    with open(KEY_PATH, "r", encoding="utf-8") as key_file:
        key = key_file.read()
    print(f"Key size is {key_file_size} bytes")
    print(f'Chosen key: {key}')
    return bytes(key, "utf-8")


print(f"Chosen Digest Size: {DIGEST_SIZE_BYTES} bytes")

# Read and process the key if needed
key = read_key() if USE_KEY else None
key_size_bytes = len(key) if USE_KEY else 0

# Read the message file
with open(MESSAGE_PATH, "rb") as message_file:
    message = message_file.read()
if not message:
    exit_with_error("Message file is empty. There is nothing to send")

message_size_bytes = len(message) + (BLOCK_SIZE if USE_KEY else 0)
print(f"Message size is {message_size_bytes} bytes")

# Prepare data for transmission
# Here, I use 'list comprehension', a 'Pythonic' way to create lists inline.
# It replaces the more verbose loop below, which was my original approach.
# Although the shorthand feels less intuitive to me, I've adopted it here following suggestions
# to make the code more aligned with Python best practices.
message_blocks = [message[i:i + BLOCK_SIZE] for i in range(0, len(message), BLOCK_SIZE)]

# Original loop for comparison (commented out):
# message_blocks = []
# for i in range(0, len(message), BLOCK_SIZE):
#     block = bytes(message[i:i+BLOCK_SIZE])
#     message_blocks.append(block)

# Padding the last block if it does not fill the entire BLOCK_SIZE
if len(message_blocks[-1]) != BLOCK_SIZE:
    message_blocks[-1] += bytes(BLOCK_SIZE - len(message_blocks[-1]))



if USE_KEY:
    key += bytes(BLOCK_SIZE - key_size_bytes)  # Padding the key

# Convert sizes to byte arrays
message_size_bytes_bytearray = message_size_bytes.to_bytes(8, byteorder='big')
key_size_bytes_bytearray = key_size_bytes.to_bytes(1, byteorder='big')
digest_size_bytes_bytearray = DIGEST_SIZE_BYTES.to_bytes(1, byteorder='big')

# Serial communication
ser = serial.Serial(port='COM3', baudrate=BAUDRATE, timeout=1)
print(f"Opened communication through: {ser.name}")
# Next 8 lines send the 0th block, the 'Bloque de Parámetros de Inicialización'.
# This way, I reuse the simple VHDL interfaces inside the FPGA.
ser.write(message_size_bytes_bytearray)  # Message size
ser.write(b'VM')  # Meaningless padding added just so I wouldn't get confused by Endianness.
if USE_KEY:
    ser.write(key_size_bytes_bytearray)
else:
    ser.write(b'\x00')  # If there's no key, an empty byte has to go in its place. Could be rewritten more elegantly.
ser.write(digest_size_bytes_bytearray)
ser.write(b'It does not really matter what you type here, friend')  # Further padding, 52 bytes to be precise.

if USE_KEY:
    ser.write(key)

for block in message_blocks:
    ser.write(block)

# Receive and handle the digest
in_bin = ser.read(DIGEST_SIZE_BYTES)
print(f"{ser.name} is now closed")
in_hex_padded = in_bin.hex().zfill(MAX_KEY_LENGTH * 2)  # Python omits leading zeroes, and I need them back.
# "Etapa de Post-procesamiento". The last two lines. That's it.
in_hex_truncated = in_hex_padded[:2 * DIGEST_SIZE_BYTES]
print(f'Blake2s digest:\n{in_hex_truncated}')
