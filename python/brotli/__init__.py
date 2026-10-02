from __future__ import annotations

import ctypes
import sys

__version__ = "0.0-ios-shim"

_COMPRESSION_BROTLI = 0xB02
_ENCODE, _DECODE = 0, 1
_FINALIZE = 1
_OK, _END, _ERROR = 0, 1, -1


class error(Exception):
    pass


class _Stream(ctypes.Structure):
    _fields_ = [
        ("dst_ptr", ctypes.POINTER(ctypes.c_uint8)),
        ("dst_size", ctypes.c_size_t),
        ("src_ptr", ctypes.POINTER(ctypes.c_uint8)),
        ("src_size", ctypes.c_size_t),
        ("state", ctypes.c_void_p),
    ]


_lib = None
if sys.platform == "darwin":
    try:
        _lib = ctypes.CDLL("/usr/lib/libcompression.dylib")
        _lib.compression_stream_init.argtypes = [ctypes.POINTER(_Stream), ctypes.c_int, ctypes.c_int]
        _lib.compression_stream_process.argtypes = [ctypes.POINTER(_Stream), ctypes.c_int]
        _lib.compression_stream_destroy.argtypes = [ctypes.POINTER(_Stream)]
    except Exception:
        _lib = None


def _run(op: int, data: bytes) -> bytes:
    if _lib is None:
        raise error("Brotli needs Apple's libcompression (iOS 15+ / macOS 12+)")
    st = _Stream()
    if _lib.compression_stream_init(ctypes.byref(st), op, _COMPRESSION_BROTLI) != _OK:
        raise error("compression_stream_init failed")
    try:
        src = (ctypes.c_uint8 * max(len(data), 1)).from_buffer_copy(data or b"\0")
        chunk = 1 << 20
        dst = (ctypes.c_uint8 * chunk)()
        st.src_ptr = ctypes.cast(src, ctypes.POINTER(ctypes.c_uint8))
        st.src_size = len(data)
        out = bytearray()
        while True:
            st.dst_ptr = ctypes.cast(dst, ctypes.POINTER(ctypes.c_uint8))
            st.dst_size = chunk
            status = _lib.compression_stream_process(ctypes.byref(st), _FINALIZE)
            produced = chunk - st.dst_size
            out += bytes(dst[:produced])
            if status == _END:
                break
            if status == _ERROR:
                raise error("brotli stream error")
        return bytes(out)
    finally:
        _lib.compression_stream_destroy(ctypes.byref(st))


def decompress(string, *args, **kwargs) -> bytes:
    return _run(_DECODE, bytes(string))


def compress(string, mode=0, quality=11, lgwin=22, lgblock=0) -> bytes:
    return _run(_ENCODE, bytes(string))
