# Xcache consistency check

It is a utility that looks for corrupted baskets within root files, it does so by decompressing every basket in the
file, when the decompression is sucessfull it assumes the basket is ok and continues with the next basket. If abasket
fails to decompress, the algoritm will log it and exit.

When dealing with a partial file(where not all baskets are fully present in the file), the algorithm
uses the .cinfo file to determine whether a bsaket is fully present on the file before attempting to
decompress it.

## Examples of use

In the following there are few examples of the use of this tool under different circumstances.
Check the help to see all the options ```bin/xcache_consistency_check --help```

There are 2 things to consider when using this tool:

1. Whether we want to analyze a single file or all the files below a directory(recursively)
2. Whether the file(s) is full or not, i.e. all the baskets are fully downloaded in the file 




#### Analyze a single root file that is full.

```
bin/xcache_consistency_check --rootfile <ROOT_FILE> --full_file
```

#### Analyze a single partial root file when there is a corresponding cinfo file with the same name and path as the root file to be analized.

```
bin/xcache_consistency_check --rootfile <ROOT_FILE>
```

If the .root and the .cinfo file do not have the same name or/and path, use the --cinfofile option

```
bin/xcache_consistency_check --rootfile <ROOT_FILE> --cinfofile <CORRESPONDING_CINFO>
```

#### Analyze all files under a certain directory.  When dealing with multiple partial files
```
bin/xcache_consistency_check --path <PATH_TO_ROOT_FILES>
```

Similarly you can use the --full_file option to indicate that all the file are full or not.
```
bin/xcache_consistency_check --path <PATH_TO_ROOT_FILES> --full_file
```

When dealing with multiple partial files, it assumes that there is a corresponding .cinfo file for each
root file found, if a .cinfo file is missing an error should be logged but the algorithm should continue running

