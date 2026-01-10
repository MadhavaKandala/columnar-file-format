import struct
from typing import Dict, List, Any, Iterable, Optional

from .format_header import (
    unpack_file_header,
    unpack_column_meta,
    ColumnMeta,
    TYPE_INT32,
    TYPE_FLOAT64,
    TYPE_STRING,
    ENDIAN,
    HEADER_SIZE,
)
from .compression import decompress_block


def _decode_column(
    raw: bytes, type_id: int, num_rows: int
) -> List[Any]:
    if type_id == TYPE_INT32:
        packer = struct.Struct(ENDIAN + "i")
        return [packer.unpack_from(raw, i * 4)[0] for i in range(num_rows)]

    if type_id == TYPE_FLOAT64:
        packer = struct.Struct(ENDIAN + "d")
        return [packer.unpack_from(raw, i * 8)[0] for i in range(num_rows)]

    if type_id == TYPE_STRING:
        vals: List[str] = []
        pos = 0
        mv = memoryview(raw)
        for _ in range(num_rows):
            (length,) = struct.unpack_from(ENDIAN + "I", mv, pos)
            pos += 4
            s = mv[pos:pos + length].tobytes().decode("utf-8")
            pos += length
            vals.append(s)
        return vals

    raise ValueError(f"Unknown type_id: {type_id}")


def read_header_and_columns(
    file_path: str, columns: Optional[List[str]] = None
) -> Dict[str, List[Any]]:
    """
    Read file, optionally only a subset of columns.
    Returns dict: column_name -> list of values.
    
    Efficiently seeks to the necessary parts of the file.
    """
    with open(file_path, "rb") as f:
        # 1. Read File Header (32 bytes)
        raw_header = f.read(HEADER_SIZE)
        if len(raw_header) != HEADER_SIZE:
             raise ValueError("File too short for header")
        
        file_header = unpack_file_header(raw_header)
        
        # 2. Read Metadata Section
        f.seek(file_header.metadata_offset)
        
        # We don't know the total size of metadata, but we know num_columns.
        # We'll read enough chunks or read one by one. 
        # Since metadata is small, we can read a chunk or read item by item.
        # Let's read a chunk to start, or just robustly read.
        
        # Robust approach: Read sequentially from metadata_offset
        # We need to buffer or read small pieces.
        # Let's read a reasonable block size (e.g. 64KB) or the whole metadata section if possible.
        # We can calculate metadata_size = data_offset - metadata_offset.
        metadata_size = file_header.data_offset - file_header.metadata_offset
        metadata_bytes = f.read(metadata_size)
        
        col_metas: List[ColumnMeta] = []
        offset_in_buffer = 0
        for _ in range(file_header.num_columns):
            meta, consumed = unpack_column_meta(metadata_bytes, offset_in_buffer)
            col_metas.append(meta)
            offset_in_buffer += consumed
            
        # 3. Read Data Section (Selective)
        data: Dict[str, List[Any]] = {}
        
        # If columns is None, read all.
        target_columns = set(columns) if columns else {c.name for c in col_metas}
        
        for meta in col_metas:
            if meta.name not in target_columns:
                continue
                
            # Seek to specific column data block
            f.seek(meta.data_offset)
            compressed_data = f.read(meta.compressed_size)
            
            if len(compressed_data) != meta.compressed_size:
                raise ValueError(f"Incomplete read for column {meta.name}")
                
            decompressed = decompress_block(compressed_data)
            
            if len(decompressed) != meta.uncompressed_size:
                 raise ValueError("Uncompressed size mismatch for column " + meta.name)
                 
            values = _decode_column(decompressed, meta.type_id, file_header.num_rows)
            data[meta.name] = values

    return data


def read_as_rows(
    file_path: str, columns: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Reconstruct rows from columnar data.
    """
    col_data = read_header_and_columns(file_path, columns)
    if not col_data:
        return []
    num_rows = len(next(iter(col_data.values())))
    rows: List[Dict[str, Any]] = []
    col_names = list(col_data.keys())
    for i in range(num_rows):
        row = {name: col_data[name][i] for name in col_names}
        rows.append(row)
    return rows
