from __future__ import annotations

import contextlib
import ctypes
import ctypes.util
import os
import re
import struct
from typing import Dict, List, NamedTuple, Optional, Tuple


NONE, PCM8, PCM16, PCM24, PCM32, PCMFLOAT, GCADPCM, IMAADPCM = 0, 1, 2, 3, 4, 5, 6, 7
VAG, HEVAG, XMA, MPEG, CELT, AT9, XWMA, VORBIS = 8, 9, 10, 11, 12, 13, 14, 15

FORMAT_NAMES = {
    0: "None", 1: "PCM8", 2: "PCM16", 3: "PCM24", 4: "PCM32", 5: "PCM float",
    6: "GC ADPCM", 7: "IMA ADPCM", 8: "VAG", 9: "HEVAG", 10: "XMA", 11: "MP3",
    12: "CELT", 13: "AT9", 14: "XWMA", 15: "Vorbis",
}

_FREQ_CODES = {1: 8000, 2: 11000, 3: 11025, 4: 16000, 5: 22050, 6: 24000,
               7: 32000, 8: 44100, 9: 48000}
_FREQ_TO_CODE = {v: k for k, v in _FREQ_CODES.items()}

_CHUNK_CHANNELS, _CHUNK_FREQUENCY = 1, 2


class FsbSample(NamedTuple):
    name: str
    frequency: int
    channels: int
    samples: int
    data: bytes


class Fsb(NamedTuple):
    mode: int
    samples: List[FsbSample]


class AudioResult(NamedTuple):
    data: bytes
    ext: str
    channels: int
    frequency: int
    length: float
    format: str
    note: str


def _bits(val: int, start: int, length: int) -> int:
    return (val >> start) & ((1 << length) - 1)


def parse_fsb5(buf: bytes) -> Fsb:
    if buf[:4] != b"FSB5":
        raise ValueError("Not an FSB5 container")
    version, num, sh_size, name_size, data_size, mode = struct.unpack_from("<6I", buf, 4)
    pos = 60
    if version == 0:
        pos += 4
    header_size = pos

    raw_samples = []
    for _ in range(num):
        (raw,) = struct.unpack_from("<Q", buf, pos)
        pos += 8
        nxt = _bits(raw, 0, 1)
        freq_code = _bits(raw, 1, 4)
        channels = _bits(raw, 5, 1) + 1
        offset = _bits(raw, 6, 28) * 16
        count = _bits(raw, 34, 30)
        freq = _FREQ_CODES.get(freq_code, 0)
        while nxt:
            (chunk,) = struct.unpack_from("<I", buf, pos)
            pos += 4
            nxt = _bits(chunk, 0, 1)
            size = _bits(chunk, 1, 24)
            ctype = _bits(chunk, 25, 7)
            payload = buf[pos:pos + size]
            pos += size
            if ctype == _CHUNK_FREQUENCY and size >= 4:
                freq = struct.unpack("<I", payload[:4])[0]
            elif ctype == _CHUNK_CHANNELS and size >= 1:
                channels = payload[0]
        raw_samples.append([freq, channels, offset, count])

    names = [f"{i:04d}" for i in range(num)]
    if name_size:
        nt = header_size + sh_size
        offs = struct.unpack_from(f"<{num}I", buf, nt)
        for i, o in enumerate(offs):
            end = buf.index(b"\x00", nt + o)
            names[i] = buf[nt + o:end].decode("utf-8", "replace")

    data_start = header_size + sh_size + name_size
    samples: List[FsbSample] = []
    for i, (freq, channels, offset, count) in enumerate(raw_samples):
        end = raw_samples[i + 1][2] if i + 1 < num else data_size
        samples.append(FsbSample(names[i], freq, channels, count,
                                 bytes(buf[data_start + offset:data_start + end])))
    return Fsb(mode, samples)


def make_wav(pcm: bytes, channels: int, rate: int, bits: int, is_float: bool = False) -> bytes:
    fmt_tag = 3 if is_float else 1
    block = channels * bits // 8
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, fmt_tag, channels, rate, rate * block, block, bits)
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm


def build_fsb5_pcm16(pcm: bytes, channels: int, rate: int) -> bytes:
    if channels not in (1, 2):
        raise ValueError("Only mono and stereo audio can be stored (got %d channels)" % channels)
    frames = len(pcm) // (2 * channels)
    pcm = pcm[:frames * 2 * channels]

    code = _FREQ_TO_CODE.get(rate, 0)
    chunks = b""
    next_chunk = 0
    if code == 0:
        next_chunk = 1
        chunks = struct.pack("<I", 1 | (4 << 1) | (_CHUNK_FREQUENCY << 25)) + struct.pack("<I", rate)
    sample_header = next_chunk | (code << 1) | ((channels - 1) << 5) | (0 << 6) | (frames << 34)
    sh = struct.pack("<Q", sample_header) + chunks

    header_size = 60
    pad = (-(header_size + len(sh))) % 32
    sh += b"\x00" * pad
    data = pcm + b"\x00" * ((-len(pcm)) % 16)

    header = b"FSB5" + struct.pack("<6I", 1, 1, len(sh), 0, len(data), PCM16)
    header += b"\x00" * 8 + b"\x00" * 16 + b"\x00" * 8
    assert len(header) == header_size
    return header + sh + data


