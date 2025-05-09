import bmesh
import bpy
from collections import defaultdict
from contextlib import closing
import io
import math
import os
import pathlib
import sqlite3
import struct
from uuid import UUID

#game_path = R"D:\games\rips\FH2XO"
#db_path = R"D:\games\rips\FH2XO\media\stripped\gamedbRC.slt"
#media_name = "NIS_SkylineFF_99"
##media_name = "AUD_S4_13" # normals bug
##media_name = "MER_SLR_05"

game_path = R"D:\games\rips\OpusDev" # unzipped
db_path = R"D:\games\rips\OpusDev\media\stripped\gamedbRC.slt" # unencrypted/decrypted
media_name = "KOE_One_15"
#media_name = "MIN_CooperS_65" # test wheels
#media_name = "FOR_FocusRSRX_16" # test materials; rotor has no rotor_center
#media_name = "NIS_Fairlady432Z_69" # multiple CarBodyID
#media_name = "LAM_Countach_88" # rotor has no controlArm bone
#media_name = "AST_Vanquish_13" # same as LAM_Countach_88
#media_name = "MOR_3Wheeler_14" # no rear brakes

#game_path = R"D:\games\rips\FH4"
#db_path = R"D:\home\models\games export\Forza series\extraction tools\filetypes\tfit\decrypted\gamedb.slt\gamedbRC_FH4_v1.477.714.0_decrypted.slt"
#media_name = "KOE_Agera_11"

#game_path = R"D:\games\rips\FH5"
#db_path = R"D:\games\rips\FH5\media\stripped\gamedbRC-decrypted.slt"
#media_name = "KOE_One_15"
##media_name = "HON_CivicTypeR_07" # same as LAM_Countach_88
##media_name = "CHE_CorvetteERay_23" # model attached to missed upgrade
##media_name = "MER_AMGOne_21"
##media_name = "FOR_F150RaptorR_23" # FH5 new 'Modl' blob version
##media_name = "MER_G63AMG6x6_14" # no LM and RM wheels
##media_name = "FOR_FocusRSRX_16"
##media_name = "NAP_Railton_33" # no BrakePart, CarRenderModel11 name "platform", normals look inside

#game_path = R"D:\games\rips\FM"
#db_path = R"D:\games\rips\FH5\media\stripped\gamedbRC-decrypted.slt"
#media_name = "KOE_AgeraRS_17"

# FH3, KOE_One_15, 2188
#game_path = R"D:\games\rips\OpusDev"
#media_name = "KOE_One_15"
#TireModelName = "WET_c" # from List_UpgradeTireCompound
#FrontTireWidthMM = 265 # from Data_Car
#OriginalFrontTireAspect = 35
#OriginalFrontWheelDiameterIN = 19
#FrontWheelDiameterIN = OriginalFrontWheelDiameterIN
#RearTireWidthMM = 345
#OriginalRearTireAspect = 30
#OriginalRearWheelDiameterIN = 20
#RearWheelDiameterIN = OriginalRearWheelDiameterIN
#ModelWheelbase = 2.659872 # from Data_CarBody
#ModelFrontTrackOuter = 1.965
#ModelRearTrackOuter = 2
#BottomCenterWheelbasePosX = 0
#BottomCenterWheelbasePosY = 0
#BottomCenterWheelbasePosZ = 0.040323
#ModelFrontStockRideHeight = 0.085
#ModelRearStockRideHeight = 0.117

car_body_id = None # load wheel positions for the specified CarBodyID
#car_body_id = 343002

requested_level_of_detail = 1 << 0 # LODS, LOD0, LOD1, ...
requested_draw_group = 1 << 0 # Exterior, Cockpit, Shadow, Hood, WindshieldReflection
hide_decal_transparent_pass = False
suspension_only = False
suspension_transform_type = 2 # 0 - skeleton, 1 - carbin, 2 - gamedb
create_spheres = False # depends on suspension_transform_type
use_materials = False
shader_processor = 1 # 0 - none, 1 - per-shader, 2 - universal shader # when use_materials == True
use_db = True
series = 0 # 0 - auto, 1 - Motorsport, 2 - Horizon

# IOSys module
class BinaryStream:
    def __init__(self, buffer: memoryview): # buffer is memoryview
        self._stream = io.BytesIO(buffer)
    
    @staticmethod
    def from_path(path: str):
        f = open(path, "rb", 0)
        s = BinaryStream(memoryview(f.read()))
        f.close()
        return s
    
    def __getitem__(self, key: slice):
        return self._stream.getbuffer()[key] # replace with self.__buffer[key] ?
    
    def tell(self):
        return self._stream.tell()
    
    def seek(self, offset: int, whence: int = 0):
        return self._stream.seek(offset, whence)
    
    def read(self, size: int | None = None):
        return self._stream.read(size)
    
    def read_list(self, _VT): # IOSys::CBinaryStream::Serialize<std::vector<T>> or std::list<T>
        length = self.read_u32() # IOSys::CBinaryStream::Serialize<unsigned long>("count")
        return [_VT() for _ in range(length)]
        # IOSys::CBinaryStream::Serialize<std::vector<ISerializable *>>
        # std_vector = [_VT() for _ in range(length)]
        # for it in std_vector:
        #     it.deserialize(self._stream)
        # return std_vector

    def read_string(self): # IOSys::CBinaryStream::Serialize<std::string>
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
        self.root = path # base
    
    def resolve(self, path):
        if path[:5].lower() == "game:":
            # if path[:16].lower() == R"game:\media\cars":
            #     if path[16:37].lower() == R"\_library\scene\tires":
            #         # path = R"GAME:\Media\Base\Cars" + path[16:]
            #         path = tires_internal_path + path[37:]
            #     else:
            #         # path = R"GAME:\Media\PCFamily\Cars" + path[16:]
            #         path = cars_internal_path + path[16:]
            return self.root + path[5:] # TODO: support directories without media\cars\
        if path.startswith(self.root):
            print("Warning: Path is already resolved.")
        else:
            print('Warning: Internal path doesn\'t start with "GAME:".')
        return path
        # TODO: find "game:" mount point. Example: Game:\Media\cars\_library\materials\exterior_misc\carPaint_livery.materialbin
        # 1. check if right part of current dir is "\Media\cars\_library\materials\exterior_misc" (C:\media\abc\media\test.modelbin -> "game:"="C:\media\abc")
        # 2. if not, test "\Media\cars\_library\materials\exterior_misc"
        # ...
        # 3. if not, test "\Media"
        # 4. assume that "game:"=current dir
        # ignore material if not found, print warning
        # find game: once, then use cached
        # what if game:\media\a.materialbin and c:\media\cars\a.modelbin?

        # if game is not set, try guess by checking requested file existance in each parent folder
        # 1. ..\media\cars\a.materialbin
        # 2. ..\..\media\cars\a.materialbin
        # ...
        # 3. if exists, assign the result to self.game; print "guessed/assumed game location: ..."

        # try to open gamedb from default location (media\stripped\gamedbRC.slt (priority) or media\db\gamedb.slt)
        # print found gamedb in location ...
        # error: the gamedb is encrypted. Try decrypt using ForzaTech-crypto-tool and set gamedb path option
    
    def test(self, path):
        return path.startswith(self.root)

