#!/usr/bin/env bash
# Copies the integration to a Home Assistant host over ssh, with the goma library
# bundled inside it, so it can be tried before goma-gg is on PyPI.
# Usage: scripts/install-on-ha.sh <ssh-host>   (restart Home Assistant afterwards)
set -euo pipefail

host=${1:?usage: $0 <ssh-host>}
repo=$(cd "$(dirname "$0")/.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT

cp -r "$repo/custom_components/goma" "$build/goma"
rm -rf "$build/goma/__pycache__"
cp -r "$repo/src/goma" "$build/goma/lib"
rm -rf "$build/goma/lib/__pycache__" "$build/goma/lib/cli.py" "$build/goma/lib/__main__.py"

sed -i -E 's/^from goma(\.[a-z_]+)? import/from .lib\1 import/' "$build"/goma/*.py
sed -i -E 's/"requirements": \[[^]]*\]/"requirements": []/' "$build/goma/manifest.json"

if grep -nE '^(from|import) goma' "$build"/goma/*.py; then
  echo "Unrewritten goma imports left" >&2
  exit 1
fi

tar -C "$build" -cz goma | ssh "$host" \
  'sudo rm -rf /config/custom_components/goma && sudo tar -C /config/custom_components -xz && sudo chown -R root:root /config/custom_components/goma'
echo "Installed on $host. Restart Home Assistant to load it."
