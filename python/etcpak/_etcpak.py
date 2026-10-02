from __future__ import annotations

import ctypes
import os
from typing import Optional, Tuple

import uabe_native


def _load_lib() -> ctypes.CDLL:
    return uabe_native.load("Etcpak")


_lib = _load_lib()
_u8 = ctypes.c_ubyte
_u8_p = ctypes.POINTER(_u8)

_i32 = ctypes.c_int

class _BC7ParamsC(ctypes.Structure):
    _fields_ = [
        ("m_mode_mask", ctypes.c_uint32),
        ("m_max_partitions", ctypes.c_uint32),
        ("m_weights", ctypes.c_uint32 * 4),
        ("m_uber_level", ctypes.c_uint32),
        ("m_perceptual", ctypes.c_uint8),
        ("m_try_least_squares", ctypes.c_uint8),
        ("m_mode17_partition_estimation_filterbank", ctypes.c_uint8),
        ("m_force_alpha", ctypes.c_uint8),
        ("m_force_selectors", ctypes.c_uint8),
        ("m_selectors", ctypes.c_uint8 * 16),
        ("m_quant_mode6_endpoints", ctypes.c_uint8),
        ("m_bias_mode1_pbits", ctypes.c_uint8),
        ("m_pbit1_weight", ctypes.c_float),
        ("m_mode1_error_weight", ctypes.c_float),
        ("m_mode5_error_weight", ctypes.c_float),
        ("m_mode6_error_weight", ctypes.c_float),
        ("m_mode7_error_weight", ctypes.c_float),
    ]


class BC7CompressBlockParams:

    def __init__(self) -> None:
        p = _BC7ParamsC()

        p.m_mode_mask = 0xFFFFFFFF
        p.m_max_partitions = 64
        p.m_try_least_squares = 1
        p.m_mode17_partition_estimation_filterbank = 1
        p.m_uber_level = 0
        p.m_force_selectors = 0
        p.m_force_alpha = 0
        p.m_quant_mode6_endpoints = 0
        p.m_bias_mode1_pbits = 0
        p.m_pbit1_weight = 1.0
        p.m_mode1_error_weight = 1.0
        p.m_mode5_error_weight = 1.0
        p.m_mode6_error_weight = 1.0
        p.m_mode7_error_weight = 1.0


        p.m_perceptual = 1
        p.m_weights[:] = (128, 64, 16, 32)

        self._p = p

    def init_linear_weights(self) -> None:
        self._p.m_perceptual = 0
        self._p.m_weights[:] = (1, 1, 1, 1)

    def init_perceptual_weights(self) -> None:
        self._p.m_perceptual = 1
        self._p.m_weights[:] = (128, 64, 16, 32)

    def _as_ptr(self) -> ctypes.POINTER(_BC7ParamsC):
        return ctypes.pointer(self._p)


    @property
    def m_weights(self) -> list[int]:
        return [int(self._p.m_weights[i]) for i in range(4)]

    @m_weights.setter
    def m_weights(self, v: list[int]) -> None:
        if len(v) != 4:
            raise ValueError("m_weights must have 4 items")
        self._p.m_weights[:] = (int(v[0]), int(v[1]), int(v[2]), int(v[3]))

def _inbuf(data: bytes) -> Tuple[ctypes.Array, _u8_p]:
    n = len(data)
    arr = (_u8 * n).from_buffer_copy(data)
    return arr, ctypes.cast(arr, _u8_p)


def _outbuf(n: int) -> Tuple[bytearray, ctypes.Array, _u8_p]:
    out = bytearray(n)
    arr = (_u8 * n).from_buffer(out)
    return out, arr, ctypes.cast(arr, _u8_p)


