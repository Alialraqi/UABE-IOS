__version__ = "ios-vendored-1.0"

from ._etcpak import *


compress_to_dxt1 = compress_bc1
compress_to_dxt1_dither = compress_bc1_dither
compress_to_dxt5 = compress_bc3
compress_to_etc1 = compress_etc1_rgb
compress_to_etc1_dither = compress_etc1_rgb_dither
compress_to_etc2 = compress_etc2_rgb
compress_to_etc2_rgba = compress_etc2_rgba
decode_dxt1 = decompress_bc1
decode_dxt5 = decompress_bc3
decode_etc_rgba = decompress_etc2_rgba


def compress_to_etc1_alpha(data: bytes, width: int, height: int) -> bytes:
    raise NotImplementedError("This function was removed in etcpak 0.9.9")


def compress_to_etc2_alpha(data: bytes, width: int, height: int) -> bytes:
    raise NotImplementedError("This function was removed in etcpak 0.9.9")


def set_use_heuristics(use_heuristics: bool) -> None:
    raise NotImplementedError("This function was removed in etcpak 0.9.9")


def get_use_multithreading() -> bool:
    raise NotImplementedError("This function was removed in etcpak 0.9.9")


__all__ = (
    "__version__",
    "compress_bc1",
    "compress_bc1_dither",
    "compress_bc3",
    "compress_bc4",
    "compress_bc5",
    "compress_bc7",
    "compress_etc1_rgb",
    "compress_etc1_rgb_dither",
    "compress_etc2_rgb",
    "compress_etc2_rgba",
    "compress_eac_r",
    "compress_eac_rg",
    "decompress_etc1_rgb",
    "decompress_etc2_rgb",
    "decompress_etc2_rgba",
    "decompress_etc2_r11",
    "decompress_etc2_rg11",
    "decompress_bc1",
    "decompress_bc3",
    "decompress_bc4",
    "decompress_bc5",
    "decompress_bc7",
    "BC7CompressBlockParams",

    "compress_to_dxt1",
    "compress_to_dxt1_dither",
    "compress_to_dxt5",
    "compress_to_etc1",
    "compress_to_etc1_dither",
    "compress_to_etc2",
    "compress_to_etc2_rgba",
    "decode_dxt1",
    "decode_dxt5",
    "decode_etc_rgba",
    "compress_to_etc1_alpha",
    "compress_to_etc2_alpha",
    "set_use_heuristics",
    "get_use_multithreading",
)
