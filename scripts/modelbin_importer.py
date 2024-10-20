import bpy
import bmesh
from collections import defaultdict
import io
import math
import os
import struct
from uuid import UUID

#game_path = R"D:\games\rips\FH2XO"
game_path = R"D:\games\rips\OpusDev"
#game_path = R"D:\games\rips\FH5"

#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\_library\Scene\KOE_Agera_Alt_001\Scene\exterior\bumperf\bumperF_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\Exterior\Hood\hood_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\_library\Scene\KOE_Agera_Alt_001\Scene\exterior\doors\doorLF_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\Exterior\Platform\body_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\_library\Scene\KOE_Agera_Alt_001\Scene\interior\floor\floor_a__SLOD.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\_library\Scene\KOE_Agera_Alt_001\Scene\exterior\primarylights\glassLHL_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\_library\Scene\KOE_Agera_Alt_001\Scene\exterior\primarylights\headlightL_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\koe_one_15\scene\Interior\dash\dashPad_custom_a.modelbin"

#p = R"D:\games\rips\OpusDev\media\cars\_library\scene\wheels\CRA_Series313\CRA_Series313_wheelLF.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\_library\scene\tires\tire_vintage\tireL_vintage.modelbin"
#p = R"D:\games\rips\FH2XOne\media\cars\NIS_SkylineFF_99\scene\Exterior\BumperF\bumperF_a.modelbin"
#p = R"D:\games\rips\FH5\media\Tracks\Hendrix\GeoChunk0\scratch\p4\woodstock\zipcache\pc\tracks\hendrix\scene\models\barnfind\global\brn_gbl_barnfind_exterior_a\brn_gbl_barnfind_exterior_a_cluster000.i.modelbin"
#p = R"D:\games\rips\FH5_modelbin\media\Homespace\Barnfind_DOD_ViperGTSACR_99\Barnfind_DOD_ViperGTSACR_99.modelbin"
#p = R"D:\games\rips\FH5_modelbin\media\particlesmodels\Prop_Cargo_Plane_01.modelbin"
#p = R"D:\games\rips\OpusDev\media\drivers\stig\driver.modelbin"
#p = R"D:\games\rips\OpusDev\media\Crowds\Opus_Male_01\Rigged\Opus_Male.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\SUB_199_WRXSTIVT15r_16\scene\_library\scene\SUB_199_WRXSTIVT15r_Alt_001\Scene\exterior\bumperf\bumperf_a.modelbin"
#p = R"D:\games\rips\FM\media\pcfamily\characters\_drivers\_library\body01_m\driver_full.modelbin"
#p = R"D:\games\rips\FH2XO\media\cars\AUD_S4_13\scene\Exterior\Doors\doorHandleLF_a.modelbin"
#p = R"D:\games\rips\FH2XO\media\cars\MER_SLR_05\scene\Exterior\BumperF\bumperF_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\MER_SLR_05\scene\Exterior\BumperF\bumperF_a.modelbin"
#p = R"D:\games\rips\OpusDev\MicrosoftStore_DLC\Hot Wheels\Media\Cinematic_Assets_OpusIsland\Showcase_AirshipIsland\Showcase_AirshipIsland.modelbin"
#p = R"D:\games\rips\FH5\media\Cars\koe_one_15\scene\_library\Scene\KOE_Agera_Alt_001\Scene\exterior\bumperf\bumperF_a.modelbin.bak"
#p = R"D:\games\rips\OpusDev\media\cars\_library\scene\tires\tire_OW_vintageRace\tireL_OW_vintageRace.modelbin"

p = R"D:\games\rips\OpusDev\media\cars\FOR_FocusRSRX_16\scene\Exterior\BumperF\bumperF_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\FOR_FocusRSRX_16\scene\Exterior\Fenders\fenders_a.modelbin"
#p = R"D:\games\rips\OpusDev\media\cars\FOR_FocusRSRX_16\scene\Exterior\Hood\hood_a.modelbin"

requested_level_of_detail = 1 << 0 # LODS, LOD0, LOD1, ...
requested_render_pass = 0xFFFF # empty: 1 << 1, max: 1 << 5
use_materials = False # set True, if you want to test materials
shader_processor = 1 # 0 - none, 1 - per-shader, 2 - universal shader # when use_materials == True

TireWidthMM = 145
Aspect = 80
WheelOriginalDiameterIN = 10
WheelDiameterIN = 15
weights = None
scale_x = 1
#weights = ((WheelDiameterIN - 10) / 14, (1 - TireWidthMM / 1000) / 0.9) # rim
#weights = ((TireWidthMM * Aspect / 100 - 225 + WheelOriginalDiameterIN * 12.7) / 275, (WheelDiameterIN - 10) / 14, 0, 0, 0) # tire, not verified
#scale_x = TireWidthMM / 1000

# IOSys module
class BinaryStream:
    def __init__(self, buffer: memoryview): # buffer is memoryview
        self._stream = io.BytesIO(buffer)
    
    def __getitem__(self, key: slice):
        return self._stream.getbuffer()[key] # replace with self.__buffer[key] ?
    
    def tell(self):
        return self._stream.tell()
    
    def seek(self, offset: int, whence: int = 0):
        return self._stream.seek(offset, whence)
    
    def read(self, size: int | None = None):
        return self._stream.read(size)
    
    def read_string(self):
        length = self.read_u32()
        return self._stream.read(length).decode("utf-8")

    def read_7bit_string(self):
        length = self.read_7bit()
        return self._stream.read(length).decode("utf-8")
    
    def read_s16(self):
        v = self._stream.read(2)
        if not v:
            return None
        return struct.unpack('h', v)[0]
    
    def read_u8(self):
        v = self._stream.read(1)
        if not v:
            return None
        return struct.unpack('B', v)[0]
    
    def read_u16(self):
        v = self._stream.read(2)
        if not v:
            return None
        return struct.unpack('H', v)[0]
    
    def read_s32(self):
        v = self._stream.read(4)
        if not v:
            return None
        return struct.unpack('i', v)[0]
    
    def read_u32(self):
        v = self._stream.read(4)
        if not v:
            return None
        return struct.unpack('I', v)[0]
    
    def read_f16(self):
        v = self._stream.read(2)
        if not v:
            return None
        return struct.unpack('e', v)[0]
    
    def read_f32(self):
        v = self._stream.read(4)
        if not v:
            return None
        return struct.unpack('f', v)[0]
    
    def read_sn16(self):
        return self.read_s16() / 32767
    
    def read_un8(self):
        return self.read_u8() / 255
    
    def read_un16(self):
        return self.read_u16() / 65535
    
    def read_7bit(self):
        value = 0
        shift = 0
        while True:
            value_byte = self.read_u8()
            value |= (value_byte & 0x7F) << shift
            shift += 7
            if value_byte & 0x80 == 0:
                break
        return value

    # Deserialize<std::vector<std::string>>()
    # Deserialize<std::vector<T>>(T &obj) # T is ISerializable
    #   obj.Deserialize()

# Utils
class GamePathResolver:
    def __init__(self, path):
        self.path = path # base
    
    def resolve(self, path):
        if path[:5].lower() != "game:":
            print("Warning: Swatchbin path doesn't start with \"Game:\".")
        return self.path + path[5:] # TODO: support directories without media\cars\
        # TODO: find "game:" mount point. Example: Game:\Media\cars\_library\materials\exterior_misc\carPaint_livery.materialbin
        # 1. check if right part of current dir is "\Media\cars\_library\materials\exterior_misc" (C:\media\abc\media\test.modelbin -> "game:"="C:\media\abc")
        # 2. if not, test "\Media\cars\_library\materials\exterior_misc"
        # ...
        # 3. if not, test "\Media"
        # 4. assume that "game:"=current dir
        # ignore material if not found, print warning
        # find game: once, then use cached
        # what if game:\media\a.materialbin and c:\media\cars\a.modelbin?

# Bundle module
class Tag: # enum CommonModel::Serialization::Tags::Enum; Bundle::BlobTag?
    # bundle
    Grub = 0x47727562 # 'Grub'; BundleTag
    
    # metadata
    Id = 0x49642020 # 'Id  '
    Name = 0x4E616D65 # 'Name'

    TXCH = 0x54584348 # 'TXCH'
    
    # blob
    Modl = 0x4D6F646C # 'Modl'
    Skel = 0x536B656C # 'Skel'
    MatI = 0x4D617449 # 'MatI'
    Mesh = 0x4D657368 # 'Mesh'
    VLay = 0x564C6179 # 'VLay'
    IndB = 0x496E6442 # 'IndB'
    VerB = 0x56657242 # 'VerB'
    MBuf = 0x4D427566 # 'MBuf'

    MATI = 0x4D415449
    MATL = 0x4D41544C
    MTPR = 0x4D545052 # 'MTPR'
    DFPR = 0x44465052

    TXCB = 0x54584342 # 'TXCB'

