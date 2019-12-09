import uproot

b1 = uproot.newbranch("i4", compression=uproot.ZLIB(5))
b2 = uproot.newbranch("i8", compression=uproot.LZMA(4))
b3 = uproot.newbranch("f4")

branchdict = {"branch1": b1, "branch2": b2, "branch3": b3}
tree = uproot.newtree(branchdict, compression=uproot.LZ4(4))
with uproot.recreate("example.root", compression=uproot.LZMA(5)) as f:
    f["t"] = tree
    f["t"].extend({"branch1": [1]*1000, "branch2": [2]*1000, "branch3": [3]*1000})
