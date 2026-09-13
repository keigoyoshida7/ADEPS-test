"""Analytic CPU fixtures for a byte-preserving, common-gain Max audio bank."""
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_max_comparison as package


def layout_fixture():
    # Twice each Cartesian axis: closed-form Y^T Y = 12 I for real N3D FOA.
    directions = np.vstack((np.eye(3), -np.eye(3), np.eye(3), -np.eye(3)))
    raw = np.column_stack((-directions[:, 1], directions[:, 0], directions[:, 2])) + [0, 0, 1.2]
    return {'schema': 'adeps-test-speaker-layout/1', 'units': 'metres',
            'speakers': [{'id': i+1, 'label': f'Fixture {i+1}', 'position_m': p.tolist()} for i, p in enumerate(raw)],
            'coordinate_system': {'axes': {'x': 'right', 'y': 'front', 'z': 'up'},
                                  'foa_from_raw_matrix': [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]},
            'source': {'kind': 'Unit fixture only', 'sha256': 'a'*64},
            'verification': {'as_built': False, 'physical_output_routes': False},
            'channel_order_note': {'jp': '試験', 'en': 'Fixture only'}}


class MaxComparisonExportTests(unittest.TestCase):
    def test_packaging_seal_checks_identity_without_reauditing_unconsumed_development(self):
        lock = {'schema': 'adeps-plus-selection-lock/1',
                'status': 'sealed_before_final_test_rendering_or_inference',
                'selection': {'fixed': True}, 'method_ids': list(package.saved.METHOD_IDS),
                'source_sha256': {'unconsumed.py': 'a'*64},
                'input_sha256': {'unconsumed-development.json': 'b'*64}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'selection-lock.json'
            path.write_bytes(package.dump(lock))
            report = {'selection': lock['selection'], 'provenance': {
                'lock_sha256': package.digest(path.read_bytes()),
                'source_sha256': lock['source_sha256'], 'input_sha256': lock['input_sha256']}}
            self.assertEqual(package.verify_packaging_seal(folder, report, lock['selection']),
                             report['provenance']['lock_sha256'])
            for mutation in ('digest', 'selection', 'input'):
                broken = deepcopy(report)
                if mutation == 'digest':broken['provenance']['lock_sha256'] = '0'*64
                if mutation == 'selection':broken['selection'] = {'fixed': False}
                if mutation == 'input':broken['provenance']['input_sha256'] = {}
                with self.assertRaises(ValueError):
                    package.verify_packaging_seal(folder, broken, lock['selection'])

    def setUp(self):
        self.layout = layout_fixture()
        self.decoder = package.speaker_decoder(self.layout, 'b'*64)
        t = np.arange(package.CLIP_SAMPLES) / package.RATE
        base = np.column_stack([np.sin(2*np.pi*(200+100*c)*t) for c in range(4)])*.04
        self.waves = {key: base*(i+1) for i, key in enumerate(package.METHOD_IDS)}
        self.labels = {key: (f'試験{i}', f'Fixture {i}') for i, key in enumerate(package.METHOD_IDS)}

    def published(self):
        peak = max(max(float(abs(w).max()), float(abs(w @ package.saved.PREVIEW_MATRIX.T).max()))
                   for w in self.waves.values())
        gain = .95/peak
        example = {'shared_gain': gain, 'audio': {'shared_gain': gain, 'sample_rate_hz': 16000,
            'samples': 3968, 'foa_channels': ['W', 'Y', 'Z', 'X'], 'sh_normalization': 'N3D'}}
        audio = {f'foa/{key}_FOA_ACN_N3D.wav': package.saved.wav_bytes(16000, w*gain)
                 for key, w in self.waves.items()}
        return example, audio

    def test_closed_form_octahedral_decoder_preserves_axis_order_and_polarity(self):
        d = np.asarray(self.decoder['matrix'])
        self.assertEqual(d.shape, (12, 4))
        self.assertEqual(self.decoder['rank'], 4)
        self.assertAlmostEqual(self.decoder['condition_number'], 1.)
        np.testing.assert_allclose(d[:, 0], 1/(12+.001), atol=1e-15)
        # Fixture S1 is front, S2 is left and S3 is up in the FOA frame.
        np.testing.assert_allclose(d[:3], np.array([
            [1, 0, 0, np.sqrt(3)], [1, np.sqrt(3), 0, 0], [1, 0, np.sqrt(3), 0]])/(12+.001), atol=1e-15)
        np.testing.assert_allclose(d[3:6, 1:], -d[:3, 1:], atol=1e-15)
        # A unit impulse in channel c produces column c of the shared decoder.
        impulses = np.eye(4)
        np.testing.assert_array_equal(impulses @ d.T, d.T)

    def test_layout_wrong_axes_ids_or_coincident_listener_are_rejected(self):
        for mutation in ('axis', 'ids', 'listener', 'nan'):
            value = deepcopy(self.layout)
            if mutation == 'axis':value['coordinate_system']['foa_from_raw_matrix'][0] = [1, 0, 0]
            if mutation == 'ids':value['speakers'][0]['id'] = 12
            if mutation == 'listener':value['speakers'][0]['position_m'] = [0, 0, 1.2]
            if mutation == 'nan':value['speakers'][0]['position_m'][0] = float('nan')
            with self.assertRaises(ValueError):package.speaker_decoder(value, 'b'*64)

    def test_published_scene_keeps_exact_wav_samples_and_shared_gain(self):
        example, payloads = self.published()
        before = dict(payloads)
        gain = package.check_published_wavs(example, payloads, self.waves)
        self.assertEqual(gain, example['shared_gain'])
        self.assertEqual(payloads, before)
        changed = dict(payloads)
        changed['foa/plus_FOA_ACN_N3D.wav'] = package.saved.wav_bytes(16000, self.waves['plus']*gain*1.01)
        with self.assertRaisesRegex(ValueError, 'differs'):
            package.check_published_wavs(example, changed, self.waves)
        wrong = deepcopy(example);wrong['audio']['sh_normalization'] = 'SN3D'
        with self.assertRaises(ValueError):package.check_published_wavs(wrong, payloads, self.waves)
        wrong = deepcopy(example);wrong['shared_gain'] *= 2;wrong['audio']['shared_gain'] = wrong['shared_gain']
        with self.assertRaisesRegex(ValueError, 'common all-method'):
            package.check_published_wavs(wrong, payloads, self.waves)

    def test_wrong_wav_rate_channels_and_nonfinite_are_rejected(self):
        for rate, signal in ((48000, self.waves['plus']), (16000, self.waves['plus'][:, :2]),
                             (16000, np.full((3968, 4), np.nan))):
            with self.assertRaises(ValueError):
                package.read_foa_wav(package.saved.wav_bytes(rate, signal), 3968)

    def test_montage_same_timeline_fades_and_one_global_gain(self):
        other = {k: v*.25 for k, v in self.waves.items()}
        identities = [{'scene_id': 'fixture-0', 'input_sha256': 'a'*64},
                      {'scene_id': 'fixture-1', 'input_sha256': 'b'*64}]
        payloads, info = package.montage([self.waves, other], identities, self.decoder)
        self.assertEqual(info['samples'], 3968*2+2400)
        self.assertEqual(info['timeline'][1]['start_sample'], 6368)
        self.assertEqual(info['fade_samples_each_edge'], 80)
        first, second = 100, 6368+100
        for key in package.METHOD_IDS:
            audio = package.read_foa_wav(payloads[f'foa/{key}_FOA_ACN_N3D.wav'], info['samples'])
            np.testing.assert_array_equal(audio[3968:6368], 0.)
            np.testing.assert_array_equal(audio[[0, 3967, 6368, -1]], 0.)
            np.testing.assert_array_equal(audio[second], audio[first]*.25)
            np.testing.assert_array_equal(audio[first], (self.waves[key][100]*info['shared_gain']).astype(np.float32))
            self.assertLessEqual(float(abs(audio).max()), .950001)
            self.assertLessEqual(float(abs(audio @ np.asarray(self.decoder['matrix']).T).max()), .950001)
        # Reference/estimate metadata cannot alter the collection observation identity.
        richer = [{**row, 'reference': 'changed', 'estimate': 'ignored'} for row in info['timeline']]
        self.assertEqual(package.collection_sha(richer), info['input_sha256'])
        richer[0]['input_sha256'] = 'c'*64
        self.assertNotEqual(package.collection_sha(richer), info['input_sha256'])

    def test_manifest_and_archive_hashes_cover_the_exact_wav_bank(self):
        example, payloads = self.published()
        details = {'samples': 3968, 'shared_gain': example['shared_gain'], 'input_sha256': 'c'*64}
        manifest = package.bank_manifest('example', details, self.labels, payloads, self.decoder,
                                         {'new_inference': False}, {'license': 'Fixture only'})
        self.assertEqual(manifest['schema'], 'adeps-max-method-bank/1')
        self.assertEqual(manifest['channel_order'], ['W', 'Y', 'Z', 'X'])
        self.assertEqual(manifest['normalization'], 'N3D')
        self.assertTrue(manifest['shared_gain_applied'])
        self.assertEqual([m['id'] for m in manifest['methods']], list(package.METHOD_IDS))
        package_files = {**payloads, 'max/fixture.js': b'// fixture only\n'}
        zipped = package.zip_bytes(manifest, package_files)
        self.assertEqual(zipped, package.zip_bytes(manifest, package_files))
        with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
            recorded = json.loads(archive.read('max-comparison.json'))
            for method in recorded['methods']:
                self.assertEqual(method['sha256'], package.digest(archive.read(method['file'])))
            for filename, record in recorded['files'].items():
                self.assertEqual(record['sha256'], package.digest(archive.read(filename)))
                self.assertEqual(record['bytes'], len(archive.read(filename)))
        with self.assertRaises(ValueError):package.zip_bytes(manifest, {'../escape': b'bad'})

    def test_actual_max_loader_accepts_exported_fixture_without_audio_start(self):
        node = shutil.which('node')
        loader = package.ROOT/'max/method-comparison-bank.js'
        if not node or not loader.is_file():
            self.skipTest('Node or Max bank loader unavailable')
        example, payloads = self.published()
        details = {'samples': 3968, 'shared_gain': example['shared_gain'], 'input_sha256': 'c'*64}
        manifest = package.bank_manifest('example', details, self.labels, payloads, self.decoder,
                                         {'new_inference': False}, {'license': 'Fixture only'})
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name, payload in payloads.items():
                path = folder/name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(payload)
            path = folder/'max-comparison.json';path.write_bytes(package.dump(manifest))
            result = subprocess.run([node, '-e',
                "require(process.argv[1]).loadBank(process.argv[2]).then(b=>{if(b.methods.length!==10||b.samples!==3968)process.exit(2)}).catch(e=>{console.error(e);process.exit(1)})",
                str(loader), str(path)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