class Version:
    def __init__(self):
        self.major = 0
        self.minor = 0
    
    def deserialize(self, stream: BinaryStream):
        self.major = stream.read_u8()
        self.minor = stream.read_u8()
    
    def is_at_least(self, major, minor):
        return self.major > major or self.major == major and self.minor >= minor
    
    def is_at_most(self, major, minor):
        return self.major < major or self.major == major and self.minor <= minor
    
    def is_equal(self, major, minor):
        return self.major == major and self.minor == minor

class Metadata:
    def __init__(self):
        self.tag = 0
        self.version = 0
    
    def deserialize(self, stream: BinaryStream):
        self.tag = stream.read_u32()
        version_and_size = stream.read_u16()
        self.version = version_and_size & 0xF
        size = version_and_size >> 4
        offset = stream.read_u16()
        self.stream = BinaryStream(stream[offset : offset + size])
    
    def read_string(self):
        return self.stream.read().decode('utf-8')
    
    def read_s32(self):
        return self.stream.read_s32()

class Blob:
    def __init__(self):
        self.tag = 0
        self.version = Version()
        self.metadata_length = 0
        self.metadata_offset = 0
        self.data_offset = 0
        self.data_size = 0
    
    def deserialize(self, stream: BinaryStream):
        self.tag = stream.read_u32()
        self.version.deserialize(stream)
        self.metadata_length = stream.read_u16()
        self.metadata_offset = stream.read_u32()
        self.data_offset = stream.read_u32()
        self.data_size = stream.read_u32()
        stream.seek(4, os.SEEK_CUR)
        self.metadata = {}
        for i in range(0, self.metadata_length):
            metadata = Metadata()
            metadata.deserialize(BinaryStream(stream[self.metadata_offset + i * 8:]))
            self.metadata[metadata.tag] = metadata
        self.stream = BinaryStream(stream[self.data_offset : self.data_offset + self.data_size])

class Bundle:
    def __init__(self):
        self.tag = 0
        self.version = Version()
        self.blobs_length = 0
        self.blobs = defaultdict(list) # std::unordered_multimap<uint32_t, Blob>
    
    def deserialize(self, stream: BinaryStream):
        self.tag = stream.read_u32()
        if self.tag != Tag.Grub:
            print("Warning: Bundle has invalid tag. Expected 'Grub'.")
        self.version.deserialize(stream)
        if not self.version.is_at_most(1, 1):
            print(F"Warning: Unsupported version. Found: {self.version.major}.{self.version.minor}. Max supported: 1.1")
        self.blobs_length = stream.read_u16()
        stream.seek(4 * 2, os.SEEK_CUR)
        if self.version.is_at_least(1, 1):
            self.blobs_length = stream.read_u32()
        for _ in range(self.blobs_length):
            blob = Blob()
            blob.deserialize(stream)
            self.blobs[blob.tag].append(blob)

class Model: # CommonModel::Model
    def __init__(self):
        self.meshes_length = 0
        self.buffers_length = 0
        self.vertex_layouts_length = 0
        self.materials_length = 0
        # self.lowest_level_of_detail = 0
        # self.highest_level_of_detail = 0
        self.levels_of_detail = 0 # LODFlags
        self.decompress_flags = 0
    
    def deserialize(self, blob: Blob):
        # read metadata?

        stream = blob.stream
        self.meshes_length = stream.read_s16()
        self.buffers_length = stream.read_s16()
        self.vertex_layouts_length = stream.read_s16()
        self.materials_length = stream.read_s16()
        stream.seek(4, os.SEEK_CUR)
        self.levels_of_detail = stream.read_u16()
        if blob.version.is_at_least(1, 2):
            self.decompress_flags = stream.read_u8()
            # stream.seek(1, os.SEEK_CUR)
        # if blob.version.is_at_least(1, 3):
        #     stream.seek(1 * 2, os.SEEK_CUR)

class D3D12_INPUT_ELEMENT_DESC:
    def __init__(self):
        self.semantic_name = ""
        self.semantic_index = 0
        self.input_slot = 0
        self.format = 0

class VertexLayout: # CommonModel::VertexLayout
    def __init__(self):
        self.element_names_length = 0
        self.element_names = None
        self.elements_length = 0
        self.elements = defaultdict(D3D12_INPUT_ELEMENT_DESC)
        # self.semantics = 0 # bitfield
    
    def deserialize(self, stream: BinaryStream):
        self.element_names_length = stream.read_u16()
        self.element_names = [None] * self.element_names_length
        for i in range(self.element_names_length):
            self.element_names[i] = stream.read_string()
        self.elements_length = stream.read_u16()
        # self.elements = [D3D12_INPUT_ELEMENT_DESC()] * self.elements_length # std::vector<D3D12_INPUT_ELEMENT_DESC>
        for i in range(self.elements_length):
            # self.elements[i].semantic_name = self.element_names[stream.read_u16()]
            self.semantic_name = self.element_names[stream.read_u16()]
            self.semantic_index = stream.read_u16()
            element = self.elements[self.semantic_name + str(self.semantic_index)] # TEXCOORD0, TEXCOORD1, ...
            element.input_slot = stream.read_u16()
            stream.seek(2, os.SEEK_CUR)
            element.format = stream.read_u32()
            stream.seek(4 * 2, os.SEEK_CUR)
        # stream.seek(4 * self.elements_length, os.SEEK_CUR) # PackedFormats
        # if blob.version.is_at_least(1, 1):
        #     self.semantics = stream.read_u32()

class ModelBuffer: # CommonModel::ModelBuffer
    def __init__(self):
        self.length = 0
        self.size = 0
        self.stride = 0
        # self.elements_length = 0
        self.format = 0
    
    def deserialize(self, blob: Blob):
        self.length = blob.stream.read_u32()
        self.size = blob.stream.read_u32()
        self.stride = blob.stream.read_u16()
        blob.stream.seek(1 + 1, os.SEEK_CUR)
        if blob.version.is_at_least(1, 0):
            self.format = blob.stream.read_u32()
            self.stream = blob.stream[0x10 : 0x10 + self.size]
        else:
            self.stream = blob.stream[0xC : 0xC + self.size]

class Mesh_VertexBufferIndex:
    def __init__(self):
        self.id = 0
        # self.input_slot = 0
        self.stride = 0
        self.offset = 0

class Mesh: # CommonModel::Mesh
    def __init__(self):
        self.material_id = 0
        self.bone_index = 0
        self.levels_of_detail = 0
        self.render_pass = 0
        self.skinning_elements_count = 0
        self.morph_weights_count = 0
        self.index_buffer_id = 0
        self.start_index_location = 0
        self.base_vertex_location = 0
        self.index_count = 0
        self.uv_transforms = [None] * 5
    
    def deserialize(self, blob: Blob):
        self.name = blob.metadata[Tag.Name].read_string()

        self.material_id = blob.stream.read_s16()
        if blob.version.is_at_least(1, 9):
            self.material_id = blob.stream.read_s16()
            blob.stream.seek(2 * 2, os.SEEK_CUR)
        self.bone_index = blob.stream.read_s16()
        self.levels_of_detail = blob.stream.read_u16()
        blob.stream.seek(2, os.SEEK_CUR)
        self.render_pass = blob.stream.read_u16()
        blob.stream.seek(1, os.SEEK_CUR)
        if blob.version.is_at_least(1, 2):
            self.skinning_elements_count = blob.stream.read_u8()
            self.morph_weights_count = blob.stream.read_u8()
        if blob.version.is_at_least(1, 3):
            blob.stream.seek(1, os.SEEK_CUR)
        blob.stream.seek(1 + 2, os.SEEK_CUR)
        self.index_buffer_id = blob.stream.read_s32()
        blob.stream.seek(4, os.SEEK_CUR)
        self.start_index_location = blob.stream.read_s32()
        self.base_vertex_location = blob.stream.read_s32()
        self.index_count = blob.stream.read_u32()
        blob.stream.seek(4, os.SEEK_CUR)
        if blob.version.is_at_least(1, 6):
            blob.stream.seek(4 + 4, os.SEEK_CUR)
        self.vertex_layout_id = blob.stream.read_u32()
        self.vertex_buffer_indices_length = blob.stream.read_u32()
        self.vertex_buffer_indices = [None] * self.vertex_buffer_indices_length
        for i in range(0, self.vertex_buffer_indices_length):
            vertex_buffer_index = Mesh_VertexBufferIndex()
            vertex_buffer_index.id = blob.stream.read_s32()
            input_slot = blob.stream.read_s32()
            vertex_buffer_index.stride = blob.stream.read_s32()
            vertex_buffer_index.offset = blob.stream.read_s32()
            self.vertex_buffer_indices[input_slot] = vertex_buffer_index
        if blob.version.is_at_least(1, 4):
            self.morph_data_buffer_id = blob.stream.read_s32()
            self.skinning_data_buffer_id = blob.stream.read_s32()
        self.constant_buffer_indices_length = blob.stream.read_u32()
        if self.constant_buffer_indices_length != 0:
            print("Warning: Mesh.constant_buffer_indices_length != 0. Please report it in GitHub issue.")
            # throw exception
        if blob.version.is_at_least(1, 1):
            blob.stream.seek(4, os.SEEK_CUR)
        if blob.version.is_at_least(1, 5):
            for i in range(5):
                self.uv_transforms[i] = ((blob.stream.read_f32(), blob.stream.read_f32()), (blob.stream.read_f32(), blob.stream.read_f32()))
        if blob.version.is_at_least(1, 8):
            self.scale = [blob.stream.read_f32(), blob.stream.read_f32(), blob.stream.read_f32(), blob.stream.read_f32()]
            self.translate = [blob.stream.read_f32(), blob.stream.read_f32(), blob.stream.read_f32(), blob.stream.read_f32()]

