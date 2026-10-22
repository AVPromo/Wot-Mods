#!/usr/bin/env python3
"""Local Session Stats versioning and artifact validation; no remote publisher."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from release_version import release_version


class ValidationError(ValueError):
    pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inputs(directory, version):
    release_version(version, 1)  # Require the same strict SemVer as the shared helper.
    directory = Path(directory)
    expected = {'grz.sessionstats_'+version+'.wotmod', 'wot-statystyki-sesji-v'+version+'.zip',
                'net.openwg.gameface_1.2.2.wotmod', 'grz.sessionstats.json', 'BUILD.json'}
    entries = list(directory.iterdir())
    if any(not p.is_file() or p.is_symlink() for p in entries):
        raise ValidationError('Release assets must be regular files')
    files = {p.name:p for p in entries}
    if set(files) != expected | {'SHA256SUMS.txt'}:
        raise ValidationError('Unexpected Session Stats release assets')
    checksums = files['SHA256SUMS.txt'].read_text(encoding='ascii').splitlines()
    wanted = {sha256(files[name])+'  '+name for name in expected}
    if len(checksums) != len(wanted) or set(checksums) != wanted:
        raise ValidationError('Session Stats checksums do not match all release assets')
    report = json.loads(files['BUILD.json'].read_text())
    if report.get('version') != version or report.get('python_bytecode') != '2.7':
        raise ValidationError('Session Stats build metadata does not match version')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--run-number', type=int)
    mode.add_argument('--verify-directory', type=Path)
    parser.add_argument('--version')
    args = parser.parse_args()
    if args.run_number is not None:
        baseline = (ROOT/'mods/sessionstats/VERSION').read_text().strip()
        print(release_version(baseline, args.run_number))
        return
    if args.version is None:
        parser.error('--verify-directory requires --version')
    inputs(args.verify_directory, args.version)
    print('Session Stats assets verified: all six files match the build and manifest')


if __name__ == '__main__':
    main()
