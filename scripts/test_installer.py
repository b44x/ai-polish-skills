"""Installer behavior, rollback and piped bootstrap regression tests (offline)."""
import argparse
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
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import installer

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source' / 'sample'
        (self.source / 'scripts').mkdir(parents=True)
        (self.source / 'scripts' / 'run.py').write_text('new version')
        self.skills = {'sample': {'_dir': str(self.source)}}
        self.target = self.root / 'target'

    def old_install(self):
        old = self.target / 'sample'
        old.mkdir(parents=True)
        (old / 'keep.txt').write_text('previous version')
        return old

    def test_dry_run_does_not_create_destination(self):
        result = installer.install(self.skills, [], self.target, dry_run=True)
        self.assertEqual(result['skills'], ['sample'])
        self.assertFalse(self.target.exists())

    def test_unknown_selection_prevents_all_writes(self):
        with self.assertRaises(installer.InstallError) as error:
            installer.install(self.skills, ['sample', '../source'], self.target)
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(self.target.exists())

    def test_successful_replacement_cleans_old_files_and_caches(self):
        self.old_install()
        cache = self.source / 'scripts' / '__pycache__'
        cache.mkdir()
        (cache / 'run.pyc').write_bytes(b'cached')
        result = installer.install(self.skills, ['sample', 'sample'], self.target)
        self.assertEqual(result['skills'], ['sample'])
        self.assertFalse((self.target / 'sample' / 'keep.txt').exists())
        script = self.target / 'sample' / 'scripts' / 'run.py'
        self.assertTrue(os.access(str(script), os.X_OK))
        self.assertFalse((script.parent / '__pycache__').exists())
        self.assertEqual([p.name for p in self.target.iterdir()], ['sample'])

    def test_copy_failure_preserves_previous_install(self):
        old = self.old_install()
        with patch.object(installer.shutil, 'copytree', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                installer.install(self.skills, [], self.target)
        self.assertEqual((old / 'keep.txt').read_text(), 'previous version')
        self.assertEqual([p.name for p in self.target.iterdir()], ['sample'])

    def test_failed_replacement_restores_previous_directory(self):
        old = self.old_install()
        original = os.replace
        def fail_new(src, dest):
            if Path(src).name == 'sample' and Path(dest) == old:
                raise OSError('replacement failed')
            return original(src, dest)
        with patch.object(installer.os, 'replace', side_effect=fail_new):
            with self.assertRaises(OSError):
                installer.install(self.skills, [], self.target)
        self.assertEqual((old / 'keep.txt').read_text(), 'previous version')

    def test_failed_restore_retains_backup_for_recovery(self):
        old = self.old_install()
        original = os.replace
        def fail_dest(src, dest):
            if Path(dest) == old:
                raise OSError('destination unavailable')
            return original(src, dest)
        with patch.object(installer.os, 'replace', side_effect=fail_dest):
            with self.assertRaises(installer.InstallError) as error:
                installer.install(self.skills, [], self.target)
        self.assertEqual(error.exception.code, 73)
        backups = list(self.target.glob('.ai-polish-skills-*/sample.backup/keep.txt'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'previous version')

    def test_source_overlap_is_rejected(self):
        for target in (self.source.parent, self.source):
            with self.subTest(target=target), self.assertRaises(installer.InstallError):
                installer.install(self.skills, [], target)
        self.assertTrue((self.source / 'scripts' / 'run.py').exists())

    def test_destination_symlink_is_rejected(self):
        self.target.mkdir()
        (self.target / 'sample').symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            installer.install(self.skills, [], self.target)
        self.assertTrue((self.source / 'scripts' / 'run.py').exists())

    def test_source_symlink_is_rejected(self):
        (self.source / 'link').symlink_to(self.source / 'scripts' / 'run.py')
        with self.assertRaises(installer.InstallError):
            installer.install(self.skills, [], self.target)
        self.assertFalse(self.target.exists())

    def test_update_preserves_unrelated_skills(self):
        self.old_install()
        foreign = self.target / 'another-skill'
        foreign.mkdir()
        (foreign / 'keep').write_text('mine')
        result = installer.install(self.skills, [], self.target, update=True)
        self.assertEqual(result['skills'], ['sample'])
        self.assertEqual((foreign / 'keep').read_text(), 'mine')

    def test_existing_lock_prevents_replacement(self):
        old = self.old_install()
        (self.target / '.ai-polish-skills.lock').mkdir()
        with self.assertRaises(installer.InstallError) as error:
            installer.install(self.skills, [], self.target)
        self.assertEqual(error.exception.code, 73)
        self.assertTrue((old / 'keep.txt').exists())


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cwd = self.root / 'project with spaces'
        self.cwd.mkdir()
        self.env = dict(os.environ, NO_COLOR='1')

    def run_cli(self, *args):
        return subprocess.run(['bash', str(ROOT / 'install.sh'), *args], cwd=self.cwd,
                              env=self.env, text=True, capture_output=True, timeout=20)

    def test_json_is_not_prefixed_by_banner_or_colors(self):
        result = self.run_cli('list', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(s['name'] == 'nbp' for s in json.loads(result.stdout)))
        self.assertNotIn('\x1b', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_legacy_shorthand_and_explicit_install_match(self):
        a = self.run_cli('nbp', '--dry-run', '--json')
        b = self.run_cli('install', 'nbp', '--dry-run', '--json')
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)
        self.assertFalse((self.cwd / '.agents').exists())

    def test_missing_directory_and_conflicting_flags_are_usage_errors(self):
        for args in (('--dir',), ('--dir', ''), ('--dir', 'x', '--global'), ('--claude', '--agents'), ('--unknown',)):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 64, result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertIn('error', json.loads(result.stderr))
        self.assertEqual(list(self.cwd.iterdir()), [])

    def test_unknown_info_returns_structured_not_found(self):
        result = self.run_cli('info', '__unknown__', '--json')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertEqual(json.loads(result.stderr)['type'], 'not_found')

    def test_target_defaults_and_legacy_aliases(self):
        (self.cwd / '.claude').mkdir()
        for args, suffix in (((), '.claude/skills'), (('--agents',), '.agents/skills'),
                             (('--antigravity',), '.agents/skills'), (('--global',), '.gemini/config/skills')):
            with self.subTest(args=args):
                result = self.run_cli('nbp', *args, '--dry-run', '--json')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)['target'].endswith(suffix))

    def test_all_selected_skills_install_from_outside_checkout(self):
        dest = self.cwd / 'custom skills'
        result = self.run_cli('dzialki', 'ostrzezenia-gis', 'produkty', '--dir', str(dest), '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(json.loads(result.stdout)['skills']), {'dzialki', 'ostrzezenia-gis', 'produkty'})
        for name in ('dzialki', 'ostrzezenia-gis', 'produkty'):
            self.assertTrue((dest / name / 'SKILL.md').is_file())
            for script in (dest / name / 'scripts').glob('*.py'):
                run = subprocess.run([sys.executable, str(script), '--help'], capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)

    def prepare_remote(self, unsafe=False):
        archive_path = self.root / 'archive.tar.gz'
        with tarfile.open(str(archive_path), 'w:gz') as archive:
            if unsafe:
                member = tarfile.TarInfo('../escaped')
                member.size = 1
                archive.addfile(member, io.BytesIO(b'x'))
            else:
                for name in ('cli.py', 'installer.py', 'manifest.py'):
                    archive.add(str(ROOT / 'scripts' / name), arcname='ai-polish-skills-main/scripts/' + name)
                archive.add(str(ROOT / 'skills' / 'nbp'), arcname='ai-polish-skills-main/skills/nbp')
        bindir = self.root / 'bin'
        bindir.mkdir()
        curl = bindir / 'curl'
        curl.write_text('#!' + sys.executable + '\nimport os,sys,shutil\n'
                        'if os.environ.get("FAIL_CURL"): sys.exit(22)\n'
                        'shutil.copyfile(os.environ["TEST_ARCHIVE"], sys.argv[sys.argv.index("--output")+1])\n')
        curl.chmod(0o755)
        tmpdir = self.root / 'tmp'
        tmpdir.mkdir()
        self.env.update(PATH=str(bindir) + os.pathsep + self.env['PATH'], TEST_ARCHIVE=str(archive_path), TMPDIR=str(tmpdir))
        return tmpdir

    def run_piped(self, *args):
        return subprocess.run(['bash', '-s', '--', *args], input=(ROOT / 'install.sh').read_text(),
                              cwd=self.cwd, env=self.env, text=True, capture_output=True, timeout=20)

    def test_remote_management_and_install_share_cli_and_cleanup(self):
        tmpdir = self.prepare_remote()
        result = self.run_piped('list', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([s['name'] for s in json.loads(result.stdout)], ['nbp'])
        self.assertEqual(list(tmpdir.iterdir()), [])
        result = self.run_piped('nbp', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.cwd / '.agents/skills/nbp/SKILL.md').is_file())
        self.assertEqual(list(tmpdir.iterdir()), [])

    def test_failed_download_does_not_create_target(self):
        tmpdir = self.prepare_remote()
        self.env['FAIL_CURL'] = '1'
        result = self.run_piped('nbp')
        self.assertEqual(result.returncode, 69)
        self.assertEqual(result.stdout, '')
        self.assertEqual(list(self.cwd.iterdir()), [])
        self.assertEqual(list(tmpdir.iterdir()), [])

    def test_archive_traversal_is_rejected_and_cleaned(self):
        tmpdir = self.prepare_remote(unsafe=True)
        result = self.run_piped('nbp')
        self.assertEqual(result.returncode, 69, result.stderr)
        self.assertEqual(list(tmpdir.iterdir()), [])
        self.assertEqual(list(self.cwd.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
