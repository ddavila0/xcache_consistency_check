import sys
import zlib
import pdb

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
        #try:
        #    import xxhash
        #except ImportError:
        #    raise ImportError("Install xxhash package with:\n    pip install xxhash\nor\n    conda install -c conda-forge python-xxhash")
        #compression = self.compression.copy(uproot.const.kLZ4)
        #compressedbytes -= 8
        #checksum = cursor.field(self._compressed, self._format_field0)
        #copy_cursor = copy(cursor)
        #after_compressed = copy_cursor.bytes(self._compressed, compressedbytes)
        #if xxhash.xxh64(after_compressed).intdigest() != checksum:
        #    raise ValueError("LZ4 checksum didn't match")
    
    elif algo == b"CS":
        print("Unsupported very OLD algorithm: "+algo_bytes+" , skipping...")
    else:
        print("Unsupported algorithm: "+algo_bytes+" , skipping...")

if file_corrupted == False:
    print("File is OK")
else:
    print("File is Corrupted")
