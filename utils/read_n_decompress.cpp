#include <iostream>
#include <tuple>
#include <vector>
#include <string>
#include <fstream>
#include "zlib.h"

using namespace std;


typedef std::tuple<long,int> btuple;

bool decompress(char * memblock, int basket_length);


bool decompress(char * compressed_bytes, int basket_length){
    char * decompressed_bytes;
    int ret;

    decompressed_bytes = new char[basket_length];

    z_stream infstream;
    infstream.zalloc = Z_NULL;
    infstream.zfree = Z_NULL;
    infstream.opaque = Z_NULL;
    infstream.avail_in = (uInt)basket_length; // size of input
    infstream.next_in = (Bytef *)compressed_bytes; // input char array
    infstream.avail_out = (uInt)basket_length; // size of output
    infstream.next_out = (Bytef *)decompressed_bytes; // output char array
     
    // the actual DE-compression work.
    inflateInit(&infstream);
    ret = inflate(&infstream, Z_NO_FLUSH);
    inflateEnd(&infstream);
   
    // cout << " decompressed length: " << infstream.total_out <<endl;
    //for(int i=0; i< infstream.total_out; i++){
    //for(int i=0; i< 64; i++){
    //    int aux = decompressed_bytes[i];
    //    cout << aux << " ";
    //} 
 
    return ret; 
}


int main (int argc, char ** argv) {
    
    char * memblock;
    int num_baskets;
    long file_size, basket_start;
    int basket_length, pos;
    string delimiter = " ";
    //string root_filename = "/Users/ddavila/projects/corrupted/files/test3.root"; 
    //string basket_list_filename = "/Users/ddavila/projects/corrupted/files/test3.bl";
    string root_filename = argv[1]; 
    string basket_list_filename = argv[2];
    file_size = stol(argv[3]);
    string line;
    vector<btuple> baskets_vector;   
     
    cout << "root filename: "<< root_filename << endl;
    cout << "bl filename: "<< basket_list_filename << endl;
    cout << "root filesize: "<< file_size << endl;

    // Read the root file in memory
    ifstream root_file(root_filename, ios::in|ios::binary);
    if (root_file.is_open()){
        memblock = new char [file_size];
        root_file.seekg (0);
        root_file.read (memblock, file_size);
        root_file.close();
    }
    else{
        cout << "Unable to open file";
        return(1);
    }
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

    // For each basket
    int b_start, b_len;
    bool corrupted = false;
    for(btuple t: baskets_vector){
        b_start = get<0>(t);
        b_len = get<1>(t);

        if(decompress(memblock+b_start, b_len) != 0){
            cout << b_start << ", " <<b_len;
            cout << " [C]" << endl;
            corrupted = true;
        }
    }
    if(corrupted == true){
        cout << "File is corrupted" <<endl;
    }
    else{
        cout << "File is OK" <<endl;
    }

    //decompress(memblock, basket_length);
    delete[] memblock;
    return 0;
}