def _vorbis_lib_path() -> Optional[str]:
    import uabe_native

    for path in uabe_native._candidates("Vorbis"):
        if os.path.exists(path):
            return path
    return None


@contextlib.contextmanager
def _redirect_vorbis_libs():
    path = _vorbis_lib_path()
    if path is None:
        raise RuntimeError("UABEVorbis framework not found (libogg/libvorbis are not bundled).")

    def remap(name):
        if isinstance(name, str) and re.search(r"vorbis|ogg", os.path.basename(name).lower()) \
                and name != path:
            return path
        return name

    orig_cdll = ctypes.CDLL
    orig_find = ctypes.util.find_library
    orig_load = ctypes.cdll.LoadLibrary

    class _Redirect(orig_cdll):
        def __init__(self, name, *a, **k):
            super().__init__(remap(name), *a, **k)

    def find(name):
        r = orig_find(name)
        return path if re.search(r"vorbis|ogg", name or "") else r

    ctypes.CDLL = _Redirect
    ctypes.util.find_library = find
    ctypes.cdll.LoadLibrary = lambda name: _Redirect(name)
    try:
        yield
    finally:
        ctypes.CDLL = orig_cdll
        ctypes.util.find_library = orig_find
        ctypes.cdll.LoadLibrary = orig_load


def ogg_to_wav(ogg: bytes) -> bytes:
    import uabe_native

    lib = uabe_native.load("Vorbis")
    lib.uabe_vorbis_info.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.POINTER(ctypes.c_int),
                                     ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_longlong)]
    lib.uabe_vorbis_info.restype = ctypes.c_int
    lib.uabe_vorbis_decode.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_void_p, ctypes.c_longlong]
    lib.uabe_vorbis_decode.restype = ctypes.c_longlong
    channels, rate, frames = ctypes.c_int(), ctypes.c_long(), ctypes.c_longlong()
    if lib.uabe_vorbis_info(ogg, len(ogg), ctypes.byref(channels), ctypes.byref(rate), ctypes.byref(frames)) != 0:
        raise ValueError("Cannot read the Ogg stream")
    if frames.value <= 0 or channels.value <= 0:
        raise ValueError("Empty Ogg stream")
    buf = ctypes.create_string_buffer(frames.value * channels.value * 2)
    got = lib.uabe_vorbis_decode(ogg, len(ogg), buf, frames.value)
    if got <= 0:
        raise ValueError("Ogg decoding failed")
    return make_wav(buf.raw[:got * channels.value * 2], channels.value, rate.value, 16)


def _vorbis_to_ogg(fsb_bytes: bytes, index: int) -> bytes:
    with _redirect_vorbis_libs():
        import fsb5

        bank = fsb5.FSB5(fsb_bytes)
        return bytes(bank.rebuild_sample(bank.samples[index]))


def decode_audio(raw: bytes, name: str = "audio", subsound: int = 0,
                 hint_channels: int = 0, hint_rate: int = 0) -> AudioResult:
    if not raw:
        raise ValueError("The AudioClip has no audio data (is the .resS stream missing?).")

    head = raw[:4]
    if head == b"OggS":
        return AudioResult(raw, "ogg", hint_channels, hint_rate, 0.0, "Vorbis", "")
    if head == b"RIFF":
        return AudioResult(raw, "wav", hint_channels, hint_rate, 0.0, "WAV", "")
    if head[:3] == b"ID3" or (len(raw) > 1 and raw[0] == 0xFF and raw[1] & 0xE0 == 0xE0):
        return AudioResult(raw, "mp3", hint_channels, hint_rate, 0.0, "MP3", "")
    if head != b"FSB5":
        return AudioResult(raw, "bin", hint_channels, hint_rate, 0.0, "Unknown",
                           "Unknown audio container - exported raw.")

    fsb = parse_fsb5(raw)
    if not fsb.samples:
        raise ValueError("The FSB5 container is empty.")
    idx = subsound if 0 <= subsound < len(fsb.samples) else 0
    s = fsb.samples[idx]
    length = (s.samples / s.frequency) if s.frequency else 0.0
    fmt_name = FORMAT_NAMES.get(fsb.mode, str(fsb.mode))

    def result(data, ext, note=""):
        return AudioResult(data, ext, s.channels, s.frequency, length, fmt_name, note)

    if fsb.mode in (PCM8, PCM16, PCM24, PCM32, PCMFLOAT):
        bits = {PCM8: 8, PCM16: 16, PCM24: 24, PCM32: 32, PCMFLOAT: 32}[fsb.mode]
        return result(make_wav(s.data, s.channels, s.frequency, bits, fsb.mode == PCMFLOAT), "wav")
    if fsb.mode == MPEG:
        return result(s.data, "mp3")
    if fsb.mode == VORBIS:
        try:
            return result(_vorbis_to_ogg(raw, idx), "ogg")
        except Exception as exc:
            return result(raw, "fsb", f"Vorbis could not be rebuilt ({exc}). Exported the raw FSB5 bank instead.")
    return result(raw, "fsb",
                  f"{fmt_name} is not decodable on iOS. Exported the raw FSB5 bank "
                  "(open it with a desktop tool such as fsb_aud_extr or vgmstream).")
