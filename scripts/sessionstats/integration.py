#!/usr/bin/env python3
"""Inspect built/carried packages without building another mod."""
import argparse
from pathlib import Path
import json
import os
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def resources(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt archive: '+path.name)
        paths = archive.namelist()
        if len(paths) != len(set(paths)):
            raise ValueError('Duplicate archive member')
        identifier = ET.fromstring(archive.read('meta.xml')).findtext('id')
        if not identifier:
            raise ValueError('Package ID is missing')
        return {p.filename for p in archive.infolist()
                if p.filename.startswith('res/') and not p.is_dir()}, identifier


def check(directory, python27=None):
    directory = Path(directory)
    stats = list(directory.glob('grz.sessionstats_*.wotmod'))
    if len(stats) != 1 or len(list(directory.glob('net.openwg.gameface_*.wotmod'))) != 1:
        raise ValueError('Expected one Session Stats package and one OpenWG dependency')
    known_paths, identifiers = set(), set()
    for package in sorted(directory.glob('*.wotmod')):
        paths, identifier = resources(package)
        if known_paths & paths or identifier in identifiers:
            raise ValueError('Mods conflict in resource paths or package ID')
        known_paths.update(paths)
        identifiers.add(identifier)
    report = json.loads((stats[0].parent/'BUILD.json').read_text())
    version = report['version']
    if stats[0].name != 'grz.sessionstats_'+version+'.wotmod':
        raise ValueError('Package filename does not match BUILD.json')
    with zipfile.ZipFile(stats[0]) as archive:
        if ET.fromstring(archive.read('meta.xml')).findtext('version') != version:
            raise ValueError('meta.xml does not match BUILD.json')
    if python27:
        subprocess.check_call([python27, '-c',
            'import marshal,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); '
            'c=marshal.loads(z.read("res/scripts/client/gui/mods/grz_session_stats/__init__.pyc")[8:]); '
            'assert sys.argv[2] in c.co_consts', str(stats[0]), version])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT/'mods/sessionstats/dist')
    args = parser.parse_args()
    check(args.directory, os.environ.get('PYTHON27'))
    print('Integration OK: built/carried package IDs and resource paths are disjoint')


if __name__ == '__main__': main()
