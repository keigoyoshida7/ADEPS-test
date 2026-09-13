"""Release-plumbing fixtures only: no corpus, real final test or GPU is read."""
import contextlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import package_plus as p


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(p.dump(value))


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'work/plus-v1'
        self.work.mkdir(parents=True)
        for module, attribute, value in [(p, 'ROOT', self.root), (p, 'WORK', self.work)]:
            context = patch.object(module, attribute, value); context.start(); self.addCleanup(context.stop)

    def fixture(self):
        selection = {'model_weights_sha256': 'a' * 64}
        lock = {'source_sha256': {}, 'source_set_sha256': 'b' * 64, 'input_sha256': {},
                'input_set_sha256': 'c' * 64, 'selection': selection}
        for name, value in [('selection-lock.json', lock), ('selection.json', selection), ('dps-selection.json', {})]:
            save(self.work / name, value)
        lock_sha = p.digest(self.work / 'selection-lock.json')
        environment = {'selection_lock_sha256': lock_sha}
        save(self.work / 'final/environment.json', environment)
        pin = {'cases': [], 'scene_manifest_sha256': 'd' * 64}
        scenes, case_hashes, metadata = [], {}, {}
        for index in range(32):
            source = self.work / 'cache/test' / f'{index:04d}.npz'
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(f'NOT A REAL NPZ: packaging fixture {index}'.encode())
            pin['cases'].append({'index': index, 'path': str(source.relative_to(self.root)), 'sha256': p.digest(source)})
            meta = {'id': f'fixture-{index}', 'cluster_id': f'pair-{index // 8}'}
            metadata[index] = meta
            row = {**meta, 'metrics': {}, 'curves': {}, 'outcomes': {}, 'runtime': {}}
            for method in p.METHODS:
                failed = index == 0 and method == 'plus'
                case = {'input_sha256': p.digest(source), 'metrics': {'fixture': None if failed else 1},
                        'curves': {'fixture': [None] if failed else [1]}, 'outcome': 'failed' if failed else 'completed',
                        'seconds': 0., 'nfe': None if failed else 0, 'vjp': None if failed else 0,
                        'memory': {}, 'diagnostics': {'fixture': 'No model/data calculation'}, 'details': {}}
                path = self.work / 'final' / f'{index:04d}' / f'{method}.json'
                save(path, case); case_hashes[str(path.relative_to(self.root))] = p.digest(path)
                for key in ('metrics', 'curves'): row[key][method] = case[key]
                row['outcomes'][method] = case['outcome']
                row['runtime'][method] = {key: case[key] for key in ('seconds', 'nfe', 'vjp', 'memory')}
            scenes.append(row)
        save(self.work / 'final/input-lock.json', pin)
        audio = {'dataset': 'VCTK 0.92', 'license': 'CC-BY-4.0', 'source_doi': 'https://doi.org/10.7488/ds/2645',
                 'files': [{'speaker': 'fixture-speaker', 'archive_member': 'no-real-audio.flac', 'sha256': 'e' * 64}], 'attribution_files': []}
        for name in ['VCTK-README.txt', 'VCTK-license.txt']:
            path = self.work / 'sealed-data/source' / name
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text('Fixture credit, not a real license')
            audio['attribution_files'].append({'path': name, 'sha256': p.digest(path)})
        for name in ['audio-manifest.json', 'scene-manifest.json', 'subset-plan.json']:
            save(self.work / 'sealed-data' / name, audio if name == 'audio-manifest.json' else {'fixture': True})
        report = {'selection': selection, 'scenes': scenes, 'provenance': {
            'lock_sha256': lock_sha, **{key: lock[key] for key in ['source_sha256', 'source_set_sha256', 'input_sha256', 'input_set_sha256']},
            'test_input_lock_sha256': p.digest(self.work / 'final/input-lock.json'), 'test_inputs': pin,
            'environment': environment, 'case_sha256': case_hashes}}
        save(self.work / 'benchmark.json', report)
        self.contexts = contextlib.ExitStack(); self.addCleanup(self.contexts.close)
        self.contexts.enter_context(patch.object(p, 'validate_benchmark'))
        self.verifier = self.contexts.enter_context(patch.object(p.benchmark, 'verify_lock', return_value=lock))
        self.contexts.enter_context(patch.object(p.benchmark, 'pin_test_inputs', return_value=(pin, {}, audio)))
        self.contexts.enter_context(patch.object(p.benchmark, 'load_final_scene', side_effect=lambda path, index, *args: ({}, metadata[index])))
        self.case_verifier = self.contexts.enter_context(patch.object(p.benchmark, 'validate_case', side_effect=lambda path, *args: p.benchmark.read_json(path)))
        return report, lock, pin, audio

    def test_all_cases_checked_failures_retained_and_inputs_unchanged(self):
        report, lock, pin, audio = self.fixture()
        verified = p.verify_completed()
        self.assertEqual(verified[-1], {'completed': 287, 'failed': 1})
        self.verifier.assert_called_once(); self.assertEqual(self.case_verifier.call_count, 288)
        save(self.work / 'development/candidate/summary.json', {'fixture': True})
        (self.work / 'development/candidate/huge-estimate.npz').write_bytes(b'Never include estimates')
        records, inputs, notes = p.collect_entries(*verified)
        self.assertEqual(sum(name.endswith('.npz') for name in inputs), 32)
        self.assertFalse(any(name.endswith(('.npz', '.pt', '.flac', '.py')) for name in records))
        self.assertIn('development/candidate/summary.json', notes['supplementary_evidence_not_part_of_pre_test_input_seal'])
        path = self.root / 'inputs.zip'
        first = p.write_archive(path, inputs, notes, 'benchmark-inputs')
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read('MANIFEST.json'))
            self.assertEqual(set(manifest['files']), set(inputs))
            for item in pin['cases']:
                name = f'cache/test/{item["index"]:04d}.npz'
                self.assertEqual(archive.read(name), (self.root / item['path']).read_bytes())
                self.assertEqual(manifest['files'][name]['sha256'], item['sha256'])
            self.assertIn(b'BENCHMARK CACHE FORMAT IS NOT THE INFERENCE CLI FORMAT', archive.read('README.txt'))
        second = p.write_archive(self.root / 'again.zip', inputs, notes, 'benchmark-inputs')
        self.assertEqual(first, second)

    def test_incomplete_report_and_missing_case_fail_closed(self):
        with self.assertRaises(FileNotFoundError): p.verify_completed()
        self.fixture()
        (self.work / 'final/0031/plus.json').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or unexpected'): p.verify_completed()

    def test_changed_cache_and_case_hash_are_rejected(self):
        self.fixture()
        source = self.work / 'cache/test/0000.npz'; original = source.read_bytes()
        source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'input changed'): p.verify_completed()
        source.write_bytes(original)
        save(self.work / 'final/0000/plus.json', {'replaced': True})
        with self.assertRaisesRegex(ValueError, 'case changed'): p.verify_completed()

    def test_zip_source_mutation_and_unsafe_member_rejected(self):
        source = self.root / 'record.json'; source.write_bytes(b'original')
        entries = {}; p.add(entries, 'record.json', source)
        with self.assertRaises(ValueError): p.add({}, '../escape', b'fixture')
        source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed during packaging'):
            p.write_archive(self.root / 'bad.zip', entries, {}, 'fixture')


if __name__ == '__main__':
    unittest.main()