class Texture:
    def __init__(self, path):
        self.path = path
        self.buffer = None
        #self.buffer_size
        self.guid = ""
    
    @staticmethod
    def from_path(path: str):
        p = path_resolver.resolve(path)
        if p is None:
            return None
        t = Texture(p)
        t.deserialize()
        return t
    
    def deserialize(self):
        # TODO: read swatchbin header without TXCB data; reserve dds buffer, write header, then write TXCB data
        # print("Texture: " + self.path)
        f = open(self.path, "rb", 0)
        s = BinaryStream(f.read())
        f.close()

        bundle = Bundle()
        bundle.deserialize(s)

        # TODO: parse encoding and pitch parameter table properly
        blob = bundle.blobs[Tag.TXCB][0] # TODO: create TextureContent class
        header_stream = blob.metadata[Tag.TXCH].stream
        header_stream.seek(4 + 4, os.SEEK_CUR)
        self.guid = "{" + str(UUID(bytes_le=header_stream.read(16))).upper() + "}"
        width = header_stream.read(4)
        height = header_stream.read(4)
        header_stream.seek(4 + 2, os.SEEK_CUR)
        mip_levels = header_stream.read(1)
        header_stream.seek(1, os.SEEK_CUR)
        transcoding = header_stream.read_u32()
        header_stream.seek(4, os.SEEK_CUR)
        color_profile = header_stream.read_u32()
        header_stream.seek(4 + 8, os.SEEK_CUR)
        encoding = header_stream.read_u32()
        header_stream.seek(8, os.SEEK_CUR)
        linear_size = header_stream.read(4) # linear_size for compressed, pitch for uncompressed?
        format_encoded = encoding if transcoding <= 1 else transcoding - 2
        match format_encoded:
            case 0:
                format = 72 if color_profile else 71 # DXGI_FORMAT_BC1_UNORM
            case 1:
                format = 75 if color_profile else 74 # DXGI_FORMAT_BC2_UNORM
            case 2:
                format = 78 if color_profile else 77 # DXGI_FORMAT_BC3_UNORM
            case 3:
                format = 80 # DXGI_FORMAT_BC4_UNORM
            case 4:
                format = 81 # DXGI_FORMAT_BC4_SNORM
            case 5:
                format = 83 # DXGI_FORMAT_BC5_UNORM
            case 6:
                format = 84 # DXGI_FORMAT_BC5_SNORM
            case 7:
                format = 95 # DXGI_FORMAT_BC6H_UF16
            case 8:
                format = 96 # DXGI_FORMAT_BC6H_SF16
            case 9:
                format = 99 if color_profile else 98 # DXGI_FORMAT_BC7_UNORM
            case 13:
                format = 29 if color_profile else 28 # DXGI_FORMAT_R8G8B8A8_UNORM
            case _:
                format = 0 # DXGI_FORMAT_UNKNOWN
                print("Warning: Unknown texture format.")

        # TODO: generate DDS header using Microsoft library
        self.buffer = b''.join([
            b'\x44\x44\x53\x20\x7C\x00\x00\x00\x07\x10\x0A\x00', height,
            width, linear_size, b'\x01\x00\x00\x00', mip_levels, b'\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20\x00\x00\x00',
            b'\x04\x00\x00\x00\x44\x58\x31\x30\x00\x00\x00\x00\x00\x00\x00\x00',
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\x10\x40\x00',
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            struct.pack("I", format), b'\x03\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00',
            b'\x03\x00\x00\x00', blob.stream.read()])
         # Image.pack doesn't support memoryview

class ShaderParameter:
    def __init__(self):
        self.hash = 0
        self.guid = None
        self.type = 0
        # self.value_stream = None
    
    def deserialize(self, stream: BinaryStream):
        version = Version()
        version.deserialize(stream)
        if not version.is_at_least(2, 0):
            print("Error: Shader Parameter versions below 2.0 are not supported.")
        self.hash = stream.read_u32()
        if version.is_at_least(3, 1) and stream.read_u8() != 0:
            stream.seek(4, os.SEEK_CUR)
        self.type = stream.read_u8()
        if version.is_at_least(3, 0):
            self.guid = stream.read(16)
        # else:
        #     print("Error: Shader Parameter versions below 3.0 are not supported (no GUID).")
        self.value_stream = stream
        match self.type:
            case 0 | 5 | 9: # Vector_ShaderParameter, Swizzle_ShaderParameter, FunctionRange_ShaderParameter
                stream.seek(16, os.SEEK_CUR)
            case 1: # Color_ShaderParameter
                self.value = (stream.read_f32(), stream.read_f32(), stream.read_f32(), stream.read_f32())
            case 2: # Float_ShaderParameter
                self.value = stream.read_f32()
            case 4: # Int_ShaderParameter
                stream.seek(4, os.SEEK_CUR)
            case 3: # Bool_ShaderParameter
                self.value = stream.read_u32() != 0
            case 6: # Texture2D_ShaderParameter
                # str_length = stream.read_7bit()
                # stream.seek(str_length + 4, os.SEEK_CUR)
                self.path = stream.read_7bit_string()
                stream.seek(4, os.SEEK_CUR)
            case 7: # Sampler_ShaderParameter
                stream.seek(4 * 2, os.SEEK_CUR)
                if version.is_at_least(1, 1):
                    stream.seek(4, os.SEEK_CUR)
            case 8: # ColorGradient_ShaderParameter
                length = stream.read_u32()
                stream.seek(4 * length, os.SEEK_CUR)
            case 11: # Vector2_ShaderParameter
                self.value = (stream.read_f32(), stream.read_f32())
                if not version.is_at_least(2, 0):
                    stream.seek(8, os.SEEK_CUR)

class MaterialSystemObject:
    def __init__(self):
        self.parameters = {} # dict
        self.shader_name = None
    
    def deserialize(self, stream: BinaryStream):
        bundle = Bundle()
        bundle.deserialize(stream)

        parent_blobs = bundle.blobs[Tag.MATI]
        if len(parent_blobs) == 0:
            parent_blobs = bundle.blobs[Tag.MATL]
        if len(parent_blobs) != 0:
            parent_blob = parent_blobs[0]
            parent_path = parent_blob.stream.read_7bit_string()
            # TODO: cache files to don't process them again
            f_path = path_resolver.resolve(parent_path)
            # print("Material: " + f_path)
            f = open(f_path, "rb", 0)
            s = BinaryStream(f.read())
            f.close()
            parent = MaterialSystemObject()
            parent.deserialize(s)
            self.shader_name = parent.shader_name
            if self.shader_name is None:
                self.shader_name = parent_blob.metadata[Tag.Name].read_string()
            self.parameters = parent.parameters

        shader_parameters_blobs = bundle.blobs[Tag.MTPR]
        if len(shader_parameters_blobs) == 0:
            shader_parameters_blobs = bundle.blobs[Tag.DFPR]
        parameters_blob = shader_parameters_blobs[0]
        if parameters_blob.version.is_at_least(2, 1):
            parameters_length = parameters_blob.stream.read_u16()
        else:
            parameters_length = parameters_blob.stream.read_u8()
        if not parameters_blob.version.is_at_least(2, 0):
            print("Error: MTPR/DFPR versions below 2.0 are not supported.")
        for i in range(parameters_length):
            parameter = ShaderParameter()
            parameter.deserialize(parameters_blob.stream)
            # self.parameters[parameter.guid] = parameter
            self.parameters[parameter.hash] = parameter

