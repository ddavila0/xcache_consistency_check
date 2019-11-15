# Get a path and an extension (e.g. .root or .cinfo) as inputs and it creates a list with all the
# files with such extension below thath path

import os
import sys
import glob
import argparse
import logging

import pdb; 
import checker

def parseargs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", dest="path", required=True,
                         help="Path to the files to files to analyze")

    args = parser.parse_args()

    return args

# Return a list of files, with a given @extension, found under @path
def list_files_recursively(path, extension):
    files_dict = dict()
    for x in os.walk(path):
        for file_with_path in glob.glob(os.path.join(x[0], "*"+extension)):
            only_filename = os.path.basename(file_with_path)
            files_dict[only_filename] = file_with_path
            
    return files_dict


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

#pdb.set_trace()

# For every root file 
for i in root_files_dict:
    # Verify that there is a corresponfing .cinfo file
    if i+".cinfo" in cinfo_files_dict:
        print("Start checking...")
        # Step 1. Calculate the byte ranges on the file
        # Step 2. Decompress every fully present basket in the file
    else:
        log.error("Cannot find a corresponding .cinfo file for root file:  %s", root_files_dict[i]) 
