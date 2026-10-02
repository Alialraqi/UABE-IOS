from __future__ import annotations

__version__ = "0.0-ios-stub"

_MSG = "Audio extraction is not available in the iOS build (FMOD is not bundled)."


def _unavailable(*_a, **_k):
    raise NotImplementedError(_MSG)


bootstrap = get_pyfmodex_system_instance = raw_to_wav = sound_to_wav = subsound_to_wav = _unavailable

__all__ = ["bootstrap", "get_pyfmodex_system_instance", "raw_to_wav", "sound_to_wav",
           "subsound_to_wav", "__version__"]
