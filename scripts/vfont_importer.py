import math
import os
import struct

import bmesh
import bpy
import mathutils

from file import File

font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_A.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_B.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_C.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_D.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_CHS.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_CHT.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_JP.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_KO.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_RU_A.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_RU_B.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_RU_C.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\Anthem_RU_D.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\DG1_ArialBold.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\DG2_LCD-BOLD.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\DG3_Moire-Bold.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\DG4_PF_Ronda_Seven.vfont"
#font_path = R"D:\games\rips\OpusDev\media\ui\Fonts\DG5_QuartzMS.vfont"

clean = False
is_vector = False # raster / vector

class File(object):
    def __init__(self, path):
        self.__f = open(path, "rb")
    
    def close(self):
        self.__f.close()
    
    def seek(self, offset, whence=0):
        self.__f.seek(offset, whence)
    
    def readS16(self):
        v = self.__f.read(2)
        if not v:
            return None
        return struct.unpack('h', v)[0]
    
    def readU8(self):
        v = self.__f.read(1)
        if not v:
            return None
        return struct.unpack('B', v)[0]
    
    def readU16(self):
        v = self.__f.read(2)
        if not v:
            return None
        return struct.unpack('H', v)[0]
    
    def readS32(self):
        v = self.__f.read(4)
        if not v:
            return None
        return struct.unpack('i', v)[0]
    
    def readU32(self):
        v = self.__f.read(4)
        if not v:
            return None
        return struct.unpack('I', v)[0]
    
    def readF16(self):
        v = self.__f.read(2)
        if not v:
            return None
        return struct.unpack('e', v)[0]
    
    def readF32(self):
        v = self.__f.read(4)
        if not v:
            return None
        return struct.unpack('f', v)[0]
    
    def readS16_NORM(self):
        return self.readS16() / 32767
    
    def readU8_NORM(self):
        return self.readU8() / 255
    
    def readU16_NORM(self):
        return self.readU16() / 65535

is_blender = hasattr(bpy, "data")

if is_blender:
    # clean scene
    if clean:
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj)

    if not is_vector:
        if clean:
            for obj in bpy.data.materials:
                bpy.data.materials.remove(obj)

        # shader
        mat = bpy.data.materials.new("Material")
        mat.use_nodes = True
        mat.surface_render_method = "BLENDED"
        mat.use_transparency_overlap = False

        principled_bsdf = mat.node_tree.nodes.get("Principled BSDF")
#        principled_bsdf.inputs[0].default_value = (0, 0, 0, 1)

        greater_than = mat.node_tree.nodes.new("ShaderNodeMath")
        greater_than.operation = "GREATER_THAN"
        greater_than.inputs[1].default_value = 0
#        mat.node_tree.links.new(greater_than.outputs[0], principled_bsdf.inputs[0]) # color
        mat.node_tree.links.new(greater_than.outputs[0], principled_bsdf.inputs[4]) # alpha

        multiply = mat.node_tree.nodes.new("ShaderNodeMath")
        multiply.operation = "MULTIPLY"
        mat.node_tree.links.new(multiply.outputs[0], greater_than.inputs[0])

        subtract = mat.node_tree.nodes.new("ShaderNodeMath")
        subtract.operation = "SUBTRACT"
        mat.node_tree.links.new(subtract.outputs[0], multiply.inputs[0])

        power = mat.node_tree.nodes.new("ShaderNodeMath")
        power.operation = "POWER"
        power.inputs[1].default_value = 2
        mat.node_tree.links.new(power.outputs[0], subtract.inputs[1])

        separate_0 = mat.node_tree.nodes.new("ShaderNodeSeparateXYZ")
        mat.node_tree.links.new(separate_0.outputs[0], power.inputs[0])
        mat.node_tree.links.new(separate_0.outputs[1], subtract.inputs[0])

        uv_0 = mat.node_tree.nodes.new("ShaderNodeUVMap")
        uv_0.uv_map = "Float2"
        mat.node_tree.links.new(uv_0.outputs[0], separate_0.inputs[0])

        separate_1 = mat.node_tree.nodes.new("ShaderNodeSeparateXYZ")
        mat.node_tree.links.new(separate_1.outputs[0], multiply.inputs[1])

        uv_1 = mat.node_tree.nodes.new("ShaderNodeUVMap")
        uv_1.uv_map = "Float2.001"
        mat.node_tree.links.new(uv_1.outputs[0], separate_1.inputs[0])

