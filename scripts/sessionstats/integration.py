#!/usr/bin/env python3
"""Check that the shipped resource namespaces of both mods remain disjoint."""
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
        return {p for p in paths if p.startswith('res/')}, ET.fromstring(archive.read('meta.xml')).findtext('id')


def main():
    medkit = list((ROOT/'dist').glob('com.staysharp.medkitreminder_*.wotmod'))
    stats = list((ROOT/'mods/sessionstats/dist').glob('grz.sessionstats_*.wotmod'))
    if len(medkit) != 1 or len(stats) != 1:
        raise ValueError('Expected one built package for each mod')
    a, a_id = resources(medkit[0])
    b, b_id = resources(stats[0])
    if a & b or a_id == b_id:
        raise ValueError('Mods conflict in resource paths or package ID')
    report = json.loads((stats[0].parent/'BUILD.json').read_text())
    version = report['version']
    if stats[0].name != 'grz.sessionstats_'+version+'.wotmod':
        raise ValueError('Package filename does not match BUILD.json')
    with zipfile.ZipFile(stats[0]) as archive:
        if ET.fromstring(archive.read('meta.xml')).findtext('version') != version:
            raise ValueError('meta.xml does not match BUILD.json')
    if os.environ.get('PYTHON27'):
        subprocess.check_call([os.environ['PYTHON27'], '-c',
            'import marshal,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); '
            'c=marshal.loads(z.read("res/scripts/client/gui/mods/grz_session_stats/__init__.pyc")[8:]); '
            'assert sys.argv[2] in c.co_consts', str(stats[0]), version])
    print('Integration OK: distinct package IDs and no shared resource paths')


if __name__ == '__main__': main()
