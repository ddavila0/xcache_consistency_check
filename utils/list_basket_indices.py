import uproot
import sys
import pdb
import zlib

if len(sys.argv) is not 2:
    print("Wrong number of arguments, expect 1: <filename>")
    exit(1)
filename = sys.argv[1]

#print("reading: "+filename)



def recursive_branch(branch, prefix):
    uncompress_count=0
    recovered_count=0
    memmap_count =0
    #print(prefix+"Branch: "+branch.name)
    if len(branch.keys()) > 0:
        for sub_branch in branch.itervalues():
            uncompress_aux, recovered_aux, memmap_aux =recursive_branch(sub_branch, "  "+prefix)
            uncompress_count +=uncompress_aux
            recovered_count +=recovered_aux
            memmap_count +=memmap_aux
    else:
        for i in range(0, branch.numbaskets):
            basket_start = branch._fBasketSeek[i]
            basket_length = branch.basket_compressedbytes(i)
            key = branch._threadsafe_key(i, None, True)
            if key.__class__.__name__ == '_RecoveredTBasket':
                #print("    Basket: "+str(i)+"\t [Recovered, "+str(basket_length)+"]")
                recovered_count +=1
                continue
                #TODO: do something
            else:
                class_name = key.source.__class__.__name__
                if class_name == "MemmapSource":
                    memmap_count +=1
                    continue
                    # Basket isn't compressed
                    basket_index = key.cursor.index
                else:
                    basket_index = key.source._cursor.index
                    #print("    Basket: "+str(i)+"\t ["+str(basket_index)+", "+str(basket_length)+"]")
                    #print(str(basket_index+9)+" "+str(basket_length-9))
                    print(str(basket_index+9))
                    #fd.seek(basket_index+9)
                    #compressed_bytes = fd.read(basket_length-9)
                    #try:
                    #    uncompressed_bytes = zlib.decompress(compressed_bytes)
                    #    uncompress_count +=1
                    #except Exception, e:
                    #    print("ERROR when trying to decompress basket: "+str(i)+" from branch: "+branch.name)
                    #    print(e)
                    #    exit(1)    
    return uncompress_count, recovered_count, memmap_count


#pdb.set_trace()
f = uproot.open(filename)
fd = open(filename)
uncompress_count=0
recovered_count=0
memmap_count =0
for tree in f.itervalues():
   if "TObjString" in str(tree.__class__):
        print("Not a tree: "+str(tree))
   else:
        #print("Tree: "+tree.name)
        for branch in tree.itervalues():
            uncompress_aux, recovered_aux, memmap_aux =recursive_branch(branch, "    ")
            uncompress_count +=uncompress_aux
            recovered_count +=recovered_aux
            memmap_count +=memmap_aux
            #for i in range(0, branch.numbaskets):
            #    basket = branch.my_basket(i)
            #    basket_start = branch._fBasketSeek[i]+74
            #    basket_length = branch.basket_compressedbytes(i)-9
            #    #basket_end = basket_start + basket_length
            #    #print("    Basket: "+str(i)+"\t ["+str(basket_start)+", "+str(basket_length)+"]")
            #    print("    Basket: "+str(i)+"\t ["+str(basket_start)+", "+str(basket_length)+"]")
#print("uncompress_count: "+str(uncompress_count))
#print("recovered_count: "+str(recovered_count))
#print("memmap_count: "+str(memmap_count))
fd.close()