class ShaderParameterName:
    # bumperF
    CH1DiffuseTextureTexture = 0x10350BBC
    UseDiffuseAlphaBool = 0xD047A271
    CH1DiffuseTextureSwitchBool = 0x7169AC81
    CH1AlphaSwitchBool = 0xE159D67B
    CH1AlphaTextureTexture = 0x66E53F62
    UniqueBaseColorSwitchBool = 0xE1D827FD
    UniqueBaseTextureSwitchBool = 0x9615CAAA
    ColorGroupSwitchBool = 0x78004A9C
    UniqueBaseColorColorParam = 0xEA718FBE
    PaintColorGroupColorParam = 0x0014A502
    PaintColorColorParam = 0xC0CB2820
    FlakeGloss_floatVal = 0x99CC69B1

    # badge
    DiffuseTextureSwitchBool = 0x05A401E7
    CH1MaskSwitchBool = 0x08B2C17F
    DiffuseColorColorParam = 0x63040D89
    
    # emblem
    DiffuseATexture = 0x6DD98CD9
    CH1DiffColTextureSwitchBool = 0x04F8F9FA
    NormalTexture = 0x8C658791
    CH1OpacityMaskSwitchBool = 0xA6BF15E8
    CH1OpacitySwitchBool = 0xCBB3D988
    CH1GlossMaskSwitchBool = 0x5A0DA36A

    # radiator
    DiffuseColorGroupColorParam = 0xF51639BE
    GlossTexture = 0x7E4A41E1
    AlphaTexture = 0x57D9D49E
    GlossA_floatVal = 0x52E99DA3
    CH1NormalMapSwitchBool = 0x553D641D
    CH1LocalAOSwitchBool = 0xE876DDCC

    # clc_metalch2normalch1mask
    CH2DiffuseTextureTexture = 0x294DA6FC
    ColorGroupColorParam = 0x73A9E2DF
    CH2DiffuseTextureTiling = 0x519B26A1
    NormalTiling = 0x730F2086
    LocalAOSwitchBool = 0x6C03F944
    CH2NormalSwitchBool = 0x255EF28A

    # ch2diffnormglossalphaemissive
    uTile_floatVal = 0xB0B8947E
    vTile_floatVal = 0xCCD9B1A5
    DiffuseColorAColorParam = 0xEF5CCE09
    CH2GlossMaskSwitchBool = 0xF5A4EEA0
    CH2NormalMapSwitchBool = 0xFA9429D7
    CH2OpacityMaskSwitchBool = 0x9FC7B8A8

    # simplediffuse
    ColorColorParam = 0x57C321A6

    # ch1ch2normlerpch1glossdiff
    CH1GlossDiffMaskTexture = 0x022DF609

