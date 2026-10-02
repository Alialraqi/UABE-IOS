from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional


sys.setrecursionlimit(6000)

_sessions: Dict[str, "Session"] = {}


class Session:
    def __init__(self, env: Any, path: str):
        self.env = env
        self.path = path
        self.dirty = False
        self.audio_cache: Dict[int, Any] = {}
        self.audio_override: Dict[int, bytes] = {}
        self.pending_audio: Dict[int, str] = {}


def _unitypy():
    import UnityPy

    return UnityPy


def _pil_image():
    from PIL import Image

    return Image


def _tname(obj: Any) -> str:
    try:
        return str(obj.type.name)
    except Exception:
        try:
            s = str(obj.type)
            if s.startswith("ClassIDType."):
                s = s[len("ClassIDType."):]
            return s or "Unknown"
        except Exception:
            return "Unknown"


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _try_size(obj: Any) -> Optional[int]:
    for a in ("byte_size", "size", "data_size", "m_Size"):
        try:
            v = getattr(obj, a)
            if v is not None and int(v) >= 0:
                return int(v)
        except Exception:
            pass
    return None


def _try_container(obj: Any) -> Optional[str]:
    try:
        c = obj.container
        if c:
            return str(c)
    except Exception:
        pass
    return None


def _extract_name(obj: Any) -> str:
    try:
        peek = getattr(obj, "peek_name", None)
        if peek is not None:
            n = peek()
            return str(n) if n else ""
        parsed = obj.parse_as_object()
        n = getattr(parsed, "m_Name", None)
        return str(n) if n else ""
    except Exception:
        return ""


def _normalize_export_name(s: Optional[str]) -> str:
    return (s or "").strip().replace(" ", "_").replace("-", "_")


def _sanitize_filename(name: Optional[str], fallback: str) -> str:
    n = fallback if not name or not name.strip() else name.strip()
    for ch in '<>:"/\\|?*\n\r\t':
        n = n.replace(ch, "_")
    n = n.rstrip(". ").strip()
    return n or fallback


def _archive_tag(obj: Any) -> str:
    try:
        af = obj.assets_file
        if af is None:
            return ""
        name = getattr(af, "name", None) or ""
        if not name:
            f = getattr(af, "file", None)
            name = getattr(f, "name", "") if f is not None else ""
        if name:
            base = os.path.basename(str(name))
            dot = base.rfind(".")
            if dot >= 0:
                base = base[:dot]
            return _normalize_export_name(base)
    except Exception:
        pass
    return ""


def _export_base_name(obj: Any, idx: int) -> str:
    obj_name = _normalize_export_name(_extract_name(obj))
    arch = _archive_tag(obj)
    pid = _safe_int(getattr(obj, "path_id", idx), idx)
    if obj_name and arch:
        base = f"{obj_name}_{arch}"
    elif obj_name:
        base = f"{obj_name}_{pid}"
    else:
        base = f"{_normalize_export_name(_tname(obj))}_{pid}"
    return _sanitize_filename(base, str(pid))


def _keep_archive_key(k: str) -> bool:
    if not k:
        return False
    if k.startswith("/") or k.startswith("\\") or ":/" in k or ":\\" in k:
        return False
    if k.startswith("CAB-"):
        return True
    if k.endswith((".resS", ".resource", ".resources")):
        return True
    return k.startswith("archive:/")


def _archive_names(env: Any) -> List[str]:
    names: List[str] = []

    def add_from(mapping: Any) -> None:
        try:
            for k in list(mapping.keys()):
                ks = str(k)
                if _keep_archive_key(ks) and ks not in names:
                    names.append(ks)
        except Exception:
            pass

    add_from(getattr(env, "files", None) or {})
    bf = getattr(env, "file", None)
    if bf is not None:
        add_from(getattr(bf, "files", None) or {})
    return names


def _mime_for(t: str) -> str:
    return {"TextAsset": "text/plain", "Texture2D": "image/png", "AudioClip": "audio/*"}.get(t, "application/json")


