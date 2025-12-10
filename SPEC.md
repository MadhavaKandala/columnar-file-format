# Columnar File Format Specification (SPEC)

## Version: 1.0

## Overview

This document defines the binary layout and structure of the Columnar File Format (.colfile). The format is designed for efficient storage and retrieval of tabular data with support for selective column reads and zlib compression.

## File Structure

A columnar file consists of three main sections:

```
┌─────────────────────────┐
│   FILE HEADER (32B)     │ Offset: 0
├─────────────────────────┤
│   METADATA SECTION      │ Offset: metadata_offset
│   (Column Info Block)   │
├─────────────────────────┤
│   DATA SECTION          │ Offset: data_offset
│   (Compressed Columns)  │
└─────────────────────────┘
```

## Section 1: File Header (32 bytes, Little-endian)

The file header contains metadata about the entire file.

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | Magic | char[4] | Magic number: "COLM" (0x434F4C4D) |
| 4 | 4 | Version | uint32 | Format version (currently 1) |
| 8 | 4 | ColumnCount | uint32 | Number of columns in the file |
| 12 | 4 | RowCount | uint32 | Number of rows in the file |
| 16 | 8 | MetadataOffset | uint64 | Byte offset to metadata section |
| 24 | 8 | DataOffset | uint64 | Byte offset to data section |

### Header Details

- **Magic**: Always "COLM" (ASCII: C=0x43, O=0x4F, L=0x4C, M=0x4D)
- **Version**: Version number for format compatibility (1)
- **ColumnCount**: Must be > 0
- **RowCount**: Number of data rows (excluding header)
- **MetadataOffset**: Points to first column metadata block
- **DataOffset**: Points to first compressed data block

## Section 2: Metadata Section

Contains column information blocks, one per column, in order.

### Column Metadata Block Layout

Each column has a metadata block with variable size:

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 4 | NameLength | uint32 | Length of column name (N) |
| 4 | N | ColumnName | UTF-8 | Column name (not null-terminated) |
| 4+N | 1 | DataType | uint8 | Data type identifier (see below) |
| 5+N | 8 | CompressedSize | uint64 | Compressed data block size |
| 13+N | 8 | UncompressedSize | uint64 | Uncompressed data block size |
| 21+N | 8 | DataOffset | uint64 | Byte offset to compressed data |

### Data Type Identifiers

| Value | Type | Size per value | Format |
|-------|------|----------------|--------|
| 1 | int32 | 4 bytes | IEEE 754 32-bit signed integer |
| 2 | float64 | 8 bytes | IEEE 754 64-bit double precision |
| 3 | string | variable | UTF-8 with length prefix |

### Column Metadata Block Size

Total size = 4 + NameLength + 1 + 8 + 8 + 8 = 29 + NameLength bytes

## Section 3: Data Section

Contains compressed column data blocks, referenced by metadata offsets.

### Compressed Data Block

Each column's data is stored as a single zlib-compressed block:

```
┌──────────────────────────┐
│  Uncompressed Data       │ (in memory)
└──────────────────────────┘
           ↓ zlib compress
┌──────────────────────────┐
│  Compressed Data Block   │ (in file)
│  - 2 byte zlib header    │
│  - Compressed payload    │
│  - 4 byte Adler-32       │
└──────────────────────────┘
```

### Column Data Layout (Uncompressed)

Data within each column block:

#### For int32 and float64 Columns
```
[Value 0] [Value 1] [Value 2] ... [Value N-1]
   4B        4B        4B              4B
```

#### For String Columns
```
[Len0][String0][Len1][String1]...[LenN-1][StringN-1]
 4B    Len0B     4B    Len1B             4B      LenN-1B
```
Where each string length is a uint32 (little-endian) followed by UTF-8 bytes.

### Row-Major Storage Within Columns

All values for a column are stored contiguously, one after another, in row order:

```
Column 0: [Row 0 Value] [Row 1 Value] [Row 2 Value] ...
Column 1: [Row 0 Value] [Row 1 Value] [Row 2 Value] ...
Column 2: [Row 0 Value] [Row 1 Value] [Row 2 Value] ...
```

## Byte Order (Endianness)

**All multi-byte values use little-endian byte order.**

Example: uint32 value 0x12345678 is stored as:
```
78 56 34 12
```

## Reading the File

### Algorithm

1. Read and validate 32-byte file header
   - Check magic number == "COLM"
   - Validate version == 1
   - Extract column count and row count

2. Seek to metadata offset
   - Read column metadata blocks sequentially
   - Store column names, types, and data offsets

