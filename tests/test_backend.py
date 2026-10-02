import json, os, sys, types, tempfile, io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))


class T:
    def __init__(self, n): self.name = n

class Obj:
    def __init__(self, t, pid, name, payload=None, container=None):
        self.type = T(t); self.path_id = pid; self._name = name
        self.payload = payload; self.container = container
        self.byte_size = 42; self.assets_file = types.SimpleNamespace(name="CAB-abc.assets")
        self.saved = None
    def peek_name(self): return self._name
    def parse_as_object(self): return self.payload
    def parse_as_dict(self): return {"m_Name": self._name, "raw": b"\x01\x02"}
    def save_typetree(self, d): self.saved = d
    def get_raw_data(self): return b"raw"

class Text:
    m_Script = "hello"
    def save(self): self.saved = True
class Mesh:
    def export(self): return "v 0 0 0\n"

class File:
    files = {"CAB-abc": 1, "/abs/path": 2}
    def save(self):
        for f in self.files.values():
            if hasattr(f, "bytes"):
                f.flags
        return b"BUNDLE"

objs = [Obj("TextAsset", 1, "readme", Text(), "a/b/readme.txt"),
        Obj("Mesh", 2, "cube", Mesh()), Obj("MonoBehaviour", 3, "cfg")]
env = types.SimpleNamespace(objects=objs, files={}, file=File())
fake = types.ModuleType("UnityPy")
fake.load = lambda p: env
fake.set_assetbundle_decrypt_key = lambda k: setattr(fake, "key", k)
sys.modules["UnityPy"] = fake

import uabe_backend as b

def call(m, **kw):
    r = json.loads(b.dispatch(m, json.dumps(kw)))
    return r

d = tempfile.mkdtemp()
src = os.path.join(d, "x.unity3d"); open(src, "wb").write(b"x")
r = call("open_bundle", path=src); assert r["ok"], r
sid = r["data"]["sessionId"]
assert [o["type"] for o in r["data"]["objects"]] == ["TextAsset", "Mesh", "MonoBehaviour"]
assert r["data"]["archives"] == ["CAB-abc"], r["data"]["archives"]
assert call("object_info", sessionId=sid, idx=0)["data"] == {
    "type": "TextAsset", "filename": "readme_CAB_abc", "ext": "txt", "mime": "text/plain"}
out = os.path.join(d, "o.txt")
assert call("export_object", sessionId=sid, idx=0, outPath=out)["ok"] and open(out).read() == "hello"
assert call("export_object", sessionId=sid, idx=1, outPath=out)["ok"] and open(out).read().startswith("v 0")
assert call("export_object", sessionId=sid, idx=2, outPath=out)["ok"]
assert json.loads(open(out).read())["raw"] == [1, 2]
open(out, "w").write('{"a": 1}')
assert call("import_object", sessionId=sid, idx=2, inPath=out)["ok"] and objs[2].saved == {"a": 1}
open(out, "w").write('[1]')
bad = call("import_object", sessionId=sid, idx=2, inPath=out); assert not bad["ok"] and "dict" in bad["error"]
open(out, "w").write('new text')
assert call("import_object", sessionId=sid, idx=0, inPath=out)["ok"] and objs[0].payload.m_Script == "new text"
bo = os.path.join(d, "out.bundle")
assert call("save_bundle", sessionId=sid, outPath=bo)["ok"] and open(bo, "rb").read() == b"BUNDLE"
r2 = call("save_bundle", sessionId=sid, outPath=bo, reload=True)
assert r2["ok"] and r2["data"]["reloaded"]["sessionId"] == sid and len(r2["data"]["reloaded"]["objects"]) == 3
assert call("set_decrypt_key", key="k")["ok"] and fake.key == "k"
assert not call("nope")["ok"]
assert call("close_bundle", sessionId=sid)["ok"] and not call("object_info", sessionId=sid, idx=0)["ok"]
p = call("ping")["data"]; print({k: v for k, v in p.items() if "MISSING" not in str(v)})
print("backend smoke test OK")


import struct, wave
import uabe_audio as au

pcm = struct.pack("<8h", 0, 1000, -1000, 2000, -2000, 3000, -3000, 0)
for rate in (44100, 12345):
    for ch in (1, 2):
        fsb = au.build_fsb5_pcm16(pcm, ch, rate)
        assert len(fsb) % 16 == 0 and (fsb[60:][:0] == b"")
        parsed = au.parse_fsb5(fsb)
        smp = parsed.samples[0]
        assert parsed.mode == au.PCM16 and smp.frequency == rate and smp.channels == ch
        assert smp.samples == len(pcm) // (2 * ch) and smp.data[:len(pcm)] == pcm, (rate, ch)
        res = au.decode_audio(fsb)
        assert res.ext == "wav" and res.data[:4] == b"RIFF" and res.format == "PCM16"
assert au.decode_audio(b"OggS....").ext == "ogg"
assert au.decode_audio(b"ID3\x03....").ext == "mp3"
assert au.decode_audio(b"\xff\xfb\x90\x00").ext == "mp3"

fake = bytearray(au.build_fsb5_pcm16(pcm, 1, 44100)); struct.pack_into("<I", fake, 24, au.GCADPCM)
r = au.decode_audio(bytes(fake)); assert r.ext == "fsb" and "GC ADPCM" in r.note


class Clip:
    m_Name = "sfx"; m_SubsoundIndex = 0; m_Channels = 1; m_Frequency = 44100
    m_AudioData = au.build_fsb5_pcm16(pcm, 1, 44100)
