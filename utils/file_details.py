#!/usr/bin/env python
import os
import sys
import glob
import argparse
import logging
import uproot
import subprocess
import pdb

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
    # Extract the block size from the output of "xrdpfc_print" command
    
    blocksize, nBlocks, nDownloaded, fileSize = get_file_details(lines)

    # Check wheter the file is fully downloaded or its a partial file 
    full_file = nBlocks == nDownloaded
 
    # Calculate percentage of downloaded file:
    percentage = 100 * nDownloaded/ nBlocks

    # Extract the lines containing the byte map 
    byte_map = get_byte_map(lines)

    # Use the bytemap to calculate byte ranges within the file
    byte_ranges = get_byte_ranges(byte_map, blocksize)
   
     
    return full_file, byte_ranges, percentage, fileSize

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


def get_file_details(lines):
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
                
                elif "fileSize" in  line_splitted[i]:
                    fileSize = int(line_splitted[i+1][:-1])
                    log.debug("Found fileSize = %d", fileSize)
                    
    return blocksize, nBlocks, nDownloaded, fileSize


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


def analyze_branch(branch, byte_ranges, is_full_file):
    try:
        num_baskets = branch.numbaskets
    except Exception, e:
        log.error("numbaskets on branch: "+branch.name+ "--" +str(e))
        return True
    
    #      branch_count, basket_count, compression_algorithm
    return 1, num_baskets, branch.compression.algo

def recursive_branch(branch, byte_ranges, is_full_file, tree_name, prefix):
    branch_count = basket_count = 0
    lzma_count = lz4_count = zlib_count = 0
    if len(branch.keys()) > 0:
        for sub_branch in branch.itervalues():
            count_branch_aux, count_basket_aux, count_lzma_aux, count_lz4_aux, count_zlib_aux = recursive_branch(sub_branch, byte_ranges, is_full_file, tree_name, "  "+prefix)
            branch_count += count_branch_aux
            basket_count += count_basket_aux
            lzma_count += count_lzma_aux
            lz4_count += count_lz4_aux
            zlib_count += count_zlib_aux
    else:
        count_branch_aux, count_basket_aux, compression_algorithm = analyze_branch(branch, byte_ranges, is_full_file)
        branch_count += count_branch_aux
        basket_count += count_basket_aux
        
        if compression_algorithm == uproot.const.kZLIB:
            zlib_count += count_basket_aux 
        elif compression_algorithm == uproot.const.kLZMA:
            lzma_count += count_basket_aux
        elif compression_algorithm == uproot.const.kLZ4:
            lz4_count += count_basket_aux
        else:
            log.error("unrecognized compression algorithm: {0}".format(compression_algorithm))
        log.debug(prefix+"branch: "+branch.name)
    return branch_count, basket_count, lzma_count, lz4_count, zlib_count

def check_file(filename,  byte_ranges, is_full_file):
    tree_count = branch_count = basket_count = 0
    lzma_count = lz4_count = zlib_count = 0

    f = uproot.open(filename)
    for tree in f.itervalues():
        tree_count +=1
        log.debug("Tree: "+tree.name)
        for branch in tree.itervalues():
            count_branch_aux, count_basket_aux, count_lzma_aux, count_lz4_aux, count_zlib_aux = recursive_branch(branch, byte_ranges, is_full_file, tree.name, "")
            branch_count += count_branch_aux
            basket_count += count_basket_aux
            lzma_count += count_lzma_aux
            lz4_count += count_lz4_aux
            zlib_count += count_zlib_aux
   
    log.debug("num trees: "+str(tree_count))
    log.debug("num branches: "+str(branch_count))
    log.debug("num baskets: "+str(basket_count))
    log.debug("lzma count: "+str(lzma_count))
    log.debug("lz4 count: "+str(lz4_count))
    log.debug("zlib count: "+str(zlib_count))
  
    return tree_count, branch_count, basket_count, 100*lzma_count/basket_count, 100*lz4_count/basket_count, 100*zlib_count/basket_count 


