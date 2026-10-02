from __future__ import annotations

import ctypes
import os
import sys

_cache: dict[str, ctypes.CDLL] = {}


def _candidates(name: str):
    override = os.environ.get(f"UABE_NATIVE_{name.upper()}")
    if override:
        yield override
    bundle = os.environ.get("UABE_BUNDLE_PATH")
    if bundle:
        yield os.path.join(bundle, "Frameworks", f"UABE{name}.framework", f"UABE{name}")

    here = os.path.dirname(os.path.abspath(__file__))
    for ext in ("dylib", "so"):
        yield os.path.join(here, "_native", f"libUABE{name}.{ext}")


def load(name: str) -> ctypes.CDLL:
    lib = _cache.get(name)
    if lib is not None:
        return lib
    tried = []
    for path in _candidates(name):
        tried.append(path)
        if os.path.exists(path):
            lib = ctypes.CDLL(path)
            _cache[name] = lib
            return lib
    raise OSError(
        f"Native library UABE{name} not found (platform={sys.platform}). Tried:\n  "
        + "\n  ".join(tried)
    )