class MaterialInstance: # MaterialSystem::MaterialInstance : MaterialSystemObject
    def __init__(self):
        self.name = ""
        self.valid = False
        self.diffuse_color = (1, 1, 1, 1)
        self.diffuse_texture = None
        self.diffuse_texture_tiling = (1, 1)
        self.diffuse_texture_texcoord = "TEXCOORD0"
        self.normal_texture = None
        self.normal_texture_tiling = (1, 1)
        self.normal_texture_texcoord = "TEXCOORD0"
        self.alpha_texture = None
        self.alpha_texture_output = 0 # channel
        self.gloss_value = None
        self.gloss_texture = None
        self.gloss_texture_output = 0
        self.gloss_texture_tiling = (1, 1)
        self.gloss_texture_texcoord = "TEXCOORD0"
        self.gloss_invert = False
        self.lcao_texture = None # local AO
        self.lcao_texture_output = 0
        self.lcao_texture_tiling = (1, 1)
        self.lcao_texture_texcoord = "TEXCOORD0"
        # self.ao_texture = None
    
    def deserialize(self, blob: Blob):
        self.name = blob.metadata[Tag.Name].read_string()
        
        if not use_materials:
            return
        
        material = MaterialSystemObject()
        material.deserialize(blob.stream)

        # universal:
        # normal_texture = NormalTexture -- if no bool parameters and one NormalTexture, then normal_texture is present
        #  if CH2NormalMapSwitchBool == false, then normal_texture = None
        #  if CH2NormalSwitchBool == false, then normal_texture = None
        #  if CH1NormalMapSwitchBool == false, then normal_texture = None
        
        # print(material.shader_name)
        if shader_processor == 1:
            match material.shader_name:
                case "carpaint_standard":
                    self.valid = True
                    self.diffuse_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.CH1DiffuseTextureTexture].path))
                    self.diffuse_texture.deserialize()
                    self.alpha_texture = self.diffuse_texture
                    self.alpha_texture_output = 1
                    if material.parameters[ShaderParameterName.UniqueBaseColorSwitchBool].value and not material.parameters[ShaderParameterName.UniqueBaseTextureSwitchBool].value:
                        self.diffuse_texture = None
                        self.diffuse_color = material.parameters[ShaderParameterName.UniqueBaseColorColorParam].value
                    if not material.parameters[ShaderParameterName.CH1DiffuseTextureSwitchBool].value:
                        self.diffuse_texture = None
                        if material.parameters[ShaderParameterName.ColorGroupSwitchBool].value:
                            self.diffuse_color = material.parameters[ShaderParameterName.PaintColorGroupColorParam].value
                        else:
                            self.diffuse_color = material.parameters[ShaderParameterName.PaintColorColorParam].value
                        if not material.parameters[ShaderParameterName.UseDiffuseAlphaBool].value:
                            self.alpha_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.CH1AlphaTextureTexture].path))
                            self.alpha_texture_output = 0
                    if not material.parameters[ShaderParameterName.CH1AlphaSwitchBool].value:
                        self.alpha_texture = None
                    self.gloss_value = material.parameters[ShaderParameterName.FlakeGloss_floatVal].value # TODO: confirm in shader
                case "badge_clc_diffuseMetalLERPCH1MaskNorm": # badge
                    self.valid = True
                    if material.parameters[ShaderParameterName.DiffuseTextureSwitchBool].value:
                        self.diffuse_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.DiffuseATexture].path))
                        self.diffuse_texture.deserialize()
                        self.gloss_texture = self.diffuse_texture
                        self.gloss_texture_output = 1
                    else:
                        self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorColorParam].value
                        self.gloss_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.CH1MaskTexture].path))
                        self.gloss_texture.deserialize()
                    if not material.parameters[ShaderParameterName.CH1MaskSwitchBool].value:
                        self.gloss_texture = None
                    self.normal_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.NormalTexture].path))
                    self.normal_texture.deserialize()
                    if material.parameters[ShaderParameterName.CH1OpacitySwitchBool].value:
                        self.alpha_texture = self.normal_texture
                        self.alpha_texture_output = 1
                case "badge_ch1difnormglossao": # emblem
                    self.valid = True
                    if material.parameters[ShaderParameterName.CH1DiffColTextureSwitchBool].value:
                        self.diffuse_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.DiffuseATexture].path))
                        self.diffuse_texture.deserialize()
                        self.gloss_texture = self.diffuse_texture
                        self.gloss_texture_output = 1
                    else:
                        self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorGroupColorParam].value
                        self.gloss_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.GlossTexture].path))
                        self.gloss_texture.deserialize()
                    self.normal_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.NormalTexture].path))
                    self.normal_texture.deserialize()
                    self.alpha_texture = self.normal_texture
                    self.alpha_texture_output = 1
                    if not material.parameters[ShaderParameterName.CH1GlossMaskSwitchBool].value:
                        self.gloss_texture = None
                        self.gloss_color = material.parameters[ShaderParameterName.GlossA_floatVal].value
                    if not material.parameters[ShaderParameterName.CH1OpacityMaskSwitchBool].value:
                        self.alpha_texture = None
                case "ch1diffnormglossalphaemissive": # radiator
                    self.valid = True
                    # self.has_diffuse_texture = True
                    self.diffuse_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.DiffuseATexture].path))
                    self.diffuse_texture.deserialize()
                    if not material.parameters[ShaderParameterName.CH1DiffColTextureSwitchBool].value:
                        self.diffuse_texture = None
                        self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorGroupColorParam].value
                    self.gloss_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.GlossTexture].path))
                    self.gloss_texture.deserialize()
                    if not material.parameters[ShaderParameterName.CH1GlossMaskSwitchBool].value:
                        self.gloss_texture = None
                        self.gloss_value = material.parameters[ShaderParameterName.GlossA_floatVal].value
                    # self.has_normal = material.parameters[ShaderParameterName.CH1NormalMapSwitchBool].value
                    self.normal_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.NormalTexture].path))
                    self.normal_texture.deserialize()
                    self.lcao_texture = self.normal_texture
                    self.lcao_texture_output = 1
                    if not material.parameters[ShaderParameterName.CH1NormalMapSwitchBool].value:
                        self.normal_texture = None
                        self.lcao_texture = None
                    if not material.parameters[ShaderParameterName.CH1LocalAOSwitchBool].value:
                        self.lcao_texture = None
                        self.lcao_color = (1, 1, 1)
                    self.alpha_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.AlphaTexture].path))
                    self.alpha_texture.deserialize()
                    if not material.parameters[ShaderParameterName.CH1OpacityMaskSwitchBool].value:
                        self.alpha_texture = None
                case "clc_metalch2normalch1mask":
                    self.valid = True
                    self.diffuse_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.CH2DiffuseTextureTexture].path))
                    self.diffuse_texture.deserialize()
                    if not material.parameters[ShaderParameterName.DiffuseTextureSwitchBool].value:
                        self.diffuse_texture = None
                        self.diffuse_color = material.parameters[ShaderParameterName.ColorGroupColorParam].value
                    self.normal_texture_texcoord = "TEXCOORD1"
                    self.normal_texture_tiling = material.parameters[ShaderParameterName.NormalTiling].value
                    self.normal_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.NormalTexture].path))
                    self.normal_texture.deserialize()
                    self.lcao_texture_texcoord = self.normal_texture_texcoord
                    self.lcao_texture = self.normal_texture
                    self.lcao_texture_output = 1
                    self.lcao_texture_tiling = self.normal_texture_tiling
                    if not material.parameters[ShaderParameterName.LocalAOSwitchBool].value:
                        self.lcao_texture = None
                    if not material.parameters[ShaderParameterName.CH2NormalSwitchBool].value:
                        self.normal_texture = None
                case "ch2diffnormglossalphaemissive": # belt
                    self.valid = True
                    self.gloss_texture_texcoord = "TEXCOORD1"
                    self.gloss_texture_tiling = (material.parameters[ShaderParameterName.uTile_floatVal].value, material.parameters[ShaderParameterName.vTile_floatVal].value)
                    self.gloss_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.GlossTexture].path))
                    self.gloss_texture.deserialize()
                    self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorAColorParam].value
                    if not material.parameters[ShaderParameterName.CH2GlossMaskSwitchBool].value:
                        self.gloss_texture = None
                    self.normal_texture_texcoord = self.gloss_texture_texcoord
                    self.normal_texture_tiling = self.gloss_texture_tiling
                    self.normal_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.NormalTexture].path))
                    self.normal_texture.deserialize()
                    if not material.parameters[ShaderParameterName.CH2NormalMapSwitchBool].value:
                        self.normal_texture = None
                    self.alpha_texture_texcoord = self.gloss_texture_texcoord
                    self.alpha_texture_tiling = self.gloss_texture_tiling
                    self.alpha_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.AlphaTexture].path))
                    self.alpha_texture.deserialize()
                    if not material.parameters[ShaderParameterName.CH2OpacityMaskSwitchBool].value:
                        self.alpha_texture = None
                case "ext_grille": # grill
                    self.valid = True
                    self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorGroupColorParam].value
                    self.normal_texture_texcoord = "TEXCOORD1"
                    self.normal_texture_tiling = material.parameters[ShaderParameterName.NormalTiling].value
                    self.normal_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.NormalTexture].path))
                    self.normal_texture.deserialize()
                    self.gloss_invert = True # ???
                    self.gloss_texture_texcoord = self.normal_texture_texcoord
                    self.gloss_texture = self.normal_texture
                    self.gloss_texture_output = 1
                    self.gloss_texture_tiling = self.normal_texture_tiling
                case "simplediffuse": # frame
                    self.valid = True
                    self.diffuse_color = material.parameters[ShaderParameterName.ColorColorParam].value
                case "ch1ch2normlerpch1glossdiff": # splitter
                    self.valid = True
                    self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorAColorParam].value
                    self.gloss_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.CH1GlossDiffMaskTexture].path))
                    self.gloss_texture.deserialize()
                    if not material.parameters[ShaderParameterName.CH1GlossMaskSwitchBool].value:
                        self.gloss_texture = None
                case "m_ch2normglossalphaemissive":
                    self.valid = True
                    # self.diffuse_color = (1, 1, 1, 1)
                    self.diffuse_color = (0, 0, 0, 1)
                    self.gloss_value = 0 # placeholder, metal mirror
                case "undercarriage":
                    self.valid = True
                    self.diffuse_texture = Texture(path_resolver.resolve(material.parameters[ShaderParameterName.DiffuseATexture].path))
                    self.diffuse_texture.deserialize()
        elif shader_processor == 2:
            self.valid = True
            if ShaderParameterName.DiffuseATexture in material.parameters:
                if material.parameters[ShaderParameterName.DiffuseATexture].path != "":
                    self.diffuse_texture = Texture.from_path(material.parameters[ShaderParameterName.DiffuseATexture].path)
                    if ShaderParameterName.DiffuseTextureSwitchBool in material.parameters:
                        if not material.parameters[ShaderParameterName.DiffuseTextureSwitchBool].value:
                            self.diffuse_texture = None
                    elif ShaderParameterName.CH1DiffColTextureSwitchBool in material.parameters:
                        # self.diffuse_texture_texcoord = "TEXCOORD1"
                        if not material.parameters[ShaderParameterName.CH1DiffColTextureSwitchBool].value:
                            self.diffuse_texture = None
            elif ShaderParameterName.CH1DiffuseTextureTexture in material.parameters:
                self.diffuse_texture = Texture.from_path(material.parameters[ShaderParameterName.CH1DiffuseTextureTexture].path)
                if ShaderParameterName.UniqueBaseColorSwitchBool in material.parameters and material.parameters[ShaderParameterName.UniqueBaseColorSwitchBool].value and not material.parameters[ShaderParameterName.UniqueBaseTextureSwitchBool].value:
                    self.diffuse_texture = None
                elif ShaderParameterName.CH1DiffuseTextureSwitchBool in material.parameters:
                    if not material.parameters[ShaderParameterName.CH1DiffuseTextureSwitchBool].value:
                        self.diffuse_texture = None
                elif ShaderParameterName.DiffuseTextureSwitchBool in material.parameters:
                    if not material.parameters[ShaderParameterName.DiffuseTextureSwitchBool].value:
                        self.diffuse_texture = None
            elif ShaderParameterName.CH2DiffuseTextureTexture in material.parameters:
                self.diffuse_texture = Texture.from_path(material.parameters[ShaderParameterName.CH2DiffuseTextureTexture].path)
                self.diffuse_texture_texcoord = "TEXCOORD1"
                if ShaderParameterName.uTile_floatVal in material.parameters and ShaderParameterName.vTile_floatVal in material.parameters:
                    self.diffuse_texture_tiling = (material.parameters[ShaderParameterName.uTile_floatVal].value, material.parameters[ShaderParameterName.vTile_floatVal].value)
                if ShaderParameterName.DiffuseTextureSwitchBool in material.parameters:
                    if not material.parameters[ShaderParameterName.DiffuseTextureSwitchBool].value:
                        self.diffuse_texture = None
            self.diffuse_color = (0, 0, 0, 1)
            if self.diffuse_texture is None:
                if ShaderParameterName.DiffuseColorGroupColorParam in material.parameters:
                    self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorGroupColorParam].value
                elif ShaderParameterName.DiffuseColorAColorParam in material.parameters:
                    self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorAColorParam].value
                elif ShaderParameterName.ColorGroupColorParam in material.parameters:
                    self.diffuse_color = material.parameters[ShaderParameterName.ColorGroupColorParam].value
                elif ShaderParameterName.DiffuseColorColorParam in material.parameters:
                    self.diffuse_color = material.parameters[ShaderParameterName.DiffuseColorColorParam].value
                elif ShaderParameterName.UniqueBaseColorSwitchBool in material.parameters and material.parameters[ShaderParameterName.UniqueBaseColorSwitchBool].value:
                    self.diffuse_color = material.parameters[ShaderParameterName.UniqueBaseColorColorParam].value
                elif ShaderParameterName.ColorGroupSwitchBool in material.parameters:
                    if material.parameters[ShaderParameterName.ColorGroupSwitchBool].value:
                        self.diffuse_color = material.parameters[ShaderParameterName.PaintColorGroupColorParam].value
                    else:
                        self.diffuse_color = material.parameters[ShaderParameterName.PaintColorColorParam].value
                elif ShaderParameterName.ColorColorParam in material.parameters:
                    self.diffuse_color = material.parameters[ShaderParameterName.ColorColorParam].value

