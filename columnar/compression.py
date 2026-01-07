# columnar/compression.py
import zlib


def compress_block(data: bytes) -> bytes:
    return zlib.compress(data)


def decompress_block(data: bytes) -> bytes:
    return zlib.decompress(data)
