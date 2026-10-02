#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY_TAG="${PY_TAG:-3.13-b13}"
ETCPAK_REF="${ETCPAK_REF:-master}"
ASTCENC_REF="${ASTCENC_REF:-main}"
UNITYPY_REF="${UNITYPY_REF:-master}"

PY_VER="${PY_TAG%%-*}"
PY_BUILD="${PY_TAG##*-}"

mkdir -p third_party

if [ ! -d Python.xcframework ]; then
  url="https://github.com/beeware/Python-Apple-support/releases/download/${PY_TAG}/Python-${PY_VER}-iOS-support.${PY_BUILD}.tar.gz"
  echo "==> Python support package: $url"
  curl -fL --retry 3 -o /tmp/python-support.tar.gz "$url"
  tar -xzf /tmp/python-support.tar.gz -C .
  [ -d Python.xcframework ] || { echo "Python.xcframework missing after extraction"; ls; exit 1; }
fi
echo "==> Python.xcframework layout:"
find Python.xcframework -maxdepth 2 | sort | head -60

UTILS="$(find Python.xcframework -maxdepth 3 -type f \( -name build_utils.sh -o -name utils.sh \) | head -n1)"
if [ -z "$UTILS" ]; then
  echo "ERROR: no build_utils.sh / utils.sh inside Python.xcframework (see layout above)."
  exit 1
fi
if ! grep -q "install_python" "$UTILS"; then
  echo "ERROR: $UTILS has no install_python function. Functions found:"
  grep -nE '^[a-zA-Z_]+\(\)' "$UTILS" || true
  exit 1
fi
echo "$UTILS" > .python_utils_path
echo "==> using $UTILS"

clone() { # name url ref
  if [ ! -d "third_party/$1/.git" ]; then
    git clone --depth 1 --branch "$3" "$2" "third_party/$1"
  fi
}
clone etcpak   https://github.com/wolfpld/etcpak.git        "$ETCPAK_REF"
clone astcenc  https://github.com/ARM-software/astc-encoder.git "$ASTCENC_REF"
clone UnityPy  https://github.com/K0lb3/UnityPy.git          "$UNITYPY_REF"
clone ogg      https://github.com/xiph/ogg.git               "${OGG_REF:-master}"
clone vorbis   https://github.com/xiph/vorbis.git            "${VORBIS_REF:-main}"
clone fsb5     https://github.com/HearthSim/python-fsb5.git  "${FSB5_REF:-master}"

cat > third_party/ogg/include/ogg/config_types.h <<'EOT'
#ifndef __CONFIG_TYPES_H__
#define __CONFIG_TYPES_H__
#include <stdint.h>
typedef int16_t ogg_int16_t;
typedef uint16_t ogg_uint16_t;
typedef int32_t ogg_int32_t;
typedef uint32_t ogg_uint32_t;
typedef int64_t ogg_int64_t;
typedef uint64_t ogg_uint64_t;
#endif
EOT

echo "==> sanity checks"
test -f third_party/etcpak/Decode.cpp
test -f third_party/etcpak/bc7enc.cpp
test -f third_party/astcenc/Source/astcenc_entry.cpp
test -d third_party/UnityPy/UnityPy
test -f third_party/ogg/src/framing.c
test -f third_party/vorbis/lib/info.c
test -f third_party/fsb5/fsb5/__init__.py
echo "dependencies ready"
