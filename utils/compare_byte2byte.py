#!/usr/bin/python

import sys
#import pdb

fname1 = sys.argv[1]
fname2 = sys.argv[2]

# Open in read+write, binary mode; read 1 byte 
fp1 = open(fname1, "r+b")
fp2 = open(fname2, "r+b")
fp1.seek(0)
fp2.seek(0)

debug_lvl=0
i=0
#pdb.set_trace()
while 1:
    byte_s1 = fp1.read(1)
    byte_s2 = fp2.read(1)
    if not byte_s1 or not byte_s2:
       break
    byte1 = byte_s1[0]
    byte2 = byte_s2[0]
    if debug_lvl > 0:
        print(byte_s1) 
        print(byte_s2)

    if byte1 is not byte2:
        print("byte number: "+ str(i)+ " is different")
        print(byte1+", "+str(ord(byte1))+", "+'{0:08b}'.format(ord(byte1))) 
        print(byte2+", "+str(ord(byte2))+", "+'{0:08b}'.format(ord(byte2)))
    i+=1 

fp1.close()
fp2.close()
