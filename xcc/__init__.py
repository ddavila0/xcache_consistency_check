#!/usr/bin/env python
import os
import sys
import glob
import argparse
import logging
import uproot
import subprocess
import zlib
from multiprocessing import Process, Value, Lock
import sqlite3
from sqlite3 import Error
import time

try:
    import lzma
except ImportError:
    try:
        import backports.lzma as lzma
    except ImportError:
        raise ImportError("Install lzma package with:\n\t pip install backports.lzma\nor\n\t conda install -c conda-forge backports.lzma\n(or use Python >= 3.3).")
try:
    import xxhash
except ImportError:
    raise ImportError("Install xxhash package with:\n\t pip install xxhash\nor\n\tconda install -c conda-forge python-xxhash")


def get_byte_ranges(byte_map_lines, blocksize):

    xcounter = xcounter_aux =pcounter = pcounter_aux =0

    xflag = True
    pflag = False

    xstart = xend = pstart = pend = 0
    range_list= []

    i = 0
    for line in byte_map_lines:
        for c in line:
            if c == "x":
                if xflag == True:
                    xcounter_aux +=1
                else:
                    pcounter += pcounter_aux
                    pend = i - 1
                    xstart = i
                    xcounter_aux = 1
                    xflag = True
                    pflag=False
                    #range_list.append(["p", pstart, pend])
            elif c == ".":
                if pflag == True:
                    pcounter_aux +=1
                else:
                    xcounter += xcounter_aux
                    xend = i - 1
                    pstart = i
                    pcounter_aux = 1
                    pflag = True
                    xflag=False
                    range_list.append([xstart*blocksize, (xend+1)*blocksize])
            else:
                continue

            if c== "x" or c ==".":
                i+=1
    if xflag == True:
        xend = i-1
        range_list.append([xstart*blocksize, (xend+1)*blocksize])

    return range_list


def parse_cinfo(filename):

    # Process the cinfo file wih the command: xrdpfc_print
    lines = get_xrdpfc_print_ouput(filename)

    # Extract the block size from the output of "xrdpfc_print" command
    blocksize = get_block_size(lines)

    # Check wheter the file is fully downloaded or its a partial file
    # and how many blocks have been downloaded
    full_file, num_blocks = is_file_fully_downloaded(lines)

    # Extract the lines containing the byte map
    byte_map = get_byte_map(lines)

    # Use the bytemap to calculate byte ranges within the file
    byte_ranges = get_byte_ranges(byte_map, blocksize)

    return full_file, byte_ranges, num_blocks

def get_byte_map(lines):
    byte_map = []
    flag_map_start = False

    for i in range(0, len(lines)):
        if "access" in lines[i]:
            break
        if flag_map_start == True:
            new_line = ""
            for c in lines[i]:
                if c == "x" or c ==".":
                    new_line+= c
            byte_map.append(new_line)

        # Find the inmediate line before the byte map starts
        elif "012345" in lines[i]:
            flag_map_start = True
        else:
            continue

    return byte_map


def get_block_size(lines):
    blocksize = -1
    log.debug("Extracting block size")
    for line in lines:
        if "bufferSize" in line:
            log.debug("Found a line with 'bufferSize': %s", line)
            line_splitted = line.split()
            for i in range(0, len(line_splitted)):
                if "bufferSize" in  line_splitted[i]:
                    blocksize = int(line_splitted[i+1])
                    log.debug("Found blocksize = %d", blocksize)

                elif "nBlocks" in  line_splitted[i]:
                    nBlocks = int(line_splitted[i+1])
                    log.debug("Found nBlocks = %d", nBlocks)


                elif "nDownloaded" in  line_splitted[i]:
                    nDownloaded = int(line_splitted[i+1])
                    log.debug("Found nDownloaded = %d", nDownloaded)

    return blocksize

# Chek whether the file is fully downloaded and how many blocks have been
# downloaded so far
def is_file_fully_downloaded(lines):
    nBlocks = -1
    nDownloaded = -2
    is_fully_downloaded = False
    log.debug("Checking if file is fully downloaded")
    for line in lines:
        if "bufferSize" in line:
            line_splitted = line.split()
            for i in range(0, len(line_splitted)):
                if "nBlocks" in  line_splitted[i]:
                    nBlocks = int(line_splitted[i+1])

                elif "nDownloaded" in  line_splitted[i]:
                    nDownloaded = int(line_splitted[i+1])

    # If nBlocks is equals to nDonwloaded then the file is fully downloaded
    return (nBlocks == nDownloaded), nDownloaded