class CollectionWrapper:
    def __init__(self, name: str, postfix: str | None = None, parent = None, visible: bool = True): # parent: LayerCollection | None
        if parent is None:
            # parent = bpy.context.scene.collection
            parent = bpy.context.view_layer.layer_collection
        if postfix is None:
            self.postfix = " - " + name
        else:
            self.postfix = postfix + " " + name
            name += postfix
        self.children = {} # map name -> CollectionWrapper
        collection = bpy.data.collections.new(name)
        parent.collection.children.link(collection)
        for layer_collection in parent.children:
            if layer_collection.collection == collection:
                self.layer_collection = layer_collection
                break
        self.layer_collection.hide_viewport = not visible

    def add(self, obj):
        self.layer_collection.collection.objects.link(obj)

    def open(self, name: str, visible: bool = True):
        if name in self.children:
            return self.children[name]

        child = CollectionWrapper(name, self.postfix, self.layer_collection, visible)
        self.children[name] = child
        return child
    
    def sort(self):
        children = self.layer_collection.collection.children
        sorted_children = sorted(self.children.items(), key = lambda a : a[0].lower())
        for (_, child) in sorted_children:
            child.sort()
            collection = child.layer_collection.collection
            children.unlink(collection)
            children.link(collection)

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
    
    def __str__(self):
        return F"{self.major}.{self.minor}"

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
        if self.version > 0:
            print(F"Warning: Unsupported 'Name' metadata version. Found: {self.version}. Max supported: 0")
        return self.stream.read().decode('utf-8')
    
    def read_s32(self):
        if self.version > 0:
            print(F"Warning: Unsupported 'Id  ' metadata version. Found: {self.version}. Max supported: 0")
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

    def get_tag(self):
        return chr((self.tag >> 24) & 0xFF) + chr((self.tag >> 16) & 0xFF) + chr((self.tag >> 8) & 0xFF) + chr(self.tag & 0xFF)

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
            print(F"Warning: Unsupported Bundle version. Found: {self.version}. Max supported: 1.1")
        if not self.version.is_at_least(1, 0):
            print(F"Warning: Unsupported Bundle version. Found: {self.version}. Min supported: 1.0")
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
        if not blob.version.is_at_most(1, 3):
            print(F"Warning: Unsupported 'Modl' blob version. Found: {blob.version}. Max supported: 1.3")
        if not blob.version.is_at_least(1, 0):
            print(F"Warning: Unsupported 'Modl' blob version. Found: {blob.version}. Min supported: 1.0")

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
    
    def deserialize(self, blob: Blob):
        if not blob.version.is_at_most(1, 1):
            print(F"Warning: Unsupported '{blob.get_tag()}' blob version. Found: {blob.version}. Max supported: 1.1")
        if not blob.version.is_at_least(1, 0):
            print(F"Warning: Unsupported '{blob.get_tag()}' blob version. Found: {blob.version}. Min supported: 1.0")

        self.element_names_length = blob.stream.read_u16()
        self.element_names = [None] * self.element_names_length
        for i in range(self.element_names_length):
            self.element_names[i] = blob.stream.read_string()
        self.elements_length = blob.stream.read_u16()
        # self.elements = [D3D12_INPUT_ELEMENT_DESC()] * self.elements_length # std::vector<D3D12_INPUT_ELEMENT_DESC>
        for i in range(self.elements_length):
            # self.elements[i].semantic_name = self.element_names[stream.read_u16()]
            self.semantic_name = self.element_names[blob.stream.read_u16()]
            self.semantic_index = blob.stream.read_u16()
            element = self.elements[self.semantic_name + str(self.semantic_index)] # TEXCOORD0, TEXCOORD1, ...
            element.input_slot = blob.stream.read_u16()
            blob.stream.seek(2, os.SEEK_CUR)
            element.format = blob.stream.read_u32()
            blob.stream.seek(4 * 2, os.SEEK_CUR)
        # blob.stream.seek(4 * self.elements_length, os.SEEK_CUR) # PackedFormats
        # if blob.version.is_at_least(1, 1):
        #     self.semantics = blob.stream.read_u32()

class ModelBuffer: # CommonModel::ModelBuffer
    def __init__(self):
        self.length = 0
        self.size = 0
        self.stride = 0
        # self.elements_length = 0
        self.format = 0
    
    def deserialize(self, blob: Blob):
        if not blob.version.is_at_most(1, 0):
            print(F"Warning: Unsupported '{blob.get_tag()}' blob version. Found: {blob.version}. Max supported: 1.0")

        self.length = blob.stream.read_u32()
        self.size = blob.stream.read_u32()
        self.stride = blob.stream.read_u16()
        blob.stream.seek(1 + 1, os.SEEK_CUR)
        if blob.version.is_at_least(1, 0):
            self.format = blob.stream.read_u32()
            self.stream = blob.stream[0x10 : 0x10 + self.size]
        else:
            # self.format = 0
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
        if not blob.version.is_at_most(1, 9):
            print(F"Warning: Unsupported 'Mesh' blob version. Found: {blob.version}. Max supported: 1.9")
        if not blob.version.is_at_least(1, 0):
            print(F"Warning: Unsupported 'Mesh' blob version. Found: {blob.version}. Min supported: 1.0")

        self.name = blob.metadata[Tag.Name].read_string()

        self.material_id = blob.stream.read_s16()
        if blob.version.is_at_least(1, 9):
            self.material_id = blob.stream.read_s16()
            blob.stream.seek(2 * 2, os.SEEK_CUR)
        self.bone_index = blob.stream.read_s16()
        self.levels_of_detail = blob.stream.read_u16()
        blob.stream.seek(2, os.SEEK_CUR)
        self.render_pass = blob.stream.read_u16()
        # if not blob.version.is_at_least(1, 7):
        #     self.render_pass |= 0x18
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
        s = BinaryStream.from_path(self.path)

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
        if not version.is_at_most(3, 1):
            print(F"Warning: Unsupported ShaderParameter version. Found: {version}. Max supported: 3.1")
        if not version.is_at_least(2, 0):
            print(F"Warning: Unsupported ShaderParameter version. Found: {version}. Min supported: 2.0")
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
            case 0 | 5 | 9: # Vector_ShaderParameter, Swizzle_ShaderParameter, FunctionRange_ShaderParameter; Float4
                stream.seek(16, os.SEEK_CUR)
            case 1: # Color_ShaderParameter; Float4
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
        if not parameters_blob.version.is_at_most(2, 1):
            print(F"Warning: Unsupported 'DFPR' blob version. Found: {parameters_blob.version}. Max supported: 2.1")
        if not parameters_blob.version.is_at_least(2, 0):
            print(F"Warning: Unsupported 'DFPR' blob version. Found: {parameters_blob.version}. Min supported: 2.0")
        if parameters_blob.version.is_at_least(2, 1):
            parameters_length = parameters_blob.stream.read_u16()
        else:
            parameters_length = parameters_blob.stream.read_u8()
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
    bones: list[Bone]

    def __init__(self):
        # store id->transform
        self.bones_length = 0
    
    def deserialize(self, blob: Blob):
        if not blob.version.is_at_most(1, 0):
            print(F"Warning: Unsupported 'Skel' blob version. Found: {blob.version}. Max supported: 1.0")

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

class VertexLayout_Element:
    def __init__(self):
        self.stream = None
        self.advance = 0 # next, after read data from stream
        self.format = -1

