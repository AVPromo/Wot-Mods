#!/usr/bin/env python3
"""Scan source, recursive ZIPs and Python 2.7 constants; report labels, never values."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / 'mods/sessionstats'
spec = importlib.util.spec_from_file_location('base_privacy', ROOT/'scripts/privacy_audit.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
PATTERNS = dict(base.PATTERNS)
PATTERNS['build_workspace'] = re.compile('/work' + r'space/scratch/[^\s\x00]+')
FORBIDDEN = {'.log', '.dmp', '.mdmp', '.sqlite', '.db', '.pfx', '.pem', '.key', '.token'}
SKIP = {'.git', '__pycache__', 'node_modules', 'dist', '.pytest_cache'}


def scan_bytes(name, data, python27, depth=0):
    if depth > 5:
        return [(name, ['archive_depth'])]
    path = Path(name)
    if path.suffix in FORBIDDEN:
        return [(name, ['forbidden_resource'])]
    if path.suffix in ('.zip', '.wotmod'):
        problems = []
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip() is not None:
                return [(name, ['corrupt_archive'])]
            for item in archive.infolist():
                if not item.is_dir():
                    problems.extend(scan_bytes(name+':'+item.filename, archive.read(item), python27, depth+1))
        return problems
    if path.suffix == '.pyc':
        if not python27:
            raise ValueError('Bytecode scan requires --python27')
        with tempfile.TemporaryDirectory(prefix='sessionstats-audit-') as directory:
            directory = Path(directory)
            (directory/'patterns.json').write_text(json.dumps([(k,v.pattern) for k,v in PATTERNS.items()]))
            (directory/'module.pyc').write_bytes(data)
            result = subprocess.check_output([python27, str(Path(__file__).with_name('bytecode_audit.py')),
                str(directory/'patterns.json'), str(directory/'module.pyc')], text=True)
            labels = json.loads(result)
    else:
        text = data.decode('utf-8', 'replace')
        labels = sorted(k for k,v in PATTERNS.items() if v.search(text))
    return [(name, labels)] if labels else []


def audit(python27, scan_dist=False):
    problems = base.scan_root()
    for path in MOD.rglob('*'):
        if path.is_file() and path.suffix not in ('.pyc', '.pyo') and not any(p in SKIP for p in path.relative_to(MOD).parts):
            problems.extend(scan_bytes(path.relative_to(ROOT).as_posix(), path.read_bytes(), python27))
    if scan_dist:
        for path in (MOD/'dist').iterdir():
            if path.is_file():
                problems.extend(scan_bytes(path.name, path.read_bytes(), python27))
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python27', required=True)
    parser.add_argument('--scan-dist', action='store_true')
    args = parser.parse_args()
    problems = audit(args.python27, args.scan_dist)
    for name, labels in problems:
        print('BLOCKED:', name, ','.join(labels))
    if problems:
        raise SystemExit(1)
    print('Privacy audit OK: source, recursive archives and bytecode constants')


if __name__ == '__main__':
    main()
