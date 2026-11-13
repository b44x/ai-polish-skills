"""Demo provenance/coverage and upstream-failure behavior, without network calls."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('demo_capture', ROOT/'docs/demo/capture.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class DemoContracts(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'docs/demo/demo_data.json').read_text())

    def test_every_registered_skill_has_one_successful_capture_and_adapter(self):
        expected = {s['name'] for s in json.loads((ROOT/'registry/registry.json').read_text())['skills']}
        scenes = self.data['scenes']
        self.assertTrue(self.data['complete'])
        self.assertEqual({s['skill'] for s in scenes}, expected)
        self.assertEqual(len(scenes), len(expected))
        self.assertEqual({fn.__name__.replace('scene_', '').replace('_', '-') for fn in M.SCENES}, expected)
        for scene in scenes:
            for run in scene['runs']:
                self.assertEqual(run['exitCode'], 0)
                self.assertIsInstance(run['output'], dict)
                self.assertTrue(run['capturedAt'])
                self.assertTrue((ROOT/run['command'][1]).is_file())

    def test_additional_cards_reproduce_their_raw_outputs(self):
        for scene in self.data['scenes']:
            if scene['skill'] in M.EXTRA_COMMANDS:
                self.assertEqual(scene, M.extra_scene(scene['skill'], scene['runs'][0]))

    def test_incomplete_or_duplicate_coverage_cannot_be_written_as_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)/'demo.json'
            for scenes in (self.data['scenes'][:-1], self.data['scenes']+[self.data['scenes'][0]]):
                with self.assertRaises(M.CaptureError):
                    M.write(str(dest), scenes, True)
            self.assertFalse(dest.exists())

    def test_failure_preserves_previous_canonical_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)/'demo.json'
            dest.write_text('previous canonical capture')
            def scene_test():
                raise M.CaptureError('upstream unavailable')
            with patch.object(M, 'SCENES', [scene_test]), patch('sys.argv', ['capture.py','--out',str(dest)]):
                self.assertEqual(M.main(), 69)
            self.assertEqual(dest.read_text(),'previous canonical capture')
            failed=json.loads(dest.with_suffix('.incomplete.json').read_text())
            self.assertFalse(failed['complete'])

    def test_throttling_does_not_trigger_automatic_retry(self):
        response=subprocess.CompletedProcess([],69,'',json.dumps({'error':'limit','type':'rate_limit','retry_after':'60'}))
        with patch.object(M.subprocess,'run',return_value=response) as run,patch.object(M.time,'sleep'):
            with self.assertRaises(M.CaptureError):M.run_skill('apteki','search','--city','Gdańsk')
        self.assertEqual(run.call_count,1)

    def test_usage_failure_does_not_trigger_retry(self):
        response=subprocess.CompletedProcess([],64,'',json.dumps({'error':'bad args'}))
        with patch.object(M.subprocess,'run',return_value=response) as run,patch.object(M.time,'sleep'):
            with self.assertRaises(M.CaptureError):M.run_skill('apteki','bad')
        self.assertEqual(run.call_count,1)


if __name__=='__main__':unittest.main()
