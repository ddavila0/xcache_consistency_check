import sys
import os
import zlib
from multiprocessing import Process, Value, Lock


def check_baskets(baskets_list, shrd_basket_index, chunk, num_baskets, shrd_corrupted, lock, filename):
    print("process : "+str(os.getpid())+ " starting check_baskets")
    fd = open(filename)
    finished = False
    corrupted = False
    while(finished == False and corrupted==False):
        lock.acquire()

        # If somebody else found something corrupted or there are no more baskets to analyze
        if shrd_corrupted.value == 1 or shrd_basket_index.value >= num_baskets:
            print("process : "+str(os.getpid())+ " finishing here. shrd_corrupted = "+str(shrd_corrupted.value)+" shrd_basket_index= "+str(shrd_basket_index.value))
            #print("process : "+str(os.getpid())+ " num_baskets = "+str(num_baskets))
            finished = True
            lock.release()
            break

        start = shrd_basket_index.value
        shrd_basket_index.value += chunk
        lock.release()
        
        stop = start + chunk
        if stop > num_baskets:
            stop = num_baskets
        for seek in baskets_list[start:stop]:
            fd.seek(seek-9)
            header = fd.read(9)
            algo_bytes = header[0:2]
            c1 = int(ord(header[3]))
            c2 = int(ord(header[4]))
            c3 = int(ord(header[5]))
            u1 = int(ord(header[6]))
            u2 = int(ord(header[7]))
            u3 = int(ord(header[8]))
            num_uncompressed_bytes = u1 + (u2 << 8) + (u3 << 16)
            num_compressed_bytes = c1 + (c2 << 8) + (c3 << 16)

            if algo_bytes == "ZL":
                try:
                    fd.seek(seek)
                    zlib.decompress(fd.read(num_compressed_bytes))
                except Exception, e:
                    corrupted = True
                    lock.acquire()
                    shrd_corrupted.value = 1
                    print("process : "+str(os.getpid())+ " found corrupted basket on seek: "+str(seek))
                    lock.release()
                    break
            else:
                print("Unsupported algorithm. skipping...")

    fd.close()

if __name__ == '__main__':
    file_root           = sys.argv[1]
    file_bl             = sys.argv[2]
    num_processes       = int(sys.argv[3])
    
    bl_fd = open(file_bl)

    baskets = []
    for line in bl_fd.readlines():
        baskets.append(int(line))
    
    chunk = 10
    basket_index = Value('i', 0)
    corrupted_flag = Value('i', 0)
    lock = Lock()

    process_list = []
    for p in range(0, num_processes):
        p = Process(target=check_baskets, args=( baskets, basket_index, chunk, len(baskets), corrupted_flag, lock, file_root))
        p.start()
        process_list.append(p)

    check_baskets(baskets, basket_index, chunk, len(baskets), corrupted_flag, lock, file_root)  
    
    for p in process_list:
        p.join()

    if corrupted_flag.value ==True:
        print("File is corrupted")
    else:
        print("file is OK")