3. For each requested column:
   - Seek to column's data offset
   - Read compressed data of specified size
   - Decompress using zlib inflate
   - Parse values according to data type
   - Return as array/list

### Selective Column Read (Column Pruning)

Advantage: Only columns listed by the client are decompressed and parsed:

```python
# Read only specific columns
reader = Reader('data.colfile')
data = reader.read_columns(['name', 'age'])  # Skip 'salary' column
```

File operations:
1. Read file header
2. Read all metadata (small, ~100-500 bytes typical)
3. For each requested column:
   - Seek to its data offset
   - Read and decompress only that block
   - Parse values
4. Skip unrequested column data blocks

Space advantage: For 100GB file with 50 columns where you need 2 columns:
- Full read: 100GB decompression
- Selective read: ~4GB decompression (50x faster)

## Example File Layout

Small example with 2 columns, 3 rows:

```
Column 0: "id" (int32)
Column 1: "name" (string)
Rows: [(1, "Alice"), (2, "Bob"), (3, "Charlie")]

Byte Layout:
─────────────────────────────────────
0x00-0x1F: FILE HEADER
  0x00: "COLM" (magic)
  0x04: 0x00000001 (version)
  0x08: 0x00000002 (2 columns)
  0x0C: 0x00000003 (3 rows)
  0x10: 0x0000000000000020 (metadata offset = 32)
  0x18: 0x00000000000000B0 (data offset = 176)

0x20-0x5F: COLUMN 0 METADATA
  0x20: 0x00000002 (name length = 2)
  0x24: "id" (column name)
  0x26: 0x01 (data type = int32)
  0x27: 0x0000000000000010 (compressed size = 16)
  0x2F: 0x000000000000000C (uncompressed size = 12)
  0x37: 0x00000000000000B0 (data offset = 176)

0x40-0x7F: COLUMN 1 METADATA
  0x40: 0x00000004 (name length = 4)
  0x44: "name" (column name)
  0x48: 0x03 (data type = string)
  0x49: 0x0000000000000030 (compressed size = 48)
  0x51: 0x000000000000002B (uncompressed size = 43)
  0x59: 0x00000000000000C0 (data offset = 192)

0xB0-0xCF: COLUMN 0 DATA (compressed)
  [zlib compressed: 1, 2, 3]

0xC0-...: COLUMN 1 DATA (compressed)
  [zlib compressed: "Alice", "Bob", "Charlie"]
```

## Endianness Examples

### uint32 (4 bytes) - Little Endian
Value: 256 (0x00000100)
Bytes: 00 01 00 00

### uint64 (8 bytes) - Little Endian
Value: 65536 (0x0000000000010000)
Bytes: 00 00 01 00 00 00 00 00

### String Encoding
String: "Hi" (2 characters, 2 bytes in UTF-8)
Encoded as: 02 00 00 00 48 69
(length as uint32 LE) + (bytes)

## Constraints and Limitations

- Maximum RowCount: 2^32 - 1 (~4.3 billion rows)
- Maximum ColumnCount: 2^32 - 1
- Maximum column name length: 2^32 - 1 characters
- Maximum string length: 2^32 - 1 bytes
- Maximum file size: Limited by zlib compressed block size

## Validation Checklist

When reading a file, validate:

- [ ] Magic number is "COLM"
- [ ] Version is 1 (or compatible)
- [ ] Column count > 0
- [ ] Row count >= 0
- [ ] Metadata offset > 32
- [ ] Data offset > metadata offset
- [ ] All column metadata blocks parse correctly
- [ ] Data offsets don't overlap
- [ ] Decompressed size matches row count × type size

## Compression Details

### zlib Format

- **Standard**: zlib deflate (RFC 1950)
- **Library**: Use Python's `zlib` module or equivalent
- **Compression Level**: Default (6) for balance

### Example (Python)

```python
import zlib

# Compression
data = b'\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00'
compressed = zlib.compress(data, wl=15)  # Default window bits

# Decompression
decompressed = zlib.decompress(compressed)
assert decompressed == data
```

## Future Extensions

Potential fields for version 2:

- Row count compression (dictionary encoding)
- Bloom filters for column values
- Index blocks for sorted columns
- Statistical metadata (min/max per column)
- Checksum/CRC for data integrity

## References

- [zlib Documentation](https://www.zlib.net/)
- [IEEE 754 Floating Point](https://en.wikipedia.org/wiki/Double-precision_floating-point_format)
- [UTF-8 Encoding](https://tools.ietf.org/html/rfc3629)