def _extension_for(obj: Any, t: str) -> str:
    if t == "TextAsset":
        name = _try_container(obj) or f"textasset_{_safe_int(getattr(obj, 'path_id', 0))}"
        if not name.endswith((".txt", ".bytes", ".json", ".lua")):
            return "txt"
        dot = name.rfind(".")
        return name[dot + 1:] if dot >= 0 else ""
    return {"Texture2D": "png", "Mesh": "obj"}.get(t, "json")


def _json_default(o: Any):
    if isinstance(o, (bytes, bytearray, memoryview)):
        return list(bytes(o))
    return str(o)


def _get_object(env: Any, idx: int) -> Any:
    objects = list(env.objects)
    if idx < 0 or idx >= len(objects):
        raise IndexError(f"Index out of range: {idx} / {len(objects)}")
    return objects[idx]


def _require(session_id: str) -> Session:
    s = _sessions.get(session_id)
    if s is None:
        raise KeyError(f"Session not found: {session_id}")
    return s


def _write_bytes(path: str, data: bytes) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def _file_dicts(obj: Any, env: Any) -> List[dict]:
    found: List[dict] = []
    parent = getattr(getattr(obj, "assets_file", None), "parent", None)
    for holder in (parent, getattr(env, "file", None), env):
        files = getattr(holder, "files", None)
        if isinstance(files, dict) and not any(files is d for d in found):
            found.append(files)
    cabs = getattr(env, "cabs", None)
    if isinstance(cabs, dict) and not any(cabs is d for d in found):
        found.append(cabs)
    return found


def _base(name: Any) -> str:
    return os.path.basename(str(name).replace("\\", "/")).lower()


def _find_stream(obj: Any, env: Any, src: str):
    target = _base(src)
    for files in _file_dicts(obj, env):
        for key in list(files.keys()):
            if _base(key) == target:
                return files, key
    return None, None


def _entry_view(entry: Any) -> memoryview:
    for attr in ("bytes", "data"):
        value = getattr(entry, attr, None)
        if value is not None:
            try:
                return memoryview(value)
            except TypeError:
                pass
    try:
        entry.Position = 0
        length = getattr(entry, "Length", None)
        if length is None:
            length = len(entry)
        return memoryview(bytes(entry.read_bytes(int(length))))
    except Exception as exc:
        raise RuntimeError(f"Cannot read stream data ({type(entry).__name__}): {exc}") from exc


def _stream_ref(tree: dict):
    res = tree.get("m_Resource")
    if isinstance(res, dict):
        return res.get("m_Source") or "", _safe_int(res.get("m_Offset")), _safe_int(res.get("m_Size")), True
    return tree.get("m_Source") or "", _safe_int(tree.get("m_Offset")), _safe_int(tree.get("m_Size")), False


def _inherit_attrs(old: Any, new: Any) -> None:
    try:
        for name, value in vars(old).items():
            if name not in vars(new):
                setattr(new, name, value)
    except TypeError:
        pass
    for name in ("flags", "name", "path"):
        if hasattr(old, name) and not hasattr(new, name):
            setattr(new, name, getattr(old, name))
    if not hasattr(new, "flags"):
        new.flags = 0


def _audio_raw(obj: Any, env: Any, override: Optional[bytes] = None):
    tree = obj.parse_as_dict()
    if override:
        return bytes(override), tree
    inline = tree.get("m_AudioData")
    if inline:
        return bytes(inline), tree
    src, off, size, _ = _stream_ref(tree)
    if not src:
        return b"", tree
    files, key = _find_stream(obj, env, src)
    if files is not None:
        view = _entry_view(files[key])
        end = off + size if size else len(view)
        return bytes(view[off:end]), tree
    try:
        from UnityPy.helpers.ResourceReader import get_resource_data

        return bytes(get_resource_data(src, obj.assets_file, off, size)), tree
    except Exception as exc:
        raise RuntimeError(
            f"The audio stream '{src}' is not inside this file, so it cannot be read: {exc}"
        ) from exc


def _audio_decode(session: "Session", idx: int):
    cached = session.audio_cache.get(idx)
    if cached is not None:
        return cached
    import uabe_audio

    obj = _get_object(session.env, idx)
    raw, tree = _audio_raw(obj, session.env, session.audio_override.get(idx))
    result = uabe_audio.decode_audio(
        raw,
        name=str(tree.get("m_Name", "audio")),
        subsound=_safe_int(tree.get("m_SubsoundIndex", 0)),
        hint_channels=_safe_int(tree.get("m_Channels", 0)),
        hint_rate=_safe_int(tree.get("m_Frequency", 0)),
    )
    session.audio_cache[idx] = result
    return result


