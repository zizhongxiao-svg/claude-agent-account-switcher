#!/usr/bin/env bash
set -euo pipefail

prefix="${PREFIX:-$HOME/.local}"
bindir="$prefix/bin"

mkdir -p "$bindir"
install -m 0755 bin/cca-freeze-import "$bindir/cca-freeze-import"
install -m 0755 bin/cca-handoff "$bindir/cca-handoff"
install -m 0755 bin/ccwhere "$bindir/ccwhere"

echo "Installed to $bindir"
echo "Make sure $bindir is on PATH."
