#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYVER_SHORT="${PYVER_SHORT:-3.13}"
ABI="cp${PYVER_SHORT/./}"

rm -rf Staging
mkdir -p Staging/app Staging/app_packages

echo "==> app/: backend + native shims + UnityPy"
for item in uabe_backend.py uabe_native.py texture2ddecoder etcpak astc_encoder lz4 brotli fmod_toolkit; do
  cp -R "python/$item" Staging/app/
done
cp -R third_party/UnityPy/UnityPy Staging/app/UnityPy
cp python/uabe_audio.py Staging/app/
cp -R third_party/fsb5/fsb5 Staging/app/fsb5
mkdir -p Staging/app/licenses && cp third_party/fsb5/LICENSE* Staging/app/licenses/ 2>/dev/null || true
find Staging/app \( -name '__pycache__' -o -name '*.so' -o -name '*.pyd' -o -name '*.pyi' \) -prune -exec rm -rf {} +

echo "==> app_packages/: pip"
python3 -m venv /tmp/uabe-venv
source /tmp/uabe-venv/bin/activate
python -m pip install --quiet --upgrade pip

for pkg in attrs fsspec typing-extensions tpk-ar; do
  python -m pip install --quiet --no-deps --target Staging/app_packages "$pkg" \
    || echo "WARNING: optional package $pkg could not be installed"
done

PLATFORMS=()
for v in 13_0 14_0 15_0 15_4 16_0; do PLATFORMS+=(--platform "ios_${v}_arm64_iphoneos"); done
BIN_ARGS=(--no-deps --only-binary=:all: --python-version "$PYVER_SHORT" --implementation cp --abi "$ABI"
          "${PLATFORMS[@]}" --extra-index-url https://pypi.anaconda.org/beeware/simple
          --target Staging/app_packages)

python -m pip install "${BIN_ARGS[@]}" pillow
python -m pip install "${BIN_ARGS[@]}" pycryptodome \
  || echo "WARNING: no iOS wheel for pycryptodome - a few encrypted bundle formats will be unavailable"

if [ "${PROTECT:-1}" = "1" ]; then
  echo "==> protecting Python code (bytecode only)"
  python - <<'PY'
import sys
if sys.version_info[:2] != (3, 13):
    sys.exit(f"Bytecode must be compiled with Python 3.13 (running {sys.version.split()[0]}). "
             "Use actions/setup-python with python-version 3.13.")
PY
  python -m compileall -b -q -f Staging/app
  find Staging/app -name '*.py' -delete
  find Staging/app -name '__pycache__' -prune -exec rm -rf {} +
  echo "   $(find Staging/app -name '*.pyc' | wc -l | tr -d ' ') .pyc files, $(find Staging/app -name '*.py' | wc -l | tr -d ' ') .py files left"
fi

find Staging/app_packages -name '__pycache__' -prune -exec rm -rf {} +
find Staging/app_packages -maxdepth 2 -name '*.dist-info' -prune -exec rm -rf {} +

echo "==> staged:"
du -sh Staging/app Staging/app_packages
ls Staging/app_packages