def _export_text_asset(obj: Any) -> bytes:
    parsed = obj.parse_as_object()
    script = getattr(parsed, "m_Script", None)
    if isinstance(script, str) and script:
        return script.encode("utf-8", "surrogateescape")
    if isinstance(script, (bytes, bytearray)) and script:
        return bytes(script)
    raw = getattr(parsed, "m_Bytes", None)
    return bytes(raw) if raw else b""


def _export_texture(obj: Any) -> bytes:
    tex = obj.parse_as_object()
    image = tex.image
    if image is None:
        return b""
    bio = io.BytesIO()
    image.save(bio, format="PNG")
    return bio.getvalue()


def _export_mesh(obj: Any) -> bytes:
    mesh = obj.parse_as_object()
    try:
        text = mesh.export()
    except AttributeError:
        from UnityPy.export import MeshExporter

        text = MeshExporter.export_mesh(mesh, "obj")
    if isinstance(text, bytes):
        return text
    return (text or "").encode("utf-8")


def _export_typetree_json(obj: Any) -> bytes:
    try:
        d = obj.parse_as_dict()
        return json.dumps(d, ensure_ascii=False, indent=2, default=_json_default).encode("utf-8")
    except Exception:
        pass
    raw = obj.get_raw_data()
    return bytes(raw) if raw else b""


def get_object_bytes(obj: Any) -> bytes:
    t = _tname(obj)
    if t == "TextAsset":
        return _export_text_asset(obj)
    if t == "Texture2D":
        return _export_texture(obj)
    if t == "Mesh":
        return _export_mesh(obj)
    return _export_typetree_json(obj)


def _import_typetree(obj: Any, data: bytes) -> None:
    text = data.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("Input JSON is empty.")
    tree = json.loads(text)
    if not isinstance(tree, dict):
        raise ValueError("Typetree JSON must be a JSON object (dict).")
    obj.save_typetree(tree)


def _import_into(obj: Any, data: bytes) -> None:
    t = _tname(obj)
    if t == "Texture2D":
        tex = obj.parse_as_object()
        img = _pil_image().open(io.BytesIO(data))
        img.load()
        tex.image = img
        tex.save()
    elif t == "TextAsset":
        txt = obj.parse_as_object()
        txt.m_Script = data.decode("utf-8", errors="surrogateescape")
        txt.save()
    elif t == "Mesh":
        raise ValueError("export_mesh not supported for type: Mesh (import is not available)")
    else:
        _import_typetree(obj, data)


def ping(_: dict) -> dict:
    info: Dict[str, Any] = {"python": sys.version.split()[0], "platform": sys.platform}
    for name in ("UnityPy", "PIL", "attr", "fsspec"):
        try:
            mod = __import__(name)
            info[name] = str(getattr(mod, "__version__", "ok"))
        except Exception as exc:
            info[name] = f"MISSING: {exc}"
    try:
        import uabe_native

        for lib in ("T2D", "Etcpak", "Astc", "Vorbis"):
            try:
                uabe_native.load(lib)
                info[f"native_{lib}"] = "ok"
            except Exception as exc:
                info[f"native_{lib}"] = f"MISSING: {exc}"
    except Exception as exc:
        info["native"] = f"MISSING: {exc}"
    for mod in ("texture2ddecoder", "etcpak", "astc_encoder", "lz4.block", "brotli", "uabe_audio", "fsb5"):
        try:
            __import__(mod)
            info[f"py_{mod}"] = "ok"
        except Exception as exc:
            info[f"py_{mod}"] = f"MISSING: {exc}"
    return info


def _describe(env: Any) -> dict:
    items: List[dict] = []
    types: List[str] = []
    for i, obj in enumerate(list(env.objects)):
        t = _tname(obj)
        name = _extract_name(obj)
        items.append({
            "index": i,
            "type": t,
            "id": _safe_int(getattr(obj, "path_id", 0)),
            "bytes": _try_size(obj),
            "name": name or "Unnamed asset",
            "container": _try_container(obj),
        })
        if t.strip() and t.strip() not in types:
            types.append(t.strip())
    return {"archives": _archive_names(env), "objects": items, "types": types}


