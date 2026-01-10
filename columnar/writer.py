import csv
import struct
from typing import List, Dict, Any, Iterable, Tuple

from .format_header import (
    ColumnMeta,
    pack_file_header,
    pack_column_meta,
    HEADER_SIZE,
    TYPE_INT32,
    TYPE_FLOAT64,
    TYPE_STRING,
    ENDIAN,
)
from .compression import compress_block


# Map from logical type string to type id and pack/unpack format
TYPE_MAP = {
    "int32": (TYPE_INT32, "i"),
    "float64": (TYPE_FLOAT64, "d"),
    "string": (TYPE_STRING, None),
}


def _encode_column(values: List[Any], logical_type: str) -> bytes:
    type_id, fmt = TYPE_MAP[logical_type]

    if type_id in (TYPE_INT32, TYPE_FLOAT64):
        packer = struct.Struct(ENDIAN + fmt)
        buf = bytearray()
        for v in values:
            if v is None or v == "":
                raise ValueError("Nulls not supported in this simple implementation")
            if type_id == TYPE_INT32:
                v = int(v)
            else:
                v = float(v)
            buf += packer.pack(v)
        return bytes(buf)

    # strings: length-prefixed UTF-8
    if type_id == TYPE_STRING:
        buf = bytearray()
        for v in values:
            s = "" if v is None else str(v)
            b = s.encode("utf-8")
            buf += struct.pack(ENDIAN + "I", len(b))
            buf += b
        return bytes(buf)

    raise ValueError(f"Unknown logical_type: {logical_type}")


def write_from_rows(
    file_path: str,
    rows: Iterable[Dict[str, Any]],
    schema: List[Tuple[str, str]],
) -> None:
    """
    Write custom columnar file from iterable of row dicts.
    """
    # Materialize rows
    rows = list(rows)
    num_rows = len(rows)

    # Collect per-column values
    columns_data: Dict[str, List[Any]] = {name: [] for name, _ in schema}
    for row in rows:
        for name, _typ in schema:
            columns_data[name].append(row.get(name))

    # 1. Encode and Compress Data Blocks
    blocks: Dict[str, bytes] = {}
    col_info: List[Dict] = []
    
    for name, logical_type in schema:
        type_id, _ = TYPE_MAP[logical_type]
        raw_bytes = _encode_column(columns_data[name], logical_type)
        comp_bytes = compress_block(raw_bytes)
        
        blocks[name] = comp_bytes
        col_info.append({
            "name": name,
            "type_id": type_id,
            "compressed_size": len(comp_bytes),
            "uncompressed_size": len(raw_bytes)
        })

    # 2. Calculate Offsets
    # Layout: [FILE HEADER 32B] [METADATA SECTION] [DATA SECTION]
    
    metadata_offset = HEADER_SIZE
    
    # Calculate size of metadata section to find where data section starts
    # We need to create temporary ColumnMeta objects to check packed size, 
    # but data_offset isn't known yet.
    # However, pack_column_meta size depends only on name length.
    
    current_meta_offset = metadata_offset
    for info in col_info:
        # Size = 4(NameLen) + NameLen + 1(Type) + 8(Comp) + 8(Uncomp) + 8(Offset)
        #      = 29 + len(name)
        meta_size = 29 + len(info["name"].encode("utf-8"))
        current_meta_offset += meta_size
        
    data_start_offset = current_meta_offset
    
    # 3. Create Final ColumnMeta objects with correct Data Offsets
    final_metas: List[ColumnMeta] = []
    current_data_offset = data_start_offset
    
    for info in col_info:
        meta = ColumnMeta(
            name=info["name"],
            type_id=info["type_id"],
            compressed_size=info["compressed_size"],
            uncompressed_size=info["uncompressed_size"],
            data_offset=current_data_offset
        )
        final_metas.append(meta)
        current_data_offset += info["compressed_size"]

    # 4. Write to File
    with open(file_path, "wb") as f:
        # Write File Header
        header_bytes = pack_file_header(
            num_columns=len(final_metas),
            num_rows=num_rows,
            metadata_offset=metadata_offset,
            data_offset=data_start_offset
        )
        f.write(header_bytes)
        
        # Write Metadata Section
        for meta in final_metas:
            f.write(pack_column_meta(meta))
            
        # Write Data Section
        for meta in final_metas:
            f.write(blocks[meta.name])


def write_from_csv(
    input_csv: str,
    output_file: str,
    schema: List[Tuple[str, str]],
    delimiter: str = ",",
) -> None:
    """
    Convenience wrapper: read CSV and write columnar file.
    """
    with open(input_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        write_from_rows(output_file, reader, schema)