class AObj(Obj):
    def __init__(self):
        super().__init__("AudioClip", 9, "sfx", Clip())
        self.tree = {"m_Name": "sfx", "m_Channels": 2, "m_Frequency": 22050, "m_BitsPerSample": 16,
                     "m_Length": 1.0, "m_CompressionFormat": 1, "m_LoadType": 2,
                     "m_Resource": {"m_Source": "", "m_Offset": 0, "m_Size": 0},
                     "m_AudioData": Clip.m_AudioData}
    def parse_as_dict(self): return dict(self.tree)
    def save_typetree(self, d): self.tree = dict(d)
aobj = AObj(); objs.append(aobj)
r = call("open_bundle", path=src); sid = r["data"]["sessionId"]; ai = len(r["data"]["objects"]) - 1
assert r["data"]["objects"][ai]["type"] == "AudioClip"
assert call("object_info", sessionId=sid, idx=ai)["data"]["ext"] == "wav"
out = os.path.join(d, "a.wav")
g = call("get_object_data", sessionId=sid, idx=ai, outPath=out)["data"]
assert g["kind"] == "audio" and g["ext"] == "wav" and g["playable"] and g["frequency"] == 44100
assert open(out, "rb").read(4) == b"RIFF"

wp = os.path.join(d, "in.wav")
with wave.open(wp, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000); w.writeframes(pcm * 10)
rr = call("replace_audio", sessionId=sid, idx=ai, inPath=wp); assert rr["ok"], rr
t = aobj.tree
assert t["m_Channels"] == 2 and t["m_Frequency"] == 48000 and t["m_CompressionFormat"] == 0
assert t["m_Resource"] == {"m_Source": "", "m_Offset": 0, "m_Size": 0}
assert au.parse_fsb5(t["m_AudioData"]).samples[0].frequency == 48000
with wave.open(wp, "wb") as w:
    w.setnchannels(1); w.setsampwidth(1); w.setframerate(8000); w.writeframes(b"\x80" * 10)
bad = call("replace_audio", sessionId=sid, idx=ai, inPath=wp); assert not bad["ok"] and "16-bit" in bad["error"]
print("audio tests OK")


class Reader:
    def __init__(self, data, endian=">"):
        self.bytes = memoryview(bytes(data))
class Orig(Reader):
    def __init__(self, data, endian=">"):
        super().__init__(data, endian)
        self.flags = 0
streams = types.ModuleType("UnityPy.streams")
streams.EndianBinaryReader = Reader
sys.modules["UnityPy.streams"] = streams

old_stream = b"OLD-STREAM-DATA" * 7
holder = types.SimpleNamespace(files={"CAB-zz": 1, "CAB-zz.resS": Orig(old_stream)})
env.file.files = holder.files
old_fsb = au.build_fsb5_pcm16(pcm, 1, 22050)
old_stream = old_stream + b"\x00" * ((-len(old_stream)) % 32)
holder.files["CAB-zz.resS"] = Orig(old_stream + old_fsb)

class SObj(Obj):
    def __init__(self):
        super().__init__("AudioClip", 11, "streamed", None)
        self.assets_file = types.SimpleNamespace(name="CAB-zz.assets", parent=types.SimpleNamespace(files=holder.files))
        self.tree = {"m_Name": "streamed", "m_Channels": 1, "m_Frequency": 22050, "m_BitsPerSample": 16,
                     "m_Length": 0.1, "m_CompressionFormat": 0, "m_LoadType": 2,
                     "m_Resource": {"m_Source": "archive:/CAB-zz/CAB-zz.resS",
                                    "m_Offset": len(old_stream), "m_Size": len(old_fsb)}}
    def parse_as_dict(self): return dict(self.tree)
    def save_typetree(self, d): self.tree = dict(d)
sobj = SObj(); objs.append(sobj)
r = call("open_bundle", path=src); sid = r["data"]["sessionId"]; si = len(r["data"]["objects"]) - 1
g = call("get_object_data", sessionId=sid, idx=si, outPath=os.path.join(d, "s.wav"))
assert g["ok"] and g["data"]["kind"] == "audio" and g["data"]["frequency"] == 22050, g
wp = os.path.join(d, "new.wav")
with wave.open(wp, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100); w.writeframes(pcm * 50)
rr = call("replace_audio", sessionId=sid, idx=si, inPath=wp); assert rr["ok"], rr
res = sobj.tree["m_Resource"]
assert res["m_Offset"] % 32 == 0 and res["m_Offset"] >= len(old_stream) + len(old_fsb)
merged = bytes(holder.files["CAB-zz.resS"].bytes)
assert merged[:len(old_stream)] == old_stream
assert au.parse_fsb5(merged[res["m_Offset"]:res["m_Offset"] + res["m_Size"]]).samples[0].frequency == 44100
assert sobj.tree["m_Channels"] == 2 and sobj.tree["m_CompressionFormat"] == 0
g2 = call("get_object_data", sessionId=sid, idx=si, outPath=os.path.join(d, "s2.wav"))["data"]
assert g2["frequency"] == 44100 and g2["channels"] == 2
sv = call("save_bundle", sessionId=sid, outPath=bo, reload=True); assert sv["ok"], sv
g3 = call("get_object_data", sessionId=sid, idx=si, outPath=os.path.join(d, "s3.wav"))["data"]
assert g3["frequency"] == 44100
call("replace_audio", sessionId=sid, idx=si, inPath=wp)
holder.files["CAB-zz.resS"] = Orig(old_stream + old_fsb)
bad = call("save_bundle", sessionId=sid, outPath=bo, reload=True)
assert not bad["ok"] and "not inside" in bad["error"], bad
lost = types.SimpleNamespace(files={})
sobj.assets_file = types.SimpleNamespace(name="x", parent=lost)
env.file.files = {}
env.files = {}
miss = call("replace_audio", sessionId=sid, idx=si, inPath=wp)
assert not miss["ok"] and "outside this file" in miss["error"], miss
print("stream audio tests OK")
