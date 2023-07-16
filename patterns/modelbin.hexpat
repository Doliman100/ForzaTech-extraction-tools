//#pragma pattern_limit 200000
#include <std/io.pat>

struct Array<T, Length> {
    Length length;
    T data[length];
};
using String = Array<char, u32>;

fn relative_to_grandparent(u128 offset) {
    return addressof(parent.parent);
};

// Properties
struct BoundingBox {
    float x_min;
    float y_min;
    float z_min;
    float x_max;
    float y_max;
    float z_max;
};
struct Property {
    char tag[4];
    u16 data_size; // bit-shifted left by 4
    match (tag) {
        ("  dI"): s32 *data_address : u16 [[pointer_base("relative_to_grandparent")]];
        ("emaN"): char *data_address[data_size >> 4] : u16 [[pointer_base("relative_to_grandparent")]];
        ("xoBB"): BoundingBox *data_address : u16 [[pointer_base("relative_to_grandparent")]];
        ("feRT"): Array<u32, u32> *data_address : u16 [[pointer_base("relative_to_grandparent")]];
        (_): u8 *data_address[data_size >> 4] : u16 [[pointer_base("relative_to_grandparent")]];
    }
};

// Skel
struct Bone {
    String name;
    s16 parent_id;
    s16 first_child_id;
    s16 next_id;
    float matrix[16];
};
struct Skeleton {
    Array<Bone, u16> bones;
    u8 unknown1[4];
};

// Mrph
struct Morph {
    Array<String, u16> weights;
};

// IndB
struct IndexBuffer {
    u32 length;
    u32 size;
    u16 block_size;
    u16 block_units; // ?
    u32 type;
    u32 indices[length];
};

// VLay
struct VertexLayer {
    u16 type;
    u16 block_type; // ?
    u32 blocks_length;
    u32 data_length; // ?
    u8 delimeter[8];
};
struct VertexLayers {
    Array<String, u16> names;
    Array<VertexLayer, u16> layers;
    u32 unknown1[layers.length];
    u32 unknown2;
};

// VerB
struct Vertex {
    s16 x, y, z; // normalized
    u16 unknown;
};
struct VertexBuffer {
    u32 length;
    u32 size;
    u16 block_size;
    u16 block_units;
    u32 type; // positions, texture coordinates
    Vertex vertices[length];
};

// Mdel
struct Model {
    u16 mesh_length;
    u16 unknown;
    u16 vertex_layers_length;
    u16 material_info_length;
};

struct Entry {
    char tag[4];
    u8 unknown1[2];
    u16 properties_length;
    Property *properties[properties_length] : u32;
    match (tag) {
        ("lekS"): Skeleton *data_address : u32;
        ("hprM"): Morph *data_address : u32;
        ("BdnI"): IndexBuffer *data_address : u32;
        ("yaLV"): VertexLayers *data_address : u32;
        ("BreV"): VertexBuffer *data_address : u32;
        ("ldoM"): Model *data_address : u32;
        (_): u8 *data_address : u32; // aligned to 4 bytes
    }
    u32 data_size[2];
};

struct Root {    
    char tag[4]; // "Grub"
    u8 unknown1[4]; // 01 01 00 00
    u8 *data_address : u32;
    u32 file_size;
    Array<Entry, u32> entries;
};

Root root @ 0x00;