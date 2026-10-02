import ctypes
from ctypes import (
    c_int, c_long, c_uint32, c_uint8, c_void_p,
    POINTER, byref
)

import uabe_native

_lib = uabe_native.load("T2D")

U8P  = POINTER(c_uint8)
U32P = POINTER(c_uint32)

def _u8buf(data: bytes):
    buf = (c_uint8 * len(data)).from_buffer_copy(data)
    return buf, ctypes.cast(buf, U8P)

def _out_u32(w: int, h: int):
    return (c_uint32 * (w * h))()

def _bytes_from_u32(out_u32):
    return ctypes.string_at(ctypes.addressof(out_u32), ctypes.sizeof(out_u32))


_lib.t2d_decode_bc1.argtypes = [U8P, c_long, c_long, U32P]
_lib.t2d_decode_bc1.restype  = c_int
_lib.t2d_decode_bc3.argtypes = [U8P, c_long, c_long, U32P]
_lib.t2d_decode_bc3.restype  = c_int

for name in ["bc4","bc5","bc6","bc7","atc_rgb4","atc_rgba8"]:
    fn = getattr(_lib, f"t2d_decode_{name}")
    fn.argtypes = [U8P, c_uint32, c_uint32, U32P]
    fn.restype  = c_int

for name in ["etc1","etc2","etc2a1","etc2a8","eacr","eacr_signed","eacrg","eacrg_signed"]:
    fn = getattr(_lib, f"t2d_decode_{name}")
    fn.argtypes = [U8P, c_long, c_long, U32P]
    fn.restype  = c_int

_lib.t2d_decode_astc.argtypes = [U8P, c_long, c_long, c_int, c_int, U32P]
_lib.t2d_decode_astc.restype  = c_int

_lib.t2d_decode_pvrtc.argtypes = [U8P, c_long, c_long, U32P, c_int]
_lib.t2d_decode_pvrtc.restype  = c_int


_lib.t2d_unpack_crunch.argtypes = [U8P, c_uint32, c_uint32, POINTER(U8P), POINTER(c_uint32)]
_lib.t2d_unpack_crunch.restype  = c_int
_lib.t2d_unpack_unity_crunch.argtypes = [U8P, c_uint32, c_uint32, POINTER(U8P), POINTER(c_uint32)]
_lib.t2d_unpack_unity_crunch.restype  = c_int
_lib.t2d_free.argtypes = [c_void_p]
_lib.t2d_free.restype  = None

def _decode(fn_name: str, data: bytes, w: int, h: int, use_u32_dims=False) -> bytes:
    _, ptr = _u8buf(data)
    out = _out_u32(w, h)
    fn = getattr(_lib, fn_name)
    ok = fn(ptr, (c_uint32(w) if use_u32_dims else c_long(w)),
            (c_uint32(h) if use_u32_dims else c_long(h)),
            out)
    if not ok:
        raise RuntimeError("Decoding failed")
    return _bytes_from_u32(out)
