#!/usr/bin/env python3
"""Allow pre-import CI only when source is absent from checkout and its history."""
import os
from pathlib import Path
import subprocess

SOURCE = 'mods/sessionstats'
ENTRY = SOURCE + '/src/mod_grz_session_stats.py'


def source_enabled(root):
    root = Path(root)
    if (root / ENTRY).is_file():
        return True
    if (root / SOURCE).exists():
        raise RuntimeError('Session Stats source is present but its entry point is missing')
    shallow = subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', '--is-shallow-repository'], text=True).strip()
    if shallow != 'false':
        raise RuntimeError('Cannot verify pre-import state without complete Git history')
    imported = subprocess.check_output(
        ['git', '-C', str(root), 'log', '--full-history', '-1', '--format=%H',
         'HEAD', '--', SOURCE], text=True).strip()
    if imported:
        raise RuntimeError('Session Stats was already imported; its missing entry point is an error')
    return False


def main():
    enabled = source_enabled(Path.cwd())
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write('enabled=' + str(enabled).lower() + '\n')
    print('Session Stats source enabled' if enabled else
          'Infrastructure ready; source has never been imported in this checkout history.')


if __name__ == '__main__':
    main()