# Argument parsing
def parseargs():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--path", dest="path", required=False,
                         help="Path to the files to files to analyze")

    parser.add_argument("--rootfile", dest="rootfile", required=False,
                         help=".root filename to be analyzed")

    parser.add_argument("--cinfofile", dest="cinfofile", required=False,
                         help=".cinfo filename corresponding to the root file to be analyzed")
    
    parser.add_argument("--full_file", dest="full_file", required=False, action="store_true",
                         help="Assume that the root file passed in --rootfile is fully downloaded thus does not requires a cinfo file (default: False)")

    parser.add_argument("--debug", dest="debug", required=False, action="store_true",
                         help="Set log to DEBUG mode (default: False)")

    parser.add_argument("--dry_run", dest="dry_run", required=False, action="store_true",
                         help="Just list the files to be analyzed but do not run the check")

    parser.add_argument("--max", dest="max", required=False, default=-1, type=int,
                         help="Maximum number of files to analyze default(unlimited)")

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

        # If --cinfofile is defined
        if args.cinfofile:
            # Check that it exists
            if os.path.isfile(args.cinfofile) == False:
                print("ERROR: --cinfofile: "+args.cinfofile+" does not exist")
                exit(1)
        # If neither --cinfo or --full_file aren't defined
        # we'll assume that rootfile+".cinfo" must exist
        elif args.full_file == False:
            if os.path.isfile(args.rootfile+".cinfo") == False:
                print("ERROR --cinfofile is not defined, neither --full_file and file: "+args.rootfile+".cinfo"+" does not exist")
                exit(1)
                
             
    # TODO:
    # make sure either path or rootfile are defined
    return args




###############################################################################
#                               MAIN
###############################################################################

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

#------ Parse arguments ------------------------------------------------------

#TODO
# validate that the path exist
path = args.path
assume_full_file = args.full_file

if not path:
    rootfile = args.rootfile
    cinfofile = args.cinfofile
    log.debug("@path is not defined, analyzing single file: "+rootfile)
    if not cinfofile and assume_full_file == False:
        cinfofile = rootfile+".cinfo"
        log.debug("Not --cinfofile or --full_file are defined assuming: "+cinfofile)
        only_filename_cinfo = os.path.basename(cinfofile)
        cinfo_files_dict = dict()
        cinfo_files_dict[only_filename_cinfo] = cinfofile
    only_filename_root  = os.path.basename(rootfile)
    root_files_dict = dict()
    root_files_dict[only_filename_root] = rootfile
else:
    root_files_dict  = list_files_recursively(path, ".root")
    cinfo_files_dict = list_files_recursively(path, ".cinfo")
    log.info("found: "+str(len(root_files_dict))+" .root files in: "+path)
#-----------------------------------------------------------------------------
max_counter = 0
if args.dry_run == True:
    for root_file in root_files_dict:
        if args.max > 0 and  max_counter >= args.max:
            break
        # Verify that there is a corresponfing .cinfo file
        root_filename  = root_files_dict[root_file]
        cinfo_filename = root_filename+".cinfo" 
        if root_file+".cinfo" in cinfo_files_dict:
            log.info("Analyzing file: "+ root_file)
        else:
            log.error("Cannot find a corresponding .cinfo file for root file:  %s", root_filename) 
        max_counter +=1

else:
    # For every root file
    file_details = [] 
    for root_file in root_files_dict:
        if args.max > 0 and max_counter >= args.max:
            break
        # Verify that there is a corresponfing .cinfo file
        root_filename  = root_files_dict[root_file]
        cinfo_filename = root_filename+".cinfo" 
        if assume_full_file == True or root_file+".cinfo" in cinfo_files_dict:
            log.info("Analyzing file: "+ root_file)
            # Step 1. Get file details
            if assume_full_file == True:
                is_full_file = True
                byte_ranges = None
            else:
                is_full_file, byte_ranges, percentage, fileSize= parse_cinfo(cinfo_filename)
                
            ## Step 2. Get trees, branchs and baskets details
            num_trees, num_branches, num_baskets, p_lzm4, p_zlib, p_lz4 = check_file(root_filename, byte_ranges, is_full_file)
            
            ## Step 3. Save record
            file_details.append([root_file, fileSize, percentage, num_trees, num_branches, num_baskets, p_lzm4, p_zlib, p_lz4])
            log.info("Done with file:  %s", root_filename) 
        max_counter +=1
    print("file name | file size | Downloaded % | num trees | num branches | num baskets | lzm4 % | zlib % | lz4 % | ")
    for record in file_details:
        print(record) 

