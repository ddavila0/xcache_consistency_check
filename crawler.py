# Get a path and an extension (e.g. .root or .cinfo) as inputs and it creates a list with all the
# files with such extension below thath path

import os
import sys
import glob
import argparse
import logging
import uproot

import pdb; 
import subprocess

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
    lines = get_xrdpfc_print_ouput(filename)
    if debug_lvl >2:
        for line in lines:
            print(line)

    # Extract the block size from the output of "xrdpfc_print" command
    blocksize = get_block_size(lines)

    # Check wheter the file is fully downloaded or its a partial file 
    full_file = is_file_fully_downloaded

    # Extract the lines containing the byte map 
    byte_map = get_byte_map(lines)

    # Use the bytemap to calculate byte ranges within the file
    byte_ranges = get_byte_ranges(byte_map, blocksize)

    if debug_lvl > 2:
        for byte_range in byte_ranges:
            print(byte_range)

    return full_file, byte_ranges

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

    if debug_lvl > 2:
        for line in lines:
            print(line)
        print("======================================")
        for line in byte_map:
            print(line)

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

# Chek whether the file is fully downloaded
def is_file_fully_downloaded(lines):
    nBlocks = -1
    nDownloaded = -2
    is_fully_downloaded = False
    log.debug("Checking if file is fully downloaded")
    for line in lines:
        if "bufferSize" in line:
            log.debug("Found a line with 'bufferSize': %s", line)
            line_splitted = line.split()
            for i in range(0, len(line_splitted)):
                if "nBlocks" in  line_splitted[i]:
                    nBlocks = int(line_splitted[i+1])
                    log.debug("Found nBlocks = %d", nBlocks)
                    
                elif "nDownloaded" in  line_splitted[i]:
                    nDownloaded = int(line_splitted[i+1])
                    log.debug("Found nDownloaded = %d", nDownloaded)

    # If nBlocks is equals to nDonwloaded then the file is fully downloaded
    return nBlocks == nDownloaded

def get_xrdpfc_print_ouput(filename):
    lines = []
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


def is_branch_corrupted(branch, byte_ranges, is_full_file):
    try:
        num_baskets = branch.numbaskets
    except Exception, e:
        log.error("numbaskets on branch: "+branch.name+ "--" +str(e))
        return True
    
    for i in range(0, num_baskets):
        basket_start = branch._fBasketSeek[i]
        basket_length = branch.basket_compressedbytes(i)        
        if is_full_file == True or basket_in_file(byte_ranges, basket_start, basket_length) == 1:
            try:
                #basket = branch.basket(i)
                basket = branch.my_basket(i)
                #print(len(basket))
            except Exception, e:
                log.debug("Corrupted basket: "+ str(i)+" in branch: "+branch.name + "--" +str(e))        
                return True
    return False

def check_file(filename,  byte_ranges, is_full_file):
    flag_corrupted = False
    f = uproot.open(filename)

    for tree in f.itervalues():
        if flag_corrupted == True:
            break

        log.debug("Tree: "+tree.name)
        for branch in tree.itervalues():
            if len(branch.keys()) > 0:
                log.debug("  Branch: "+branch.name)
                for subranch in branch.itervalues():
                    corrupted = is_branch_corrupted(subranch, byte_ranges, is_full_file)
                    if corrupted: 
                        log.info("  CORRUPTED Branch: "+branch.name+" on tree: "+tree.name)
                        flag_corrupted = True
                        break
                    else:
                        log.debug("    Subranch: "+subranch.name)
            else:
                corrupted = is_branch_corrupted(branch, byte_ranges, is_full_file)
                if corrupted:
                    log.info("  CORRUPTED Branch: "+branch.name+" on tree: "+tree.name)
                    flag_corrupted = True
                    break
                else:
                    log.debug("  Branch: "+branch.name)

    return flag_corrupted


# Argument parsing
def parseargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", dest="path", required=True,
                         help="Path to the files to files to analyze")

    args = parser.parse_args()

    return args




###############################################################################
#                               MAIN
###############################################################################
#------ Configs --------------------------------------------------------------

# Dedbug level
debug_lvl = 3

# Log level: {CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET}
log_lvl = logging.DEBUG

#------ Parse arguments path and extension -----------------------------------
args = parseargs()

#TODO
# validate that the path exist
path = args.path

root_files_dict  = list_files_recursively(path, ".root")
cinfo_files_dict = list_files_recursively(path, ".cinfo")
#-----------------------------------------------------------------------------

#----- Setup the logger and the log level ------------------------------------
logging.basicConfig(level=log_lvl, format='%(asctime)s - %(name)s -  %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S')
log = logging.getLogger(__name__)
#-----------------------------------------------------------------------------


if debug_lvl > 0:
    print("Path: "+path)

if debug_lvl > 2:
    print("list of .root files:") 
    for i in root_files_dict:
        print(i+" : "+root_files_dict[i])
    
    print("list of .cinfo files:") 
    for i in cinfo_files_dict:
        print(i+" : "+cinfo_files_dict[i])


# For every root file 
for root_file in root_files_dict:
    # Verify that there is a corresponfing .cinfo file
    root_filename  = root_files_dict[root_file]
    cinfo_filename = root_filename+".cinfo" 
    if root_file+".cinfo" in cinfo_files_dict:
        print("Analyzing file: %s", root_file)
        # Step 1. Calculate the byte ranges on the file
        is_full_file, byte_ranges = parse_cinfo(cinfo_filename)
        
        # Step 2. Decompress every fully present basket in the file
        pdb.set_trace()
        file_corrupted = check_file(root_filename, byte_ranges, is_full_file)
        if file_corrupted == True:
            log.info("CORRUPTED file:  %s", root_filename)
        else: 
            log.info("OK file:  %s", root_filename) 
    else:
        log.error("Cannot find a corresponding .cinfo file for root file:  %s", root_filename) 


