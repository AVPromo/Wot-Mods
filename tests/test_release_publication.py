"""Offline, end-to-end tests of the native GitHub CLI release workflow.

A fake executable `gh` and `git` simulates API data and error conditions.
Production contains no custom GitHub REST/HTTP client and never requires Java.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / 'scripts/publish_release.sh'
VERSION = '1.6.7'
TAG = 'v' + VERSION
SHA = 'a' * 40
OTHER_SHA = 'b' * 40
REPO = 'example/WotMods'

CLI_STUB = r'''#!/usr/bin/python3
import base64, json, os, pathlib, sys
statefile=pathlib.Path(os.environ['FAKE_STATE'])
state=json.loads(statefile.read_text())
args=sys.argv[1:]
cmd=os.path.basename(sys.argv[0])
state['actions'].append([cmd]+args)

def save(): statefile.write_text(json.dumps(state))
def fail(message):
    save()
    print(message, file=sys.stderr)
    sys.exit(1)

def field(flag,default=None):
    try: return args[args.index(flag)+1]
    except ValueError: return default

if cmd=='git':
    if args[:2]==['ls-remote','--tags']:
        tag=args[-2].split('/')[-1].split('^{')[0]
        sha=state['tags'].get(tag)
        if sha: print(sha+'\trefs/tags/'+tag)
        save();sys.exit(0)
    if args[:1]==['tag'] and len(args)==3:
        tag,commit=args[1:]
        if tag in state['local_tags']: fail('Local tag already exists')
        state['local_tags'][tag]=commit
        save();sys.exit(0)
    if args[:2]==['push','origin'] and len(args)==3:
        tag=args[2].split('/')[-1].split(':')[0]
        if tag not in state['local_tags']: fail('Missing local tag before push')
        if tag in state['tags']: fail('Remote tag already exists')
        if os.environ.get('FAKE_FAIL_PUSH_TAG')=='1': fail('Simulated tag push failure')
        state['tags'][tag]=state['local_tags'][tag]
        save();sys.exit(0)
    fail('Unexpected git operation')
if cmd=='gh' and args[:2]==['auth','setup-git']:
    save();sys.exit(0)
if cmd!='gh' or len(args)<2 or args[0]!='release': fail('No native gh release')
operation=args[1]
if operation=='list':
    if os.environ.get('FAKE_LIST_FAILURE')=='1': fail('Simulated listing failure')
    snap=[{'tagName':k,'isDraft':v['draft'],'isPrerelease':v.get('prerelease',False)}
          for k,v in state['releases'].items()]
    if os.environ.get('FAKE_PUBLISH_AFTER_LIST')=='1':
        for entry in state['releases'].values():
            entry['draft']=False
    print(json.dumps(snap))
if operation=='create':
    tag=args[2]
    if tag in state['releases']: fail('Release already exists')
    if '--verify-tag' not in args or tag not in state['tags']: fail('Tag must exist BEFORE creating a draft')
    release={'draft':True,'prerelease':False,'assets':{}}
    state['releases'][tag]=release
    if os.environ.get('FAKE_FAIL_CREATE_AFTER_DRAFT')=='1':
        fail('Interrupted after creating draft')
    paths=[]
    for v in args[3:]:
        if v.startswith('--'): break
        paths.append(pathlib.Path(v))
    for p in paths:
        release['assets'][p.name]=base64.b64encode(p.read_bytes()).decode('ascii')
    release['draft']=False
if operation=='delete':
    tag=args[2]
    if os.environ.get('FAKE_DELETE_FAILURE')=='1': fail('Cannot delete draft')
    if tag not in state['releases'] or not state['releases'][tag]['draft']:
        fail('Not a draft')
    state['releases'].pop(tag)
if operation=='view':
    tag=args[2]
    release=state['releases'].get(tag)
    if not release or release['draft']: fail('Release not found')
    assets=[{'name':k,'size':len(base64.b64decode(v))} for k,v in release['assets'].items()]
    print(json.dumps({'tagName':tag,'isDraft':False,'isPrerelease':release['prerelease'],
                      'assets':assets,'url':'https://github.com/example/WotMods/releases/tag/'+tag}))
if operation=='download':
    tag=args[2]
    release=state['releases'].get(tag)
    if not release or release['draft']: fail('Release not found')
    target=pathlib.Path(field('--dir'))
    target.mkdir(parents=True,exist_ok=True)
    for k,v in release['assets'].items():
        if k in [args[i+1] for i,elm in enumerate(args) if elm=='--pattern']:
            (target/k).write_bytes(base64.b64decode(v))
save()
'''


class NativeReleaseTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.work = Path(self.dir.name)
        self.bin = self.work / 'bin'
        self.bin.mkdir()
        stub = self.bin / 'gh'
        stub.write_text(CLI_STUB)
        stub.chmod(0o755)
        (self.bin / 'git').symlink_to(stub)
        self.dist = self.work / 'dist'
        self.dist.mkdir()
        self.mod = self.dist / ('com.staysharp.medkitreminder_%s.wotmod' % VERSION)
        self.mod.write_bytes(b'wotmod-test-binary--NoCredentials')
        self.manifest = self.dist / 'SHA256SUMS.txt'
        self.manifest.write_text(hashlib.sha256(self.mod.read_bytes()).hexdigest() +
                                 '  ' + self.mod.name + '\n',encoding='ascii')
        self.state_path = self.work / 'github.json'
        self.state = {'tags':{},'local_tags':{},'releases':{},'actions':[]}
        self.store()

    def store(self):
        self.state_path.write_text(json.dumps(self.state))

    def load(self):
        self.state = json.loads(self.state_path.read_text())
        return self.state

    def already_published(self, tag=TAG, commit=SHA, missing=False, corrupt=False):
        assets = {
            self.mod.name:base64.b64encode(b'corruption' if corrupt else self.mod.read_bytes()).decode('ascii'),
            self.manifest.name:base64.b64encode(self.manifest.read_bytes()).decode('ascii'),
        }
        if missing: assets.pop(self.mod.name)
        self.state['tags'][tag]=commit
        self.state['releases'][tag]={'draft':False,'prerelease':False,'assets':assets}
        self.store()

    def run_native(self,recovery=False,extra=None):
        env = os.environ.copy()
        env.update(PATH=str(self.bin) + os.pathsep + env['PATH'],
                   FAKE_STATE=str(self.state_path), GH_TOKEN='fake-not-secret',
                   GITHUB_REPOSITORY=REPO, RELEASE_TAG=TAG,
                   RELEASE_VERSION=VERSION, RELEASE_COMMIT=SHA,
                   STAYSHARP_RECOVERY_MODE='1' if recovery else '0',
                   STAYSHARP_DIST_DIR=str(self.dist))
        env.update(extra or {})
        return subprocess.run(['bash',str(PUBLISHER)],cwd=ROOT,env=env,
                              text=True,capture_output=True,check=False)

    def assert_ok(self,r):
        self.assertEqual(r.returncode,0,r.stderr+'\n'+r.stdout)

    def test_new_release_is_created_with_both_assets(self):
        r=self.run_native();self.assert_ok(r)
        state=self.load()
        self.assertEqual(state['tags'][TAG],SHA)
        self.assertFalse(state['releases'][TAG]['draft'])
        self.assertEqual(set(state['releases'][TAG]['assets']),{self.mod.name,self.manifest.name})
        self.assertIn('Published and verified',r.stdout)
        actions=state['actions']
        auth=next(i for i,a in enumerate(actions) if a[:3]==['gh','auth','setup-git'])
        tag=next(i for i,a in enumerate(actions) if a[:2]==['git','tag'])
        push=next(i for i,a in enumerate(actions) if a[:2]==['git','push'])
        create=next(i for i,a in enumerate(actions) if a[:3]==['gh','release','create'])
        self.assertLess(auth,tag)
        self.assertLess(tag,push)
        self.assertLess(push,create)
        self.assertIn('--verify-tag',actions[create])
        self.assertNotIn('--latest=false',actions[create])

    def test_existing_correct_release_is_verified_without_mutation(self):
        self.already_published()
        r=self.run_native();self.assert_ok(r)
        actions=self.load()['actions']
        self.assertFalse(any(a[:3] in (['gh','release','create'],['gh','release','delete']) for a in actions))

    def test_existing_release_corrupt_asset_rejected(self):
        self.already_published(corrupt=True)
        r=self.run_native();self.assertNotEqual(r.returncode,0)
        self.assertIn('differs',r.stderr)

    def test_published_release_with_missing_asset_fails(self):
        self.already_published(missing=True)
        r=self.run_native();self.assertNotEqual(r.returncode,0)
        self.assertIn('incomplete',r.stderr)

    def test_wrong_tag_commit_fails_before_release_write(self):
        self.state['tags'][TAG]=OTHER_SHA;self.store()
        r=self.run_native();self.assertNotEqual(r.returncode,0)
        self.assertIn('belongs to',r.stderr)
        self.assertFalse(any(a[:3]==['gh','release','create'] for a in self.load()['actions']))

    def test_draft_blocks_normal_release(self):
        self.state['tags'][TAG]=SHA
        self.state['releases'][TAG]={'draft':True,'prerelease':False,'assets':{}}
        self.store()
        r=self.run_native();self.assertNotEqual(r.returncode,0)
        self.assertIn('Recovery workflow',r.stderr)
        self.assertTrue(self.load()['releases'][TAG]['draft'])

    def test_recovery_never_automatically_deletes_a_draft(self):
        self.state['tags'][TAG]=SHA
        self.state['releases'][TAG]={'draft':True,'prerelease':False,'assets':{}}
        self.store()
        r=self.run_native(recovery=True)
        self.assertNotEqual(r.returncode,0)
        self.assertIn('manually delete ONLY the draft',r.stderr)
        state=self.load()
        self.assertTrue(state['releases'][TAG]['draft'])
        self.assertFalse(any(a[:3]==['gh','release','delete'] for a in state['actions']))
        self.assertFalse(any(a[:3]==['gh','release','create'] for a in state['actions']))

    def test_recovery_after_manual_draft_deletion_keeps_existing_tag(self):
        self.state['tags'][TAG]=SHA
        self.state['releases'][TAG]={'draft':True,'prerelease':False,'assets':{}}
        self.store()
        blocked=self.run_native(recovery=True)
        self.assertNotEqual(blocked.returncode,0)
        # Manual maintenance in GitHub UI, outside this privileged workflow.
        self.load()['releases'].pop(TAG)
        self.store()
        result=self.run_native(recovery=True)
        self.assert_ok(result)
        state=self.load()
        self.assertEqual(state['tags'][TAG],SHA)
        self.assertFalse(state['releases'][TAG]['draft'])
        self.assertFalse(any(a[:3]==['gh','release','delete'] for a in state['actions']))
        self.assertFalse(any(a[:2]==['git','push'] for a in state['actions']))
        creates=[a for a in state['actions'] if a[:3]==['gh','release','create']]
        self.assertEqual(len(creates),1)
        self.assertIn('--verify-tag', creates[0])
        self.assertNotIn('--latest=false',creates[0])

    def test_tagless_draft_is_detected_and_never_implicitly_tagged(self):
        self.state['releases'][TAG]={'draft':True,'prerelease':False,'assets':{}}
        self.store()
        result=self.run_native(recovery=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('manually delete ONLY the draft',result.stderr)
        state=self.load()
        self.assertNotIn(TAG,state['tags'])
        self.assertTrue(state['releases'][TAG]['draft'])
        self.assertFalse(any(a[:2] in (['git','push'],['git','tag']) for a in state['actions']))

    def test_draft_published_after_listing_is_never_deleted(self):
        self.state['tags'][TAG]=SHA
        self.state['releases'][TAG]={'draft':True,'prerelease':False,'assets':{}}
        self.store()
        result=self.run_native(recovery=True,extra={'FAKE_PUBLISH_AFTER_LIST':'1'})
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.load()['releases'][TAG]['draft'])
        self.assertFalse(any(a[:3]==['gh','release','delete'] for a in self.load()['actions']))

    def test_push_tag_failure_never_creates_a_draft(self):
        result=self.run_native(extra={'FAKE_FAIL_PUSH_TAG':'1'})
        self.assertNotEqual(result.returncode,0)
        state=self.load()
        self.assertNotIn(TAG,state['tags'])
        self.assertNotIn(TAG,state['releases'])
        self.assertFalse(any(a[:3]==['gh','release','create'] for a in state['actions']))

    def test_recover_wrong_tag_sha_never_deletes(self):
        self.state['tags'][TAG]=OTHER_SHA
        self.state['releases'][TAG]={'draft':True,'prerelease':False,'assets':{}}
        self.store()
        r=self.run_native(recovery=True)
        self.assertNotEqual(r.returncode,0)
        self.assertFalse(any(a[:3]==['gh','release','delete'] for a in self.load()['actions']))

    def test_partial_create_leaves_draft_detected_next_attempt(self):
        r=self.run_native(extra={'FAKE_FAIL_CREATE_AFTER_DRAFT':'1'})
        self.assertNotEqual(r.returncode,0)
        self.assertTrue(self.load()['releases'][TAG]['draft'])
        self.assertEqual(self.load()['tags'][TAG],SHA)
        r=self.run_native()
        self.assertNotEqual(r.returncode,0)
        self.assertIn('Recovery workflow',r.stderr)

    def test_bad_manifest_fails_before_github_calls(self):
        self.manifest.write_text('bad hash\n')
        r=self.run_native();self.assertNotEqual(r.returncode,0)
        self.assertEqual(self.load()['actions'],[])

    def test_github_listing_failure_fails_closed(self):
        r=self.run_native(extra={'FAKE_LIST_FAILURE':'1'})
        self.assertNotEqual(r.returncode,0)
        self.assertIn('Cannot list',r.stderr)

    def test_no_homegrown_http_or_gh_api(self):
        code=PUBLISHER.read_text()
        self.assertNotIn('gh api',code)
        self.assertNotIn('urllib',code)
        self.assertNotIn('https://api.github.com',code)
        self.assertNotIn('curl ',code)
        self.assertNotIn('java ',code)
        for workflow in ('release.yml','recover.yml'):
            source=(ROOT/'.github/workflows'/workflow).read_text()
            self.assertIn('publish_release.sh',source)
            self.assertNotIn('publish_release.py',source)
            self.assertNotIn('gh api',source)
        self.assertFalse((ROOT/'scripts/publish_release.py').exists())

    def test_no_unexpected_release_cli_actions(self):
        self.run_native()
        for args in self.load()['actions']:
            if args[0] == 'gh' and args[1] == 'auth':
                self.assertEqual(args[2:],[ 'setup-git','--hostname','github.com'])
            elif args[0] == 'gh':
                self.assertEqual(args[1], 'release')
                self.assertIn(args[2], {'create','list','view','download'})
            elif args[0] == 'git':
                self.assertIn(args[1], {'ls-remote','tag','push'})


if __name__=='__main__':
    unittest.main()
