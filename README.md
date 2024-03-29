# ForzaTech extraction tools
Collection of patterns, scripts and more for reverse engineering ForzaTech game engine resources used in Forza game series since 2015, starting with Forza Motorsport 6.

## Patterns
![screenshot of .carbin file opened in a hex editor](https://user-images.githubusercontent.com/5512376/230833781-2040b6e6-3628-420d-89f7-91cf4a57582f.png)
[ImHex](https://imhex.werwolv.net/) patterns for `.carbin` and `.modelbin` game resources.

## Scripts
```
cd  D:\ForzaTech-extraction-tools-main\scripts
node carbin_converter.js "D:\games\rips\FH5\media\Cars\NUL_Car_00\NUL_Car_00.carbin.bak"
```

### `carbin_converter.js`
![screenshot of Mercedes AMG One opened in 3DSimED](https://user-images.githubusercontent.com/5512376/230759882-c1af0cf0-9a80-4f39-adf0-105b43bcac22.png)
It deserializes the Forza Horizon 5/Forza Motorsport (2023) input file and then serializes the Forza Horizon 4/Forza Motorsport 7 output file compatible with 3DSimED 3.2c. Actually, it just replaces the first byte with `05` and drops 5 unnecessary bytes at the end of model chunks. Forza Horiozn 5 also has an updated `.materialbin` file format not supported by 3DSimED, so a lot of warnings must be skipped.

### `string_extractor.js`
Prints a list of all strings contained in the input file in the following formats:
```
<u32 length> <u8 data[length]>
<u16 length> <u8 data[length]>
```
For example, `0A 00 00 00 6E 75 6C 5F 63 61 72 5F 30 30` is a string "nul_car_00" 10 bytes long. It was useful for researching `.carbin` and `_skeleton.modelbin`.

## Resources

### `media\Cars\*\*.carbin`
*279 / 397 bytes unknown*

#### Hierarchy
- Root
  - ChunkA[0]
    - Model[0]
    - Model[1]
    - ...
  - ...
  - ChunkB[0]
    - Model[0]
    - Model[1]
    - ...
  - ...

#### Structures
- Root *(1\*5+2=7 / 42 bytes unknown)*
  - type  
`05 00` FH4, FH5 NUL_Car_00  
`06 00` FH5
  - guid
  - car name
  - skeleton path
  - `01` at the end (type 6 only)
- ChunkA *(1\*7+4\*8=39 / 43 bytes unknown)*
- ChunkB *(4+(1\*13+4\*8)+((4))=53 / 67 bytes unknown)*  
Upgrade parts?
  - `03 00` type
- Model *(4\*16+2+1+4+(4)+8+4+(1\*2+1\*27)+1\*19+1\*20+4+(16)+5=180 / 245 bytes unknown)*
  - type  
`10 00` FH4  
`12 00` FH5
  - guid  
  - 5 unknown bytes at the end (type 18 only)

#### Links
- [Model chunk](https://web.archive.org/web/20231023061958/https://forum.xentax.com/viewtopic.php?t=4256&start=1815#p128496)

### `media\Cars\*\*.modelbin`

#### Structures
- Entry
  - tag

    Reversed because it is stored as a number.[\[link\]](https://stackoverflow.com/q/22239629) In C++ it looks like this:
    ```C++
    uint32_t type = *(uint32_t *)("Grub");
    std::cout << std::hex << type;
    // Expected output: 62757247
    ```

    - Skel - Skeleton
      - count: 1
      - no properties
    - Mrph - Morph
      - count: 0-1
      - no properties
    - MatI - Material Info
      - properties
        - Name
        - Id
    - Mesh
      - properties
        - Name
        - BBox
    - IndB - Index Buffer
      - count: 0-1
      - properties
        - Id
    - VLay - Vertex Layouts
      - properties
        - Id  
`-1` FH5 DOD_caliperLR_006
    - VerB - Vertex Buffer
      - properties
        - Id
    - Skin
      - properties
        - Id
    - MBuf
    - Modl - Model
      - count: 1
      - properties
        - BBox
        - TRef (optional)
  - properties
    - Name
    - Id
    - BBox - Bounding Box
    - TRef
      - array of unknown 4-byte elements
  - data address
    - aligned to 4 bytes

#### Links
- [Part 1](https://web.archive.org/web/20231024100158/https://forum.xentax.com/viewtopic.php?t=4256&start=1590#p126552)
  - [Entry properties](https://web.archive.org/web/20231014012208/https://forum.xentax.com/viewtopic.php?t=4256&start=2010#p135231)
- [Part 2](https://web.archive.org/web/20231024083039/https://forum.xentax.com/viewtopic.php?t=4256&start=1650#p126817)
- [Part 3 - LOD](https://web.archive.org/web/20231024054710/https://forum.xentax.com/viewtopic.php?t=4256&start=1695#p127004)
  - [Skel entry](https://web.archive.org/web/20231024041832/https://forum.xentax.com/viewtopic.php?t=4256&start=1725#p127226)
- [Part 4 - UV](https://web.archive.org/web/20231024022340/https://forum.xentax.com/viewtopic.php?t=4256&start=1770#p127586)
- [Download experimental tools](https://mega.nz/folder/2pojyLQL#w1TZFlChnXTkrigs_uQhGw)

### `media\Stripped\gamedbRC.slt`
It seems to be necessary for correct scaling and positioning of wheels and selecting of tires.

#### Decrypt
[Tutorial](https://youtu.be/jOIT7nVqjRI)  
ForzaHorizon5.exe (CRC32: BFCEECA8)
```
00000001408FCFFE: call DeobfuscateGameDB(_, _, destination address, size, _)
```
Stage 1: Arxan TransformIT.  
Stage 2: Obfuscation based on CRC-32.

#### Links
- [Crypto tool](https://github.com/Doliman100/ForzaTech-encryption-tool)
- [Download decrypted](https://mega.nz/folder/btYnBayQ#VVFbwoZ8uxli2xfTmmvadw)
- [Data_Car table](https://web.archive.org/web/20231021095102/https://forum.xentax.com/viewtopic.php?t=4256&start=1905#p129562)

### `media\Stripped\StringTables\EN\*.str`
Related to gamedbRC.slt tables.

#### Structures
- Root
	- `00 04` version
	- table name buffer
- StringInfo
	- id  
The first byte of the placeholder name hash.  
`_&16972226482902517561` `39 C7 E1 40 10 76 89 EB` "IDS_DisplayName_1"

#### Links
- [010 Editor pattern and C# hash function](https://github.com/Nenkai/010GameTemplates/blob/main/Forza/STR_StringTable.bt)

## Other tools

### 3DSimED
Keygen is available on [GameModels Community](https://discord.gg/XkCQGws).  
[3DSimED3.exe v3.2.3.1](https://web.archive.org/web/20230416135931/http://sim-garage.co.uk/wp-content/uploads/3DSimED32c.zip) (CRC32: C7FD36C3, protection: PC Guard 5.01, OEP: 007CC646, IAT: 008B1000)  
IAT invalid imports:
```
008B141C: kernel32.ExitProcess
008B15D8: ?
008B15DC: ?
008B15E0: ?
008B1BC8: ?
```
The first four APIs are mentioned [here](https://foro.elhacker.net/ingenieria_inversa/help_desempacar_pc_guard_501-t420259.0.html;msg1961677#msg1961677). I couldn't find which DLLs they refer to. Maybe they are used to load import/export modules dynamically.

## Environment
- Node.js v18.14.0
- ImHex v1.30.1
- Forza Horizon 5 v1.405.2.0 (Steam) \[EMPRESS\]
- Forza Horizon 4 v1.466.445.0 (Steam) \[EMPRESS\]
- Forza Horizon 3 v1.0.37.2 (UWP) "OpusDev"

## Thanks
The [XeNTaX](https://web.archive.org/web/20231024043255/https://forum.xentax.com/index.php) community for sharing their research of `.carbin` and `.modelbin` file structure and creating tutorials for researching unknown 3D formats.