class Modelbin: # CommonModel::ModelInstance?
    def __init__(self): # TODO: multiple constructors: common, wheel, rim?
        self.weights = None
        self.scale_x = 1
        self.transform = [[1 if i == j else 0 for i in range(4)] for j in range(4)]
    
    def set_weights(self, weights, scale_x):
        self.weights = weights
        self.scale_x = scale_x

    def set_transform(self, transform):
        self.transform = transform

    def deserialize(self, stream: BinaryStream):
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
        self.skeleton = Skeleton()
        self.skeleton.deserialize(skeleton_blob)

        vertex_layout_blobs = bundle.blobs[Tag.VLay]
        vertex_layout_blobs_length = len(vertex_layout_blobs) # TODO: group (length + array of type) into std::vector(list: []) deserializer. auto-call it.deserialize()
        if vertex_layout_blobs_length != model.vertex_layouts_length:
            print(F"Warning: Read unexpected number of 'VLay' entries. Read [{vertex_layout_blobs_length}]. Expected [{model.vertex_layouts_length}].")
        self.vertex_layouts = [VertexLayout() for _ in range(vertex_layout_blobs_length)]
        for vertex_layout, vertex_layout_blob in zip(self.vertex_layouts, vertex_layout_blobs):
            vertex_layout.deserialize(vertex_layout_blob)

        index_buffer_blobs = bundle.blobs[Tag.IndB]
        index_buffer_blobs_length = len(index_buffer_blobs)
        if index_buffer_blobs_length != 1:
            print("Warning: Read unexpected number of 'IndB' entries. Expected [1].")
        self.index_buffer = ModelBuffer()
        if index_buffer_blobs_length > 0:
            self.index_buffer.deserialize(index_buffer_blobs[0])

        vertex_buffer_blobs = bundle.blobs[Tag.VerB] # TODO: process buffers in batch, then just access required verts?
        self.vertex_buffers = [ModelBuffer() for _ in range(len(vertex_buffer_blobs))]
        for vertex_buffer_blob in vertex_buffer_blobs:
            self.vertex_buffers[vertex_buffer_blob.metadata[Tag.Id].read_s32() + 1].deserialize(vertex_buffer_blob)

        morph_data_buffer_blobs = bundle.blobs[Tag.MBuf]
        self.morph_data_buffers = defaultdict(ModelBuffer)
        for morph_data_buffer_blob in morph_data_buffer_blobs:
            self.morph_data_buffers[morph_data_buffer_blob.metadata[Tag.Id].read_s32()].deserialize(morph_data_buffer_blob)

        mesh_blobs = bundle.blobs[Tag.Mesh]
        mesh_blobs_length = len(mesh_blobs)
        if mesh_blobs_length != model.meshes_length:
            print(F"Warning: Read unexpected number of 'Mesh' entries. Read [{mesh_blobs_length}]. Expected [{model.meshes_length}].")
        self.meshes = [Mesh() for _ in range(mesh_blobs_length)]
        for mesh, mesh_blob in zip(self.meshes, mesh_blobs):
            mesh.deserialize(mesh_blob)

        material_blobs = bundle.blobs[Tag.MatI]
        material_blobs_length = len(material_blobs)
        if material_blobs_length != model.materials_length:
            print(F"Warning: Read unexpected number of 'MatI' entries. Read [{material_blobs_length}]. Expected [{model.materials_length}].")
        self.materials = [MaterialInstance() for _ in range(material_blobs_length)]
        for material_blob in material_blobs:
            self.materials[material_blob.metadata[Tag.Id].read_s32()].deserialize(material_blob)

    def process_mesh(self, mesh: Mesh):
        self.draw_indices = [None] * self.index_buffer.length
        self.verts = [(0, 0, 0)] * self.vertex_buffers[0].length # assumption that VerB[-1] contains all possible vertices
        self.norms = [(0, 0, 0)] * self.vertex_buffers[0].length
        self.uvs = [[(0, 0)] * self.vertex_buffers[0].length for _ in range(5)]
        self.colors = [(1, 1, 1, 1)] * self.vertex_buffers[0].length

        vertex_id_min = 0xFFFFFFFF
        vertex_id_max = 0
        stream = BinaryStream(self.index_buffer.stream[mesh.start_index_location * self.index_buffer.stride : (mesh.start_index_location + mesh.index_count) * self.index_buffer.stride]) # mesh.index_buffer_id
        for i in range(mesh.index_count):
            if self.index_buffer.stride == 4:
                vertex_id = stream.read_u32()
            else:
                vertex_id = stream.read_u16()
            if vertex_id_max < vertex_id:
                vertex_id_max = vertex_id
            if vertex_id_min > vertex_id:
                vertex_id_min = vertex_id
            self.draw_indices[i] = vertex_id
        
        faces = []
        for i in range(mesh.index_count // 3): # reshape
            j = i * 3
            faces.append((self.draw_indices[j] - vertex_id_min, self.draw_indices[j + 2] - vertex_id_min, self.draw_indices[j + 1] - vertex_id_min)) # (A, B, C)->(A, C, B); Left-handed -> Right-handed coordinate system

        vertex_buffer_offsets = [0 for _ in range(mesh.vertex_buffer_indices_length)]
        
        elements = defaultdict(VertexLayout_Element)
        for semantic_name, vertex_layout_element_desc in self.vertex_layouts[mesh.vertex_layout_id].elements.items():
            vertex_buffer_index = mesh.vertex_buffer_indices[vertex_layout_element_desc.input_slot]
            vertex_buffer = self.vertex_buffers[vertex_buffer_index.id + 1]
            
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
        if mesh.morph_weights_count > 0 and self.weights:
            morph_data_buffer = self.morph_data_buffers[mesh.morph_data_buffer_id]
            morph_data.stream = BinaryStream(morph_data_buffer.stream[(vertex_id_min + mesh.base_vertex_location) * morph_data_buffer.stride : (vertex_id_max + mesh.base_vertex_location + 1) * morph_data_buffer.stride])
            morph_data.format = morph_data_buffer.format
            morph_data.advance = morph_data_buffer.stride
            if morph_data.format == 10: # DXGI_FORMAT_R16G16B16A16_FLOAT
                morph_data.advance -= 4
            else:
                print("Error: Unexpected morph data format.")

        n = [1, 0, 0] # length must be 1 for division during normalization
        color_warning_printed = False
        for vertex_id in range(vertex_id_min, vertex_id_max + 1): # TODO: split loop on small wrapped with if-statement
            for texcoord, uv, uv_transform in zip(texcoords, self.uvs, mesh.uv_transforms):
                if texcoord.format == 35:
                    t = [texcoord.stream.read_un16(), texcoord.stream.read_un16()]
                    t[0] = t[0] * uv_transform[0][1] + uv_transform[0][0]
                    t[1] = t[1] * uv_transform[1][1] + uv_transform[1][0]
                    uv[vertex_id] = ((t[0], 1 - t[1]))
                    texcoord.stream.seek(texcoord.advance, os.SEEK_CUR)

            if color0.format != -1:
                self.colors[vertex_id] = (color0.stream.read_un8(), color0.stream.read_un8(), color0.stream.read_un8(), color0.stream.read_un8())
                c = self.colors[vertex_id]
                # if not color_warning_printed and c[2] != 0 and (c[0] != c[1] or c[1] != c[2] or c[3] != 1): # don't allow gray; !(R==G && G==B && A==1)
                if not color_warning_printed and c[2] != 0 and (c[0] != 1 or c[1] != 1 or c[2] != 1 or c[3] != 1): # don't allow white; !(R==1 && G==1 && B==1 && A==1)
                    # print("Warning: Color.B != 0.")
                    color_warning_printed = True
                # if c[2] != 0 and (c[0] != 1 or c[1] != 1 or c[2] != 1 or c[3] != 1):
                #     self.colors[vertex_id] = (1, 1, 1, 1)
                #     color_warning_printed = True
                # else:
                #     self.colors[vertex_id] = (0, 0, 0, 1)
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
                    weight = self.weights[int(morph_data.stream.read_f16())]
                    v[0] += m[0] * weight # TODO: replace with mathutils.Vector
                    v[1] += m[1] * weight
                    v[2] += m[2] * weight
                for i in range(mesh.morph_weights_count):
                    m = (morph_data.stream.read_f16(), morph_data.stream.read_f16(), morph_data.stream.read_f16())
                    weight = self.weights[int(morph_data.stream.read_f16())]
                    n[0] += m[0] * weight
                    n[1] += m[1] * weight
                    n[2] += m[2] * weight
                
                # norm; TODO: replace with mathutils.Vector.normalize()
                n_length = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
                n[0] /= n_length
                n[1] /= n_length
                n[2] /= n_length
                
                v[0] *= self.scale_x # TODO: bake scale_x to local transform
                n[0] /= self.scale_x # n * transpose(invert(scale_x))
            
            # TODO: don't bake local transform to vertex position; apply local transform using Blender (matrix_world, not rotation_euler)
            v3 = [0, 0, 0]
            n3 = [0, 0, 0]
            for j in range(3):
                for k in range(4):
                    if k == 3:
                        v3[j] += self.transform[k][j]
                    else:
                        v3[j] += v[k] * self.transform[k][j]
                        n3[j] += n[k] * self.transform[k][j]
            # TODO: don't bake bone transform; apply bone transform to bones only
            v2 = [0, 0, 0]
            n2 = [0, 0, 0]
            for j in range(3):
                for k in range(4):
                    if k == 3:
                        v2[j] += self.skeleton.bones[mesh.bone_index].transform[k][j]
                    else:
                        v2[j] += v3[k] * self.skeleton.bones[mesh.bone_index].transform[k][j]
                        n2[j] += n3[k] * self.skeleton.bones[mesh.bone_index].transform[k][j]

            # norm; located at the beginning of the pixel shader; TODO: replace with mathutils.Vector.normalize()
            n_length = math.sqrt(n2[0] * n2[0] + n2[1] * n2[1] + n2[2] * n2[2])
            n2[0] /= n_length
            n2[1] /= n_length
            n2[2] /= n_length

            self.verts[vertex_id] = (-v2[0], -v2[2], v2[1]) # Y-up, Left-handed -> Z-up, Right-handed
            # self.verts[vertex_id] = (-v[0], -v[2], v[1])
            self.norms[vertex_id] = (-n2[0], -n2[2], n2[1])
            # self.norms[vertex_id] = (-n[0], -n[2], n[1])

        verts2 = self.verts[vertex_id_min : vertex_id_max + 1] # bad, memory copying
        if normal0.format in [10, 37]:
            norms2 = self.norms[vertex_id_min : vertex_id_max + 1]
        else:
            norms2 = None

        name = mesh.name
        #if mesh.render_pass >> 6 != 0:
        #    name += str(mesh.render_pass >> 6)
        #name += F"({(mesh.render_pass >> 5) & 1}{(mesh.render_pass >> 4) & 1}{(mesh.render_pass >> 3) & 1}{(mesh.render_pass >> 2) & 1}{(mesh.render_pass >> 1) & 1}{mesh.render_pass & 1})"
        if mesh.material_id < 0:
            print(F"Warning: Mesh {mesh.name} material id {mesh.material_id} is not valid.")
        else:
            name += " " + self.materials[mesh.material_id].name
        # if "COLOR0" not in self.vertex_layouts[mesh.vertex_layout_id].elements:
        #     name += " [no color]"
        #     # print(F'Mesh "{name}" has no COLOR0')
        
        return name, faces, verts2, norms2, vertex_id_min, color_warning_printed

# carbin
class AOMapInfo: # CarScene::ICarRenderModel::AOMapInfo
    def __init__(self):
        self.version = 0

    def deserialize(self, stream: BinaryStream):
        self.version = stream.read_u16()
        if self.version > 3:
            print(F"Warning: Unsupported AOMapInfo version. Found: {self.version}. Max supported: 3")
        if self.version < 1:
            print(F"Warning: Unsupported AOMapInfo version. Found: {self.version}. Min supported: 1")
        stream.read_string()
        stream.seek(4 * 2, os.SEEK_CUR)
        if self.version >= 2:
            stream.seek(16, os.SEEK_CUR)
        else:
            stream.seek(2 + 1, os.SEEK_CUR)
        stream.seek(1, os.SEEK_CUR)
        if self.version >= 3:
            stream.seek(1 * 2, os.SEEK_CUR)

class CarRenderModel11:
    def __init__(self):
        self.version = 0
        self.modelbin = None

    def deserialize(self, stream: BinaryStream):
        global series, series_is_weak
        self.version = stream.read_u16()
        if series == 0 or series_is_weak:
            known = False
            if self.version == 18:
                series = 2
                if scene.version == 6:
                    known = True
            elif self.version in [15, 16]:
                series = 2
                if scene.version == 5:
                    known = True
            else:
                series = 1
                if self.version == 21:
                    if scene.version in [10, 11]:
                        known = True
                elif self.version in [14, 17] and scene.version == 5:
                    known = True
            if not known:
                print(F"Warning: Unknown CarScene (v{scene.version}) and CarRenderModel11 (v{self.version}) version combination.")
            if series == 2:
                print("Assumed game series: Forza Horizon")
            else:
                print("Assumed game series: Forza Motorsport")
            series_is_weak = False
        max_version = 18 if series == 2 else 21
        if self.version > max_version:
            print(F"Warning: Unsupported CarRenderModel11 version. Found: {self.version}. Max supported: {max_version}")
        if self.version < 1:
            print(F"Warning: Unsupported CarRenderModel11 version. Found: {self.version}. Min supported: 1")
        self.path = stream.read_string()
        self.transform = [[stream.read_f32() for _ in range(4)] for _ in range(4)]
        if self.version > 5:
            self.levels_of_detail = stream.read_u16()
        else:
            self.levels_of_detail = stream.read_u32()
        self.bone_name = stream.read_string()
        self.bone_index = stream.read_u16()
        stream.seek(1, os.SEEK_CUR)
        self.draw_groups = stream.read_s32()
        if self.version < 9:
            stream.read_string()
        if self.version >= 2:
            material_overrides_length = stream.read_u32()
            for _ in range(material_overrides_length):
                stream.read_string()
                stream.seek(stream.read_u32(), os.SEEK_CUR) # Bundle
        if self.version >= 3:
            material_indices_length = stream.read_u32()
            for _ in range(material_indices_length):
                stream.read_string()
                if series == 1 and self.version >= 21:
                    stream.seek(8, os.SEEK_CUR)
                else:
                    stream.seek(4, os.SEEK_CUR)
        if self.version >= 6:
            if stream.read_u8():
                stream.seek(4 + 4, os.SEEK_CUR)
        if self.version >= 8:
            stream.seek(4, os.SEEK_CUR)
        if self.version >= 9:
            ao_maps_info_length = stream.read_u32()
            for _ in range(ao_maps_info_length):
                AOMapInfo().deserialize(stream)
        if self.version >= 10:
            stream.seek(1, os.SEEK_CUR)
        if self.version >= 11:
            stream.seek(1 * 2 + 4 * 4, os.SEEK_CUR)
        if self.version >= 12:
            self.type = self.fix_type_case(stream.read_string())
        if self.version >= 13:
            stream.seek(16, os.SEEK_CUR)
        if self.version >= 14:
            stream.seek(16 + 4, os.SEEK_CUR)
        if series == 2 and self.version >= 15:
            stream.seek(4, os.SEEK_CUR)
        if series == 1 and self.version >= 15 or series == 2 and self.version >= 16:
            stream.seek(16 * stream.read_u32(), os.SEEK_CUR)
        if series == 1:
            if self.version >= 16:
                stream.seek(4, os.SEEK_CUR)
            if self.version >= 17:
                stream.seek(1, os.SEEK_CUR)
            if self.version >= 18:
                stream.read_string()
            if self.version >= 19:
                stream.read_string()
            if self.version >= 20:
                stream.seek(1 + 4 * 2 + 1 * 2, os.SEEK_CUR)
        elif series == 2:
            if self.version >= 17:
                stream.seek(1, os.SEEK_CUR)
            if self.version >= 18:
                stream.seek(4, os.SEEK_CUR)
    
    def fix_type_case(self, name):
        match name:
            case "bumperr":
                return "BumperR"
            case "centerconsole":
                return "CenterConsole"
            case "centerstack":
                return "CenterStack"
            case "chassis":
                return "Chassis"
            case "dash":
                return "Dash"
            case "details":
                return "Details"
            case "doors":
                return "Doors"
            case "floor":
                return "Floor"
            case "interiorlod":
                return "InteriorLOD"
            case "interiorwindows":
                return "InteriorWindows"
            case "pillar":
                return "Pillar"
            case "plate" | "plates":
                return name # actual value
            case "platform":
                return "Platform"
            case "primarylights":
                return "PrimaryLights"
            case "secondarylights":
                return "SecondaryLights"
            case "windows":
                return "Windows"
        if not any(c.isupper() for c in name):
            print(F'Warning: Unknown lowercase CarRenderModel11 type name "{name}".')
        return name

class IPart:
    @staticmethod
    def type_v1_to_latest(type):
        if type >= 42:
            type += 1
        return type
    
    # def get_type_name(self):
    #     match self.type:
    #         case 0:
    #             return "Engine"
    #         case 1:
    #             return "Drivetrain"
    #         case 2:
    #             return "CarBody"
    #         case 3:
    #             return "Motor"
    #         case 9:
    #             return "RearWing"
    #         case 12:
    #             return "Camshaft"
    #         case 13:
    #             return "Valves"
    #         case 14:
    #             return "Displacement"
    #         case 15:
    #             return "PistonsCompression"
    #         case 16:
    #             return "FuelSystem"
    #         case 17:
    #             return "Ignition"
    #         case 18:
    #             return "Exhaust"
    #         case 19:
    #             return "Intake"
    #         case 20:
    #             return "Flywheel"
    #         case 21:
    #             return "Manifold"
    #         case 22:
    #             return "RestrictorPlate"
    #         case 23:
    #             return "OilCooling"
    #         case 24:
    #             return "SingleTurbo"
    #         case 25:
    #             return "TwinTurbo"
    #         case 26:
    #             return "QuadTurbo"
    #         case 27:
    #             return "SuperchargerCSC"
    #         case 28:
    #             return "SuperchargerDSC"
    #         case 29:
    #             return "Intercooler"
    #         case 30:
    #             return "Clutch"
    #         case 31:
    #             return "Transmission"
    #         case 32:
    #             return "Driveline"
    #         case 33:
    #             return "Differential"
    #         case 34:
    #             return "FrontBumper"
    #         case 35:
    #             return "RearBumper"
    #         case 36:
    #             return "Hood"
    #         case 42:
    #             return "MotorParts"
    #         case 44:
    #             return "Aspiration"
        
    #     if self.type <= 44:
    #         return "WheelStyle"
        
    #     return None

    def get_type_name(self):
        match self.type:
            case 0:
                return "Engine"
            case 1:
                return "Drivetrain"
            case 2:
                return "CarBody"
            case 3:
                return "Motor"
            case 4:
                return "Brakes"
            case 5:
                return "SpringDamper"
            case 6:
                return "AntiSwayFront"
            case 7:
                return "AntiSwayRear"
            case 8:
                return "TireCompound"
            case 9:
                return "RearWing"
            case 10:
                return "RimSizeFront"
            case 11:
                return "RimSizeRear"
            case 12:
                return "Camshaft"
            case 13:
                return "Valves"
            case 14:
                return "Displacement"
            case 15:
                return "PistonsCompression"
            case 16:
                return "FuelSystem"
            case 17:
                return "Ignition"
            case 18:
                return "Exhaust"
            case 19:
                return "Intake"
            case 20:
                return "Flywheel"
            case 21:
                return "Manifold"
            case 22:
                return "RestrictorPlate"
            case 23:
                return "OilCooling"
            case 24:
                return "SingleTurbo"
            case 25:
                return "TwinTurbo"
            case 26:
                return "QuadTurbo"
            case 27:
                return "SuperchargerCSC"
            case 28:
                return "SuperchargerDSC"
            case 29:
                return "Intercooler"
            case 30:
                return "Clutch"
            case 31:
                return "Transmission"
            case 32:
                return "Driveline"
            case 33:
                return "Differential"
            case 34:
                return "FrontBumper"
            case 35:
                return "RearBumper"
            case 36:
                return "Hood"
            case 37:
                return "SideSkirts"
            case 38:
                return "TireWidthFront"
            case 39:
                return "TireWidthRear"
            case 40:
                return "WeightReduction"
            case 41:
                return "ChassisStiffness"
            case 42:
                return "Ballast"
            case 43:
                return "MotorParts"
            case 44:
                return "Wheels" # WheelStyle
            case 45:
                return "Aspiration"
        return None

class Part(IPart):
    def __init__(self):
        self.version = 0

    def deserialize(self, stream: BinaryStream):
        self.version = stream.read_u16()
        max_version = 2 if series == 2 else 3
        if self.version > max_version:
            print(F"Warning: Unsupported CarPart version. Found: {self.version}. Max supported: {max_version}")
        if self.version < 1:
            print(F"Warning: Unsupported CarPart version. Found: {self.version}. Min supported: 1")
        self.type = stream.read_u32()
        if series != 1 or self.version < 3:
            self.type = self.type_v1_to_latest(self.type)
        self.models = stream.read_list(CarRenderModel11)
        for model in self.models:
            model.deserialize(stream)
        if self.version >= 2:
            stream.seek(32, os.SEEK_CUR)

class Upgrade:
    def __init__(self):
        self.version = 0

    def deserialize(self, stream: BinaryStream):
        self.version = stream.read_u16()
        max_version = 3 if series == 2 else 4
        if self.version > max_version:
            print(F"Warning: Unsupported Upgrade version. Found: {self.version}. Max supported: {max_version}")
        if self.version < 1:
            print(F"Warning: Unsupported Upgrade version. Found: {self.version}. Min supported: 1")
        self.level = stream.read_u8() # use as Collection name instead of id?
        self.is_stock = stream.read_u8() # bool
        self.id = stream.read_s32()
        self.car_body_id = stream.read_s32()
        self.parent_is_stock = stream.read_u8() # bool
        if self.version < 3:
            print("Error: Upgrade less than v3 is not supported.")
        if self.version >= 2:
            stream.seek(32, os.SEEK_CUR)

class SharedCarModel:
    def __init__(self):
        self.upgrade_ids = None

    def deserialize(self, stream: BinaryStream):
        self.upgrade_ids = stream.read_list(int)
        for i in range(len(self.upgrade_ids)):
            self.upgrade_ids[i] = stream.read_u32()
        self.model = CarRenderModel11()
        self.model.deserialize(stream)

class UpgradablePart(IPart):
    def __init__(self):
        self.version = 0

    def deserialize(self, stream: BinaryStream):
        self.version = stream.read_u16()
        max_version = 3 if series == 2 else 4
        if self.version > max_version:
            print(F"Warning: Unsupported UpgradablePart version. Found: {self.version}. Max supported: {max_version}")
        if self.version < 1:
            print(F"Warning: Unsupported UpgradablePart version. Found: {self.version}. Min supported: 1")
        self.type = stream.read_u32()
        if series != 1 or self.version < 4:
            self.type = self.type_v1_to_latest(self.type)
        # self.upgrades = stream.read_list(Upgrade)
        # for upgrade in self.upgrades:
        #     upgrade.deserialize(stream)
        upgrades_length = stream.read_u32()
        self.upgrades = {}
        for _ in range(upgrades_length):
            upgrade = Upgrade()
            upgrade.deserialize(stream)
            self.upgrades[upgrade.id] = upgrade
        if self.version >= 3:
            self.models = stream.read_list(SharedCarModel)
            for model in self.models:
                model.deserialize(stream)

class CarScene:
    # if reads Serialize<unsigned long>("count") and loop Serialize<T>(), then this is std::vector; writer: 1424ED6E4
    # no universal reader, because of template Serialize<std::vector<T>>

    parts: list[Part] # actual name: nonUpgradableParts
    part_wheels: Part # Wheels/WheelStyle
    part_brakes: Part = None # Brakes
    part_tires: Part # TireCompound
    upgradable_parts: list[UpgradablePart]

    def __init__(self):
        self.version = 0

    def deserialize(self, stream: BinaryStream):
        global series, series_is_weak
        self.version = stream.read_u16()
        if series == 0 and self.version in [10, 11]:
            series = 1
            series_is_weak = True
        max_version = 6 if series == 2 else 11
        if self.version > max_version:
            print(F"Warning: Unsupported CarScene version. Found: {self.version}. Max supported: {max_version}")
        if self.version < 1:
            print(F"Warning: Unsupported CarScene version. Found: {self.version}. Min supported: 1")
        if self.version >= 3:
            stream.seek(16, os.SEEK_CUR)
        if self.version >= 5:
            stream.seek(1, os.SEEK_CUR)
        self.ordinal = stream.read_u32()
        self.media_name = stream.read_string()
        self.skeleton_path = stream.read_string()
        if self.version >= 2:
            stream.seek(2, os.SEEK_CUR)

        if self.version < 5: # assume that it is .carbin, if the file was successfully parsed up to here
            print("Warning: CarScene v4 or below. Please, create an issue and upload this file.")

        self.parts = stream.read_list(Part)
        for part in self.parts:
            if self.version >= 4:
                type = stream.read_u8() # used to check WheelPart/TirePart/...
                if series != 1 or self.version < 6:
                    type = IPart.type_v1_to_latest(type)
                match type:
                    case 4:
                        self.part_brakes = part
                    case 44:
                        self.part_wheels = part
            part.deserialize(stream)
        
        self.upgradable_parts = stream.read_list(UpgradablePart)
        for upgradable_part in self.upgradable_parts:
            upgradable_part.deserialize(stream)
        # if series == 2 and self.version >= 6:
        #     stream.seek(1, os.SEEK_CUR)

# main
path_resolver = GamePathResolver(game_path)

if use_db:
    try:
        with closing(sqlite3.connect(pathlib.Path(db_path).as_uri() + "?mode=ro", uri=True)) as connection:
            cursor = connection.execute(F"""
            SELECT Data_Car.MediaName,
                Data_Car.Id,
                List_UpgradeCarBody.CarBodyID,
                List_UpgradeTireCompound.TireModelName,
                Data_Car.FrontTireWidthMM,
                Data_Car.FrontTireAspect,
                Data_Car.FrontWheelDiameterIN,
                Data_Car.RearTireWidthMM,
                Data_Car.RearTireAspect,
                Data_Car.RearWheelDiameterIN,
                Data_CarBody.ModelWheelbase,
                Data_CarBody.ModelFrontTrackOuter,
                Data_CarBody.ModelRearTrackOuter,
                Data_CarBody.ModelFrontStockRideHeight,
                Data_CarBody.ModelRearStockRideHeight,
                Data_CarBody.BottomCenterWheelbasePosx,
                Data_CarBody.BottomCenterWheelbasePosy,
                Data_CarBody.BottomCenterWheelbasePosZ
            FROM Data_Car
                INNER JOIN List_UpgradeTireCompound ON List_UpgradeTireCompound.Ordinal = Data_Car.Id
                INNER JOIN List_UpgradeCarBody ON List_UpgradeCarBody.Ordinal = Data_Car.Id
                INNER JOIN Data_CarBody ON Data_CarBody.Id = List_UpgradeCarBody.CarBodyID
            WHERE MediaName LIKE '{media_name}'
                AND List_UpgradeTireCompound.IsStock = 1
            ORDER BY List_UpgradeCarBody.CarBodyID
            """)
            rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        if e.sqlite_errorcode == sqlite3.SQLITE_CANTOPEN:
            e.args = (F'The database file was not found. db_path = "{db_path}"',)
            #raise RuntimeError(F'The database file was not found. db_path = "{db_path}"') from e
        elif e.sqlite_errorcode == sqlite3.SQLITE_CANTOPEN_ISDIR:
            e.args = (F'db_path is a folder, but a file was expected. db_path = "{db_path}"',) # "The database must be a file, but a folder was provided."
        raise
    except sqlite3.DatabaseError as e:
        if e.sqlite_errorcode == sqlite3.SQLITE_NOTADB:
            e.args = (F'The database file is not SQLite3, it\'s probably encrypted. db_path = "{db_path}"',)
        raise

    if not rows:
        raise RuntimeError(F'The database file doesn\'t contain the requested MediaName "{media_name}", it\'s probably outdated. db_path = "{db_path}"')
    
    if car_body_id is None:
        row = rows[0]
    else:
        for row in reversed(rows):
            if row[2] == car_body_id:
                break

    media_name = row[0]
    TireModelName = row[3]
    FrontTireWidthMM = row[4]
    OriginalFrontTireAspect = row[5]
    OriginalFrontWheelDiameterIN = row[6]
    FrontWheelDiameterIN = OriginalFrontWheelDiameterIN
    RearTireWidthMM = row[7]
    OriginalRearTireAspect = row[8]
    OriginalRearWheelDiameterIN = row[9]
    RearWheelDiameterIN = OriginalRearWheelDiameterIN
    ModelWheelbase = row[10]
    ModelFrontTrackOuter = row[11]
    ModelRearTrackOuter = row[12]
    ModelFrontStockRideHeight = row[13]
    ModelRearStockRideHeight = row[14]
    BottomCenterWheelbasePosX = row[15]
    BottomCenterWheelbasePosY = row[16]
    BottomCenterWheelbasePosZ = row[17]
    #DefRideHeight = 0.1616 # unused; from List_UpgradeSpringDamper(FrontSpringDamperPhysicsID, RearSpringDamperPhysicsID) -> List_SpringDamperPhysics

# if cars_internal_path[:5].lower() != "game:":
#     raise RuntimeError(F'The internal path doesn\'t start with "GAME:". cars_internal_path = "{cars_internal_path}"')
# if tires_internal_path[:5].lower() != "game:":
#     raise RuntimeError(F'The internal path doesn\'t start with "GAME:". tires_internal_path = "{tires_internal_path}"')

cars_internal_path = R"GAME:\Media\Cars"
tires_internal_path = R"GAME:\Media\Cars\_library\scene\tires"
#cars_internal_path = R"GAME:\Media\PCFamily\Cars" # FM7+
#tires_internal_path = R"GAME:\Media\Base\Cars\_library\scene\tires"
carbin_internal_path = FR"{cars_internal_path}\{media_name}\{media_name}.carbin"
tire_internal_path = FR"{tires_internal_path}\tire_{TireModelName}\tireL_{TireModelName}.modelbin" # x64dbg: "GAME:\Media\Cars\_library\scene\tires\tire_WET_c\tireL_WET_c.modelbin"
#carbin_internal_path = FR"GAME:\Media\Cars\{media_name}\{media_name}.carbin"
#tire_internal_path = FR"GAME:\Media\Cars\_library\scene\tires\tire_{TireModelName}\tireL_{TireModelName}.modelbin" # x64dbg: "GAME:\Media\Cars\_library\scene\tires\tire_WET_c\tireL_WET_c.modelbin"

carbin_path = path_resolver.resolve(carbin_internal_path)

series_is_weak = False

# if not path_resolver.test(carbin_path):
#     print(F'Error: The file "{carbin_path}" is not inside game folder "{path_resolver.root}"')
s = BinaryStream.from_path(carbin_path)
scene = CarScene()
scene.deserialize(s)

# skeleton
if suspension_transform_type == 0:
    s = BinaryStream.from_path(path_resolver.resolve(scene.skeleton_path))
    skeleton_modelbin = Modelbin()
    skeleton_modelbin.deserialize(s)

    if create_spheres:
        #print("skeleton")
        for bone in skeleton_modelbin.skeleton.bones:
            v = bone.transform[3]
            bpy.ops.mesh.primitive_uv_sphere_add(location=(-v[0], -v[2], v[1]), radius=0.05)
            bpy.context.active_object.name = bone.name
            #print(bone.name, translate)
        #print("carbin")

#
rotate_y_180 = ((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1))
rotate_z_180 = ((-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))

def bone_name_to_wheel_index(bone_name: str):
    if bone_name.endswith("LF"):
        return 0
    if bone_name.endswith("RF"):
        return 1
    if bone_name.endswith("RR"):
        return 2
    if bone_name.endswith("LR"):
        return 3
    if bone_name.endswith("LM"):
        return 4
    if bone_name.endswith("RM"):
        return 5
    print("Error: Unknown wheel bone name.")

def wheel_index_to_name(wheel_index):
    match wheel_index:
        case 0:
            return "LF"
        case 1:
            return "RF"
        case 2:
            return "RR"
        case 3:
            return "LR"
        case 4:
            return "LM" # swap LM and RM?
        case 5:
            return "RM"
    print("Error: Unknown wheel index.")

def wheel_index_is_right(wheel_index):
    return wheel_index in [1, 2, 5] # RF, RR, RM

models = []
for model in scene.part_wheels.models:
    if model.levels_of_detail & requested_level_of_detail:
        models.append(model)
scene.part_wheels.models = models # remove unused wheel models to correctly detect the number of wheels

scene.part_tires = Part()
#scene.part_tires.version = 0
scene.part_tires.type = 8 # TireCompound
scene.part_tires.models = [CarRenderModel11() for _ in range(len(scene.part_wheels.models))]
scene.parts.append(scene.part_tires)
for (model, wheel_model) in zip(scene.part_tires.models, scene.part_wheels.models):
    model.path = tire_internal_path
    model.levels_of_detail = 127
    # model.bone_index = -1
    model.bone_index = wheel_model.bone_index
    model.type = "Tires"
    # model.bone_name = "spindle" + bone_name # actual value is empty
    model.bone_name = wheel_model.bone_name
    model.transform = [[1 if i == j else 0 for i in range(4)] for j in range(4)] # actual value is all zeroes (even diagonal)
    model.draw_groups = 5 # TODO: find actual value

scene.part_tires.tire_models = [None] * 6
scene.part_wheels.wheel_models = [None] * 6
if scene.part_brakes is not None:
    scene.part_brakes.rotor_models = [None] * 6
    scene.part_brakes.caliper_models = [None] * 6
scene.control_arm_models = [None] * 6
for part in [*scene.parts, *scene.upgradable_parts]:
    if suspension_only and part.type != 44 and part.type != 4 and part.type != 2 and part.type != 8: # WheelStyle, Brakes, CarBody, TireCompund
       continue

    for model in part.models:
        if type(model) is SharedCarModel:
            upgrade_ids = part.upgrades.keys() & model.upgrade_ids
            if not upgrade_ids:
                print("Warning: Model is not attached to any upgrade")
                for upgrade_id in model.upgrade_ids:
                    upgrade = Upgrade()
                    upgrade.is_stock = 0
                    upgrade.id = upgrade_id
                    upgrade.car_body_id = -1
                    upgrade.parent_is_stock = 1 # default for CarBodyId = -1
                    part.upgrades[upgrade_id] = upgrade
            elif len(upgrade_ids) != len(model.upgrade_ids):
                model.upgrade_ids = list(upgrade_ids)
            model = model.model
        if suspension_only and part.type == 2 and not model.bone_name.startswith("controlArm"):
            continue
        if model.draw_groups & requested_draw_group == 0:
            continue
        if model.levels_of_detail & requested_level_of_detail == 0:
            continue
        
        p = path_resolver.resolve(model.path)
        print(p)
        s = BinaryStream.from_path(p)
        model.modelbin = Modelbin()
        model.modelbin.deserialize(s)

        if part.type == 44:
            wheel_index = bone_name_to_wheel_index(model.bone_name)
            scene.part_wheels.wheel_models[wheel_index] = model

            is_front = wheel_index < 2
            is_right = wheel_index_is_right(wheel_index)
            if is_front:
                tire_width_mm = FrontTireWidthMM
                original_tire_aspect = OriginalFrontTireAspect
                wheel_diameter_in = FrontWheelDiameterIN
            else:
                tire_width_mm = RearTireWidthMM
                original_tire_aspect = OriginalRearTireAspect
                wheel_diameter_in = RearWheelDiameterIN
            model.modelbin.set_weights(((wheel_diameter_in - 10) / 14, (1 - tire_width_mm / 1000) / 0.9), 1) # rim
            
            if suspension_transform_type == 2:
                if is_front:
                    model_track_outer = ModelFrontTrackOuter
                    model_ride_height = ModelFrontStockRideHeight
                else:
                    model_track_outer = ModelRearTrackOuter
                    model_ride_height = ModelRearStockRideHeight
                half_wheel_outer_diameter_m = (original_tire_aspect * 0.01) * (tire_width_mm * 0.001) + wheel_diameter_in * 0.0254 / 2
                
                model.transform = [[1 if i == j else 0 for i in range(4)] for j in range(4)]
                if is_right:
                    model.transform[0][0] = -model.transform[0][0]
                    model.transform[2][2] = -model.transform[2][2]
                translate = model.transform[3]
                translate[0] = model_track_outer / 2
                translate[1] = half_wheel_outer_diameter_m - model_ride_height # or (min + max) / 2
                translate[2] = ModelWheelbase / 2
                
                if not is_right:
                    translate[0] = -translate[0]
                if not is_front:
                    translate[2] = -translate[2]
                
                translate[0] += BottomCenterWheelbasePosX
                translate[1] += BottomCenterWheelbasePosY
                translate[2] -= BottomCenterWheelbasePosZ
                
                if create_spheres:
                    v = translate
                    bpy.ops.mesh.primitive_uv_sphere_add(location=(-v[0], -v[2], v[1]), radius=0.05)
                    bpy.context.active_object.name = model.bone_name
        elif part.type == 8:
            wheel_index = bone_name_to_wheel_index(model.bone_name)
            scene.part_tires.tire_models[wheel_index] = model

            if wheel_index < 2:
                tire_width_mm = FrontTireWidthMM
                original_tire_aspect = OriginalFrontTireAspect
                original_wheel_diameter_in = OriginalFrontWheelDiameterIN
                wheel_diameter_in = FrontWheelDiameterIN
            else:
                tire_width_mm = RearTireWidthMM
                original_tire_aspect = OriginalRearTireAspect
                original_wheel_diameter_in = OriginalRearWheelDiameterIN
                wheel_diameter_in = RearWheelDiameterIN
            model.modelbin.set_weights(((tire_width_mm * original_tire_aspect / 100 - 225 + original_wheel_diameter_in * 12.7) / 275, (wheel_diameter_in - 10) / 14, 0, 0, 0), tire_width_mm / 1000) # tire, not verified
        elif part.type == 4:
            wheel_index = bone_name_to_wheel_index(model.bone_name)
            if model.bone_name.startswith("spindle"):
                scene.part_brakes.rotor_models[wheel_index] = model
            elif model.bone_name.startswith("hub"):
                scene.part_brakes.caliper_models[wheel_index] = model
            else:
                print("Warning: Unknown BrakePart bone name.")
        elif model.bone_name.startswith("controlArm"):
            wheel_index = bone_name_to_wheel_index(model.bone_name)
            scene.control_arm_models[wheel_index] = model

        if part.type != 8:
            if suspension_transform_type == 0:
                model.modelbin.set_transform(skeleton_modelbin.skeleton.bones[model.bone_index].transform)
            elif suspension_transform_type == 1:
                model.modelbin.set_transform(model.transform)

car_bodies = {} # car_body_id -> parent_is_stock
for upgradable_part in scene.upgradable_parts:
    for upgrade in upgradable_part.upgrades.values():
        if upgrade.car_body_id == -1:
            continue
        if upgrade.car_body_id in car_bodies:
            if car_bodies[upgrade.car_body_id] != upgrade.parent_is_stock:
                print("Warning: CarBody {upgrade.car_body_id} is marked as both stock and non-stock.")
        else:
            car_bodies[upgrade.car_body_id] = upgrade.parent_is_stock

# 14250F5B8 CarScene::BrakePart::InitLocalTransforms
for wheel_index in range(6):
    wheel_model = scene.part_wheels.wheel_models[wheel_index]
    if wheel_model is None:
        continue
    is_right = wheel_index_is_right(wheel_index)
    spindle_offset = None
    for bone in wheel_model.modelbin.skeleton.bones:
        if bone.name == "spindle":
            spindle_offset = bone.transform[3][0]
            break
    control_arm_offset = 0.30480003 # 12 inch (0x3E9C0EC0)
    if scene.part_brakes is not None:
        rotor_model = scene.part_brakes.rotor_models[wheel_index]
    else:
        rotor_model = None
    if rotor_model is not None:
        for bone in rotor_model.modelbin.skeleton.bones: # if no bone, then find in _skeleton.modelbin (non-native not equal to offset from rotor)
            if bone.name == "controlArm":
                control_arm_offset = bone.transform[3][0]
                break
        rotor_center_offset = 0
        caliper_model = scene.part_brakes.caliper_models[wheel_index]
        if caliper_model is not None:
            for bone in rotor_model.modelbin.skeleton.bones: # if no bone, then calculate from carbin matrices?
                #if bone.name.startswith("rotor") and bone.name.endswith("_center"):
                if bone.name == F"rotor{wheel_index_to_name(wheel_index)}_center" or bone.name == "rotor_center" or bone.name == "rotorLF_center": # comparison order is important
                    rotor_center_offset = bone.transform[3][0]
                    break

            # carbin transform may rotate around both Y and Z axis
            # rotor_local_transform = [[1 if i == j else 0 for i in range(4)] for j in range(4)]
            # rotor_local_transform = scene.part_brakes.rotor_local_transform[wheel_index] # unused
            # for j in range(3):
            #     for i in range(3):
            #         rotor_local_transform[j][i] = rotor_model.transform[j][i] # copy rotate component. assume that it doesn't have scale component; may require rotate_y_180 if right
            caliper_local_transform = [[0 for _ in range(4)] for _ in range(4)]
            caliper_local_translate = caliper_local_transform[3]
            caliper_local_translate[0] = rotor_center_offset
            caliper_local_translate[1] = caliper_model.transform[3][1] - rotor_model.transform[3][1]
            caliper_local_translate[2] = caliper_model.transform[3][2] - rotor_model.transform[3][2]
            caliper_local_translate[3] = 1
            if is_right:
                for i in range(3): # rotate Y 180, because hub bone has own rotation around Y-axis
                    for j in range(3):
                        for k in range(3):
                            caliper_local_transform[i][j] += caliper_model.transform[i][k] * rotate_y_180[k][j]
                caliper_local_translate[2] = -caliper_local_translate[2] # rotate Y 180; X coordinate is already rotated
            else:
                for j in range(3):
                    for i in range(3):
                        caliper_local_transform[j][i] = caliper_model.transform[j][i]

    # 142A57058 Presentation11::CarPresentation::SetWheelAndTireTransforms
    if suspension_transform_type == 2:
        # wheel
        spindle_transform = wheel_model.transform
        wheel_model.modelbin.set_transform(spindle_transform)

        translate_x = [[1 if i == j else 0 for i in range(4)] for j in range(4)]
        translate_x[3][0] = spindle_offset

        # brake
        if rotor_model is not None:
            brake_transform = [[0 for _ in range(4)] for _ in range(4)]
            for i in range(4): # translate_x * spindle_transform
                for j in range(4):
                    for k in range(4):
                        brake_transform[i][j] += translate_x[i][k] * spindle_transform[k][j]
            rotor_model.modelbin.set_transform(brake_transform)

            if caliper_model is not None:
                caliper_transform = [[0 for _ in range(4)] for _ in range(4)]
                for i in range(4): # caliper_local_transform * brake_transform - only way, otherwise the caliper will rotating the world
                    for j in range(4):
                        for k in range(4):
                            caliper_transform[i][j] += caliper_local_transform[i][k] * brake_transform[k][j] # assume that hub_transform == spindle_transform (rotate around Y-axis)
                caliper_model.modelbin.set_transform(caliper_transform)

        # control arm
        control_arm_model = scene.control_arm_models[wheel_index]
        if control_arm_model is not None:
            transform = [[0 for _ in range(4)] for _ in range(4)]
            for j in range(4):
                for i in range(4):
                    transform[j][i] = translate_x[j][i]
            transform[3][0] += control_arm_offset
            if is_right:
                transform[3][0] = -transform[3][0]
            for i in range(3):
                transform[3][i] += spindle_transform[3][i]
            control_arm_model.modelbin.set_transform(transform)
    scene.part_tires.tire_models[wheel_index].modelbin.set_transform(wheel_model.modelbin.transform)

blender_version_checked = False
root_collection = None
for part in [*scene.parts, *scene.upgradable_parts]:
    if suspension_only and part.type != 44 and part.type != 4 and part.type != 2 and part.type != 8:
       continue

    part_collection = None
    for model in part.models:
        if type(model) is SharedCarModel:
            upgrade_ids = model.upgrade_ids
            model = model.model
        modelbin = model.modelbin
        if modelbin is None:
            continue

        if suspension_transform_type == 1 and create_spheres:
            v = model.transform[3]
            bpy.ops.mesh.primitive_uv_sphere_add(location=(-v[0], -v[2], v[1]), radius=0.05)
            bpy.context.active_object.name = model.bone_name
            #print(model.bone_name, v)

        for mesh in modelbin.meshes:
            if mesh.levels_of_detail & requested_level_of_detail == 0:
                continue
            if mesh.render_pass & 0x10 == 0: # skip Shadow
                continue
            if hide_decal_transparent_pass and mesh.render_pass & 0x4 != 0: # skip DecalTransparent
                continue
            
            #if not (mesh.render_pass & (1 << 0) != 0 and mesh.render_pass & (1 << 4) != 0): # A|C
            #if not (not (mesh.render_pass & (1 << 2) != 0) and mesh.render_pass & (1 << 5) != 0): # D
            #if not (mesh.render_pass & (1 << 2) != 0 and not (mesh.render_pass & (1 << 5) != 0)): # E
            #if not (mesh.render_pass & (1 << 2) != 0 and mesh.render_pass & (1 << 5) != 0): # F
            #    continue

            # if part.type == 44 and modelbin.materials[mesh.material_id].name in ["blur_lip", "blur_rim"]: # TODO: replace by shader name at least; find the actual way to hide
            #     continue
            if part.type == 44 and mesh.render_pass & 0x4 != 0:
                continue

            name, faces, verts2, norms2, vertex_id_min, color_warning_printed = modelbin.process_mesh(mesh)
            # if not color_warning_printed:
            #     continue
            # paste below
            if not blender_version_checked:
                blender_version_checked = True
                if bpy.app.version < (4, 2, 0):
                    raise RuntimeError(F"Blender version 4.2.x required, but found: {bpy.app.version_string}")
                if bpy.app.version >= (4, 3, 0):
                    print(F"Warning: Blender version 4.2.x required, but found: {bpy.app.version_string}")

            mesh2 = bpy.data.meshes.new(name=name)
            mesh2.from_pydata(verts2, [], faces, False)
            mesh2.validate()
            if norms2 is not None:
                mesh2.normals_split_custom_set_from_vertices(norms2)
            obj = bpy.data.objects.new(name, mesh2)
            
            #mat = bpy.data.materials.get("Material")
            #if mat is None:
            material_instance = modelbin.materials[mesh.material_id]
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

            if root_collection is None:
                name = scene.media_name
                if media_name.lower() == name:
                    name = media_name
                root_collection = CollectionWrapper(name)
            if type(part) is Part:
                for (car_body_id, is_stock) in car_bodies.items() if car_bodies else [(None, None)]:
                    collection = root_collection
                    if car_body_id is not None:
                        collection = collection.open(str(car_body_id), is_stock)
                    collection = collection.open(part.get_type_name())
                    name = model.type
                    if part.type == 4 or part.type == 8 or part.type == 44:# or part.type == 2 and model.type == "ControlArm":
                        name += " " + model.bone_name[-2:]
                    #elif part.type == 2 and model.type == "Doors":
                    #    bone_postfix = modelbin.skeleton.bones[mesh.bone_index].name[-2:]
                    #    if bone_postfix not in ["LF", "RF"]:
                    #        bone_postfix = bone_postfix[1] # get last char
                    #        if bone_postfix == "L":
                    #            bone_postfix = "LF"
                    #        elif bone_postfix == "R":
                    #            bone_postfix = "RF"
                    #    name += " " + bone_postfix
                    collection = collection.open(name, name != "InteriorWindows")
                    collection.add(obj)
            else:
                for upgrade_id in upgrade_ids:
                    if upgrade_id not in part.upgrades:
                        continue
                    upgrade = part.upgrades[upgrade_id] # error: no model.upgrade_id 3771001 in part.upgrades RearBumper, BumperR
                    for (car_body_id, is_stock) in car_bodies.items() if upgrade.car_body_id == -1 else [(upgrade.car_body_id, upgrade.parent_is_stock)]:
                        collection = root_collection.open(str(car_body_id), is_stock)
                        collection = collection.open(part.get_type_name())
                        
                        name = str(upgrade_id)
                        if upgrade.is_stock:
                            name += " [stock]"
                        collection = collection.open(name, upgrade.is_stock)
                        
                        collection = collection.open(model.type, model.type != "InteriorWindows")
                        collection.add(obj)
            
            bm = bmesh.new()
            bm.from_mesh(mesh2)
            uv_layers = [bm.loops.layers.uv.new("TEXCOORD" + str(i)) for i in range(5)]
            for face in bm.faces:
                for loop in face.loops:
                    for uv_layer, uv in zip(uv_layers, modelbin.uvs):
                        loop[uv_layer].uv = uv[loop.vert.index + vertex_id_min]
            
            color_layer = bm.verts.layers.color.new("COLOR0")
            for vert in bm.verts:
                vert[color_layer] = modelbin.colors[vert.index + vertex_id_min]
            
            bm.to_mesh(mesh2)
            bm.free()
root_collection.sort()
