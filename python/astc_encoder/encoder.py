from __future__ import annotations

import os
import ctypes
from ctypes import c_int, c_float, c_void_p, c_uint8, POINTER
from typing import Optional

from .enum import ASTCProfile, ASTCType, ASTCConfigFlags


def _load_lib() -> ctypes.CDLL:
    import uabe_native

    return uabe_native.load("Astc")


_LIB = _load_lib()

_LIB.astc_create.restype = c_void_p
_LIB.astc_create.argtypes = [c_int, c_int, c_int, c_int, c_float, c_int]

_LIB.astc_destroy.restype = None
_LIB.astc_destroy.argtypes = [c_void_p]

_LIB.astc_compress_rgba8.restype = c_int
_LIB.astc_compress_rgba8.argtypes = [
    c_void_p,
    POINTER(c_uint8), c_int, c_int,
    POINTER(c_uint8), c_int,
]

_LIB.astc_decompress_rgba8.restype = c_int
_LIB.astc_decompress_rgba8.argtypes = [
    c_void_p,
    POINTER(c_uint8), c_int,
    c_int, c_int,
    POINTER(c_uint8), c_int,
]


class ASTCError(RuntimeError):
    pass


class ASTCSwizzle:

    __slots__ = ("r", "g", "b", "a")

    def __init__(self, r: int = 0, g: int = 1, b: int = 2, a: int = 3):
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)
        self.a = int(a)

    @classmethod
    def from_str(cls, s: str) -> "ASTCSwizzle":

        s = (s or "").strip().lower()
        if s == "rgba":
            return cls(0, 1, 2, 3)
        if s == "bgra":
            return cls(2, 1, 0, 3)
        if s == "argb":
            return cls(1, 2, 3, 0)
        if s == "abgr":
            return cls(3, 2, 1, 0)

        return cls(0, 1, 2, 3)


class ASTCImage:

    __slots__ = ("data_type", "dim_x", "dim_y", "dim_z", "data")

    def __init__(
            self,
            data_type: int,
            dim_x: int,
            dim_y: int,
            dim_z: int = 1,
            data: Optional[bytes] = None,
    ):
        self.data_type = int(data_type)
        self.dim_x = int(dim_x)
        self.dim_y = int(dim_y)
        self.dim_z = int(dim_z)

        if data is not None:
            if not isinstance(data, (bytes, bytearray, memoryview)):
                raise TypeError("ASTCImage data must be bytes-like")
            self.data = bytes(data)
        else:
            self.data = None

    @property
    def width(self) -> int:
        return self.dim_x

    @property
    def height(self) -> int:
        return self.dim_y

    @property
    def depth(self) -> int:
        return self.dim_z


class ASTCConfig:

    __slots__ = ("profile", "block_x", "block_y", "block_z", "quality", "flags")

    def __init__(
            self,
            profile: int,
            block_x: int,
            block_y: int,
            *,
            block_z: int = 1,
            quality: float = 100,
            flags: int = ASTCConfigFlags.NONE,
            **_ignored,
    ):
        self.profile = int(profile)
        self.block_x = int(block_x)
        self.block_y = int(block_y)
        self.block_z = int(block_z)
        self.quality = float(quality)
        self.flags = int(flags)


class ASTCContext:

    __slots__ = ("config", "_ctx")

    def __init__(self, config: ASTCConfig):
        self.config = config

        quality = float(config.quality)


        if quality < 0:
            quality = 0.0
        if quality > 1000:
            quality = 1000.0

        self._ctx = _LIB.astc_create(
            int(config.profile),
            int(config.block_x),
            int(config.block_y),
            int(config.block_z),
            float(quality),
            int(config.flags),
        )
        if not self._ctx:
            raise ASTCError("astc_create failed")

    def close(self) -> None:
        if self._ctx:
            _LIB.astc_destroy(self._ctx)
            self._ctx = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    @staticmethod
    def _astc_output_size(width: int, height: int, block_x: int, block_y: int) -> int:
        blocks_x = (width + block_x - 1) // block_x
        blocks_y = (height + block_y - 1) // block_y
        return blocks_x * blocks_y * 16

    def compress(self, image: ASTCImage, swizzle: Optional[ASTCSwizzle] = None) -> bytes:

        if image.data_type != ASTCType.U8:
            raise ASTCError(f"Unsupported ASTCType={image.data_type}; Android backend supports U8 only")

        if image.data is None:
            raise ASTCError("ASTCImage.data is None; cannot compress")

        w, h = int(image.dim_x), int(image.dim_y)

        expected = w * h * 4
        if len(image.data) != expected:
            raise ASTCError(f"RGBA size mismatch: got {len(image.data)} expected {expected}")

        out_size = self._astc_output_size(w, h, self.config.block_x, self.config.block_y)

        out = (c_uint8 * out_size)()
        inp = (c_uint8 * len(image.data)).from_buffer_copy(image.data)

        rc = _LIB.astc_compress_rgba8(self._ctx, inp, w, h, out, out_size)
        if rc != 0:
            raise ASTCError(f"compress failed rc={rc}")

        return bytes(out)

    def decompress(self, data: bytes, image: ASTCImage, swizzle: Optional[ASTCSwizzle] = None) -> None:

        if image.data_type != ASTCType.U8:
            raise ASTCError(f"Unsupported ASTCType={image.data_type}; Android backend supports U8 only")

        w, h = int(image.dim_x), int(image.dim_y)
        out_size = w * h * 4

        out = (c_uint8 * out_size)()
        inp = (c_uint8 * len(data)).from_buffer_copy(data)

        rc = _LIB.astc_decompress_rgba8(self._ctx, inp, len(data), w, h, out, out_size)
        if rc != 0:
            raise ASTCError(f"decompress failed rc={rc}")

        image.data = bytes(out)
