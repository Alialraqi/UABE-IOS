# Third-party software

This project uses the following components. Each keeps its own license, see the linked repositories for the full text.

| Component | License | Link |
|---|---|---|
| UnityPy | MIT | https://github.com/K0lb3/UnityPy |
| Texture2DDecoder | MIT | https://github.com/K0lb3/Texture2DDecoder |
| etcpak | BSD 3-Clause | https://github.com/wolfpld/etcpak |
| astc-encoder (Arm) | Apache 2.0 | https://github.com/ARM-software/astc-encoder |
| libogg, libvorbis (Xiph.Org) | BSD 3-Clause | https://github.com/xiph |
| python-fsb5 | MIT | https://github.com/HearthSim/python-fsb5 |
| Python-Apple-support (BeeWare) | BSD 3-Clause, bundles CPython (PSF License) | https://github.com/beeware/Python-Apple-support |
| Pillow | HPND | https://python-pillow.org |
| attrs | MIT | https://github.com/python-attrs/attrs |
| fsspec | BSD 3-Clause | https://github.com/fsspec/filesystem_spec |
| XcodeGen (build tool) | MIT | https://github.com/yonaskolb/XcodeGen |

The iOS port is based on UABE-Android by elfilibusterismo (https://github.com/elfilibusterismo/UABE-Android).

Dependencies are downloaded at build time by `scripts/fetch_deps.sh` and `scripts/stage_python.sh`, they are not stored in this repository.
