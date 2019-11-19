import sys

fname = sys.argv[1]
bytepos = int(sys.argv[2])

# Open in read+write, binary mode; read 1 byte 
fp = open(fname, "r+b")
fp.seek(bytepos)
byte_read = fp.read(1)

a = ord(byte_read)
b = 1
c = a ^ b
toogled = chr(c)
# Back up one byte, write out the modified byte
fp.seek(bytepos)

fp.write(toogled)
fp.close()
