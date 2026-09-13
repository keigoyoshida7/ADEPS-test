"""Small, offline restoration tests. No real audio, network, Torch or HARP import."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('restore_paper_data', ROOT / 'scripts/restore_paper_data.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.zip = self.root / 'metadata.zip'
        self.report_path = self.root / 'report.json'
        self.destination = self.root / 'restored'
        self.payloads = {}
        splits = {'train': ['p100'], 'validation': ['p200'], 'test': ['p300']}
        files, acquired, scenes = [], [], []
        for index, (split, speakers) in enumerate(splits.items()):
            speaker = speakers[0]
            member = f'wav48_silence_trimmed/{speaker}/{speaker}_001_mic2.flac'
            relative = f'audio/{speaker}/{speaker}_001_mic2.flac'
            body = f'fake-audio-{split}'.encode()
            self.payloads[relative] = body
            row = {'split': split, 'speaker': speaker, 'archive_member': member,
                   'size_bytes': len(body), 'compressed_bytes': len(body), 'crc32': '00000000'}
            files.append(row)
            acquired.append({**row, 'path': relative, 'sha256': digest(body),
                             'sample_rate': 48000, 'frames': 480, 'duration_seconds': .01})
            scenes.append({'id': f'{split}-000000', 'split': split, 'audio_indexes': [index]})
        self.plan = {'schema': restore.paper_data.SCHEMA, 'stage': 'planned-not-downloaded',
                     'archive_url': restore.paper_data.VCTK_URL,
                     'source_doi': restore.paper_data.VCTK_DOI, 'archive_size_bytes': 10_000,
                     'archive_etag': 'original-etag', 'metadata_transfer_bytes': 100,
                     'compressed_member_bytes': sum(row['compressed_bytes'] for row in files),
                     'extracted_member_bytes': sum(row['size_bytes'] for row in files),
                     'speaker_splits': splits, 'files': files}
        attribution, upstream = [], []
        for relative, url in restore.ATTRIBUTION.items():
            body = f'official-document-{relative}'.encode()
            self.payloads[relative] = body
            attribution.append({'url': url, 'path': Path(relative).name,
                                'bytes': len(body), 'sha256': digest(body)})
        for name in restore.HARP_FILES:
            relative = f'upstream/HARP/{name}'
            body = f'pinned-upstream-{name}'.encode()
            self.payloads[relative] = body
            upstream.append({'url': restore.paper_data.HARP_SOURCE + name, 'path': Path(name).name,
                             'bytes': len(body), 'sha256': digest(body)})
        self.audio = {**copy.deepcopy(self.plan), 'stage': 'downloaded-and-crc-sha-verified',
                      'transfer_bytes': 12345, 'files': acquired, 'attribution_files': attribution,
                      'harp_upstream': {'commit': restore.paper_data.HARP_COMMIT, 'files': upstream}}
        source_hashes = {name: restore.paper_data.sha256(ROOT / name) for name in restore.SOURCE_FILES}
        self.scene = {'schema': restore.paper_data.SCHEMA, 'audio_manifest_path': 'audio-manifest.json',
                      'scene_generator_script_sha256': source_hashes['scripts/paper_data.py'],
                      'planned_scene_counts': dict.fromkeys(splits, 1), 'scenes': scenes}
        self.report = {'schema': 'adeps-test-paper-prior-training/1', 'status': 'evaluated',
                       'model': {'id': 'paper-prior-v1', 'weights_sha256': 'a' * 64},
                       'source_sha256': source_hashes,
                       'data': {'downloaded_utterances': 3,
                                **{f'{key}_speakers': value for key, value in splits.items()}}}
        self.calls = []
        self.pack()

    def tearDown(self):
        self.temp.cleanup()

    def pack(self, additions=()):
        self.scene['audio_manifest_sha256'] = digest(encoded(self.audio))
        self.raw = {'subset-plan.json': encoded(self.plan), 'audio-manifest.json': encoded(self.audio),
                    'scene-manifest.json': encoded(self.scene)}
        self.report['data']['manifest_sha256'] = digest(self.raw['scene-manifest.json'])
        self.report_path.write_bytes(encoded(self.report))
        with zipfile.ZipFile(self.zip, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, payload in self.raw.items():
                archive.writestr(name, payload)
            for name, payload in additions:
                archive.writestr(name, payload)

    def fake_acquire(self, staging, max_bytes):
        self.calls.append(max_bytes)
        for relative, body in self.payloads.items():
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        # Real acquire_subset writes a new transfer count. It must not survive.
        generated = {**self.audio, 'transfer_bytes': 987654321}
        (staging / 'audio-manifest.json').write_bytes(encoded(generated))
        return generated

    def run_restore(self, **options):
        return restore.restore(self.zip, self.report_path, self.destination,
                               acquire=self.fake_acquire, **options)

    def test_preserves_original_manifest_bytes_and_verifies_existing_without_network(self):
        result = self.run_restore(metadata_sha256=digest(self.zip.read_bytes()), max_bytes=123000)
        self.assertEqual(result['status'], 'restored-exact-manifests')
        self.assertEqual(self.calls, [123000])
        for name, original in self.raw.items():
            self.assertEqual((self.destination / name).read_bytes(), original)
        self.assertEqual(json.loads((self.destination / 'audio-manifest.json').read_text())['transfer_bytes'], 12345)
        result = self.run_restore(verify_only=True)
        self.assertEqual(result['status'], 'verified-existing')
        self.assertEqual(self.calls, [123000])
        self.assertEqual(len(list(self.root.glob('.adeps-restore-*'))), 0)

    def test_corrupted_audio_or_upstream_source_never_installs_a_partial_tree(self):
        for relative in ['audio/p100/p100_001_mic2.flac', 'upstream/HARP/v1/SphericalHarmonic.py']:
            with self.subTest(relative=relative):
                original = self.payloads[relative]
                self.payloads[relative] = b'wrong-data'
                with self.assertRaisesRegex(ValueError, 'SHA-256 or size mismatch'):
                    self.run_restore()
                self.assertFalse(self.destination.exists())
                self.assertEqual(list(self.root.glob('.adeps-restore-*')), [])
                self.payloads[relative] = original

    def test_rejects_extra_archive_members_and_symlinks(self):
        for name in ['../escaped.json', 'extra.json', 'audio-manifest.json']:
            with self.subTest(name=name):
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    self.pack([(name, b'{}')])
                with self.assertRaisesRegex(ValueError, 'three known'):
                    self.run_restore()
        self.pack()
        with zipfile.ZipFile(self.zip, 'w') as archive:
            for name, body in self.raw.items():
                info = zipfile.ZipInfo(name)
                if name == 'subset-plan.json':
                    info.create_system = 3
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, body)
        with self.assertRaisesRegex(ValueError, 'link'):
            self.run_restore()
        self.assertEqual(self.calls, [])

    def test_rejects_oversized_member_and_duplicate_json_keys_before_fetch(self):
        with patch.dict(restore.LIMITS, {'scene-manifest.json': 100}):
            with self.assertRaisesRegex(ValueError, 'too large'):
                self.run_restore()
        with zipfile.ZipFile(self.zip, 'w') as archive:
            for name, body in self.raw.items():
                archive.writestr(name, b'{"schema":1,"schema":2}' if name == 'subset-plan.json' else body)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            self.run_restore()
        self.assertEqual(self.calls, [])

    def test_hash_chain_zip_identity_and_checkout_identity_are_required(self):
        with self.assertRaisesRegex(ValueError, 'ZIP SHA-256'):
            self.run_restore(metadata_sha256='0' * 64)
        self.report['data']['manifest_sha256'] = '0' * 64
        self.report_path.write_bytes(encoded(self.report))
        with self.assertRaisesRegex(ValueError, 'Scene manifest'):
            self.run_restore()
        self.pack()
        self.report['source_sha256']['scripts/paper_data.py'] = '0' * 64
        self.report_path.write_bytes(encoded(self.report))
        with self.assertRaisesRegex(ValueError, 'Checkout differs'):
            self.run_restore()
        self.assertEqual(self.calls, [])

    def test_unsafe_audio_paths_and_unofficial_source_urls_are_rejected(self):
        self.audio['files'][0]['path'] = '../outside.flac'
        self.pack()
        with self.assertRaisesRegex(ValueError, 'audio path'):
            self.run_restore()
        self.audio['files'][0]['path'] = 'audio/p100/p100_001_mic2.flac'
        self.audio['harp_upstream']['files'][0]['url'] = 'https://unrelated.example/source.py'
        self.pack()
        with self.assertRaisesRegex(ValueError, 'Only pinned'):
            self.run_restore()
        self.assertEqual(self.calls, [])

    def test_existing_nonempty_and_public_destinations_are_never_changed(self):
        self.destination.mkdir()
        marker = self.destination / 'keep.txt'; marker.write_bytes(b'keep-me')
        with self.assertRaisesRegex(ValueError, 'not empty'):
            self.run_restore()
        self.assertEqual(marker.read_bytes(), b'keep-me')
        with self.assertRaisesRegex(ValueError, 'non-public'):
            restore.restore(self.zip, self.report_path, ROOT / 'public' / 'forbidden', acquire=self.fake_acquire)
        self.assertEqual(self.calls, [])

    def test_verify_only_rejects_corruption_extra_files_and_symlinks(self):
        self.run_restore()
        audio = self.destination / 'audio/p100/p100_001_mic2.flac'
        original = audio.read_bytes(); audio.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SHA-256 or size mismatch'):
            self.run_restore(verify_only=True)
        audio.write_bytes(original)
        extra = self.destination / 'unexpected.txt'; extra.write_text('extra')
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            self.run_restore(verify_only=True)
        extra.unlink()
        external = self.root / 'elsewhere.flac'; external.write_bytes(original)
        audio.unlink(); audio.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            self.run_restore(verify_only=True)
        self.assertEqual(len(self.calls), 1)


if __name__ == '__main__':
    unittest.main()
