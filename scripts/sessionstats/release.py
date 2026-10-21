#!/usr/bin/env python3
"""Independent Session Stats tags, using the accepted resumable publisher."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import publish_release as shared
from release_version import release_version


def inputs(directory, version):
    directory = Path(directory)
    expected = {'grz.sessionstats_'+version+'.wotmod', 'wot-statystyki-sesji-v'+version+'.zip',
                'net.openwg.gameface_1.2.2.wotmod', 'grz.sessionstats.json', 'BUILD.json'}
    files = {p.name:p for p in directory.iterdir() if p.is_file()}
    if set(files) != expected | {'SHA256SUMS.txt'}:
        raise shared.PublicationError('Unexpected Session Stats release assets')
    checksums = files['SHA256SUMS.txt'].read_text(encoding='ascii').splitlines()
    wanted = {shared.sha256(files[name])+'  '+name for name in expected}
    if len(checksums) != len(wanted) or set(checksums) != wanted:
        raise shared.PublicationError('Session Stats checksums do not match all release assets')
    report = json.loads(files['BUILD.json'].read_text())
    if report.get('version') != version or report.get('python_bytecode') != '2.7':
        raise shared.PublicationError('Session Stats build metadata does not match version')
    return files


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--run-number':
        baseline = (ROOT/'mods/sessionstats/VERSION').read_text().strip()
        print(release_version(baseline, int(sys.argv[2])))
        return
    version = os.environ['SESSIONSTATS_VERSION']
    repo = os.environ['GITHUB_REPOSITORY']
    shared.publish(shared.GitHubCLI(repo), repo, 'sessionstats-v'+version,
        os.environ['GITHUB_SHA'], version, ROOT/'mods/sessionstats/dist',
        tag_prefix='sessionstats-v', title='Session Stats', artifact_loader=inputs)


if __name__ == '__main__':
    main()
