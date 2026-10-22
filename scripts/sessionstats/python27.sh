#!/usr/bin/env bash
# Offline after the verified CPython source archive is downloaded.
set -euo pipefail
build_root="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-cpython27"
mkdir -p "$build_root"
curl --fail --location --retry 3 --proto '=https' --tlsv1.2 \
  https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz \
  --output "$build_root/Python-2.7.18.tgz"
printf '%s  %s\n' da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814 \
  "$build_root/Python-2.7.18.tgz" | sha256sum --check --status
tar -xzf "$build_root/Python-2.7.18.tgz" -C "$build_root"
cd "$build_root/Python-2.7.18"
./configure --without-ensurepip > "$build_root/configure.log" 2>&1
make -j2 > "$build_root/make.log" 2>&1
"$build_root/Python-2.7.18/python" -c 'import sys; assert sys.version_info[:3] == (2,7,18)'
printf 'PYTHON27=%s\n' "$build_root/Python-2.7.18/python" >> "$GITHUB_ENV"
