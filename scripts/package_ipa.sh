#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
APP="$(find build/Build/Products -maxdepth 2 -name 'UABE.app' -path '*iphoneos*' | head -n1)"
[ -n "$APP" ] || { echo "UABE.app not found"; exit 1; }
rm -rf Payload UABE.ipa
mkdir Payload
cp -R "$APP" Payload/
zip -qry UABE.ipa Payload
rm -rf Payload
ls -lh UABE.ipa
