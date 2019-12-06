import sys
import zlib

root_filename = sys.argv[1]
bl_filename = sys.argv[2]

fd = open(bl_filename)
fd_root = open(root_filename)

for line in fd.readlines():
    seek = int(line[:-1].split()[0])
    num_bytes = int(line[:-1].split()[1])
        
    fd_root.seek(seek -9)
    algo_bytes = fd_root.read(2)
    #u1 = u_bytes[0]
    #u2 = u_bytes[1]
    #u3 = u_bytes[2]
    #num_uncompressed_bytes = u1 + (u2 << 8) + (u3 << 16) 
    #print(str(seek) + " "+str(num_bytes)+ " "+str(num_uncompressed_bytes))
    
    if algo_bytes == "ZL":
        fd_root.seek(seek)
        uncompressed_bytes= fd_root.read(num_bytes)
        try:
            decompressed_bytes = zlib.decompress(uncompressed_bytes)
        except Exception, e:
            print("Corrupted basket")
            print(seek)
            print(num_bytes)
            print(e)
            exit(0)
    # lzma
    elif algo_bytes == "XZ":
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
            print(num_bytes)
            print(e)
            exit(0)
         
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

print("File is OK")
    