def open_bundle(p: dict) -> dict:
    path = p["path"]
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input not found: {path}")
    env = _unitypy().load(path)
    sid = uuid.uuid4().hex[:12]
    _sessions[sid] = Session(env, path)
    result = _describe(env)
    result["sessionId"] = sid
    return result


def close_bundle(p: dict) -> dict:
    _sessions.pop(p.get("sessionId", ""), None)
    return {}


def save_bundle(p: dict) -> dict:
    s = _require(p["sessionId"])
    out = p["outPath"]
    env_file = getattr(s.env, "file", None)
    if env_file is None or not hasattr(env_file, "save"):
        raise RuntimeError("save_bundle not supported (env.file missing)")
    data = bytes(env_file.save())
    tmp = out + ".tmp"
    _write_bytes(tmp, data)
    os.replace(tmp, out)
    s.dirty = False
    result: Dict[str, Any] = {"path": out, "bytes": len(data)}
    if p.get("reload"):
        del data
        s.env = _unitypy().load(out)
        s.path = out
        s.audio_cache.clear()
        _verify_pending_audio(s)
        described = _describe(s.env)
        described["sessionId"] = p["sessionId"]
        result["reloaded"] = described
    return result


def set_decrypt_key(p: dict) -> dict:
    _unitypy().set_assetbundle_decrypt_key(p.get("key", ""))
    return {}


def object_info(p: dict) -> dict:
    s = _require(p["sessionId"])
    idx = int(p["idx"])
    obj = _get_object(s.env, idx)
    t = _tname(obj)
    ext = _audio_decode(s, idx).ext if t == "AudioClip" else _extension_for(obj, t)
    return {
        "type": t,
        "filename": _export_base_name(obj, idx),
        "ext": ext,
        "mime": _mime_for(t),
    }


def export_object(p: dict) -> dict:
    s = _require(p["sessionId"])
    obj = _get_object(s.env, int(p["idx"]))
    t = _tname(obj)
    data = _audio_decode(s, int(p["idx"])).data if t == "AudioClip" else get_object_bytes(obj)
    if not data:
        raise ValueError(f"export_object not supported for type: {t}")
    _write_bytes(p["outPath"], data)
    return {"idx": int(p["idx"]), "type": t, "bytes": len(data)}


def get_object_data(p: dict) -> dict:
    s = _require(p["sessionId"])
    idx = int(p["idx"])
    obj = _get_object(s.env, idx)
    t = _tname(obj)
    extra: Dict[str, Any] = {}
    if t == "AudioClip":
        a = _audio_decode(s, idx)
        data = a.data
        extra = {"ext": a.ext, "channels": a.channels, "frequency": a.frequency,
                 "length": a.length, "format": a.format, "note": a.note,
                 "playable": a.ext in ("wav", "mp3"), "preview": False}
        if a.ext == "ogg" and p.get("previewPath"):
            try:
                import uabe_audio

                _write_bytes(p["previewPath"], uabe_audio.ogg_to_wav(a.data))
                extra["preview"] = True
            except Exception:
                extra["preview"] = False
    else:
        data = get_object_bytes(obj)
    _write_bytes(p["outPath"], data)
    kind = {"Texture2D": "image", "Mesh": "mesh", "TextAsset": "text", "AudioClip": "audio"}.get(t, "json")
    result = {
        "idx": idx,
        "type": t,
        "id": _safe_int(getattr(obj, "path_id", 0)),
        "name": _extract_name(obj),
        "kind": kind,
        "bytes": len(data),
    }
    result.update(extra)
    return result


def import_object(p: dict) -> dict:
    s = _require(p["sessionId"])
    obj = _get_object(s.env, int(p["idx"]))
    with open(p["inPath"], "rb") as fh:
        data = fh.read()
    if _tname(obj) == "AudioClip":
        raise ValueError("Use replace_audio for AudioClip objects.")
    _import_into(obj, data)
    s.dirty = True
    s.audio_cache.clear()
    return {}


