# columnar/format_header.py
import struct
from dataclasses import dataclass
from typing import List, Dict

MAGIC = b"COLD"  # 4 bytes magic
VERSION = 1
ENDIAN = "<"  # little-endian

# Data type ids (align to your SPEC)
TYPE_INT32 = 1
TYPE_FLOAT64 = 2
TYPE_STRING = 3


@dataclass
class ColumnMeta:
    name: str
    type_id: int
    offset: int
    compressed_size: int
    uncompressed_size: int


@dataclass
class FileHeader:
    version: int
    num_rows: int
    columns: List[ColumnMeta]


def build_header(num_rows: int, columns: List[ColumnMeta]) -> bytes:
    """
    Serialize header to bytes.
    Layout (all little-endian; adjust to SPEC if different):

    magic[4] + version(u8) + num_rows(u64) + num_cols(u32) +
    repeated:
      name_len(u16) + name(bytes) +
      type_id(u8) +
      offset(u64) +
      compressed_size(u64) +
      uncompressed_size(u64)
    """
    buf = bytearray()
    buf += MAGIC
    buf += struct.pack(ENDIAN + "B", VERSION)
    buf += struct.pack(ENDIAN + "Q", num_rows)
    buf += struct.pack(ENDIAN + "I", len(columns))

    for col in columns:
        name_bytes = col.name.encode("utf-8")
        buf += struct.pack(ENDIAN + "H", len(name_bytes))
        buf += name_bytes
        buf += struct.pack(ENDIAN + "B", col.type_id)
        buf += struct.pack(ENDIAN + "Q", col.offset)
        buf += struct.pack(ENDIAN + "Q", col.compressed_size)
        buf += struct.pack(ENDIAN + "Q", col.uncompressed_size)

    return bytes(buf)


def parse_header(raw: bytes) -> FileHeader:
    """
    Parse header bytes back into FileHeader.
    """
    mv = memoryview(raw)
    pos = 0

    magic = mv[pos:pos + 4].tobytes()
    if magic != MAGIC:
        raise ValueError("Invalid magic number")
    pos += 4

    (version,) = struct.unpack_from(ENDIAN + "B", mv, pos)
    pos += 1

    (num_rows,) = struct.unpack_from(ENDIAN + "Q", mv, pos)
    pos += 8

    (num_cols,) = struct.unpack_from(ENDIAN + "I", mv, pos)
    pos += 4

    columns: List[ColumnMeta] = []
    for _ in range(num_cols):
        (name_len,) = struct.unpack_from(ENDIAN + "H", mv, pos)
        pos += 2
        name = mv[pos:pos + name_len].tobytes().decode("utf-8")
        pos += name_len

        (type_id,) = struct.unpack_from(ENDIAN + "B", mv, pos)
        pos += 1

        offset, comp_size, uncomp_size = struct.unpack_from(
            ENDIAN + "QQQ", mv, pos
        )
        pos += 8 * 3

        columns.append(
            ColumnMeta(
                name=name,
                type_id=type_id,
                offset=offset,
                compressed_size=comp_size,
                uncompressed_size=uncomp_size,
            )
        )

    return FileHeader(version=version, num_rows=num_rows, columns=columns)
