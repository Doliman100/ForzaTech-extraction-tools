import { readFile } from 'fs/promises';

// config
const path = process.argv[2];

const printAddresses = true; // prints the address of the first character of string

// program
const buffer = await readFile(path);

const re = /^[\x20-\x7e]+$/;
let ptr = 0;

function readString(lengthSize) {
  const begin = ptr + lengthSize;
  if (begin > buffer.byteLength) {
    return false;
  }
  const length = buffer.readUIntLE(ptr, lengthSize);
  const end = begin + length;
  if (end > buffer.byteLength) {
    return false;
  }
  const str = buffer.toString('utf8', begin, end);
  if (!re.test(str)) {
    return false;
  }
  console.log([
    printAddresses && begin.toString(16).padStart(8, '0').toUpperCase(),
    str.toString(),
  ].filter(Boolean).join(' '));
  ptr = end;
  return true;
}

while (ptr < buffer.length) {
  if (!readString(4) && !readString(2)) {
    ptr++;
  }
}
