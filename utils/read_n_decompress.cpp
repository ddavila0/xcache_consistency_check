#include <iostream>
#include <tuple>
#include <vector>
#include <string>
#include <fstream>
#include "zlib.h"
#include <chrono>

using namespace std;
using namespace std::chrono;


typedef std::tuple<long,int> btuple;


bool decompress(char * compressed_bytes, int basket_length, int num_decompressed_bytes, char ** decompressed_bytes){
    int ret;

    z_stream infstream;
    infstream.zalloc = Z_NULL;
    infstream.zfree = Z_NULL;
    infstream.opaque = Z_NULL;
    infstream.avail_in = (uInt)basket_length; // size of input
    infstream.next_in = (Bytef *)compressed_bytes; // input char array
    infstream.avail_out = (uInt)num_decompressed_bytes; // size of output
    infstream.next_out = (Bytef *)(*decompressed_bytes); // output char array
     
    // the actual DE-compression work.
    inflateInit(&infstream);
    ret = inflate(&infstream, Z_NO_FLUSH);
    inflateEnd(&infstream);
   
    if(ret == Z_STREAM_END)
        return 0;
    else
        return 1;
}

int main (int argc, char ** argv) {
    
    char * memblock;
    int num_baskets;
    long file_size, basket_start;
    int basket_length, pos;

    string delimiter = " ";
    string root_filename = argv[1]; 
    string basket_list_filename = argv[2];
    file_size = stol(argv[3]);
    string line;
    vector<btuple> baskets_vector;   
     
    cout << "root filename: "<< root_filename << endl;
    cout << "bl filename: "<< basket_list_filename << endl;
    cout << "root filesize: "<< file_size << endl;

    auto start_read = high_resolution_clock::now(); 
    //// Read the root file in memory
    ifstream root_file(root_filename, ios::in|ios::binary);
    if (root_file.is_open()){
        memblock = new char [file_size];
        if(memblock ==NULL){
            cout << "ERROR allocating memory" <<endl;
            return(1);
        }
        root_file.read(memblock, file_size);
    }
    
    auto stop_read = high_resolution_clock::now();
    auto duration_read = duration_cast<seconds>(stop_read - start_read); 
    cout << "duration of read: " << duration_read.count() << endl;
    
    auto start_list_baskets = high_resolution_clock::now(); 
    // Create a list of the baskets to decompress
    ifstream bl_file(basket_list_filename);
    if (bl_file.is_open()){
        while (getline (bl_file,line)){
            pos = line.find(delimiter);
            basket_start = stol(line.substr(0, pos));
            basket_length = stoi(line.substr(pos+1, line.length()));
            baskets_vector.push_back(btuple(basket_start, basket_length));
        }
        bl_file.close();
    }
    else{
        cout << "Unable to open file";
        return(1);
    }
    auto stop_list_baskets = high_resolution_clock::now(); 
    auto duration_list_baskets = duration_cast<seconds>(stop_list_baskets - start_list_baskets); 
    cout << "duration of list_baskets: " << duration_list_baskets.count() << endl;

     // For each basket
    int b_len; 
    long u1, u2, u3;
    long b_start, num_decompressed_bytes, max_uncompressed_size;	
    bool corrupted = false;
    
    auto start_decompress = high_resolution_clock::now(); 
	char * decompressed_bytes;
    int allocations = 0;
    max_uncompressed_size = 0;
    for(btuple t: baskets_vector){
        b_start = get<0>(t);
        b_len = get<1>(t);
	    u1 = memblock[b_start -3];
	    u2 = memblock[b_start -2];
	    u3 = memblock[b_start -1];
        //cout << u1 << ", " << u2 << ", " << u3 << endl;
        if(u1 < 0)
            u1+=256;

        if(u2 < 0)
            u2+=256;

        if(u3 < 0)
            u3+=256;
	    num_decompressed_bytes = u1 + (u2 << 8) + (u3 << 16);
        decompressed_bytes = new char[num_decompressed_bytes];
        if(num_decompressed_bytes > max_uncompressed_size){
            max_uncompressed_size = num_decompressed_bytes;
            delete[] decompressed_bytes;
            decompressed_bytes = new char[num_decompressed_bytes];
            allocations ++;
        }

        if(decompress(memblock+b_start, b_len, num_decompressed_bytes, &decompressed_bytes) != 0){
            corrupted = true;
        }
    }
    if(corrupted == true){
        cout << "File is corrupted" <<endl;
    }
    else{
        cout << "File is OK" <<endl;
    }

    auto stop_decompress = high_resolution_clock::now(); 
    auto duration_decompress = duration_cast<seconds>(stop_decompress - start_decompress); 
    cout << "duration of decompress: " << duration_decompress.count() << endl;
    cout << "number of reallocations: " << allocations << endl;
 
    delete[] decompressed_bytes;
    delete [] memblock;
    return 0;
}