# main
f = File(font_path)

f.seek(0x80, os.SEEK_CUR) # name
chars_length = f.readU32()
f.seek(0x8, os.SEEK_CUR)
unk4_length = f.readU32()
f.seek(0x10, os.SEEK_CUR)
win_ascent = f.readS32() # Word height
win_descent = f.readS32()
dwordA8 = f.readS32() # f.seek(0x4, os.SEEK_CUR)
typo_ascent = f.readS32()
typo_descent = f.readS32()
typo_line_gap = f.readS32()
hhead_ascent = f.readS32()
hhead_descent = f.readS32()
hhead_line_gap = f.readS32()
em_size = f.readS32()
capital_height = f.readS32()
#f.seek(0x3C, os.SEEK_CUR)

#
chars_width = [None] * chars_length
for i in range(chars_length):
    f.seek(0x4, os.SEEK_CUR)
    chars_width[i] = f.readF32()
    f.seek(0x14, os.SEEK_CUR)
#f.seek(0x1C * chars_length, os.SEEK_CUR)

f.seek(0xC * unk4_length, os.SEEK_CUR)

y_advance = (win_ascent + win_descent) / em_size
x_offset = 0
y_offset = 0

glyphs_length = f.readS32()
for i in range(glyphs_length):
    character = f.readS32()
    vertexes_length = f.readS32()
    indexes_length = f.readS32()
    verts = [None] * vertexes_length
    uvs = [[None] * vertexes_length for _ in range(2)]
    for j in range(vertexes_length):
        x = f.readF16()
        verts[j] = (abs(x), f.readF16(), 0)
        uvs[0][j] = (f.readF16(), f.readF16())
        uvs[1][j] = ((x > 0) - (x < 0), 0)
    faces_length = indexes_length // 3
    faces = [None] * faces_length
    for j in range(faces_length):
        faces[j] = (abs(f.readU16()), f.readU16(), f.readU16())

    if is_blender:
        if is_vector:
            curve = bpy.data.curves.new("Glyph", type="CURVE")
            for k in range(faces_length):
                f0 = faces[k]
                
                v0 = verts[f0[0]]
                v1 = verts[f0[1]]
                v2 = verts[f0[2]]
                
                # texcoord
                t0 = uvs[0][f0[0]]
                t1 = uvs[0][f0[1]]
                t2 = uvs[0][f0[2]]
                
                if t0[0] == t1[0] and t0[1] == t1[1] and t0[0] == t2[0] and t0[1] == t2[1]:
                    # inner part, don't draw
                    pass
                elif f0[0] == f0[1] or f0[1] == f0[2] or f0[0] == f0[2]:
                    # two point face. Nothing to draw
                    pass
                else:
                    if t0[0] == 0 and t1[0] == 0 and t2[0] == 0:
                        # line, because A=0 at A*x^2=0
                        if (t0[1] < 0) == (t1[1] < 0):
                            t0, t2 = t2, t0
                            v0, v2 = v2, v0
                        if (t0[1] < 0) == (t2[1] < 0):
                            t0, t1 = t1, t0
                            v0, v1 = v1, v0
                        
                        try:
                            a = t1[1] / (t1[1] - t0[1]) # (P - B) / (A - B)
                            p0 = mathutils.Vector((v0[0], v0[1], 0)) * a + mathutils.Vector((v1[0], v1[1], 0)) * (1 - a)
                            a = t2[1] / (t2[1] - t0[1])
                            p1 = mathutils.Vector((v0[0], v0[1], 0)) * a + mathutils.Vector((v2[0], v2[1], 0)) * (1 - a)
                            cp = (p0 + p1) / 2 # linear -> quadratic
                        except Exception as e:
                            print(k, f0)
                            print(t0, t1, t2)
                            raise e
                    else:
                        if (t0[1] < 1) == (t1[1] < 1):
                            t0, t2 = t2, t0
                            v0, v2 = v2, v0
                        if (t0[1] < 1) == (t2[1] < 1):
                            t0, t1 = t1, t0
                            v0, v1 = v1, v0
                        
                        A = mathutils.Matrix(((t0[0], t1[0], t2[0]), (t0[1], t1[1], t2[1]), (1, 1, 1)))
                        B = mathutils.Matrix(((v0[0], v1[0], v2[0]), (v0[1], v1[1], v2[1]), (1, 1, 1)))
                        try:
                            T = B @ A.inverted()
                        except Exception as e:
                            print(k, f0)
                            print(t0, t1, t2)
                            print(A)
                            raise e

                        # begin edge
                        A = mathutils.Vector((t0[0], t0[1], 1))
                        B = mathutils.Vector((t1[0], t1[1], 1))
                        l = A.cross(B) # a*x + b*y + c = 0
                        # x^2 = b*x + c
                        if l[1] == 0:
                            p0_x = -l[2] / l[0]
                            p0_y = p0_x**2
                        else:
                            b = l[0] / l[1]
                            c = l[2] / l[1]
                            delta = math.sqrt(b**2 - 4*c)
                            x0 = (-b - delta) / 2
                            x1 = (-b + delta) / 2
                            p0_x = x0
                            if abs(x0) > abs(x1):
                                p0_x = x1
                            p0_y = p0_x**2
                        
                        # end edge
                        A = mathutils.Vector((t0[0], t0[1], 1))
                        B = mathutils.Vector((t2[0], t2[1], 1))
                        l = A.cross(B)
                        # x^2 = b*x + c
                        if l[1] == 0:
                            p1_x = -l[2] / l[0]
                            p1_y = p1_x**2
                        else:
                            b = l[0] / l[1]
                            c = l[2] / l[1]
                            delta = math.sqrt(b**2 - 4*c)
                            x0 = (-b - delta) / 2
                            x1 = (-b + delta) / 2
                            p1_x = x0
                            if abs(x0) > abs(x1):
                                p1_x = x1
                            p1_y = p1_x**2
                        
                        # control point
                        cp_x = (p0_x + p1_x) / 2
                        cp_y = p0_y + 2 * p0_x * (p1_x - p0_x) / 2
                        
                        A = mathutils.Matrix(((p0_x, p0_y, 1), (p1_x, p1_y, 1), (cp_x, cp_y, 1))).transposed()
                        A = T @ A
                        p0 = mathutils.Vector((A[0][0], A[1][0], 0))
                        p1 = mathutils.Vector((A[0][1], A[1][1], 0))
                        cp = mathutils.Vector((A[0][2], A[1][2], 0))
                    
                    # quadratic -> cubic
                    cp0 = (p0 + 2 * cp) / 3
                    cp1 = (2 * cp + p1) / 3
                    
                    s = curve.splines.new("BEZIER")
                    points = s.bezier_points
                    points.add(1) # curve over 2 points
                    
                    points[0].co = p0
                    points[0].handle_left = p0
                    points[0].handle_right = cp0
                    points[1].co = p1
                    points[1].handle_left = cp1
                    points[1].handle_right = p1
            
            obj = bpy.data.objects.new("Glyph", curve)
        else:
            mesh = bpy.data.meshes.new(name="Glyph")
            mesh.from_pydata(verts, [], faces, False)
            #mesh.validate(verbose=True)
            #mesh.update()
            
            bm = bmesh.new()
            bm.from_mesh(mesh)
            uv_layers = [bm.loops.layers.uv.new() for _ in range(2)]
            for face in bm.faces:
                for loop in face.loops:
                    for uv_layer, uv in zip(uv_layers, uvs):
                        loop[uv_layer].uv = uv[loop.vert.index]
            bm.to_mesh(mesh)
            bm.free()
            
            obj = bpy.data.objects.new("Glyph", mesh)
            obj.data.materials.append(mat)

        obj.location = (x_offset, y_offset, 0)
        bpy.context.scene.collection.objects.link(obj)
    
    if (i + 1) % 10 == 0:
        x_offset = 0
        y_offset -= y_advance
    else:
#        x_offset += chars_width[i]
        x_offset += 1

f.close()