def get_xrdpfc_print_ouput(filename):
    lines = []
    # TODO:
    # add a check in case xrdpfc_print is not available
    out = subprocess.Popen(['xrdpfc_print', '-v', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = out.communicate()
    if stderr is None:
        log.debug("Parsing cinfo file: %s", filename)
        lines = stdout.split("\n")
    else:
        log.error("Something went wrong when parsing cinfo file: %s", filename)
    return lines

# Return a list of files, with a given @extension, found under @path
def list_files_recursively(path, extension):
    files_dict = dict()
    for x in os.walk(path):
        for file_with_path in glob.glob(os.path.join(x[0], "*"+extension)):
            only_filename = os.path.basename(file_with_path)
            files_dict[only_filename] = file_with_path

    return files_dict


def basket_in_file(range_list, basket_start, basket_length):
    status_in_file = 0
    basket_end = basket_start + basket_length
    for i in range_list:
        if  basket_start >= i[0] and basket_end <= i[1]:
                status_in_file = 1
                break
        elif basket_start >= i[0] and basket_start <= i[1]:
            status_in_file = 2
            break
        elif basket_end >= i[0] and basket_end <= i[1]:
            status_in_file = 3
            break

    return status_in_file


def get_list_of_baskets_in_branch(branch, byte_ranges, is_full_file):
    num_baskets = branch.numbaskets

    list_baskets = []
    for i in range(0, num_baskets):
        key = branch._threadsafe_key(i, None, True)
        if key.__class__.__name__ == '_RecoveredTBasket':
            continue
            #TODO: do something
        else:
            class_name = key.source.__class__.__name__
            if class_name == "MemmapSource":
                continue
                # Basket isn't compressed
            else:
                basket_start = key.source._cursor.index
                basket_length = branch.basket_compressedbytes(i)
                if is_full_file == True or basket_in_file(byte_ranges, basket_start, basket_length) == 1:
                    #TODO:
                    # append also the length of the basket to compare it with
                    # the size read from the header of the basket

                    # 9 is the size of the header
                    list_baskets.append(basket_start+9)
    return list_baskets


def recursive_branch(branch, byte_ranges, is_full_file):
    list_baskets = []
    if len(branch.keys()) > 0:
        for sub_branch in branch.itervalues():
            baskets_in_branch = recursive_branch(sub_branch, byte_ranges, is_full_file)
            list_baskets += baskets_in_branch
    else:
        baskets_in_branch = get_list_of_baskets_in_branch(branch, byte_ranges, is_full_file)
        list_baskets += baskets_in_branch

    return list_baskets


def get_list_of_baskets_in_file(filename,  byte_ranges, is_full_file):
    corrupted = False
    f = uproot.open(filename)
    list_baskets = []

    for tree in f.itervalues():
        for branch in tree.itervalues():
            baskets_in_branch = recursive_branch(branch, byte_ranges, is_full_file)
            list_baskets += baskets_in_branch

    # Remove duplicates
    list_baskets = list(dict.fromkeys(list_baskets))

    # Sort
    list_baskets.sort()
    log.info("done sorting. Starting to check baskets")

    return list_baskets


def convert_checksum(checksum_8bytes):
    checksum = 0
    j=0
    my_range =range(0, 64, 8)
    my_range.reverse()
    for i in my_range:
        checksum += (int(ord(checksum_8bytes[j]))*pow(2, i))
        j+=1
    return checksum


def check_baskets(baskets_list, shrd_basket_index, chunk, num_baskets, shrd_corrupted, lock, filename):
    log.debug("process : "+str(os.getpid())+ " starting check_baskets")
    fd = open(filename)
    finished = False
    corrupted = False
    while(finished == False and corrupted==False):
        lock.acquire()

        # If somebody else found something corrupted or there are no more baskets to analyze
        if shrd_corrupted.value == 1 or shrd_basket_index.value >= num_baskets:
            log.debug("process : "+str(os.getpid())+ " finishing here. shrd_corrupted = "+str(shrd_corrupted.value)+" shrd_basket_index= "+str(shrd_basket_index.value))
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
                fd.seek(seek)
                try:
                    zlib.decompress(fd.read(num_compressed_bytes))
                except Exception, e:
                    corrupted = True
                    lock.acquire()
                    shrd_corrupted.value = 1
                    log.info("process: " +str(os.getpid()) + ", Corrupted Basket on Seek: "+str(seek)+ ". Error message: "+str(e))
                    lock.release()
                    break

            # lzma
            elif algo_bytes == "XZ":
                fd.seek(seek)
                try:
                    lzma.decompress(fd.read(num_uncompressed_bytes))
                except Exception, e:
                    corrupted = True
                    lock.acquire()
                    shrd_corrupted.value = 1
                    log.info("process: " +str(os.getpid()) + ", Corrupted Basket on Seek: "+str(seek)+ ". Error message: "+str(e))
                    lock.release()
                    break

            # lz4
            elif algo_bytes == "L4":
                # Baskets compressed with this algorithm have an extra 8-byte header containing
                # a checksum of the compressed data, meaning that the length of the basket is
                # actually 8 bytes shorter
                num_compressed_bytes -= 8

                # Read the checksum from the header of the basket
                fd.seek(seek)
                checksum_8bytes = fd.read(8)
                # Convert the 8 separated byte into a single number
                checksum = convert_checksum(checksum_8bytes)

                # Get the compressed bytes of the basket
                fd.seek(seek+8)
                compressed_bytes = fd.read(num_compressed_bytes)
                # Calculate the checksum of the compressed bytes and compare it to the one
                # in the header of the basket
                if xxhash.xxh64(compressed_bytes).intdigest() != checksum:
                    lock.acquire()
                    shrd_corrupted.value = 1
                    log.info("process: " +str(os.getpid()) + ", Corrupted Basket on Seek: "+str(seek))
                    lock.release()
                    break

            elif algo == b"CS":
                log.info("process: " +str(os.getpid()) +", Unsupported very OLD algorithm: "+algo_bytes+" , skipping basket...")

            else:
                ("process: " +str(os.getpid()) + ", Unsupported algorithm. skipping...")

    fd.close()




# Argument parsing
def parseargs():
    parser = argparse.ArgumentParser()

    parser.add_argument("--path", dest="path", required=False,
                         help="Path to the files to analyze, for a single file use --rootfile")

    parser.add_argument("--rootfile", dest="rootfile", required=False,
                         help=".root filename to be analyzed, if this is a partial file a .cinfo file with the same \
                            name is expected or use --cinfofile to point to the corresponding .cinfo file. If this is\
                             a full file set --full_file")

    parser.add_argument("--full-file", dest="full_file", required=False, action="store_true",
                         help="Assume that the root file passed in --rootfile is fully downloaded thus does not requires a cinfo file (default: False)")

    parser.add_argument("--debug", dest="debug", required=False, action="store_true",
                         help="Set log to DEBUG mode (default: False)")

    parser.add_argument("--dry-run", dest="dry_run", required=False, action="store_true",
                         help="Just list the files to be analyzed but do not run the check")

    parser.add_argument("--max", dest="max", required=False, default=-1, type=int,
                         help="Maximum number of files to analyze default(analyze all files)")

    parser.add_argument("--num-procs", dest="num_procs", required=False, default=1, type=int,
                         help="Number of parallel processes used to analyze the file(s) (default: 1)")

    parser.add_argument("--db", dest="db", required=True,
                         help="Database used to keep track of analyzed files")

    parser.add_argument("--last-check-threshold", dest="last_check_threshold", required=False, default=86400, type=int,
                         help="If a file has been checked within less than the number of seconds defined here, \
                             the check on this file will be skipped (default: 86400(24hrs)")

    args = parser.parse_args()

    if not args.path and not args.rootfile:
        print("ERROR: Either --path or --rootfile need to be defined")
        exit(1)
    # If --path is not defined then --rootfile it is
    if not args.path:
        # Check that the  root file exist
        if os.path.isfile(args.rootfile) == False:
            print("ERROR: --rootfile: "+args.rootfile+" does not exist")
            exit(1)

        # If --full_file isn't defined then rootfile+".cinfo" must exist
        elif args.full_file == False:
            if os.path.isfile(args.rootfile+".cinfo") == False:
                print("ERROR --full_file isn't defined and file: "+args.rootfile+".cinfo"+" does not exist")
                exit(1)

    return args

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        log.error("Cannot create database table. Error message: "+str(e))
        log.error(create_table_sql)


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        log.error("Cannot create database connection. Error message: "+str(e))

    return conn


def create_db(filename):
    sql = """ CREATE TABLE IF NOT EXISTS files (
                                        id integer PRIMARY KEY,
                                        filename text,
                                        last_check_ts integer,
                                        last_num_blocks integer,
                                        checksum text
                                    ); """

    # create a database connection
    conn = create_connection(filename)

    # create tables
    if conn is not None:
        # create projects table
        create_table(conn, sql)
    else:
        log.error("Cannot create database connection.")

def calculate_checksum(filename):
    fd = open(filename)
    file_bytes = fd.read()
    checksum = str(xxhash.xxh64(file_bytes).intdigest())
    return checksum

def insert_in_db(conn, root_filename, ts, num_blocks, file_checksum):
    sql = ''' INSERT INTO files(filename, last_check_ts, last_num_blocks, checksum)
              VALUES(?,?,?,?) '''

    record =(root_filename, ts, num_blocks, file_checksum)
    with conn:
        cur = conn.cursor()
        cur.execute(sql, record)
    log.debug("inserted record: "+str(cur.lastrowid))

# When a file has changed (new blocks have been downloaded) its record needs to be updated
def update_db(conn, root_filename, ts, num_blocks, file_checksum):
    sql = ''' UPDATE files
                SET last_check_ts = ?,
                    last_num_blocks = ?,
                    checksum = ?
                WHERE filename = ?'''

    record =(ts, num_blocks, file_checksum, root_filename)
    with conn:
        cur = conn.cursor()
        cur.execute(sql, record)
    log.debug("updated record: "+root_filename)



def get_file_from_db(conn, root_filename):
    sql = ''' SELECT id, last_check_ts, last_num_blocks, checksum
              FROM files
              WHERE filename =?'''

    cur = conn.cursor()
    cur.execute(sql, (root_filename,))
    rows = cur.fetchall()
    if len(rows) > 1:
        log.error("Duplicated file in the DB: "+root_filename)
    if len(rows) == 0:
        ret = (None, -1, -1, -1)
    else:
        ret = (rows[0])
    return ret
###############################################################################
#                               MAIN
###############################################################################
def main():
    # Get arguments
    args = parseargs()
    
    #------ Configs --------------------------------------------------------------
    
    # Log level: {CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET}
    if args.debug == True:
        log_lvl = logging.DEBUG
    else:
        log_lvl = logging.INFO
    
    #----- Setup the logger and the log level ------------------------------------
    #logging.basicConfig(level=log_lvl, format='%(asctime)s - %(name)s -  %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S')
    logging.basicConfig(level=log_lvl, format='%(asctime)s  %(levelname)s - %(message)s', datefmt='%Y%m%d %H:%M:%S')
    log = logging.getLogger(__name__)
    #-----------------------------------------------------------------------------
    
    
    #------ DB setup--------------------------------------------------------------
    create_db(args.db)
    conn = create_connection(args.db)
    #-----------------------------------------------------------------------------
    
    
    #------ Find file(s)  ---------------------------------------------------------
    #TODO
    # validate that the path exist
    path = args.path
    assume_full_file = args.full_file
    
    # If path is not defined that means we are analizing a single root file
    if not path:
        rootfile = args.rootfile
        log.debug("@path is not defined, analyzing single file: "+rootfile)
        only_filename_root  = os.path.basename(rootfile)
        root_files_dict = dict()
        root_files_dict[only_filename_root] = rootfile
    else:
        root_files_dict  = list_files_recursively(path, ".root")
        log.info("found: "+str(len(root_files_dict))+" .root files in: "+path)
    max_counter = 0
    
    
    #------ Dry Run  --------------------------------------------------------------
    if args.dry_run == True:
        for root_file in root_files_dict:
            if args.max > 0 and  max_counter >= args.max:
                break
            # Verify that there is a corresponfing .cinfo file
            root_filename  = root_files_dict[root_file]
            cinfo_filename = root_filename+".cinfo"
            if os.path.isfile(cinfo_filename):
                log.info("Analyzing file: "+ root_file)
            else:
                log.error("Cannot find a corresponding .cinfo file for root file:  %s", root_filename)
            max_counter +=1
    
    #------ Real Run  -------------------------------------------------------------
    else:
        # For every root file
        for root_file in root_files_dict:
            if args.max > 0 and max_counter >= args.max:
                break
            # Verify that there is a corresponfing .cinfo file
            root_filename  = root_files_dict[root_file]
            cinfo_filename = root_filename+".cinfo"
            if assume_full_file == True or os.path.isfile(cinfo_filename):
            #if assume_full_file == True or root_file+".cinfo" in cinfo_files_dict:
                log.info("Analyzing file: "+ root_file)
                # Step 1. Calculate the byte ranges on the file
                if assume_full_file == True:
                    is_full_file = True
                    byte_ranges = None
                    num_blocks=0
                else:
                    is_full_file, byte_ranges, num_blocks = parse_cinfo(cinfo_filename)
                ### Step 1.1 Do I need to fully analyze this file or only verify the checksum?
                db_file_id = None
                db_file_id, db_last_check_ts, db_last_num_blocks, db_checksum = get_file_from_db(conn, root_file)
    
                # if the file is in the DB and the number of downloaded blocks registerd in the db
                # is the same as the current number of blocks in the file it means that the file
                # hasn't change since the last analisis, so we just need to verify the checksums.
                ts = int(time.time())
                if db_file_id is not None:
                    if num_blocks == db_last_num_blocks:
                        curr_checksum = calculate_checksum(root_filename)
                        if db_checksum == curr_checksum:
                            log.info("OK file's checksum:  %s", root_filename)
                            continue
                        # There are no new blocks added to the file but the file has changed
                        # that means the file is corrupted
                        else:
                            log.info("Corrupted file's checksum:  %s, db:%s, curr:%s", root_filename, db_checksum, curr_checksum)
                            # TODO:
                            #remove_file(filename)
                    # If file has changed but we have checked this file recently, then we skip the check
                    elif ts - db_last_check_ts <= args.last_check_threshold:
                        log.debug("file %s, has changed since last analisis but last check is more recent than the threshold, skipping", root_filename)
                        continue
                    else:
                        log.debug("file %s, has changed since last analisis and last check less recent that the threshold")
                else:
                    log.debug("file %s, not in the DB", root_filename)
    
                # Step 2. Create a list of baskets in the file
                list_of_baskets = get_list_of_baskets_in_file(root_filename, byte_ranges, is_full_file)
    
                # Step 3. Look for a corrupted basket within the list
                chunk = 10
                basket_index = Value('i', 0)
                corrupted_flag = Value('i', 0)
                lock = Lock()
    
                # The total number of processes to be used are num_workers + 1. The parent process is
                # also used
                num_workers = args.num_procs -1
                process_list = []
                for p in range(0, num_workers):
                    p = Process(target=check_baskets, args=(list_of_baskets, basket_index, chunk, len(list_of_baskets), corrupted_flag, lock, root_filename))
                    p.start()
                    process_list.append(p)
    
                # The parent process is also doing his part
                check_baskets(list_of_baskets, basket_index, chunk, len(list_of_baskets), corrupted_flag, lock, root_filename)
    
                for p in process_list:
                    p.join()
    
                if corrupted_flag.value ==True:
                    log.info("CORRUPTED file:  %s", root_filename)
                    #remove_file(root_filename)
                else:
                    log.info("OK file:  %s", root_filename)
                    file_checksum = calculate_checksum(root_filename)
                    if db_file_id == None:
                        insert_in_db(conn, root_file, ts, num_blocks, file_checksum)
                    else:
                        update_db(conn, root_file, ts, num_blocks,file_checksum)
    
            else:
                log.error("Cannot find a corresponding .cinfo file for root file:  %s", root_filename)
    
            max_counter +=1

if __name__ == "__main__":
    main()
