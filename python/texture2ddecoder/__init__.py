__version__ = "ios-ctypes"

from ._native import _decode, _lib, _u8buf, _out_u32, _bytes_from_u32
from ctypes import c_uint32, POINTER, byref

def decode_bc1(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_bc1", data, w, h)
def decode_bc3(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_bc3", data, w, h)

def decode_bc4(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_bc4", data, w, h, use_u32_dims=True)
def decode_bc5(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_bc5", data, w, h, use_u32_dims=True)
def decode_bc6(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_bc6", data, w, h, use_u32_dims=True)
def decode_bc7(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_bc7", data, w, h, use_u32_dims=True)

def decode_atc_rgb4(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_atc_rgb4", data, w, h, use_u32_dims=True)
def decode_atc_rgba8(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_atc_rgba8", data, w, h, use_u32_dims=True)

def decode_etc1(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_etc1", data, w, h)
def decode_etc2(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_etc2", data, w, h)
def decode_etc2a1(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_etc2a1", data, w, h)
def decode_etc2a8(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_etc2a8", data, w, h)

def decode_eacr(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_eacr", data, w, h)
def decode_eacr_signed(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_eacr_signed", data, w, h)
def decode_eacrg(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_eacrg", data, w, h)
def decode_eacrg_signed(data: bytes, w: int, h: int) -> bytes: return _decode("t2d_decode_eacrg_signed", data, w, h)

def decode_astc(data: bytes, w: int, h: int, bw: int, bh: int) -> bytes:
    from ._native import _u8buf, _out_u32, _bytes_from_u32
    from ctypes import c_long, c_int
    _, ptr = _u8buf(data)
    out = _out_u32(w, h)
    ok = _lib.t2d_decode_astc(ptr, c_long(w), c_long(h), c_int(bw), c_int(bh), out)
    if not ok:
        raise RuntimeError("Decoding failed")
    return _bytes_from_u32(out)

def decode_pvrtc(data: bytes, w: int, h: int, is2bpp: bool=False) -> bytes:
    from ._native import _u8buf, _out_u32, _bytes_from_u32
    from ctypes import c_long, c_int
    _, ptr = _u8buf(data)
    out = _out_u32(w, h)
    ok = _lib.t2d_decode_pvrtc(ptr, c_long(w), c_long(h), out, c_int(1 if is2bpp else 0))
    if not ok:
        raise RuntimeError("Decoding failed")
    return _bytes_from_u32(out)

def unpack_crunch(data: bytes, level_index: int=0) -> bytes:
    from ._native import _u8buf, _lib
    from ctypes import c_uint32, c_uint8, POINTER, byref
    buf, ptr = _u8buf(data)
    out_ptr = POINTER(c_uint8)()
    out_size = c_uint32(0)
    ok = _lib.t2d_unpack_crunch(ptr, c_uint32(len(data)), c_uint32(level_index), byref(out_ptr), byref(out_size))
    if not ok:
        raise RuntimeError("Unpacking failed")
    try:
        return ctypes.string_at(out_ptr, out_size.value)
    finally:
        _lib.t2d_free(out_ptr)

def unpack_unity_crunch(data: bytes, level_index: int=0) -> bytes:
    from ._native import _u8buf, _lib
    from ctypes import c_uint32, c_uint8, POINTER, byref
    buf, ptr = _u8buf(data)
    out_ptr = POINTER(c_uint8)()
    out_size = c_uint32(0)
    ok = _lib.t2d_unpack_unity_crunch(ptr, c_uint32(len(data)), c_uint32(level_index), byref(out_ptr), byref(out_size))
    if not ok:
        raise RuntimeError("Unpacking failed")
    try:
        return ctypes.string_at(out_ptr, out_size.value)
    finally:
        _lib.t2d_free(out_ptr)
