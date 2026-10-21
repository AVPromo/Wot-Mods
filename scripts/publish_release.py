#!/usr/bin/env python3
"""Resumable, fail-closed GitHub Release publication for Stay Sharp.

A Release is considered successful only if its tag resolves to the exact
checkout commit, it is published, and both uploaded asset hashes match the
files that this workflow built. Published assets are never overwritten.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class PublicationError(RuntimeError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def release_inputs(directory, version):
    """Validate local build before touching a remote tag or release."""
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise PublicationError('Invalid release version')
    directory = Path(directory).resolve()
    mod = directory / ('com.staysharp.medkitreminder_%s.wotmod' % version)
    checksums = directory / 'SHA256SUMS.txt'
    if not mod.is_file() or not checksums.is_file():
        raise PublicationError('Missing release artifact or SHA256SUMS.txt')
    mods = sorted(directory.glob('*.wotmod'))
    if mods != [mod]:
        raise PublicationError('Unexpected or multiple .wotmod artifacts in dist')
    expected = '%s  %s' % (sha256(mod), mod.name)
    if checksums.read_text(encoding='ascii').strip() != expected:
        raise PublicationError('Checksum manifest does not match built artifact')
    return {mod.name: mod, checksums.name: checksums}


class GitHubCLI:
    """Minimal adapter; independent from the publication state machine."""

    def __init__(self, repo):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise PublicationError('Invalid GitHub repository')
        self.repo = repo

    def command(self, *args, missing_ok=False):
        result = subprocess.run(['gh', *args], text=True, capture_output=True, check=False)
        if result.returncode:
            # Treat ONLY HTTP 404 as missing, not 401/403/5xx, timeouts,
            # invalid credentials or an unavailable API.
            if missing_ok and re.search(r'\bHTTP 404\b', result.stderr):
                return None
            raise PublicationError('GitHub CLI failed: %s: %s' % (
                ' '.join(args[:3]), result.stderr.strip()[-450:]))
        return result.stdout

    def api(self, resource, *, missing_ok=False):
        raw = self.command('api', 'repos/%s/%s' % (self.repo, resource), missing_ok=missing_ok)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise PublicationError('Invalid GitHub API response: %s' % resource) from exc

    def tag_commit(self, tag):
        ref = self.api('git/ref/tags/' + tag, missing_ok=True)
        if ref is None:
            return None
        if isinstance(ref, list) or not isinstance(ref, dict):
            raise PublicationError('Ambiguous Git tag reference')
        obj = ref.get('object')
        for _ in range(5):
            if not isinstance(obj, dict) or 'sha' not in obj:
                raise PublicationError('Invalid Git tag object')
            if obj.get('type') == 'commit':
                return obj['sha']
            if obj.get('type') != 'tag':
                raise PublicationError('Unsupported Git tag reference type')
            tag_data = self.api('git/tags/' + obj['sha'])
            obj = tag_data.get('object', {})
        raise PublicationError('Excessive nested Git tags')

    def create_tag(self, tag, commit):
        self.command('api', '--method', 'POST', 'repos/%s/git/refs' % self.repo,
                     '-f', 'ref=refs/tags/' + tag, '-f', 'sha=' + commit)

    @staticmethod
    def _release_id(release):
        release_id = release.get('id') if isinstance(release, dict) else None
        if type(release_id) is not int or release_id <= 0:
            raise PublicationError('GitHub returned an invalid Release ID')
        return release_id

    def get_release(self, tag):
        """Look up published *and draft* releases.

        GET /releases/tags/<tag> returns HTTP 404 for drafts, even with write
        access. Listing with the workflow's contents:write token includes them;
        follow up by numeric ID to get the full, current asset inventory.
        Never mistake an inaccessible draft for a missing Release.
        """
        for page in range(1, 101):
            entries = self.api('releases?per_page=100&page=%d' % page)
            if not isinstance(entries, list):
                raise PublicationError('Invalid GitHub release listing')
            matches = [item for item in entries
                       if isinstance(item, dict) and item.get('tag_name') == tag]
            if len(matches) != 1 and matches:
                raise PublicationError('Ambiguous Release tag in GitHub listing')
            if matches:
                release_id = self._release_id(matches[0])
                result = self.api('releases/%d' % release_id)
                if (not isinstance(result, dict) or
                        result.get('tag_name') != tag or
                        self._release_id(result) != release_id):
                    raise PublicationError('Release changed during ID lookup')
                return result
            if len(entries) < 100:
                return None
        raise PublicationError('Release listing exceeded safe pagination limit')

    def create_draft(self, tag, commit, title):
        self.command('release', 'create', tag, '--repo', self.repo,
                     '--verify-tag', '--draft', '--target', commit,
                     '--title', title, '--generate-notes')

    def _request_bytes(self, url, *, method='GET', payload=None,
                       content_type='application/vnd.github+json'):
        """Authenticated binary REST access; never put a token in URLs/logs."""
        if not (url.startswith('https://uploads.github.com/repos/' + self.repo + '/') or
                url.startswith('https://api.github.com/repos/' + self.repo + '/')):
            raise PublicationError('Unexpected GitHub asset endpoint')
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if not token:
            raise PublicationError('Missing GitHub Actions token for asset transfer')
        headers = {
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'Content-Type': content_type,
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'StaySharp-ReleasePublisher',
        }
        request = Request(url, data=payload, headers=headers, method=method)
        try:
            with urlopen(request, timeout=90) as response:
                return response.read()
        except HTTPError as exc:
            # Do not echo response contents: server errors can contain private
            # details, and Authorization must remain in the request headers.
            raise PublicationError('GitHub asset API HTTP %d (%s)' % (
                exc.code, method)) from exc
        except (OSError, URLError) as exc:
            raise PublicationError('GitHub asset API connection failed (%s)' % method) from exc

    def upload_draft(self, tag, paths):
        """Upload by release ID; gh release upload TAG fails on draft releases."""
        release = self.get_release(tag)
        if release is None or release.get('draft') is not True:
            raise PublicationError('Cannot upload: Release is not an existing draft')
        release_id = self._release_id(release)
        assets = release.get('assets')
        if not isinstance(assets, list):
            raise PublicationError('Cannot read assets of existing draft')
        for path in paths:
            if not isinstance(path, Path) or not path.is_file():
                raise PublicationError('Cannot upload an absent local asset')
            existing = [a for a in assets
                        if isinstance(a, dict) and a.get('name') == path.name]
            if len(existing) > 1:
                raise PublicationError('Duplicate asset names in draft')
            if existing:
                entry = existing[0]
                if (entry.get('state') == 'uploaded' and
                        entry.get('size') == path.stat().st_size and
                        entry.get('digest') == 'sha256:' + sha256(path)):
                    continue
                asset_id = entry.get('id')
                if type(asset_id) is not int or asset_id <= 0:
                    raise PublicationError('Invalid existing draft asset ID')
                self.command('api', '--method', 'DELETE',
                             'repos/%s/releases/assets/%d' % (self.repo, asset_id))
            url = ('https://uploads.github.com/repos/%s/releases/%d/assets?name=%s' %
                   (self.repo, release_id, quote(path.name, safe='')))
            raw = self._request_bytes(url, method='POST', payload=path.read_bytes(),
                                      content_type='application/octet-stream')
            try:
                created = json.loads(raw)
            except (ValueError, TypeError) as exc:
                raise PublicationError('Invalid asset upload response') from exc
            if (not isinstance(created, dict) or
                    created.get('name') != path.name or
                    created.get('size') != path.stat().st_size or
                    created.get('state') != 'uploaded'):
                raise PublicationError('GitHub did not confirm asset upload')
            digest = created.get('digest')
            if digest is not None and digest != 'sha256:' + sha256(path):
                raise PublicationError('GitHub reported an unexpected asset hash')

    def publish_draft(self, tag):
        release = self.get_release(tag)
        if release is None or release.get('draft') is not True:
            raise PublicationError('Cannot publish: Release is not a draft')
        release_id = self._release_id(release)
        # Numeric ID avoids the unreliable draft-by-tag API/CLI resolution.
        args = ['api', '--method', 'PATCH',
                'repos/%s/releases/%d' % (self.repo, release_id),
                '-F', 'draft=false']
        # Publishing an older recovered draft must never demote a newer release
        # from "Latest" merely because this recovery finished afterward.
        if os.environ.get('STAYSHARP_RECOVERY_MODE') == '1':
            args.extend(('-f', 'make_latest=false'))
        self.command(*args)

    def asset_hash(self, tag, asset, filename):
        """Prefer API-provided SHA-256, download and verify when absent."""
        digest = asset.get('digest')
        if isinstance(digest, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            return digest.split(':', 1)[1]
        # GitHub documents SHA-256 digests in the Release asset API.
        # Fail closed rather than making a draft-by-tag download request
        # (which can return HTTP 404) or trusting an unverifiable asset.
        raise PublicationError('Asset lacks a valid GitHub SHA-256 digest: ' + filename)


def verify_assets(api, release, tag, artifacts):
    seen = release.get('assets')
    if not isinstance(seen, list):
        raise PublicationError('Release asset list not available')
    by_name = {}
    for asset in seen:
        name = asset.get('name')
        if not isinstance(name, str) or name in by_name:
            raise PublicationError('Duplicate or invalid Release asset name')
        by_name[name] = asset
    if set(by_name) != set(artifacts):
        raise PublicationError('Wrong Release asset set: %s' % sorted(by_name))
    for name, path in artifacts.items():
        asset = by_name[name]
        if asset.get('state') != 'uploaded':
            raise PublicationError('Asset not uploaded: ' + name)
        if asset.get('size') != path.stat().st_size:
            raise PublicationError('Asset size mismatch: ' + name)
        if api.asset_hash(tag, asset, name) != sha256(path):
            raise PublicationError('Asset SHA-256 mismatch: ' + name)


def publish(api, repo, tag, commit, version, dist):
    """Idempotent transaction: create/check tag, draft, assets, publish."""
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag) or tag != 'v' + version:
        raise PublicationError('Release tag and version do not match')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise PublicationError('Invalid Git commit SHA')
    artifacts = release_inputs(dist, version)

    release = api.get_release(tag)
    current_tag_commit = api.tag_commit(tag)
    if release is not None and current_tag_commit is None:
        raise PublicationError('Release exists but its Git tag is missing')
    if current_tag_commit is not None and current_tag_commit != commit:
        raise PublicationError('Tag %s points to %s, expected %s' % (
            tag, current_tag_commit, commit))

    if release is None:
        if current_tag_commit is None:
            api.create_tag(tag, commit)
            # Verify that GitHub created the expected tag, not an unrelated ref.
            if api.tag_commit(tag) != commit:
                raise PublicationError('Tag creation did not target the expected commit')
        api.create_draft(tag, commit, 'Stay Sharp Medkit Reminder %s' % tag)
        # A newly created draft may briefly lag behind the list endpoint.
        # Retry only this post-create visibility check, not API failures.
        for attempt in range(6):
            release = api.get_release(tag)
            if release is not None:
                break
            if attempt < 5:
                time.sleep(1)
        if release is None:
            raise PublicationError('Draft not visible in GitHub listing after retries')

    if release.get('tag_name') != tag or release.get('prerelease') is not False:
        raise PublicationError('Unexpected tag/prerelease flags for Release')

    if release.get('draft') is False:
        verify_assets(api, release, tag, artifacts)
        print('Already published and verified (immutable):', release.get('html_url', tag))
        return 'verified_existing'
    if release.get('draft') is not True:
        raise PublicationError('Unknown draft state')

    # A previous run may have stopped after creating the draft or after
    # uploading the first file. Draft assets may safely be replaced.
    api.upload_draft(tag, artifacts.values())
    staged = api.get_release(tag)
    if staged is None or staged.get('draft') is not True:
        raise PublicationError('Draft disappeared or was published unexpectedly')
    if api.tag_commit(tag) != commit:
        raise PublicationError('Git tag changed during upload')
    verify_assets(api, staged, tag, artifacts)

    api.publish_draft(tag)
    published = api.get_release(tag)
    if published is None or published.get('draft') is not False:
        raise PublicationError('Release is not published after edit')
    if api.tag_commit(tag) != commit:
        raise PublicationError('Git tag changed during publication')
    verify_assets(api, published, tag, artifacts)
    print('Published and verified:', published.get('html_url', tag))
    return 'published'


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    tag = os.environ['RELEASE_TAG']
    version = os.environ['RELEASE_VERSION']
    commit = os.environ.get('RELEASE_COMMIT') or os.environ['GITHUB_SHA']
    api = GitHubCLI(repo)
    try:
        dist = Path(os.environ.get('STAYSHARP_DIST_DIR') or
                    (Path(__file__).resolve().parents[1] / 'dist'))
        publish(api, repo, tag, commit, version, dist)
    except PublicationError as exc:
        print('Release blocked:', exc, file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
