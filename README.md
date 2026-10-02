<p align="center"><img src="docs/icon.png" width="120" alt="UABE"></p>

# UABE for iOS

A Unity AssetBundle viewer and editor for iPhone and iPad. Open a bundle, browse every object inside it, preview textures, meshes and audio, and replace them with your own files. Everything runs on the device, no server and no computer needed.

It is an iOS port of [UABE-Android](https://github.com/elfilibusterismo/UABE-Android): the interface is rewritten in SwiftUI and the engine is [UnityPy](https://github.com/K0lb3/UnityPy) running inside an embedded CPython.

## Features

**Opening files**
- Open `.unity3d`, `.bundle` and `.ab` files from the Files app, or send them from another app with "Open in".
- Recent files list (last 15) with swipe to delete, and the last bundle reopens on launch.
- Decryption key support for encrypted bundles.

**Browsing**
- Every object is listed with its name, type, size, index and path ID.
- Search by name, type or ID.
- Filter by type, size range, or "edited only".
- Sort by index, name, type, size or modified state.
- Edited objects are marked, pull down to reload.

**Textures (Texture2D)**
- Preview, export as PNG, replace with an image from the Photo Library or Files.
- Decoders for DXT/BC, ETC, ASTC, PVRTC, ATC and Crunch formats.

**Meshes**
- Interactive 3D preview (rotate and zoom) and export as OBJ.

**Audio (AudioClip)**
- Listen to the current audio inside the app, including Vorbis clips.
- Export as WAV (PCM), MP3, OGG (Vorbis) or M4A (AAC).
- Replace a clip with an audio file (MP3, M4A, WAV, ...) or with the sound of a video (MP4/MOV). The new audio can be played before you apply it.
- Clips in formats that cannot be decoded on iOS are exported as the raw `.fsb` bank.

**Text and data**
- Edit TextAssets directly.
- Edit any other object (MonoBehaviour and so on) as JSON through its TypeTree.

**Saving**
- Changes are saved automatically to a private working copy.
- "Export (Save As...)" writes the modified bundle anywhere in Files.
- Light, dark or system theme in Settings.

## Using the app

1. Tap the folder button, pick **Browse** and choose a bundle. It is copied into the app, your original file is never touched.
2. Tap an object to preview or edit it. Long press for export and import shortcuts.
3. For audio: open the clip, press **Play** to hear it, then **Replace with audio...**, choose a file, listen to it and press **Apply replacement**.
4. Open the menu (top right) and choose **Export (Save As...)** to get the modified bundle out of the app.

If something looks wrong, **Menu > Diagnostics** lists which libraries loaded.

## Limitations

- Audio replacement stores the new clip as uncompressed PCM, so the bundle gets bigger. The old audio stays inside the file.
- Audio that lives in a separate file outside the bundle cannot be replaced.
- ADPCM and other exotic audio formats are exported raw instead of decoded.
- Mesh import is not available.
- arm64 devices only (no Intel simulator).
- The build is unsigned, you sign it when you install it.

## Building

### With GitHub Actions (no Mac needed)

1. Fork this repository, or create your own and upload these files.
2. Open the **Actions** tab, enable workflows if asked, choose **Build iOS IPA** and press **Run workflow**.
3. When it finishes (around 15 to 25 minutes), download the **UABE-ipa** artifact. Inside the zip is `UABE.ipa`.
4. Install the unsigned IPA with a sideloading tool that signs it for you: Sideloadly, AltStore, or TrollStore on supported iOS versions.

If the build fails, download the **build-log** artifact and look for lines starting with `error:`.

### On a Mac

Requirements: macOS with Xcode 16 or newer, Python 3.13, and XcodeGen (`brew install xcodegen`).

```
bash scripts/fetch_deps.sh
bash scripts/stage_python.sh
xcodegen generate
xcodebuild build -project UABE.xcodeproj -scheme UABE -configuration Release \
  -sdk iphoneos -destination 'generic/platform=iOS' -derivedDataPath build \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY=""
bash scripts/package_ipa.sh
```

`UABE.ipa` appears in the project folder. Python code is shipped as bytecode only; run `PROTECT=0 bash scripts/stage_python.sh` if you want plain `.py` files in your own debug build.

To run the backend tests on any machine with Python: `python3 tests/test_backend.py`.

## How it works

- **App** (`App/`): SwiftUI interface. A small Objective-C layer starts CPython 3.13 inside the app, and Swift talks to it through JSON messages on a dedicated thread.
- **Backend** (`python/uabe_backend.py`): the bundle logic, built on UnityPy. Large data is exchanged through files, not JSON.
- **Native codecs** (`native/`): texture decoders, etcpak, ASTC and libogg/libvorbis are compiled as frameworks and loaded from Python with ctypes.
- **Audio** (`python/uabe_audio.py`): reads FSB5 containers, rebuilds Ogg Vorbis, and writes the PCM FSB5 used for replacements. The new audio is appended to the bundle's `.resource`/`.resS` stream and the clip's offset and size are updated. After each save the bundle is reopened and checked.
- **Compression**: `lz4` and `brotli` are small replacements that use Apple's libcompression, so no extra wheels are needed.
- **Build**: `project.yml` is turned into an Xcode project by XcodeGen. The scripts in `scripts/` download Python for iOS, UnityPy and the native sources.

```
App/        SwiftUI app and the Objective-C Python runtime
python/     backend, audio support and the small compatibility modules
native/     C/C++ sources built as frameworks
scripts/    dependency download, packaging
tests/      backend tests
```

## Credits

Based on [UABE-Android](https://github.com/elfilibusterismo/UABE-Android). Built with UnityPy, Texture2DDecoder, etcpak, astc-encoder, libogg, libvorbis, python-fsb5, BeeWare's Python-Apple-support and XcodeGen. Licenses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Developer: [@frezcode on TikTok](https://www.tiktok.com/@frezcode)

Use this tool only on files you own or have permission to modify.

---

# بالعربي

**UABE for iOS** تطبيق لتصفح وتعديل ملفات Unity AssetBundle على الآيفون والآيباد مباشرة، بدون كمبيوتر.

**المميزات**
- فتح ملفات `.unity3d` و`.bundle` و`.ab`، مع قائمة الملفات الأخيرة ودعم مفتاح فك التشفير.
- بحث وفلترة وترتيب للكائنات.
- الصور: معاينة وتصدير PNG واستبدال من مكتبة الصور أو الملفات.
- المجسمات: معاينة ثلاثية الأبعاد وتصدير OBJ.
- الصوت: تشغيل الصوت الحالي، تصدير WAV وMP3 وOGG وM4A، واستبدال الصوت بملف صوت أو فيديو مع إمكانية سماع الصوت الجديد قبل التطبيق.
- النصوص وبقية الكائنات: تعديل كنص أو JSON.
- حفظ تلقائي، وتصدير الملف المعدّل (Save As)، ووضع فاتح وداكن.

**البناء بدون ماك**
1. ارفع المشروع إلى مستودع GitHub خاص بك.
2. من تبويب Actions شغّل **Build iOS IPA**.
3. نزّل الملف `UABE-ipa` من Artifacts، وفيه `UABE.ipa`.
4. ثبّته عبر Sideloadly أو AltStore أو TrollStore (الملف غير موقّع، والأداة توقّعه لك).

**ملاحظات**
- استبدال الصوت يحفظه كـ PCM غير مضغوط، فيكبر حجم الملف.
- الصوت المخزّن في ملف خارج الـ Bundle لا يمكن استبداله.
- الأجهزة المدعومة: arm64 فقط.
