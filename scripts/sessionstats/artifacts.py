#!/usr/bin/env python3
"""Snapshot/verify the entire validated six-file release set, including its manifest."""
import argparse
import json
from pathlib import Path

from release import ROOT, ValidationError, inputs, sha256


def snapshot(directory):
    directory = Path(directory)
    version = json.loads((directory / 'BUILD.json').read_text(encoding='utf-8'))['version']
    files = inputs(directory, version)
    return {name: sha256(path) for name, path in sorted(files.items())}


def verify(directory, expected):
    actual = snapshot(directory)
    if actual != expected:
        changed = sorted(name for name in set(actual) | set(expected)
                         if actual.get(name) != expected.get(name))
        raise ValidationError('Release assets are not reproducible: ' + ', '.join(changed))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['snapshot', 'verify'])
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--directory', type=Path, default=ROOT / 'mods/sessionstats/dist')
    args = parser.parse_args()
    if args.operation == 'snapshot':
        args.manifest.write_text(json.dumps(snapshot(args.directory), sort_keys=True) + '\n', encoding='utf-8')
    else:
        verify(args.directory, json.loads(args.manifest.read_text(encoding='utf-8')))
        print('Reproducibility OK: all six published assets, including SHA256SUMS.txt')


if __name__ == '__main__':
    main()
