import uproot
import sys

def parse_cinfo(filename_cinfo):

    fd = open(filename_cinfo)
    
    #TODO: Get it from cinfo file
    #blocksize=4096
    blocksize=1048576
    
    xcounter =0
    xcounter_aux = 0
    pcounter = 0
    pcounter_aux =0
    
    xflag = True
    pflag = False
    
    xstart=0
    xend = 0
    pstart =0
    pend = 0
    
    range_list= []
    
    i = 0
    for line in fd:
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

def is_branch_corrupted(branch):

    try:
        num_baskets = branch.numbaskets
    except Exception, e:
        print("ERROR numbaskets on branch: "+branch.name+ "--" +str(e))
        return True
    
    for i in range(0, num_baskets):
        basket_start = branch._fBasketSeek[i]
        basket_length = branch.basket_compressedbytes(i)        
        #status = 
        #print("Basket: "+str(i)+" start: "+str(basket_start)+" end: "+str(basket_start+basket_length)+" status: "+str(status))
        if is_full_file or basket_in_file(range_list, basket_start, basket_length) == 1:
            try:
                #basket = branch.basket(i)
                basket = branch.my_basket(i)
                #print(len(basket))
            except Exception, e:
                print("Corrupted basket: "+ str(i)+" in branch: "+branch.name + "--" +str(e))        
                return True
        else:
            print("ERROR: Basket not in file")
            exit(0)
    return False


def main():

    #------------------------------------------------------------
    #                   Configs
    #------------------------------------------------------------
    # Assume that all basket are full yin the file, no need
    # to filter out partial baskets
    is_full_file = True
    #------------------------------------------------------------
    
    #filename = sys.argv[1]
    #filename = "test3_part.root"
    #filename = "files/DAOD_STDM7.16395058._000079.pool.root.1"
    #filename = "files/corrupted/DAOD_STDM7.16394714._000023.pool.root.1"
    filename = "files/original/DAOD_STDM7.16394714._000023.pool.root.1"
    #filename_cinfo = filename+".cinfo"
    #filename_cinfo = "files/DAOD_STDM7.16395058._000079.pool.root.1.cinfo.extracted"
    #filename_cinfo = "extracted.txt"
    
    print("filename: "+filename)
    
    if not is_full_file:
        print("cinfo: "+filename_cinfo)
        range_list = parse_cinfo(filename_cinfo)
        for i in range_list:
            print(i)
    
    f = uproot.open(filename)
    #pdb.set_trace()
    #tree_list = []
    #t= f['MetaData']
    #tree_list.append(t)
    
    #for tree in tree_list:
    for tree in f.itervalues():
        print("Tree: "+tree.name)
        for branch in tree.itervalues():
            if len(branch.keys()) > 0:
                #print("  "+str(branch))
                print("  Branch: "+branch.name)
                for subranch in branch.itervalues():
                    corrupted = is_branch_corrupted(subranch)
                    if corrupted: 
                        print("    [C]Subranch: "+subranch.name)
                    else:
                        print("    Subranch: "+subranch.name)
                        #print("    "+str(subranch))
            else:
                corrupted = is_branch_corrupted(branch)
                if corrupted:
                    print("  [C]Branch: "+branch.name)
                else:
                    print("  Branch: "+branch.name)
                    #print("  "+str(branch))


if __name__ == "__main__":
    main()




