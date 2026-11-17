#!/usr/bin/env bash
# Reuse a restored build only after the same probe used for a new build.
set -euo pipefail
: "${GITHUB_ENV:?Set GITHUB_ENV to the Actions environment file}"
build_root="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/sessionstats-cpython27"
runtime_root="$build_root/Python-2.7.18"
python27="$runtime_root/python"
[[ "$build_root" != *$'\n'* && "$build_root" != *$'\r'* ]] || {
  echo 'Python 2.7 build path must not contain line breaks' >&2; exit 1;
}

verify_runtime() {
  "$python27" -B -E -s - <<'PY'
import sys
assert sys.version_info[:3] == (2, 7, 18), 'Expected CPython 2.7.18'
import hashlib
import imp
import marshal
import types
import zipfile
import zlib
from io import BytesIO

assert imp.get_magic() == b'\x03\xf3\r\n', 'Unexpected Python bytecode magic'
code = compile('value = 42', '<sessionstats-runtime-probe>', 'exec')
restored = marshal.loads(marshal.dumps(code))
assert isinstance(restored, types.CodeType) and restored.co_consts == code.co_consts
payload = b'Session Stats runtime probe'
assert zlib.decompress(zlib.compress(payload)) == payload
assert hashlib.sha256(b'abc').hexdigest() == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
buffer = BytesIO()
with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('probe.txt', payload)
buffer.seek(0)
with zipfile.ZipFile(buffer, 'r') as archive:
    assert archive.read('probe.txt') == payload
PY
}

if [[ -e "$runtime_root" || -L "$runtime_root" ]]; then
  [[ -d "$runtime_root" && ! -L "$runtime_root" && -f "$python27" &&
     ! -L "$python27" && -x "$python27" ]] || {
    echo 'Restored Python 2.7 runtime is incomplete; refusing to use it' >&2; exit 1;
  }
  verify_runtime || {
    echo 'Restored Python 2.7 runtime failed verification; refusing to use it' >&2; exit 1;
  }
  printf 'Reusing verified CPython 2.7.18\n'
  printf 'PYTHON27=%s\n' "$python27" >> "$GITHUB_ENV"
  exit 0
fi

mkdir -p "$build_root"
curl --fail --location --retry 3 --proto '=https' --tlsv1.2 \
  https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz \
  --output "$build_root/Python-2.7.18.tgz"
printf '%s  %s\n' da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814 \
  "$build_root/Python-2.7.18.tgz" | sha256sum --check --status
tar -xzf "$build_root/Python-2.7.18.tgz" -C "$build_root"
cd "$runtime_root"
./configure --without-ensurepip > "$build_root/configure.log" 2>&1
make -j2 > "$build_root/make.log" 2>&1
verify_runtime
printf 'PYTHON27=%s\n' "$python27" >> "$GITHUB_ENV"
