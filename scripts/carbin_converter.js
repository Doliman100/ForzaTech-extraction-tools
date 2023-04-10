import { readFile, writeFile } from 'fs/promises';
import { basename, dirname, extname, join } from 'path';

// configuration
const path = 'D:\\games\\rips\\FH5\\media\\Cars\\NUL_Car_00\\NUL_Car_00.carbin.bak';

// fuse
if (extname(path) !== '.bak') {
  throw 'Error: Please, rename the original ".carbin" file to ".carbin.bak".';
}

const root = {};

// deserialize
class Reader {
  ptr = 0;
  constructor(buffer) {
    this.buffer = buffer;
  }
  read(size) {
    const value = this.buffer.subarray(this.ptr, this.ptr + size);
    this.ptr += size;
    return value;
  }
  readSequence(element_size) {
    const length = this.buffer.readUInt32LE(this.ptr);
    return this.read(length * element_size + 4);
  }
  readString() {
    return this.readSequence(1);
  }
  readArray(callback) {
    const length = this.read(4);
    const data = new Array(length.readUInt32LE());
    for (let i = 0; i < data.length; i++) {
      callback(data[i] = {});
    }
    return {length, data};
  }
};

const input = await readFile(path);
const reader = new Reader(input);

function readModel(reader, model) {
  model.type = reader.read(2);
  const model_type = model.type.readUInt16LE();
  if (model_type !== 18) {
    if (model_type == 16) {
      throw 'Warning: Deprecated model chunk type detected (16). Make sure the input file is not from Forza Horizon 4. Otherwise, report the issue and provide the path to the file you are trying to convert.'
    }
    throw `Error: Unknown model chunk type: ${model_type}.`;
  }
  model.path = reader.readString();
  model.unknown1 = reader.read(66);
  model.parent_bone_name = reader.readString();
  model.unknown2 = reader.read(7);
  model.materials = reader.readArray((material) => {
    material.name = reader.readString();
    material.data = reader.readString();
  });
  model.textures = reader.readArray((texture) => {
    texture.name = reader.readString();
    texture.unknown1 = reader.read(4);
  });
  model.has_hash = reader.read(1);
  model.unknown3 = reader.read(model.has_hash.readUInt8() ? 8 : 0);
  model.unknown4 = reader.read(10);
  model.swatch_path = reader.readString();
  model.unknown5 = reader.read(46);
  model.part_name = reader.readString();
  model.unknown6 = reader.read(40);
  model.unknown7 = reader.readSequence(16);
  model.unknown8 = reader.read(5);
}

root.type = reader.read(2);
const root_type = root.type.readUInt16LE();
if (root_type != 5 && root_type != 6) {
  throw `Error: Unknown root chunk type: ${model_type}.`;
}
root.unknown1 = reader.read(21);
root.name = reader.readString();
root.path = reader.readString();
root.unknown2 = reader.read(2);
root.block_b = reader.readArray((block_b) => {
  block_b.unknown1 = reader.read(7);
  block_b.models = reader.readArray((model) => {
    readModel(reader, model);
  });
  block_b.unknown2 = reader.read(32);
});
root.block_c = reader.readArray((block_c) => {
  block_c.unknown1 = reader.read(6);
  block_c.unknown_floats = reader.readSequence(45);
  block_c.models = reader.readArray((model) => {
    model.unknown9 = reader.readSequence(4);
    readModel(reader, model);
  });
});
if (root_type == 6) {
  root.unknown3 = reader.read(1);
}

console.log(root);

// serialize
class Writer {
  ptr = 0;
  constructor(buffer) {
    this.buffer = buffer;
  }
  write(buffer) {
    buffer.copy(this.buffer, this.ptr);
    this.ptr += buffer.byteLength;
  }
  writeUInt16(value) {
    this.buffer.writeUInt16LE(value, this.ptr);
    this.ptr += 2;
  }
  writeUInt32(value) {
    this.buffer.writeUInt32LE(value, this.ptr);
    this.ptr += 4;
  }
  writeArray(array, callback) {
    this.write(array.length);
    for (const value of array.data) {
      callback(value);
    }
  }
};

const output = Buffer.alloc(input.byteLength);
const writer = new Writer(output);

function writeModel(writer, model) {
  writer.writeUInt16(16); // model.type
  writer.write(model.path);
  writer.write(model.unknown1);
  writer.write(model.parent_bone_name);
  writer.write(model.unknown2);
  writer.writeArray(model.materials, (material) => {
    writer.write(material.name);
    writer.write(material.data);
  });
  writer.writeArray(model.textures, (texture) => {
    writer.write(texture.name);
    writer.write(texture.unknown1);
  });
  writer.write(model.has_hash);
  writer.write(model.unknown3);
  writer.write(model.unknown4);
  writer.write(model.swatch_path);
  writer.write(model.unknown5);
  writer.write(model.part_name);
  writer.write(model.unknown6);
  writer.write(model.unknown7);
  // writer.write(model.unknown8); // for type 18 (not used)
}

writer.writeUInt16(5); // root.type
writer.write(root.unknown1);
writer.write(root.name);
writer.write(root.path);
writer.write(root.unknown2);
writer.writeArray(root.block_b, (block_b) => {
  writer.write(block_b.unknown1);
  writer.writeArray(block_b.models, (model) => {
    writeModel(writer, model);
  });
  writer.write(block_b.unknown2);
});
writer.writeArray(root.block_c, (block_c) => {
  writer.write(block_c.unknown1);
  writer.write(block_c.unknown_floats);
  writer.writeArray(block_c.models, (model) => {
    writer.write(model.unknown9);
    writeModel(writer, model);
  });
});

await writeFile(join(dirname(path), `${basename(path, '.bak')}`), output.subarray(0, writer.ptr));
