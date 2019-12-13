import sys
import os
import zlib
from multiprocessing import Process, Value, Array, Lock


def check_baskets(file_bytes, baskets_list, shrd_basket_index, chunk, num_baskets, shrd_corrupted, lock):
    print("process : "+str(os.getpid())+ " starting check_baskets")
    finished = False
    corrupted = False
    while(finished == False and corrupted==False):
        lock.acquire()

        print("process : "+str(os.getpid())+ " checking")
        # If somebody else found something corrupted or there are no more baskets to analyze
        if shrd_corrupted.value == 1 or shrd_basket_index.value >= num_baskets:
            print("process : "+str(os.getpid())+ " finishing here. shrd_corrupted = "+str(shrd_corrupted.value)+" shrd_basket_index= "+str(shrd_basket_index.value))
            print("process : "+str(os.getpid())+ " num_baskets = "+str(num_baskets))
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
            header = file_bytes[seek-9:seek]
            algo_bytes = header[0:2]
            c1 = int(ord(header[3]))
            c2 = int(ord(header[4]))
            c3 = int(ord(header[5]))
            u1 = int(ord(header[6]))
            u2 = int(ord(header[7]))
            u3 = int(ord(header[8]))
            num_uncompressed_bytes = u1 + (u2 << 8) + (u3 << 16)
            num_compressed_bytes = c1 + (c2 << 8) + (c3 << 16)
            #print(str(seek) + ", num_compressed_bytes(header) "+str(num_compressed_bytes))
            #print(str(seek) + ", num_uncompressed_bytes(header) "+str(num_uncompressed_bytes))
            #print(str(seek) + ",  algo: "+algo_bytes)

            if algo_bytes == "ZL":
                try:
                    zlib.decompress(file_bytes[seek:seek+num_compressed_bytes])
                except Exception, e:
                    corrupted = True
                    lock.acquire()
                    shrd_corrupted.value = 1
                    print("process : "+str(os.getpid())+ " found corrupted basket on seek: "+str(seek))
                    lock.release()
                    break
            else:
                print("Unsupported algorithm. skipping...")


if __name__ == '__main__':
    file_root           = sys.argv[1]
    file_bl             = sys.argv[2]
    file_size_root      = int(sys.argv[3])
    
    root_fd = open(file_root)
    bl_fd = open(file_bl)

    baskets = []
    for line in bl_fd.readlines():
        baskets.append(int(line))
    
    chunk = 10
    basket_index = Value('i', 0)
    corrupted_flag = Value('i', 0)
    arr_root = Array('c', root_fd.read(file_size_root))
    lock = Lock()

    p1 = Process(target=check_baskets, args=(arr_root, baskets, basket_index, chunk, len(baskets), corrupted_flag, lock))
    p2 = Process(target=check_baskets, args=(arr_root, baskets, basket_index, chunk, len(baskets), corrupted_flag, lock))
    p3 = Process(target=check_baskets, args=(arr_root, baskets, basket_index, chunk, len(baskets), corrupted_flag, lock))
    p1.start()
    p2.start()
    p3.start()
    print("process : "+str(os.getpid())+ " waiting on workers")
    p1.join()
    p2.join()
    p3.join()
    if corrupted_flag.value ==True:
        print("File is corrupted")
    else:
        print("file is OK")
