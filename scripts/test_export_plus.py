"""CPU presentation tests using memory-only synthetic coefficients, never public data."""
from __future__ import annotations

import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import unittest

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_plus as exporter
from diffusion_studio import covariance, frequency_metrics, real_wave_foa
from plus_consistency import synthesize_spectra


class ExportPlusTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(57191)
        self.reference = (rng.normal(size=(257, 4, 32)) + 1j*rng.normal(size=(257, 4, 32))) * .02
        self.reference[[0, -1]] = self.reference[[0, -1]].real
        self.data = {'reference': self.reference, 'p': self.reference[:, :4],
            'V': np.broadcast_to(np.eye(4, 36), (257, 4, 36)),
            'frequencies': exporter.FREQUENCIES,
            'positions': np.array([[.06, 0, 0], [-.06, 0, 0], [0, .06, 0], [0, -.06, 0]])}
        self.arrays = {key: self.reference*(.7+i*.1) for i, key in enumerate(exporter.METHOD_IDS)}
        self.methods = [{'id': key, 'label_jp': f'試験方式 {i}', 'label_en': f'Test method {i}'}
                        for i, key in enumerate(exporter.METHOD_IDS)]
        self.cases = {key: {'metrics': {'nrmse_db': -3., 'coherence': 1., 'si_sdr_db': None},
                           'details': {'frequency_metrics': frequency_metrics(value, self.reference, exporter.FREQUENCIES)}}
                      for key, value in self.arrays.items()}
        self.credit = {'title': 'Synthetic unit fixture, no speech', 'corpus': 'Synthetic unit fixture',
            'license': 'Fixture only', 'license_url': 'https://example.org/license',
            'source_url': 'https://example.org/source', 'speakers': [], 'files': [], 'changes': 'No actual corpus used.'}

    def build(self):
        return exporter.build_example(self.data, {'id': 'cpu-fixture-0000'}, self.arrays,
            self.cases, self.methods, self.credit, 'a'*64, {'test_fixture_only': True})

    def test_all_methods_share_exact_crop_gain_pcm16_and_covariance_gain_squared(self):
        example, wavs = self.build()
        exporter.validate_example(example)
        self.assertEqual(len(wavs), 20)
        self.assertEqual(example['audio']['full_synthesis_samples'], 4480)
        self.assertEqual(example['audio']['samples'], 3968)
        self.assertEqual(example['audio']['duration_seconds'], .248)
        self.assertEqual(example['scene_index'], 0)
        gain = example['shared_gain']
        maximum = 0.
        for item in [example['reference'], *example['estimates']]:
            key = item['id']
            spectra = self.reference if key == 'reference' else self.arrays[key]
            foa = real_wave_foa(spectra)
            unscaled = synthesize_spectra(foa)[:, 256:-256].T
            rate, audio = wavfile.read(io.BytesIO(wavs[f'foa/{key}_FOA_ACN_N3D.wav']))
            self.assertEqual(rate, 16000)
            self.assertEqual(audio.shape, (3968, 4))
            self.assertEqual(audio.dtype, np.float32)
            np.testing.assert_array_equal(audio, (unscaled*gain).astype(np.float32))
            maximum = max(maximum, float(abs(audio).max()))
            rate, preview = wavfile.read(io.BytesIO(base64.b64decode(item['preview_wav_base64'])))
            self.assertEqual(preview.shape, (3968, 2))
            self.assertEqual(preview.dtype, np.int16)
            expected = np.rint((unscaled*gain @ exporter.PREVIEW_MATRIX.T)*32767).astype(np.int16)
            np.testing.assert_array_equal(preview, expected)
            self.assertEqual(base64.b64decode(item['preview_wav_base64']), wavs[f'preview/{key}_stereo.wav'])
            for band, raw in covariance(foa, exporter.FREQUENCIES).items():
                np.testing.assert_allclose(item['covariance'][band], np.asarray(raw)*gain**2, atol=1e-17, rtol=1e-12)
        self.assertAlmostEqual(maximum, .95, places=6)
        self.assertEqual(len({item['frequency_metrics']['magnitude_floor_absolute']
                              for item in [example['reference'], *example['estimates']]}), 1)
        json.dumps(example, allow_nan=False)

    def test_saved_scores_are_preserved_and_reference_is_not_fake_finite_accuracy(self):
        example, _ = self.build()
        self.assertIsNone(example['reference']['metrics']['nrmse_db'])
        self.assertIsNone(example['reference']['metrics']['si_sdr_db'])
        for item in example['estimates']:
            self.assertEqual(item['metrics'], self.cases[item['id']]['metrics'])
            self.assertEqual(item['frequency_metrics'], self.cases[item['id']]['details']['frequency_metrics'])
        self.assertEqual(example['audio']['attribution'], self.credit)
        self.assertFalse(example['official_model'])
        self.assertFalse(example['paper_performance_reproduced'])

    def test_different_saved_reference_floor_is_rejected(self):
        self.cases['plus']['details']['frequency_metrics']['magnitude_floor_absolute'] *= 2
        with self.assertRaisesRegex(ValueError, 'reference floor'):
            self.build()

    def test_missing_method_or_corrupt_covariance_is_not_a_valid_example(self):
        example, _ = self.build()
        missing = deepcopy(example)
        missing['estimates'].pop()
        with self.assertRaises(ValueError):
            exporter.validate_example(missing)
        example['estimates'][0]['covariance']['low'][0][0] = float('nan')
        with self.assertRaises(ValueError):
            exporter.validate_example(example)

    def test_exact_current_browser_validator_accepts_json_fixture(self):
        node = shutil.which('node')
        compiler = exporter.ROOT / 'node_modules/typescript'
        if not node or not compiler.exists():
            self.skipTest('Node/TypeScript unavailable for browser-validator interoperability check')
        example, _ = self.build()
        # Read the actual private validator body, erase its TypeScript types,
        # and run it without React or browser rendering. No public fixture file.
        javascript = r'''
const fs = require('fs'), ts = require(process.argv[1]);
const source = fs.readFileSync(process.argv[2], 'utf8');
const body = source.slice(source.indexOf('const BANDS:'), source.indexOf('export default function PlusAudition'));
if (!body.includes('function example(')) throw Error('Validator boundary changed');
const compiled = ts.transpileModule('function directionalGrid(){return [];}\n'+body,
    {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
const validate = new Function(compiled+'; return example;')();
if (!validate(JSON.parse(fs.readFileSync(0, 'utf8')))) process.exit(1);
'''
        result = subprocess.run([node, '-e', javascript, str(compiler),
                                  str(exporter.ROOT / 'app/lab/PlusAudition.tsx')],
                                 input=json.dumps(example), text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_observation_identity_does_not_hash_the_reference(self):
        first = exporter.canonical_observation_sha(self.data)
        changed = {**self.data, 'reference': self.reference*10}
        self.assertEqual(first, exporter.canonical_observation_sha(changed))
        changed = {**self.data, 'p': self.data['p']*1.1}
        self.assertNotEqual(first, exporter.canonical_observation_sha(changed))

    def test_prepared_input_roundtrips_pressure_response_without_ground_truth(self):
        data = {**self.data, 'source_directions': [[1., 0., 0.]], 'sources_m': [[3., 2., 1.]]}
        payload, digest = exporter.prepared_input(data, self.credit, scene_id='fixture-0000',
            cache_file_sha='a'*64, selection_sha='b'*64, model_sha='c'*64)
        with tempfile.NamedTemporaryFile(suffix='.npz') as temporary:
            temporary.write(payload)
            temporary.flush()
            loaded = exporter.load_input(temporary.name)
        np.testing.assert_array_equal(loaded['p'], self.data['p'])
        np.testing.assert_array_equal(loaded['V'], self.data['V'])
        np.testing.assert_array_equal(loaded['frequencies'], self.data['frequencies'])
        self.assertEqual(loaded['observation_sha256'], exporter.canonical_observation_sha(self.data))
        self.assertEqual(loaded['input_file_sha256'], digest)
        self.assertEqual(loaded['provenance']['attribution'], self.credit)
        provenance = loaded['provenance']['provenance']
        self.assertFalse(provenance['reference_coefficients_included'])
        self.assertFalse(provenance['true_source_directions_included'])
        self.assertNotIn('source_directions', provenance)
        self.assertNotIn('sources_m', provenance)
        with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
            self.assertEqual(set(archive.files), {'p_real', 'p_imag', 'V_real', 'V_imag',
                'frequencies_hz', 'sample_rate_hz', 'n_fft', 'hop', 'sh_ordering',
                'sh_normalization', 'observation_sha256', 'attribution_json', 'provenance_json'})

    def test_attribution_documents_resolve_from_actual_nested_source_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source = work/'sealed-data/source'
            source.mkdir(parents=True)
            credits = []
            for name in ('VCTK-README.txt', 'VCTK-license.txt'):
                path = source/name
                path.write_text('Synthetic test credit, not an actual license document.')
                credits.append({'path': name, 'sha256': exporter.sha(path)})
            audio = {'dataset': 'VCTK 0.92', 'license': 'CC-BY-4.0',
                'source_doi': 'https://doi.org/10.7488/ds/2645', 'attribution_files': credits,
                'files': [{'speaker': 'fixture-p1', 'archive_member': 'fixture/utterance.flac',
                           'sha256': 'a'*64, 'split': 'test'}]}
            audio_path = work/'sealed-data/audio-manifest.json'
            audio_path.write_bytes(exporter.dump(audio))
            scenes = {'audio_manifest_sha256': exporter.sha(audio_path),
                      'scenes': [{'id': 'fixture-0000', 'audio_indexes': [0], 'split': 'test'}]}
            scene_path = work/'sealed-data/scene-manifest.json'
            scene_path.write_bytes(exporter.dump(scenes))
            metadata = {'manifest_sha256': exporter.sha(scene_path), 'id': 'fixture-0000',
                        'audio_indexes': [0], 'source_audio_sha256': ['a'*64]}
            value, _, _, documents = exporter.attribution(work, metadata)
            self.assertEqual(value['speakers'], ['fixture-p1'])
            self.assertEqual(set(documents), {'dataset/VCTK-README.txt', 'dataset/VCTK-license.txt'})
            for name in ('VCTK-README.txt', 'VCTK-license.txt'):
                self.assertEqual(documents[f'dataset/{name}'], (source/name).read_bytes())

    def test_incomplete_benchmark_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError, 'completed'):
            exporter.validate_benchmark({'schema': 'adeps-plus-benchmark/1', 'status': 'running'})
        report = {'schema': 'adeps-plus-benchmark/1', 'status': 'evaluated',
            'conditions': {'scenes': 31, 'clusters': 4, 'microphones': 6, 'sample_rate_hz': 16000}}
        with self.assertRaisesRegex(ValueError, 'complete predeclared'):
            exporter.validate_benchmark(report)


if __name__ == '__main__':
    unittest.main()
