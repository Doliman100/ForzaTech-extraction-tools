import sys
import zlib

# usage:
#   py ca2_extractor.py <input_path> <output_path>
# example:
#   py ca2_extractor.py Mega.ca2 Mega.cab

# .ca2 is a concatenation of 4 MB chunks of a .cab file, compressed with zlib and aligned to 2048

input_path = sys.argv[1]
output_path = sys.argv[2]

with open(input_path, "rb", 0) as f:
    b = memoryview(f.read())

with open(output_path, "wb", 0) as f:
    while True:
        d_stream = zlib.decompressobj()
        uncompressed_data = d_stream.decompress(b)
        f.write(uncompressed_data)
        offset = len(d_stream.unused_data) & ~0x7FF
        if offset == 0:
            break
        b = b[-offset:]
