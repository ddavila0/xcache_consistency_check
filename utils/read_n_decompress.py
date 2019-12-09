import sys
import zlib
import pdb

def convert(my_list):
    accumulator = 0
    j=0
    my_range =range(0, 64, 8)
    my_range.reverse()
    for i in my_range:
        accumulator += (int(ord(my_list[j]))*pow(2, i))
        j+=1
    return accumulator

root_filename = sys.argv[1]
bl_filename = sys.argv[2]
if len(sys.argv) == 4 and sys.argv[3]=="-d":
    pdb.set_trace()
    
fd = open(bl_filename)
fd_root = open(root_filename)

file_corrupted = False
for line in fd.readlines():
    seek = int(line[:-1].split()[0])
    num_bytes = int(line[:-1].split()[1])
        
    fd_root.seek(seek -9)
    header = fd_root.read(9)
    algo_bytes = header[0:2]
    c1 = int(ord(header[3]))
    c2 = int(ord(header[4]))
    c3 = int(ord(header[5]))
    u1 = int(ord(header[6]))
    u2 = int(ord(header[7]))
    u3 = int(ord(header[8]))
    num_uncompressed_bytes = u1 + (u2 << 8) + (u3 << 16)
    num_compressed_bytes = c1 + (c2 << 8) + (c3 << 16)
    print(str(seek) + ", num_compressed_bytes(uproot) "+str(num_bytes))
    print(str(seek) + ", num_compressed_bytes(header) "+str(num_compressed_bytes))
    print(str(seek) + ", num_uncompressed_bytes(header) "+str(num_uncompressed_bytes))
    print(str(seek) + ",  algo: "+algo_bytes)
    
    if algo_bytes == "ZL":
        fd_root.seek(seek)
        uncompressed_bytes= fd_root.read(num_compressed_bytes)
        try:
            decompressed_bytes = zlib.decompress(uncompressed_bytes)
        except Exception, e:
            print("Corrupted basket")
            print(seek)
            print(num_compressed_bytes)
            print(e)
            file_corrupted = True
    # lzma
    elif algo_bytes == "XZ":
        uncompressed_bytes= fd_root.read(num_compressed_bytes)
        try:
            from lzma import decompress as lzma_decompress
        except ImportError:
            try:
                from backports.lzma import decompress as lzma_decompress
            except ImportError:
                raise ImportError("Install lzma package with:\n pip install backports.lzma\nor\n conda install -c conda-forge backports.lzma\n(or just use Python >= 3.3).")
            
        try:
            lzma_decompress(uncompressed_bytes)
        except Exception, e:
            print("Corrupted basket")
            print(seek)
            print(num_uncompressed_bytes)
            print(e)
            file_corrupted = True
    # lz4
    elif algo_bytes == "L4":
        print("Unsupported algorithm: "+algo_bytes+" , skipping...")
        try:
            import xxhash
        except ImportError:
            raise ImportError("Install xxhash package with:\n    pip install xxhash\nor\n    conda install -c conda-forge python-xxhash")
        num_compressed_bytes -= 8
        # Read the checksum from the header of the basket
        fd_root.seek(seek)
        checksum_8bytes = fd_root.read(8)
        checksum = convert(checksum_8bytes)
        fd_root.seek(seek+8)
        compressed_bytes = fd_root.read(num_compressed_bytes)
        if xxhash.xxh64(compressed_bytes).intdigest() != checksum:
            print("Corrupted basket")
            print(seek)
            print(num_uncompressed_bytes)
            print(e)
            file_corrupted = True
    
    elif algo == b"CS":
        print("Unsupported very OLD algorithm: "+algo_bytes+" , skipping...")
    else:
        print("Unsupported algorithm: "+algo_bytes+" , skipping...")

if file_corrupted == False:
    print("File is OK")
else:
    print("File is Corrupted")