# CommonModel::Pose?
class Bone:
    def __init__(self):
        self.name = ""
        self.transform = [[1 if i == j else 0 for i in range(4)] for j in range(4)]
    
    def deserialize(self, blob: Blob):
        self.name_length = blob.stream.read_u32()
        self.name = blob.stream.read(self.name_length).decode("utf-8")
        self.parent_index = blob.stream.read_s16()
        self.child_index = blob.stream.read_s16()
        self.next_index = blob.stream.read_s16()
        for j in range(4):
            for i in range(4):
                self.transform[j][i] = blob.stream.read_f32()

class Skeleton:
    def __init__(self):
        # store id->transform
        self.bones_length = 0
    
    def deserialize(self, blob: Blob):
        self.bones_length = blob.stream.read_u16()
        self.bones = [Bone() for _ in range(self.bones_length)]
        transform = [[0 for _ in range(4)] for _ in range(4)]
        for bone in self.bones:
            bone.deserialize(blob)
            if bone.parent_index != -1:
                tr = self.bones[bone.parent_index].transform
                for j in range(4):
                    for i in range(4):
                        transform[j][i] = 0
                for i in range(4): # TODO: replace with mathutils.Matrix multiplication
                    for j in range(4):
                        for k in range(4):
                            transform[i][j] += bone.transform[i][k] * tr[k][j]
                bone.transform = [row[:] for row in transform]
        # if blob.version.is_at_least(1, 0):
        #     blob.stream.seek(blob.stream.read_u32(), os.SEEK_CUR)

# main
path_resolver = GamePathResolver(game_path)

f = open(p, "rb", 0)
s = BinaryStream(memoryview(f.read()))
f.close()

bundle = Bundle()
bundle.deserialize(s)

model_blobs = bundle.blobs[Tag.Modl]
if len(model_blobs) != 1:
    print("Warning: Read unexpected number of 'Modl' entries. Expected [1].")
model_blob = model_blobs[0]
model = Model()
model.deserialize(model_blob)
if model.levels_of_detail & requested_level_of_detail == 0:
    print(F"Error: Model has no requested LOD. Requested 0x{requested_level_of_detail:x}, Contained 0x{model.levels_of_detail:x}.")

skeleton_blobs = bundle.blobs[Tag.Skel]
if len(skeleton_blobs) != 1:
    print("Warning: Read unexpected number of 'Skel' entries. Expected [1].")
skeleton_blob = skeleton_blobs[0]
skeleton = Skeleton()
skeleton.deserialize(skeleton_blob)

vertex_layout_blobs = bundle.blobs[Tag.VLay]
vertex_layout_blobs_length = len(vertex_layout_blobs)
if vertex_layout_blobs_length != model.vertex_layouts_length:
    print(F"Warning: Read unexpected number of 'VLay' entries. Read [{vertex_layout_blobs_length}]. Expected [{model.vertex_layouts_length}].")
vertex_layouts = [VertexLayout() for _ in range(vertex_layout_blobs_length)]
for vertex_layout, vertex_layout_blob in zip(vertex_layouts, vertex_layout_blobs):
    vertex_layout.deserialize(vertex_layout_blob.stream)

index_buffer_blobs = bundle.blobs[Tag.IndB]
if len(index_buffer_blobs) != 1:
    print("Warning: Read unexpected number of 'IndB' entries. Expected [1].")
index_buffer = ModelBuffer()
index_buffer.deserialize(index_buffer_blobs[0])

vertex_buffer_blobs = bundle.blobs[Tag.VerB] # TODO: process buffers in batch, then just access required verts?
vertex_buffers = [ModelBuffer() for _ in range(len(vertex_buffer_blobs))]
for vertex_buffer_blob in vertex_buffer_blobs:
    vertex_buffers[vertex_buffer_blob.metadata[Tag.Id].read_s32() + 1].deserialize(vertex_buffer_blob)

morph_data_buffer_blobs = bundle.blobs[Tag.MBuf]
morph_data_buffers = [ModelBuffer() for _ in range(len(morph_data_buffer_blobs))]
for morph_data_buffer_blob in morph_data_buffer_blobs:
    morph_data_buffers[morph_data_buffer_blob.metadata[Tag.Id].read_s32()].deserialize(morph_data_buffer_blob)

mesh_blobs = bundle.blobs[Tag.Mesh]
mesh_blobs_length = len(mesh_blobs)
if mesh_blobs_length != model.meshes_length:
    print(F"Warning: Read unexpected number of 'Mesh' entries. Read [{mesh_blobs_length}]. Expected [{model.meshes_length}].")
meshes = [Mesh() for _ in range(mesh_blobs_length)]
for mesh, mesh_blob in zip(meshes, mesh_blobs):
    mesh.deserialize(mesh_blob)

material_blobs = bundle.blobs[Tag.MatI]
material_blobs_length = len(material_blobs)
if material_blobs_length != model.materials_length:
    print(F"Warning: Read unexpected number of 'MatI' entries. Read [{material_blobs_length}]. Expected [{model.materials_length}].")
materials = [MaterialInstance() for _ in range(material_blobs_length)]
for material_blob in material_blobs:
    materials[material_blob.metadata[Tag.Id].read_s32()].deserialize(material_blob)

# processing
draw_indices = [None] * index_buffer.length
verts = [(0, 0, 0)] * vertex_buffers[0].length # assumption that VerB[-1] contains all possible vertices
norms = [(0, 0, 0)] * vertex_buffers[0].length
uvs = [[(0, 0)] * vertex_buffers[0].length for _ in range(5)]
colors = [(1, 1, 1, 1)] * vertex_buffers[0].length

class VertexLayout_Element:
    def __init__(self):
        self.stream = None
        self.advance = 0 # next, after read data from stream
        self.format = -1