def replace_audio(p: dict) -> dict:
    import wave

    import uabe_audio

    s = _require(p["sessionId"])
    idx = int(p["idx"])
    obj = _get_object(s.env, idx)
    if _tname(obj) != "AudioClip":
        raise ValueError("Object is not an AudioClip")

    with wave.open(p["inPath"], "rb") as wav:
        channels, width, rate, frames = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        pcm = wav.readframes(frames)
    if width != 2:
        raise ValueError(f"Expected 16-bit PCM WAV, got {width * 8}-bit")
    if frames == 0:
        raise ValueError("The audio file is empty.")

    fsb = uabe_audio.build_fsb5_pcm16(pcm, channels, rate)
    tree = obj.parse_as_dict()
    src, _, _, nested = _stream_ref(tree)

    updates = {
        "m_Channels": channels, "m_Frequency": rate, "m_BitsPerSample": 16,
        "m_Length": frames / float(rate), "m_CompressionFormat": 0,
        "m_IsTrackerFormat": False, "m_SubsoundIndex": 0,
        "m_PreloadAudioData": True, "m_LoadType": 0,
    }
    for key, value in updates.items():
        if key in tree:
            tree[key] = value

    if src:
        files, key = _find_stream(obj, s.env, src)
        if files is None:
            raise ValueError(
                f"The audio stream '{src}' is stored outside this file, so this clip cannot be replaced here."
            )
        old = _entry_view(files[key])
        offset = (len(old) + 31) // 32 * 32
        merged = bytearray(offset + len(fsb))
        merged[:len(old)] = old
        merged[offset:] = fsb
        try:
            from UnityPy.streams import EndianBinaryReader
        except ImportError:
            from UnityPy.streams.EndianBinaryReader import EndianBinaryReader
        reader = EndianBinaryReader(bytes(merged), endian=">")
        _inherit_attrs(files[key], reader)
        del merged
        for holder in _file_dicts(obj, s.env):
            for k in list(holder.keys()):
                if _base(k) == _base(src):
                    holder[k] = reader
        if nested:
            tree["m_Resource"] = {"m_Source": src, "m_Offset": offset, "m_Size": len(fsb)}
        else:
            tree["m_Offset"] = offset
            tree["m_Size"] = len(fsb)
    elif "m_AudioData" in tree:
        tree["m_AudioData"] = fsb
        if isinstance(tree.get("m_Resource"), dict):
            tree["m_Resource"] = {"m_Source": "", "m_Offset": 0, "m_Size": 0}
    else:
        raise ValueError("This clip has neither an inline buffer nor a stream reference.")

    obj.save_typetree(tree)
    s.audio_override[idx] = fsb
    s.pending_audio[idx] = hashlib.sha256(fsb).hexdigest()
    s.audio_cache.pop(idx, None)
    s.dirty = True
    return {"bytes": len(fsb), "channels": channels, "frequency": rate}


def _verify_pending_audio(s: "Session") -> None:
    pending = dict(s.pending_audio)
    s.pending_audio.clear()
    s.audio_override.clear()
    s.audio_cache.clear()
    for idx, digest in pending.items():
        raw, _ = _audio_raw(_get_object(s.env, idx), s.env)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise RuntimeError(
                f"The file was saved, but the new audio for object #{idx} is not inside it "
                "(the audio stream was not written back)."
            )


_METHODS: Dict[str, Callable[[dict], dict]] = {
    "ping": ping,
    "open_bundle": open_bundle,
    "close_bundle": close_bundle,
    "save_bundle": save_bundle,
    "set_decrypt_key": set_decrypt_key,
    "object_info": object_info,
    "export_object": export_object,
    "get_object_data": get_object_data,
    "import_object": import_object,
    "replace_audio": replace_audio,
}


def dispatch(method: str, payload_json: str) -> str:
    try:
        fn = _METHODS.get(method)
        if fn is None:
            raise KeyError(f"Unknown method: {method}")
        payload = json.loads(payload_json) if payload_json else {}
        return json.dumps({"ok": True, "data": fn(payload)}, ensure_ascii=False)
    except Exception as exc:
        msg = str(exc) or exc.__class__.__name__
        return json.dumps({"ok": False, "error": msg, "trace": traceback.format_exc()},
                          ensure_ascii=False)