def _require_dims(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("width/height must be > 0")
    if (width % 4) != 0 or (height % 4) != 0:
        raise ValueError("width/height must be multiples of 4")


def _require_rgba(data: bytes, width: int, height: int) -> None:
    _require_dims(width, height)
    exp = width * height * 4
    if len(data) != exp:
        raise ValueError(f"expected RGBA bytes size {exp}, got {len(data)}")

def _bind(name: str, argtypes, restype=ctypes.c_int):
    fn = getattr(_lib, name)
    fn.argtypes = argtypes
    fn.restype = restype
    return fn


_compress_bc1 = _bind("etcpak_compress_bc1", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_bc1_dither = _bind("etcpak_compress_bc1_dither", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_bc3 = _bind("etcpak_compress_bc3", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_bc4 = _bind("etcpak_compress_bc4", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_bc5 = _bind("etcpak_compress_bc5", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_bc7 = _bind("etcpak_compress_bc7", [_u8_p, _i32, _i32, ctypes.POINTER(_BC7ParamsC), _u8_p, _i32])

_compress_etc1_rgb = _bind("etcpak_compress_etc1_rgb", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_etc1_rgb_dither = _bind("etcpak_compress_etc1_rgb_dither", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_etc2_rgb = _bind("etcpak_compress_etc2_rgb", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_etc2_rgba = _bind("etcpak_compress_etc2_rgba", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_eac_r = _bind("etcpak_compress_eac_r", [_u8_p, _i32, _i32, _u8_p, _i32])
_compress_eac_rg = _bind("etcpak_compress_eac_rg", [_u8_p, _i32, _i32, _u8_p, _i32])


_decompress_etc1_rgb = _bind("etcpak_decompress_etc1_rgb", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_etc2_rgb = _bind("etcpak_decompress_etc2_rgb", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_etc2_rgba = _bind("etcpak_decompress_etc2_rgba", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_etc2_r11 = _bind("etcpak_decompress_etc2_r11", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_etc2_rg11 = _bind("etcpak_decompress_etc2_rg11", [_u8_p, _i32, _i32, _u8_p, _i32])

_decompress_bc1 = _bind("etcpak_decompress_bc1", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_bc3 = _bind("etcpak_decompress_bc3", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_bc4 = _bind("etcpak_decompress_bc4", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_bc5 = _bind("etcpak_decompress_bc5", [_u8_p, _i32, _i32, _u8_p, _i32])
_decompress_bc7 = _bind("etcpak_decompress_bc7", [_u8_p, _i32, _i32, _u8_p, _i32])


def _size_4bpp(w: int, h: int) -> int:
    return (w * h) // 2

def _size_8bpp(w: int, h: int) -> int:
    return (w * h)

def _size_rgba(w: int, h: int) -> int:
    return w * h * 4


def compress_bc1(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_4bpp(width, height))
    ok = _compress_bc1(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_bc1 failed")
    return bytes(out)

def compress_bc1_dither(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_4bpp(width, height))
    ok = _compress_bc1_dither(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_bc1_dither failed")
    return bytes(out)

def compress_bc3(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_8bpp(width, height))
    ok = _compress_bc3(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_bc3 failed")
    return bytes(out)

def compress_bc4(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_4bpp(width, height))
    ok = _compress_bc4(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_bc4 failed")
    return bytes(out)

def compress_bc5(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_8bpp(width, height))
    ok = _compress_bc5(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_bc5 failed")
    return bytes(out)

def compress_bc7(data: bytes, width: int, height: int, params: Optional[BC7CompressBlockParams] = None) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_8bpp(width, height))

    if params is None:
        null_ptr = ctypes.cast(None, ctypes.POINTER(_BC7ParamsC))
        ok = _compress_bc7(in_ptr, width, height, null_ptr, out_ptr, len(out))
    else:
        ok = _compress_bc7(in_ptr, width, height, params._as_ptr(), out_ptr, len(out))

    if not ok:
        raise RuntimeError("compress_bc7 failed")
    return bytes(out)

def compress_etc1_rgb(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_4bpp(width, height))
    ok = _compress_etc1_rgb(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_etc1_rgb failed")
    return bytes(out)

def compress_etc1_rgb_dither(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_4bpp(width, height))
    ok = _compress_etc1_rgb_dither(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_etc1_rgb_dither failed")
    return bytes(out)

def compress_etc2_rgb(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_4bpp(width, height))
    ok = _compress_etc2_rgb(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_etc2_rgb failed")
    return bytes(out)

def compress_etc2_rgba(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_8bpp(width, height))
    ok = _compress_etc2_rgba(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_etc2_rgba failed")
    return bytes(out)

def compress_eac_r(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_4bpp(width, height))
    ok = _compress_eac_r(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_eac_r failed")
    return bytes(out)

def compress_eac_rg(data: bytes, width: int, height: int) -> bytes:
    _require_rgba(data, width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_8bpp(width, height))
    ok = _compress_eac_rg(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("compress_eac_rg failed")
    return bytes(out)


def _decompress(fn, data: bytes, width: int, height: int) -> bytes:
    _require_dims(width, height)
    in_arr, in_ptr = _inbuf(data)
    out, out_arr, out_ptr = _outbuf(_size_rgba(width, height))
    ok = fn(in_ptr, width, height, out_ptr, len(out))
    if not ok:
        raise RuntimeError("decompress failed")
    return bytes(out)


def decompress_etc1_rgb(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_etc1_rgb, data, width, height)

def decompress_etc2_rgb(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_etc2_rgb, data, width, height)

def decompress_etc2_rgba(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_etc2_rgba, data, width, height)

def decompress_etc2_r11(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_etc2_r11, data, width, height)

def decompress_etc2_rg11(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_etc2_rg11, data, width, height)

def decompress_bc1(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_bc1, data, width, height)

def decompress_bc3(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_bc3, data, width, height)

def decompress_bc4(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_bc4, data, width, height)

def decompress_bc5(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_bc5, data, width, height)

def decompress_bc7(data: bytes, width: int, height: int) -> bytes:
    return _decompress(_decompress_bc7, data, width, height)
