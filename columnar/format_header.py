import struct
from dataclasses import dataclass
from typing import List

MAGIC = b"COLM"  # 4 bytes magic
VERSION = 1
ENDIAN = "<"  # little-endian

# Section 1: File Header (32 bytes)
# Magic(4) + Version(4) + ColumnCount(4) + RowCount(4) + MetadataOffset(8) + DataOffset(8)
HEADER_STRUCT = struct.Struct(ENDIAN + "4s I I I Q Q")
HEADER_SIZE = HEADER_STRUCT.size

# Data Type Identifiers from SPEC
TYPE_INT32 = 1
TYPE_FLOAT64 = 2
TYPE_STRING = 3

@dataclass
class ColumnMeta:
    name: str
    type_id: int
    compressed_size: int
    uncompressed_size: int
    data_offset: int  # SPEC calls this DataOffset in metadata block

@dataclass
class FileHeader:
    version: int
    num_columns: int
    num_rows: int
    metadata_offset: int
    data_offset: int

def pack_file_header(num_columns: int, num_rows: int, metadata_offset: int, data_offset: int) -> bytes:
    """Pack the 32-byte file header."""
    return HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        num_columns,
        num_rows,
        metadata_offset,
        data_offset
    )

def unpack_file_header(data: bytes) -> FileHeader:
    """Unpack the 32-byte file header."""
    if len(data) != HEADER_SIZE:
        raise ValueError(f"Header must be {HEADER_SIZE} bytes")
    
    magic, ver, n_cols, n_rows, meta_off, data_off = HEADER_STRUCT.unpack(data)
    
    if magic != MAGIC:
        raise ValueError(f"Invalid magic number: {magic!r}")
    if ver != VERSION:
        raise ValueError(f"Unsupported version: {ver}")
        
    return FileHeader(
        version=ver,
        num_columns=n_cols,
        num_rows=n_rows,
        metadata_offset=meta_off,
        data_offset=data_off
    )

def pack_column_meta(col: ColumnMeta) -> bytes:
    """
    Pack a single column metadata block.
    Format:
    NameLength (uint32)
    ColumnName (UTF-8 bytes)
    DataType (uint8)
    CompressedSize (uint64)
    UncompressedSize (uint64)
    DataOffset (uint64)
    """
    name_bytes = col.name.encode("utf-8")
    name_len = len(name_bytes)
    
    # 4 + name_len + 1 + 8 + 8 + 8 = 29 + name_len
    # Struct: I {name_len}s B Q Q Q
    fmt = ENDIAN + f"I{name_len}sBQQQ"
    return struct.pack(
        fmt,
        name_len,
        name_bytes,
        col.type_id,
        col.compressed_size,
        col.uncompressed_size,
        col.data_offset
    )

def unpack_column_meta(data: bytes, offset: int) -> tuple[ColumnMeta, int]:
    """
    Unpack a single column metadata block from data at offset.
    Returns (ColumnMeta, bytes_consumed).
    """
    mv = memoryview(data)
    # Read NameLength (4 bytes)
    (name_len,) = struct.unpack_from(ENDIAN + "I", mv, offset)
    current_pos = offset + 4
    
    # Read Name
    name_bytes = mv[current_pos : current_pos + name_len].tobytes()
    name = name_bytes.decode("utf-8")
    current_pos += name_len
    
    # Read rest: Type(1) + CompSize(8) + UncompSize(8) + DataOffset(8)
    rest_fmt = ENDIAN + "BQQQ"
    rest_size = struct.calcsize(rest_fmt)
    
    type_id, comp_size, uncomp_size, data_off = struct.unpack_from(rest_fmt, mv, current_pos)
    current_pos += rest_size
    
    meta = ColumnMeta(
        name=name,
        type_id=type_id,
        compressed_size=comp_size,
        uncompressed_size=uncomp_size,
        data_offset=data_off
    )
    
    return meta, (current_pos - offset)
