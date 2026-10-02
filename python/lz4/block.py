from __future__ import annotations

import ctypes
import struct
import sys

_COMPRESSION_LZ4_RAW = 0x101
_lib = None
if sys.platform == "darwin":
    try:
        _lib = ctypes.CDLL("/usr/lib/libcompression.dylib")
        for _fn in ("compression_encode_buffer", "compression_decode_buffer"):
            _f = getattr(_lib, _fn)
            _f.restype = ctypes.c_size_t
            _f.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p,
                           ctypes.c_size_t, ctypes.c_void_p, ctypes.c_int]
    except Exception:
        _lib = None


class LZ4BlockError(Exception):
    pass


def _py_decompress(src: bytes, size: int) -> bytes:
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        out += src[i:i + lit]
        i += lit
        if i >= n:
            break
        offset = src[i] | (src[i + 1] << 8)
        i += 2
        if offset == 0 or offset > len(out):
            raise LZ4BlockError("invalid match offset")
        mlen = token & 15
        if mlen == 15:
            while True:
                b = src[i]
                i += 1
                mlen += b
                if b != 255:
                    break
        mlen += 4
        start = len(out) - offset
        if offset >= mlen:
            out += out[start:start + mlen]
        else:
            for k in range(mlen):
                out.append(out[start + k])
    if size >= 0 and len(out) != size:
        raise LZ4BlockError(f"decompressed {len(out)} bytes, expected {size}")
    return bytes(out)


def decompress(source, uncompressed_size: int = -1, return_bytearray: bool = False, dict=None):
    data = bytes(source)
    if uncompressed_size is None or uncompressed_size < 0:
        if len(data) < 4:
            raise LZ4BlockError("missing size header")
        uncompressed_size = struct.unpack_from("<I", data, 0)[0]
        data = data[4:]
    if uncompressed_size == 0:
        return bytearray() if return_bytearray else b""
    result = None
    if _lib is not None:
        buf = ctypes.create_string_buffer(uncompressed_size)
        n = _lib.compression_decode_buffer(buf, uncompressed_size, data, len(data), None,
                                           _COMPRESSION_LZ4_RAW)
        if n == uncompressed_size:
            result = buf.raw
    if result is None:
        result = _py_decompress(data, uncompressed_size)
    return bytearray(result) if return_bytearray else result


def _literal_only(src: bytes) -> bytes:
    n = len(src)
    out = bytearray()
    if n < 15:
        out.append(n << 4)
    else:
        out.append(0xF0)
        rest = n - 15
        while rest >= 255:
            out.append(255)
            rest -= 255
        out.append(rest)
    out += src
    return bytes(out)


def compress(source, mode: str = "default", acceleration: int = 1, compression: int = 0,
             store_size: bool = True, dict=None, return_bytearray: bool = False):
    data = bytes(source)
    body = None
    if _lib is not None and data:
        cap = len(data) + len(data) // 255 + 64
        buf = ctypes.create_string_buffer(cap)
        n = _lib.compression_encode_buffer(buf, cap, data, len(data), None, _COMPRESSION_LZ4_RAW)
        if n:
            body = buf.raw[:n]
    if body is None:
        body = _literal_only(data) if data else b"\x00"
    if store_size:
        body = struct.pack("<I", len(data)) + body
    return bytearray(body) if return_bytearray else body