for mesh in meshes:
#for mesh in [meshes[0]]:
    if mesh.levels_of_detail & requested_level_of_detail == 0:
        continue
    if mesh.render_pass & 0x10 == 0: # Shadow
        continue
    if mesh.render_pass & requested_render_pass == 0:
        continue

    vertex_id_min = 0xFFFFFFFF
    vertex_id_max = 0
    stream = BinaryStream(index_buffer.stream[mesh.start_index_location * index_buffer.stride : (mesh.start_index_location + mesh.index_count) * index_buffer.stride]) # mesh.index_buffer_id
    for i in range(mesh.index_count):
        if index_buffer.stride == 4:
            vertex_id = stream.read_u32()
        else:
            vertex_id = stream.read_u16()
        if vertex_id_max < vertex_id:
            vertex_id_max = vertex_id
        if vertex_id_min > vertex_id:
            vertex_id_min = vertex_id
        draw_indices[i] = vertex_id
    
    faces = []
    for i in range(mesh.index_count // 3): # reshape
        j = i * 3
        faces.append((draw_indices[j] - vertex_id_min, draw_indices[j + 2] - vertex_id_min, draw_indices[j + 1] - vertex_id_min)) # (A, B, C)->(A, C, B); Left-handed -> Right-handed coordinate system

    vertex_buffer_offsets = [0 for _ in range(mesh.vertex_buffer_indices_length)]
    
    elements = defaultdict(VertexLayout_Element)
    for semantic_name, vertex_layout_element_desc in vertex_layouts[mesh.vertex_layout_id].elements.items():
        vertex_buffer_index = mesh.vertex_buffer_indices[vertex_layout_element_desc.input_slot]
        vertex_buffer = vertex_buffers[vertex_buffer_index.id + 1]
        
        element = elements[semantic_name]
        element.stream = BinaryStream(vertex_buffer.stream[vertex_buffer_index.offset + (vertex_id_min + mesh.base_vertex_location) * vertex_buffer.stride + vertex_buffer_offsets[vertex_layout_element_desc.input_slot] : vertex_buffer_index.offset + (vertex_id_max + mesh.base_vertex_location + 1) * vertex_buffer.stride + vertex_buffer_offsets[vertex_layout_element_desc.input_slot]])
        element.format = vertex_layout_element_desc.format
        element.advance = vertex_buffer.stride

        match vertex_layout_element_desc.format:
            case 6: # DXGI_FORMAT_R32G32B32_FLOAT
                vertex_buffer_offsets[vertex_layout_element_desc.input_slot] += 12
            case 10 | 13: # DXGI_FORMAT_R16G16B16A16_FLOAT, DXGI_FORMAT_R16G16B16A16_SNORM
                vertex_buffer_offsets[vertex_layout_element_desc.input_slot] += 8
            case 24 | 28 | 35 | 37: # DXGI_FORMAT_R10G10B10A2_UNORM, DXGI_FORMAT_R8G8B8A8_UNORM, DXGI_FORMAT_R16G16_UNORM, DXGI_FORMAT_R16G16_SNORM
                vertex_buffer_offsets[vertex_layout_element_desc.input_slot] += 4
            case _:
                print(F"Error: Unexpected element format: {vertex_layout_element_desc.format}.")

    position0 = elements["POSITION0"]
    if position0.format == 13: # DXGI_FORMAT_R16G16B16A16_SNORM
        position0.advance -= 8
    elif position0.format == 6: # DXGI_FORMAT_R32G32B32_FLOAT
        position0.advance -= 12
    elif position0.format != -1:
        print("Error: Unexpected position format.")

    normal0 = elements["NORMAL0"]
    if normal0.format == 37: # DXGI_FORMAT_R16G16_SNORM
        normal0.advance -= 4
    elif normal0.format == 10: # DXGI_FORMAT_R16G16B16A16_FLOAT
        normal0.advance -= 6
    elif normal0.format != -1:
        print("Error: Unexpected normal format.")

    color0 = elements["COLOR0"]
    if color0.format == 28: # DXGI_FORMAT_R8G8B8A8_UNORM
        color0.advance -= 4
    elif color0.format != -1:
        print("Error: Unexpected color format.")

    texcoords = [None] * 5
    for i in range(5):
        texcoords[i] = elements["TEXCOORD" + str(i)]
        if texcoords[i].format == 35: # DXGI_FORMAT_R16G16_UNORM
            texcoords[i].advance -= 4
        elif texcoords[i].format != -1:
            print("Error: Unexpected texcoord format.")

    morph_data = VertexLayout_Element()
    if mesh.morph_weights_count > 0 and weights:
        morph_data_buffer = morph_data_buffers[mesh.morph_data_buffer_id]
        morph_data.stream = BinaryStream(morph_data_buffer.stream[(vertex_id_min + mesh.base_vertex_location) * morph_data_buffer.stride : (vertex_id_max + mesh.base_vertex_location + 1) * morph_data_buffer.stride])
        morph_data.format = morph_data_buffer.format
        morph_data.advance = morph_data_buffer.stride
        if morph_data.format == 10: # DXGI_FORMAT_R16G16B16A16_FLOAT
            morph_data.advance -= 4
        else:
            print("Error: Unexpected morph data format.")

    n = [1, 0, 0]
    for vertex_id in range(vertex_id_min, vertex_id_max + 1): # TODO: split loop on small wrapped with if-statement
        for texcoord, uv, uv_transform in zip(texcoords, uvs, mesh.uv_transforms):
            if texcoord.format == 35:
                t = [texcoord.stream.read_un16(), texcoord.stream.read_un16()]
                t[0] = t[0] * uv_transform[0][1] + uv_transform[0][0]
                t[1] = t[1] * uv_transform[1][1] + uv_transform[1][0]
                uv[vertex_id] = ((t[0], 1 - t[1]))
                texcoord.stream.seek(texcoord.advance, os.SEEK_CUR)

        if color0.format != -1:
            c = (color0.stream.read_un8(), color0.stream.read_un8(), color0.stream.read_un8(), color0.stream.read_un8())
            colors[vertex_id] = (c[0], c[1], c[2], c[3])
            #colors[vertex_id] = (c[0], 0, 0, 1)
            #colors[vertex_id] = (0, c[1], 0, 1)
            #colors[vertex_id] = (0, 0, c[2], 1)
            #colors[vertex_id] = (color0.stream.read_un8(), color0.stream.read_un8(), color0.stream.read_un8(), color0.stream.read_un8())
            #if colors[vertex_id][3] != 1:
            #    print("Warning: Color.A != 1.")
            color0.stream.seek(color0.advance, os.SEEK_CUR)

        if position0.format == 13:
            v = [position0.stream.read_sn16() * mesh.scale[0] + mesh.translate[0], position0.stream.read_sn16() * mesh.scale[1] + mesh.translate[1], position0.stream.read_sn16() * mesh.scale[2] + mesh.translate[2]]
            v_w = position0.stream.read_sn16()
        else:
            v = [position0.stream.read_f32(), position0.stream.read_f32(), position0.stream.read_f32()] # FH2
        position0.stream.seek(position0.advance, os.SEEK_CUR)

        if normal0.format == 37: # model.decompress_flags
            n = [v_w, normal0.stream.read_sn16(), normal0.stream.read_sn16()]
            normal0.stream.seek(normal0.advance, os.SEEK_CUR)
        elif normal0.format == 10:
            n = [normal0.stream.read_f16(), normal0.stream.read_f16(), normal0.stream.read_f16()] # FH2
            normal0.stream.seek(normal0.advance, os.SEEK_CUR)

        if morph_data.format == 10:
            for i in range(mesh.morph_weights_count):
                m = (morph_data.stream.read_f16(), morph_data.stream.read_f16(), morph_data.stream.read_f16())
                weight = weights[int(morph_data.stream.read_f16())]
                v[0] += m[0] * weight # TODO: replace with mathutils.Vector
                v[1] += m[1] * weight
                v[2] += m[2] * weight
            for i in range(mesh.morph_weights_count):
                m = (morph_data.stream.read_f16(), morph_data.stream.read_f16(), morph_data.stream.read_f16())
                weight = weights[int(morph_data.stream.read_f16())]
                n[0] += m[0] * weight
                n[1] += m[1] * weight
                n[2] += m[2] * weight
            
            # norm; TODO: replace with mathutils.Vector.normalize()
            n_length = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
            n[0] /= n_length
            n[1] /= n_length
            n[2] /= n_length
            
            v[0] *= self.scale_x
            n[0] /= self.scale_x # n * transpose(invert(scale_x))
        
        # TODO: don't bake transform to vertex position
        v2 = [0, 0, 0]
        n2 = [0, 0, 0]
#        transform = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
#        transform = ((0.7071067811865476, -0.7071067811865476, 0, 0), (0.7071067811865476, 0.7071067811865476, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)) # rotate_z_330
        transform = skeleton.bones[mesh.bone_index].transform
        for j in range(3):
            for k in range(4):
                if k == 3:
                    v2[j] += transform[k][j]
                else:
                    v2[j] += v[k] * transform[k][j]
                    n2[j] += n[k] * transform[k][j]
        
        # norm; located at the beginning of the pixel shader; TODO: replace with mathutils.Vector.normalize()
        n_length = math.sqrt(n2[0] * n2[0] + n2[1] * n2[1] + n2[2] * n2[2])
        n2[0] /= n_length
        n2[1] /= n_length
        n2[2] /= n_length
        
        verts[vertex_id] = (-v2[0], -v2[2], v2[1]) # Y-up, Left-handed -> Z-up, Right-handed
#        verts[vertex_id] = (-v[0], -v[2], v[1])
        norms[vertex_id] = (-n2[0], -n2[2], n2[1])
#        norms[vertex_id] = (-n[0], -n[2], n[1])
    
    verts2 = verts[vertex_id_min : vertex_id_max + 1] # bad, memory copying
    norms2 = norms[vertex_id_min : vertex_id_max + 1]

    name = ""
    #if mesh.render_pass >> 6 != 0:
    #    name += str(mesh.render_pass >> 6)
    #name += F"({(mesh.render_pass >> 5) & 1}{(mesh.render_pass >> 4) & 1}{(mesh.render_pass >> 3) & 1}{(mesh.render_pass >> 2) & 1}{(mesh.render_pass >> 1) & 1}{mesh.render_pass & 1})"
    name += mesh.name
    name += " " + materials[mesh.material_id].name
    if "COLOR0" not in vertex_layouts[mesh.vertex_layout_id].elements:
        name += " [no color]"
        # print(F"Mesh \"{name}\" has no COLOR0")
    # paste below
    mesh2 = bpy.data.meshes.new(name=name)
    mesh2.from_pydata(verts2, [], faces, False)
    if normal0.format in [10, 37]:
        mesh2.normals_split_custom_set_from_vertices(norms2)
    #mesh2.validate(verbose=True)
    #mesh2.update()
    obj = bpy.data.objects.new(name, mesh2)
    #obj.rotation_euler[0] = math.radians(90) # Forza -> Blender coordinates
    #obj.scale[0] = -1
    
    #mat = bpy.data.materials.get("Material")
    #if mat is None:
    material_instance = materials[mesh.material_id]
    if material_instance.valid:
        material = bpy.data.materials.new(material_instance.name)
        material.use_nodes = True
        
        principled_bsdf = material.node_tree.nodes.get("Principled BSDF")
        
        diffuse_mul_node = material.node_tree.nodes.new("ShaderNodeVectorMath")
        diffuse_mul_node.operation = "MULTIPLY"
        diffuse_mul_node.inputs[0].default_value = (1, 1, 1)
        diffuse_mul_node.inputs[1].default_value = (1, 1, 1)
        material.node_tree.links.new(diffuse_mul_node.outputs[0], principled_bsdf.inputs[0])

        texture = material_instance.diffuse_texture
        if texture is not None:
            texture_image = bpy.data.images.get(texture.guid)
            if texture_image is None:
                texture_image = bpy.data.images.new(texture.guid, 1, 1) # TextureContext.guid or filename
                texture_image.pack(data=texture.buffer, data_len=len(texture.buffer))
                texture_image.source = "FILE"
                texture_image.alpha_mode = "CHANNEL_PACKED"
            texture_image_node = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture_image_node.image = texture_image
            material.node_tree.links.new(texture_image_node.outputs[0], diffuse_mul_node.inputs[0])
            
            uv_mul_node = material.node_tree.nodes.new("ShaderNodeVectorMath")
            uv_mul_node.operation = "MULTIPLY"
            uv_mul_node.inputs[1].default_value = (material_instance.diffuse_texture_tiling[0], material_instance.diffuse_texture_tiling[1], 1)
            material.node_tree.links.new(uv_mul_node.outputs[0], texture_image_node.inputs[0])
            
            uv_map_node = material.node_tree.nodes.new("ShaderNodeUVMap")
            uv_map_node.uv_map = material_instance.diffuse_texture_texcoord
            material.node_tree.links.new(uv_map_node.outputs[0], uv_mul_node.inputs[0])
        else:
            color_node = material.node_tree.nodes.new("ShaderNodeRGB")
            color_node.outputs[0].default_value = material_instance.diffuse_color
            material.node_tree.links.new(color_node.outputs[0], diffuse_mul_node.inputs[0])
        
        texture = material_instance.alpha_texture
        if texture is not None:
            texture_image = bpy.data.images.get(texture.guid)
            if texture_image is None:
                texture_image = bpy.data.images.new(texture.guid, 1, 1)
                texture_image.pack(data=texture.buffer, data_len=len(texture.buffer))
                texture_image.source = "FILE"
                texture_image.alpha_mode = "CHANNEL_PACKED"
                texture_image.colorspace_settings.name = "Non-Color"
#                if material_instance.alpha_texture_output == 0:
#                    texture_image.colorspace_settings.name = "Non-Color"
            texture_image_node = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture_image_node.image = texture_image
            material.node_tree.links.new(texture_image_node.outputs[material_instance.alpha_texture_output], principled_bsdf.inputs[4])
            
        texture = material_instance.gloss_texture
        if texture is not None:
            if material_instance.gloss_invert:
                invert_node = material.node_tree.nodes.new("ShaderNodeInvert")
                material.node_tree.links.new(invert_node.outputs[0], principled_bsdf.inputs[2])
            
            texture_image = bpy.data.images.get(texture.guid)
            if texture_image is None:
                texture_image = bpy.data.images.new(texture.guid, 1, 1)
                texture_image.pack(data=texture.buffer, data_len=len(texture.buffer))
                texture_image.source = "FILE"
                texture_image.alpha_mode = "CHANNEL_PACKED"
                texture_image.colorspace_settings.name = "Non-Color"
            texture_image_node = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture_image_node.image = texture_image
            if material_instance.gloss_invert:
                material.node_tree.links.new(texture_image_node.outputs[material_instance.gloss_texture_output], invert_node.inputs[1])
            else:
                material.node_tree.links.new(texture_image_node.outputs[material_instance.gloss_texture_output], principled_bsdf.inputs[2])
            
            uv_mul_node = material.node_tree.nodes.new("ShaderNodeVectorMath")
            uv_mul_node.operation = "MULTIPLY"
            uv_mul_node.inputs[1].default_value = (material_instance.gloss_texture_tiling[0], material_instance.gloss_texture_tiling[1], 1)
            material.node_tree.links.new(uv_mul_node.outputs[0], texture_image_node.inputs[0])
            
            uv_map_node = material.node_tree.nodes.new("ShaderNodeUVMap")
            uv_map_node.uv_map = material_instance.gloss_texture_texcoord
            material.node_tree.links.new(uv_map_node.outputs[0], uv_mul_node.inputs[0])
        elif material_instance.gloss_value is not None:
            value_node = material.node_tree.nodes.new("ShaderNodeValue")
            value_node.outputs[0].default_value = material_instance.gloss_value
            material.node_tree.links.new(value_node.outputs[0], principled_bsdf.inputs[2])
            
        texture = material_instance.normal_texture
        if texture is not None:
            normal_map_node = material.node_tree.nodes.new("ShaderNodeNormalMap")
            normal_map_node.uv_map = material_instance.normal_texture_texcoord
            material.node_tree.links.new(normal_map_node.outputs[0], principled_bsdf.inputs[5])
            
            texture_image = bpy.data.images.get(texture.guid)
            if texture_image is None:
                texture_image = bpy.data.images.new(texture.guid, 1, 1)
                texture_image.pack(data=texture.buffer, data_len=len(texture.buffer))
                texture_image.source = "FILE"
                texture_image.alpha_mode = "CHANNEL_PACKED"
                texture_image.colorspace_settings.name = "Non-Color"
            texture_image_node = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture_image_node.image = texture_image
            material.node_tree.links.new(texture_image_node.outputs[0], normal_map_node.inputs[1])
            
            uv_mul_node = material.node_tree.nodes.new("ShaderNodeVectorMath")
            uv_mul_node.operation = "MULTIPLY"
            uv_mul_node.inputs[1].default_value = (material_instance.normal_texture_tiling[0], material_instance.normal_texture_tiling[1], 1)
            material.node_tree.links.new(uv_mul_node.outputs[0], texture_image_node.inputs[0])
            
            uv_map_node = material.node_tree.nodes.new("ShaderNodeUVMap")
            uv_map_node.uv_map = material_instance.normal_texture_texcoord
            material.node_tree.links.new(uv_map_node.outputs[0], uv_mul_node.inputs[0])
            
        texture = material_instance.lcao_texture
        if texture is not None:
            texture_image = bpy.data.images.get(texture.guid)
            if texture_image is None:
                texture_image = bpy.data.images.new(texture.guid, 1, 1)
                texture_image.pack(data=texture.buffer, data_len=len(texture.buffer))
                texture_image.source = "FILE"
                texture_image.alpha_mode = "CHANNEL_PACKED"
                texture_image.colorspace_settings.name = "Non-Color"
            texture_image_node = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture_image_node.image = texture_image
            material.node_tree.links.new(texture_image_node.outputs[material_instance.lcao_texture_output], diffuse_mul_node.inputs[1])
            
            uv_mul_node = material.node_tree.nodes.new("ShaderNodeVectorMath")
            uv_mul_node.operation = "MULTIPLY"
            uv_mul_node.inputs[1].default_value = (material_instance.lcao_texture_tiling[0], material_instance.lcao_texture_tiling[1], 1)
            material.node_tree.links.new(uv_mul_node.outputs[0], texture_image_node.inputs[0])
            
            uv_map_node = material.node_tree.nodes.new("ShaderNodeUVMap")
            uv_map_node.uv_map = material_instance.lcao_texture_texcoord
            material.node_tree.links.new(uv_map_node.outputs[0], uv_mul_node.inputs[0])
            
        obj.data.materials.append(material)
        
    bpy.context.scene.collection.objects.link(obj)
    
    bm = bmesh.new()
    bm.from_mesh(mesh2)
    uv_layers = [bm.loops.layers.uv.new("TEXCOORD" + str(i)) for i in range(5)]
    for face in bm.faces:
        for loop in face.loops:
            for uv_layer, uv in zip(uv_layers, uvs):
                loop[uv_layer].uv = uv[loop.vert.index + vertex_id_min]
    
    color_layer = bm.verts.layers.color.new("COLOR0")
    for vert in bm.verts:
        vert[color_layer] = colors[vert.index + vertex_id_min]
    
    bm.to_mesh(mesh2)
    bm.free()
