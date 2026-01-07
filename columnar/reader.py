# columnar/reader.py
import csv
import struct
from typing import Dict, List, Any, Iterable, Optional

from .format_header import (
    parse_header,
    FileHeader,
    TYPE_INT32,
    TYPE_FLOAT64,
    TYPE_STRING,
    ENDIAN,
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
    """
    with open(file_path, "rb") as f:
        raw = f.read()
    header: FileHeader = parse_header(raw)

    data: Dict[str, List[Any]] = {}
    selected = set(columns) if columns else {c.name for c in header.columns}

    for col_meta in header.columns:
        if col_meta.name not in selected:
            continue
        block = raw[col_meta.offset : col_meta.offset + col_meta.compressed_size]
        decompressed = decompress_block(block)
        if len(decompressed) != col_meta.uncompressed_size:
            raise ValueError("Uncompressed size mismatch for column " + col_meta.name)
        values = _decode_column(decompressed, col_meta.type_id, header.num_rows)
        data[col_meta.name] = values

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
