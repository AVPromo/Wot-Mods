"""Cold/warm bootstrap contracts, using real archive and checksum tools."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT/'scripts/sessionstats/python27.sh'
SOURCE_SHA256 = 'da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814'

LOG_CODE = '''
def record(name):
    with open(os.environ['COMMAND_LOG'], 'a') as stream:
        stream.write(json.dumps({'name': name, 'args': sys.argv[1:], 'cwd': os.getcwd()}) + '\\n')
'''


@unittest.skipUnless(all(shutil.which(name) for name in ('bash', 'tar', 'sha256sum')),
                     'Linux bootstrap tools are required')
class Python27BootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='synthetic-python27-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)/'runtime path with spaces'
        self.directory.mkdir()
        self.bin = self.directory/'commands'
        self.bin.mkdir()
        self.runtime_root = self.directory/'sessionstats-cpython27/Python-2.7.18'
        self.python = self.runtime_root/'python'
        self.environment = self.directory/'github-env'
        self.environment.write_text('EXISTING=value\n')
        self.log = self.directory/'commands.jsonl'
        self.template = self.directory/'synthetic-python'
        self.executable(self.template, '''
import builtins, hashlib, io, json, marshal, os, sys, types, zipfile, zlib
''' + LOG_CODE + '''
record('python')
assert sys.argv[1:] == ['-B', '-E', '-s', '-']
mode = os.environ.get('PYTHON27_FIXTURE_MODE', 'valid')
sys.version_info = (3, 12, 0) if mode == 'version' else (2, 7, 18)
imp = types.ModuleType('imp')
sys.modules['imp'] = imp
imp.get_magic = lambda: b'BAD!' if mode == 'magic' else b'\\x03\\xf3\\r\\n'
if mode == 'crash':
    raise SystemExit(17)
if mode == 'module':
    original_import = builtins.__import__
    def missing_module(name, *args, **kwargs):
        if name == 'zlib':
            raise ImportError('Synthetic missing zlib')
        return original_import(name, *args, **kwargs)
    builtins.__import__ = missing_module
exec(compile(sys.stdin.read(), '<synthetic-runtime-probe>', 'exec'))
''')
        configure = '''
import json, os, sys
''' + LOG_CODE + '''
record('configure')
raise SystemExit(19 if os.environ.get('BOOTSTRAP_FAILURE') == 'configure' else 0)
'''
        self.archive = self.directory/'synthetic-source.tgz'
        with tarfile.open(self.archive, 'w:gz') as archive:
            data = self.executable_bytes(configure)
            entry = tarfile.TarInfo('Python-2.7.18/configure')
            entry.mode = 0o755
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        original = BOOTSTRAP.read_text()
        self.assertEqual(original.count(SOURCE_SHA256), 1)
        self.script = self.directory/'bootstrap.sh'
        # The synthetic archive has its own exact digest. The production source
        # pin is checked above; real sha256sum and tar still exercise fail-closed flow.
        self.script.write_text(original.replace(SOURCE_SHA256, digest))
        self.executable(self.bin/'curl', '''
import json, os, shutil, sys
''' + LOG_CODE + '''
record('curl')
if os.environ.get('BOOTSTRAP_FAILURE') == 'download':
    raise SystemExit(22)
output = sys.argv[sys.argv.index('--output') + 1]
shutil.copyfile(os.environ['PYTHON27_SOURCE_FIXTURE'], output)
if os.environ.get('BOOTSTRAP_FAILURE') == 'checksum':
    with open(output, 'ab') as stream:
        stream.write(b'corrupted')
''')
        self.executable(self.bin/'make', '''
import json, os, shutil, sys
''' + LOG_CODE + '''
record('make')
if os.environ.get('BOOTSTRAP_FAILURE') == 'compile':
    raise SystemExit(23)
shutil.copyfile(os.environ['PYTHON27_RUNTIME_FIXTURE'], 'python')
os.chmod('python', 0o755)
''')
        self.env = dict(os.environ)
        self.env.update({
            'RUNNER_TEMP': str(self.directory), 'GITHUB_ENV': str(self.environment),
            'PATH': str(self.bin) + os.pathsep + self.env.get('PATH', ''),
            'COMMAND_LOG': str(self.log), 'PYTHON27_SOURCE_FIXTURE': str(self.archive),
            'PYTHON27_RUNTIME_FIXTURE': str(self.template),
        })
        self.env.pop('BOOTSTRAP_FAILURE', None)
        self.env.pop('PYTHON27_FIXTURE_MODE', None)

    @staticmethod
    def executable_bytes(body):
        return ('#!' + sys.executable + '\n' + body.lstrip()).encode()

    def executable(self, path, body):
        path.write_bytes(self.executable_bytes(body))
        path.chmod(0o755)

    def run_bootstrap(self):
        return subprocess.run(['bash', str(self.script)], cwd=self.directory,
                              env=self.env, capture_output=True, text=True, timeout=15)

    def events(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def cached_runtime(self):
        self.runtime_root.mkdir(parents=True)
        shutil.copyfile(self.template, self.python)
        self.python.chmod(0o755)

    def assert_unexported(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.environment.read_text(), 'EXISTING=value\n')

    def test_cold_build_verifies_archive_and_runtime_before_export(self):
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = self.events()
        self.assertEqual([event['name'] for event in events], ['curl', 'configure', 'make', 'python'])
        self.assertIn('https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz', events[0]['args'])
        self.assertEqual(events[0]['args'][:7], ['--fail', '--location', '--retry', '3', '--proto', '=https', '--tlsv1.2'])
        self.assertEqual(events[1]['args'], ['--without-ensurepip'])
        self.assertEqual(events[2]['args'], ['-j2'])
        self.assertEqual(events[2]['cwd'], str(self.runtime_root))
        self.assertEqual(events[3]['args'], ['-B', '-E', '-s', '-'])
        self.assertEqual(self.environment.read_text(), 'EXISTING=value\nPYTHON27=' + str(self.python) + '\n')

    def test_warm_cache_only_runs_the_probe_and_preserves_cached_files(self):
        self.cached_runtime()
        marker = self.runtime_root/'keep'
        marker.write_text('existing build')
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([event['name'] for event in self.events()], ['python'])
        self.assertEqual(marker.read_text(), 'existing build')
        self.assertIn('Reusing verified CPython 2.7.18', result.stdout)
        self.assertEqual(self.environment.read_text(), 'EXISTING=value\nPYTHON27=' + str(self.python) + '\n')

    def test_same_job_second_call_reuses_the_successfully_built_runtime(self):
        self.assertEqual(self.run_bootstrap().returncode, 0)
        self.assertEqual(self.run_bootstrap().returncode, 0)
        self.assertEqual([event['name'] for event in self.events()], ['curl', 'configure', 'make', 'python', 'python'])

    def test_bad_cached_runtime_never_downloads_rebuilds_or_exports(self):
        for mode in ('version', 'magic', 'module', 'crash'):
            with self.subTest(mode=mode):
                if self.runtime_root.exists():
                    shutil.rmtree(self.runtime_root)
                self.cached_runtime()
                self.log.unlink(missing_ok=True)
                self.env['PYTHON27_FIXTURE_MODE'] = mode
                result = self.run_bootstrap()
                self.assert_unexported(result)
                self.assertEqual([event['name'] for event in self.events()], ['python'])
                self.assertIn('Restored Python 2.7 runtime failed verification', result.stderr)

    def test_incomplete_cached_runtime_fails_before_running_any_command(self):
        self.runtime_root.mkdir(parents=True)
        result = self.run_bootstrap()
        self.assert_unexported(result)
        self.assertEqual(self.events(), [])
        self.assertIn('runtime is incomplete', result.stderr)

    def test_nonexecutable_or_symlinked_cached_binary_is_rejected(self):
        self.cached_runtime()
        self.python.chmod(0o644)
        self.assert_unexported(self.run_bootstrap())
        self.python.unlink()
        self.python.symlink_to(self.template)
        self.assert_unexported(self.run_bootstrap())
        self.assertEqual(self.events(), [])

    def test_symlinked_runtime_directory_is_rejected(self):
        self.runtime_root.parent.mkdir(parents=True)
        target = self.directory/'unrelated-runtime'
        target.mkdir()
        self.runtime_root.symlink_to(target, target_is_directory=True)
        self.assert_unexported(self.run_bootstrap())
        self.assertTrue(target.is_dir())
        self.assertEqual(self.events(), [])

    def test_download_checksum_configure_and_compile_failures_block_export(self):
        expected = {'download': ['curl'], 'checksum': ['curl'],
                    'configure': ['curl', 'configure'], 'compile': ['curl', 'configure', 'make']}
        for failure, commands in expected.items():
            with self.subTest(failure=failure):
                build = self.directory/'sessionstats-cpython27'
                if build.exists():
                    shutil.rmtree(build)
                self.log.unlink(missing_ok=True)
                self.env['BOOTSTRAP_FAILURE'] = failure
                self.assert_unexported(self.run_bootstrap())
                self.assertEqual([event['name'] for event in self.events()], commands)
                if failure in ('download', 'checksum'):
                    self.assertFalse(self.runtime_root.exists())

    def test_failed_probe_after_cold_build_blocks_export(self):
        self.env['PYTHON27_FIXTURE_MODE'] = 'version'
        self.assert_unexported(self.run_bootstrap())
        self.assertEqual([event['name'] for event in self.events()], ['curl', 'configure', 'make', 'python'])

    def test_tempdir_fallback_preserves_the_existing_path_contract(self):
        self.env.pop('RUNNER_TEMP')
        self.env['TMPDIR'] = str(self.directory)
        self.cached_runtime()
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.environment.read_text(), 'EXISTING=value\nPYTHON27=' + str(self.python) + '\n')

    def test_line_breaks_cannot_inject_environment_values(self):
        for separator in ('\n', '\r'):
            with self.subTest(separator=repr(separator)):
                self.env['RUNNER_TEMP'] = str(self.directory) + separator + 'INJECTED=value'
                result = self.run_bootstrap()
                self.assert_unexported(result)
                self.assertEqual(self.events(), [])

    def test_missing_environment_output_fails_before_download(self):
        self.env.pop('GITHUB_ENV')
        result = self.run_bootstrap()
        self.assert_unexported(result)
        self.assertEqual(self.events(), [])


if __name__ == '__main__':
    unittest.main()
