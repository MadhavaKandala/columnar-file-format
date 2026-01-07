# columnar/writer.py
import csv
import struct
from typing import List, Dict, Any, Iterable, Tuple

from .format_header import (
    ColumnMeta,
    build_header,
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

    schema: list of (name, logical_type) where logical_type in {"int32","float64","string"}.
    """
    # materialize rows (task is small-scale)
    rows = list(rows)
    num_rows = len(rows)

    # collect per-column values
    columns_data: Dict[str, List[Any]] = {name: [] for name, _ in schema}
    for row in rows:
        for name, _typ in schema:
            columns_data[name].append(row.get(name))

    # build column blocks
    column_metas: List[ColumnMeta] = []
    blocks: Dict[str, bytes] = {}

    # header will be written first; we do a two-pass:
    # 1) encode & compress columns
    # 2) compute offsets (after header length is known)
    for name, logical_type in schema:
        raw_bytes = _encode_column(columns_data[name], logical_type)
        comp_bytes = compress_block(raw_bytes)
        blocks[name] = comp_bytes

    # dummy metas
    dummy_metas: List[ColumnMeta] = []

    for name, logical_type in schema:
        type_id, _fmt = TYPE_MAP[logical_type]
        comp_bytes = blocks[name]
        if logical_type == "int32":
            uncomp_size = 4 * num_rows
        elif logical_type == "float64":
            uncomp_size = 8 * num_rows
        else:
            uncomp_size = len(_encode_column(columns_data[name], logical_type))
        dummy_metas.append(
            ColumnMeta(
                name=name,
                type_id=type_id,
                offset=0,
                compressed_size=len(comp_bytes),
                uncompressed_size=uncomp_size,
            )
        )

    # first header to estimate size
    dummy_header_bytes = build_header(num_rows, dummy_metas)
    header_size = len(dummy_header_bytes)

    # now compute real offsets
    offset = header_size
    real_metas: List[ColumnMeta] = []
    for meta in dummy_metas:
        real_metas.append(
            ColumnMeta(
                name=meta.name,
                type_id=meta.type_id,
                offset=offset,
                compressed_size=meta.compressed_size,
                uncompressed_size=meta.uncompressed_size,
            )
        )
        offset += meta.compressed_size

    # final header
    header_bytes = build_header(num_rows, real_metas)

    # write file
    with open(file_path, "wb") as f:
        f.write(header_bytes)
        for meta in real_metas:
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
