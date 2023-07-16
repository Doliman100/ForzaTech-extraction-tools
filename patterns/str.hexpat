struct Ref<SizeType, T> {
    T *data : SizeType;
};
struct SizedArray<SizeType, T> {
    SizeType length;
    T data[length];
};

struct StringInfo {
    u32 id;
    u32 offset;
};
struct List {
    u32 total_size; // strings_info + buffer
    u32 buffer_size;
    SizedArray<u32, StringInfo> strings_info;
    u8 buffer[buffer_size];
};

struct Root {
    u8 version[2];
    char table_name[128];
    SizedArray<u16, Ref<u32, List>> lists;
};

Root root @ 0x0;

//char16 string[] @ addressof(root.lists.data[0].data.buffer[954]);