#include <std/io.pat>
#include <type/guid.pat>

struct Array<T> {
    u32 length;
    T data[length];
};
using String = Array<char>;

struct Material {
    String name;
    String data;
};
struct Texture {
    String name;
    u32 unknown;
};
struct Swatch {
    u8 unknown1[2];
    String path; // .swatchbin
    u8 unknown2[27];
};
struct Model {
    u16 type; // 16, 18
    String path; // .modelbin
    float matrix[16];
    u16 unknown1; // bitfield?
    String parent_bone_name;
    u16 parent_bone_index;
    u8 unknown2;
    u32 bone_number; // ??? index?
    Array<Material> materials;
    Array<Texture> textures; // texture names? vertex layers, UVs?

    u8 has_hash;
    if (has_hash) {
        u64 hash64; // of what?
    }

    float unknown3; // -1, 0.5
    Array<Swatch> swatches;
    u8 unknown5[19];
    String part_name;
    type::GUID guid;
    u8 zeroes[20];
    u32 unknown6;
    Array<type::GUID> unknown7; // reference to other Models

    if (type == 18) {
        u8 unknown8[5];
    }
};

struct ChunkA {
    u8 unknown1[7];
    Array<Model> models;
    float unknown2[8];
};

struct UnknownFloats {
    u8 unknown1[13];
    float unknown2[8];
};
struct ModelEx {
    Array<u32> unknown;
    Model model;
};
struct ChunkB {
    u16 type; // 3
    u32 unknown;
    Array<UnknownFloats> floats;
    Array<ModelEx> models;
};

struct Root {
    u16 type; // 5, 6
    type::GUID guid;
    u8 unknown1[5];
    String car_name;
    String skeleton_path;
    u16 unknown2; // 7F 00
    Array<ChunkA> chunk_a; // stock parts?
    Array<ChunkB> chunk_b; // upgrades, optional?
    if (type == 6) {
        u8 end_of_file;
    }
};

Root root @ 0x00;