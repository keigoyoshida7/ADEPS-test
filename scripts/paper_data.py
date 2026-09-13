#!/usr/bin/env python3
"""Bounded official VCTK subsets and an explicit HARP-derived ideal HOA adapter.

Audio, downloaded upstream code, manifests and generated data stay in --data-dir;
none are browser assets. No training or full-corpus download is performed here.
"""
from __future__ import annotations
import argparse
import binascii
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import shutil
import sys
import struct
import threading
import time
import zipfile
import zlib

VCTK_DOI = 'https://doi.org/10.7488/ds/2645'
VCTK_URL = 'https://datashare.ed.ac.uk/server/api/core/bitstreams/535f4286-e54c-4038-838c-a02285e32cb2/content'
VCTK_LICENSE_URL = 'https://datashare.ed.ac.uk/server/api/core/bitstreams/956a1688-0b59-428c-8a2f-10837433dde3/content'
VCTK_README_URL = 'https://datashare.ed.ac.uk/server/api/core/bitstreams/bb7edd96-5d96-4c0e-8989-1e45597e7b72/content'
HARP_COMMIT = 'e4408f8a849c3c1906ee53e44606945e54b0af46'
HARP_SOURCE = f'https://raw.githubusercontent.com/whojavumusic/HARP/{HARP_COMMIT}/'
SCHEMA = 'adeps-test-paper-data/1'
REPO = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO / 'work' / 'paper-data'


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temporary.replace(path)


class RangeReader(io.RawIOBase):
    """Seekable HTTP resource. A server ignoring Range is rejected before reading.

    zipfile reads ZIP64 metadata and checks each extracted member's CRC. The
    whole archive is never fetched or placed on disk. All response bytes count
    against an explicit transfer budget, including metadata and small read-ahead.
    """
    def __init__(self, url=VCTK_URL, max_bytes=500_000_000):
        import requests
        self.session = requests.Session()
        self.url, self.max_bytes, self.transferred, self.position = url, int(max_bytes), 0, 0
        self.requested, self.budget_lock = 0, threading.Lock()
        self.cache = OrderedDict()
        self.size, self.etag = None, None
        self._range(0, 1)

    def _range(self, start, length):
        if length <= 0:
            return b''
        if length > 1_048_576:
            parts = [(start + offset, min(1_048_576, length - offset)) for offset in range(0, length, 1_048_576)]
            with ThreadPoolExecutor(max_workers=4) as pool:
                return b''.join(pool.map(lambda part: self._range(*part), parts))
        with self.budget_lock:
            if self.requested + length > self.max_bytes:
                raise RuntimeError('Range transfer budget exceeded; no full-download fallback exists')
            self.requested += length
        headers = {'Range': f'bytes={start}-{start + length - 1}', 'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache'}
        # This DSpace endpoint rejects conditional Range requests; verify the
        # returned ETag and total length on every response before reading it.
        import requests
        with requests.get(self.url, headers=headers, stream=True, timeout=(15, 60)) as response:
            if response.status_code != 206:
                raise RuntimeError(f'HTTP Range required, received {response.status_code}; response body was not read')
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
            if not match or tuple(map(int, match.groups()[:2])) != (start, start + length - 1):
                raise RuntimeError('Unexpected Content-Range; response body was not read')
            total = int(match.group(3))
            if self.size is not None and total != self.size:
                raise RuntimeError('Archive size changed during retrieval')
            if self.etag and response.headers.get('ETag') != self.etag:
                raise RuntimeError('Archive identity changed during retrieval')
            self.size, self.etag = total, response.headers.get('ETag')
            body = bytearray()
            for chunk in response.iter_content(65536):
                with self.budget_lock:
                    self.transferred += len(chunk)
                if self.transferred > self.max_bytes or len(body) + len(chunk) > length:
                    raise RuntimeError('Range response exceeds its declared size or budget')
                body.extend(chunk)
            if len(body) != length:
                raise RuntimeError('Truncated Range response')
            return bytes(body)

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if self.position < 0:
            raise ValueError('Negative seek')
        return self.position

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        if size <= 0:
            return b''
        if size > 65536:
            result = self._range(self.position, size)
        else:
            block = self.position // 65536
            if block not in self.cache:
                start = block * 65536
                self.cache[block] = self._range(start, min(65536, self.size - start))
                while len(self.cache) > 8:
                    self.cache.popitem(last=False)
            self.cache.move_to_end(block)
            begin = self.position - block * 65536
            result = self.cache[block][begin:begin + size]
            if len(result) < size:
                result += self._range(self.position + len(result), size - len(result))
        self.position += len(result)
        return result

    def close(self):
        self.session.close()
        super().close()


def choose_members(archive, train_speakers=12, val_speakers=2, test_speakers=2, utterances=20, seed=17391):
    import numpy as np
    if min(train_speakers, val_speakers, test_speakers, utterances) < 1:
        raise ValueError('Every split needs at least one speaker and one utterance')
    groups = {}
    for info in archive.infolist():
        match = re.search(r'(?:^|/)wav48_silence_trimmed/(p\d+)/(p\d+)_\d+_mic2\.flac$', info.filename)
        if match and match.group(1) == match.group(2) and match.group(1) not in {'p280', 'p315'}:
            groups.setdefault(match.group(1), []).append(info)
    eligible = sorted(speaker for speaker, files in groups.items() if len(files) >= utterances)
    wanted = train_speakers + val_speakers + test_speakers
    if len(eligible) < wanted:
        raise ValueError(f'Only {len(eligible)} eligible speakers; requested {wanted}')
    rng = np.random.default_rng(seed)
    speakers = list(rng.permutation(eligible))[:wanted]
    split_lists = {'train': speakers[:train_speakers], 'validation': speakers[train_speakers:train_speakers + val_speakers], 'test': speakers[-test_speakers:]}
    members = []
    for split, selected in split_lists.items():
        for speaker in selected:
            files = sorted(groups[speaker], key=lambda info: info.filename)
            indexes = sorted(rng.choice(len(files), utterances, replace=False))
            for index in indexes:
                info = files[index]
                members.append({'split': split, 'speaker': str(speaker), 'archive_member': info.filename,
                                'size_bytes': info.file_size, 'compressed_bytes': info.compress_size, 'crc32': f'{info.CRC:08x}'})
    return split_lists, members


def plan_subset(data_dir=DEFAULT_DATA, **options):
    data_dir = Path(data_dir).resolve()
    with RangeReader(max_bytes=50_000_000) as remote, zipfile.ZipFile(remote) as archive:
        splits, files = choose_members(archive, **options)
        plan = {'schema': SCHEMA, 'stage': 'planned-not-downloaded', 'dataset': 'VCTK 0.92', 'source_doi': VCTK_DOI,
                'license': 'CC-BY-4.0', 'archive_url': VCTK_URL, 'archive_size_bytes': remote.size, 'archive_etag': remote.etag,
                'metadata_transfer_bytes': remote.transferred, 'compressed_member_bytes': sum(f['compressed_bytes'] for f in files),
                'extracted_member_bytes': sum(f['size_bytes'] for f in files), 'speaker_splits': splits, 'selection': options, 'files': files}
    write_json(data_dir / 'subset-plan.json', plan)
    return plan


def fetch_small(url, path, limit=1_000_000):
    import requests
    with requests.get(url, stream=True, timeout=(15, 60)) as response:
        response.raise_for_status()
        output = bytearray()
        for chunk in response.iter_content(65536):
            output.extend(chunk)
            if len(output) > limit:
                raise RuntimeError('Small source/document download exceeded its limit')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(output)
    return {'url': url, 'path': str(Path(path).name), 'bytes': len(output), 'sha256': sha256(path)}


def acquire_subset(data_dir=DEFAULT_DATA, max_bytes=500_000_000):
    import soundfile as sf
    data_dir = Path(data_dir).resolve()
    if data_dir == REPO or data_dir.is_relative_to(REPO / 'public'):
        raise ValueError('Audio must be stored in a dedicated non-public data directory')
    plan = json.loads((data_dir / 'subset-plan.json').read_text())
    if plan['schema'] != SCHEMA or plan['archive_url'] != VCTK_URL:
        raise ValueError('Unsupported source plan')
    if plan['compressed_member_bytes'] + plan['metadata_transfer_bytes'] + len(plan['files']) * 150000 > max_bytes:
        raise ValueError('Conservative transfer estimate exceeds --max-mb; reduce the planned subset')
    if shutil.disk_usage(data_dir).free < plan['extracted_member_bytes'] + 2_000_000_000:
        raise RuntimeError('Insufficient disk space while preserving 2 GB free')
    attribution = [fetch_small(VCTK_README_URL, data_dir / 'source' / 'VCTK-README.txt'),
                   fetch_small(VCTK_LICENSE_URL, data_dir / 'source' / 'VCTK-license.txt')]
    upstream = []
    for name in ['README.md', 'requirements.txt', 'v1/Generate.py', 'v1/SphericalHarmonic.py']:
        upstream.append(fetch_small(HARP_SOURCE + name, data_dir / 'upstream' / 'HARP' / name))
    files = []
    with RangeReader(max_bytes=max_bytes) as remote, zipfile.ZipFile(remote) as archive:
        if remote.size != plan['archive_size_bytes'] or remote.etag != plan['archive_etag']:
            raise RuntimeError('Archive no longer matches the reviewed plan')
        def retrieve(entry):
            relative = Path('audio') / entry['speaker'] / Path(entry['archive_member']).name
            destination = data_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            info = archive.getinfo(entry['archive_member'])
            if info.file_size != entry['size_bytes'] or f'{info.CRC:08x}' != entry['crc32']:
                raise RuntimeError('Archive member changed')
            if destination.exists() and destination.stat().st_size == info.file_size:
                payload = destination.read_bytes()
                if binascii.crc32(payload) & 0xffffffff != info.CRC:
                    payload = None
            else:
                payload = None
            if payload is None:
                # One bounded range per member normally contains its local
                # header and compressed payload; no global seek is shared.
                block = remote._range(info.header_offset, min(info.compress_size + 4096, remote.size - info.header_offset))
                if len(block) < 30 or block[:4] != b'PK\x03\x04':
                    raise RuntimeError('Invalid ZIP local header')
                _, _, flags, method, _, _, _, _, _, name_size, extra_size = struct.unpack('<4s5H3I2H', block[:30])
                if flags & 1 or method != info.compress_type:
                    raise RuntimeError('Encrypted or inconsistent ZIP member')
                begin, end = 30 + name_size + extra_size, 30 + name_size + extra_size + info.compress_size
                if end > len(block):
                    block += remote._range(info.header_offset + len(block), end - len(block))
                compressed = block[begin:end]
                if method == zipfile.ZIP_DEFLATED:
                    decoder = zlib.decompressobj(-15)
                    payload = decoder.decompress(compressed, info.file_size + 1)
                    if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
                        raise RuntimeError('Truncated or oversized ZIP deflate stream')
                elif method == zipfile.ZIP_STORED:
                    payload = compressed
                else:
                    raise RuntimeError('Unsupported ZIP compression method')
            if len(payload) != info.file_size or binascii.crc32(payload) & 0xffffffff != info.CRC:
                raise RuntimeError('ZIP member size or CRC mismatch')
            temporary = destination.with_suffix('.partial')
            temporary.write_bytes(payload); temporary.replace(destination)
            audio_info = sf.info(destination)
            if audio_info.channels != 1 or audio_info.samplerate != 48000:
                raise RuntimeError('Unexpected VCTK audio format')
            return {**entry, 'path': str(relative), 'sha256': sha256(destination),
                    'sample_rate': audio_info.samplerate, 'frames': audio_info.frames, 'duration_seconds': audio_info.duration}
        with ThreadPoolExecutor(max_workers=4) as pool:
            for record in pool.map(retrieve, plan['files']):
                files.append(record)
                if len(files) % 20 == 0:
                    print(f'Fetched {len(files)}/{len(plan["files"])} clips; {remote.transferred / 1e6:.1f} MB transferred', flush=True)
        transfer = remote.transferred
    record = {**plan, 'stage': 'downloaded-and-crc-sha-verified', 'files': files, 'transfer_bytes': transfer,
              'attribution_files': attribution, 'harp_upstream': {'commit': HARP_COMMIT, 'files': upstream,
              'license_status': 'No LICENSE file in the pinned upstream tree; source is not redistributed by this project.'},
              'wsj0': 'Not owned or downloaded. This test split is held-out VCTK, not the paper WSJ0 evaluation.'}
    write_json(data_dir / 'audio-manifest.json', record)
    return record


def scene_spec(seed):
    import numpy as np
    rng = np.random.default_rng(seed)
    dimensions = rng.uniform([6., 6., 2.], [10., 10., 3.])
    receiver = dimensions / 2 + [rng.uniform(-.5, .5), rng.uniform(-.5, .5), 0.]
    sources = []
    for _ in range(int(rng.integers(1, 3))):
        for _attempt in range(1000):
            direction = rng.normal(size=3); direction /= np.linalg.norm(direction)
            source = receiver + direction * rng.uniform(.8, 1.5)
            if np.all(source > .1) and np.all(source < dimensions - .1):
                sources.append(source.tolist()); break
        else:
            raise RuntimeError('Could not place a source inside the room')
    return {'room_dimensions_m': dimensions.tolist(), 'receiver_m': receiver.tolist(), 'sources_m': sources,
            'target_rt60_seconds': float(rng.uniform(.1, .4)), 'seed': int(seed)}


def make_scene_manifest(data_dir=DEFAULT_DATA, train_scenes=20000, validation_scenes=100, test_scenes=100, seed=29091):
    import numpy as np
    data_dir = Path(data_dir).resolve()
    audio = json.loads((data_dir / 'audio-manifest.json').read_text())
    if audio['schema'] != SCHEMA or audio['stage'] != 'downloaded-and-crc-sha-verified':
        raise ValueError('Acquire the reviewed subset first')
    rng = np.random.default_rng(seed)
    rows = []
    for split, count in [('train', train_scenes), ('validation', validation_scenes), ('test', test_scenes)]:
        eligible = [i for i, item in enumerate(audio['files']) if item['split'] == split]
        if not eligible or not 1 <= count <= 100000:
            raise ValueError('Each split needs audio and a scene count in 1..100000')
        for index in range(count):
            scene_seed = seed + len(rows) * 7919
            spec = scene_spec(scene_seed)
            spec.update({'id': f'{split}-{index:06d}', 'split': split,
                         'audio_indexes': [int(v) for v in rng.choice(eligible, len(spec['sources_m']), replace=False)],
                         'crop_fraction': float(rng.uniform(0., 1.))})
            rows.append(spec)
    manifest = {'schema': SCHEMA, 'audio_manifest_path': 'audio-manifest.json', 'audio_manifest_sha256': sha256(data_dir / 'audio-manifest.json'),
                'scene_generator_script_sha256': sha256(__file__), 'seed': seed, 'target_order': 5,
                'target_convention': 'ACN/N3D real SH, Y00=1, first order W,Y,Z,X',
                'harp_adapter': 'Pinned HARP v1 class with explicit ACN/N3D, angle and pyroomacoustics-0.9 API corrections; ideal colocated receiver. Not unchanged upstream HARP output.',
                'split_policy': 'Speaker-disjoint VCTK training/validation/test; no WSJ0. Scene seeds are distinct across all splits.',
                'planned_scene_counts': {'train': train_scenes, 'validation': validation_scenes, 'test': test_scenes},
                'actual_consumed_scenes': 'Not implied by this manifest; record in the training run log.', 'scenes': rows}
    write_json(data_dir / 'scene-manifest.json', manifest)
    return manifest


def n3d_response(n, m, azimuth, colatitude):
    import numpy as np
    from scipy.special import gammaln, lpmv
    azimuth, colatitude = np.broadcast_arrays(np.asarray(azimuth), np.asarray(colatitude))
    k = abs(m)
    scale = np.sqrt((2*n + 1) * np.exp(gammaln(n-k+1) - gammaln(n+k+1)))
    response = ((-1.)**k) * scale * lpmv(k, n, np.cos(colatitude))
    if m:
        response = response * np.sqrt(2.) * (np.sin(k*azimuth) if m < 0 else np.cos(k*azimuth))
    return response


def harp_directivities(data_dir, order=5):
    import numpy as np
    path = Path(data_dir) / 'upstream' / 'HARP' / 'v1' / 'SphericalHarmonic.py'
    provenance_path = Path(data_dir) / 'audio-manifest.json'
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text())['harp_upstream']
        expected = next(item['sha256'] for item in provenance['files'] if item['path'] == 'SphericalHarmonic.py')
        if provenance['commit'] != HARP_COMMIT or sha256(path) != expected:
            raise ValueError('External HARP source identity mismatch')
    spec = importlib.util.spec_from_file_location('_adeps_external_harp_sh', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class CorrectedHARPDirectivity(module.SphericalHarmonicDirectivity):
        # HARP v1 predates the abstract-property API in pyroomacoustics 0.9.
        # No original source code is copied into this repository.
        def __init__(self, n, m): self._n, self._m = n, m
        @property
        def is_impulse_response(self): return False
        @property
        def filter_len_ir(self): return 1
        def get_response(self, azimuth, colatitude=None, magnitude=False, frequency=None, degrees=True):
            azimuth = np.asarray(azimuth, dtype=float)
            colatitude = np.full_like(azimuth, 90. if degrees else np.pi/2) if colatitude is None else np.asarray(colatitude, dtype=float)
            if degrees:
                azimuth, colatitude = np.deg2rad(azimuth), np.deg2rad(colatitude)
            response = n3d_response(self._n, self._m, azimuth, colatitude)
            return np.abs(response) if magnitude else response
    return [CorrectedHARPDirectivity(n, m) for n in range(order + 1) for m in range(-n, n + 1)]


def ideal_arirs(spec, data_dir=DEFAULT_DATA, sample_rate=16000, max_image_order=None):
    import numpy as np
    import pyroomacoustics as pra
    dimensions = np.asarray(spec['room_dimensions_m'], dtype=float)
    target_rt60 = float(spec['target_rt60_seconds'])
    c = float(pra.constants.get('c'))
    surface = 2 * sum(dimensions[i] * dimensions[j] for i, j in [(0, 1), (0, 2), (1, 2)])
    sabine_absorption = 24 * np.log(10) * np.prod(dimensions) / (c * surface * target_rt60)
    pair_radii = [dimensions[i] * dimensions[j] / np.hypot(dimensions[i], dimensions[j]) for i, j in [(0, 1), (0, 2), (1, 2)]]
    # Same c*T60 spatial coverage criterion as Pyroomacoustics inverse_sabine,
    # including rooms where Sabine's approximate absorption would exceed one.
    recommended = int(np.ceil(c * target_rt60 / min(pair_radii) - 1))
    absorption = float(sabine_absorption if sabine_absorption < 1 else -np.expm1(-sabine_absorption))
    initialization = 'Sabine' if sabine_absorption < 1 else 'Eyring (Sabine absorption exceeded one)'
    order = int(recommended if max_image_order is None else max_image_order)
    if not 0 <= order <= 200:
        raise ValueError('Image order must be in 0..200')
    calibration, lower, upper = [], 0.001, 0.9999
    for _ in range(8 if order > 0 else 0):
        pilot = pra.ShoeBox(dimensions, fs=sample_rate, materials=pra.Material(absorption), max_order=order,
                           air_absorption=False, ray_tracing=False)
        pilot.add_microphone(spec['receiver_m'])
        for source in spec['sources_m']: pilot.add_source(source)
        pilot.compute_rir()
        estimates = []
        for rir in pilot.rir[0]:
            try:
                value = float(pra.experimental.measure_rt60(rir, fs=sample_rate, decay_db=30))
                if np.isfinite(value) and value > 0: estimates.append(value)
            except (ValueError, RuntimeError): pass
        measured_mean = float(np.mean(estimates)) if estimates else None
        calibration.append({'energy_absorption': absorption, 'mean_rt30_extrapolated_seconds': measured_mean})
        if measured_mean is not None and abs(measured_mean / target_rt60 - 1) <= .05:
            break
        if measured_mean is None or measured_mean < target_rt60: upper = absorption
        else: lower = absorption
        absorption = .5 * (lower + upper)
    valid_trials = [trial for trial in calibration if trial['mean_rt30_extrapolated_seconds'] is not None]
    if valid_trials:
        absorption = min(valid_trials, key=lambda trial: abs(trial['mean_rt30_extrapolated_seconds'] - target_rt60))['energy_absorption']
    room = pra.ShoeBox(spec['room_dimensions_m'], fs=sample_rate, materials=pra.Material(absorption), max_order=order,
                       air_absorption=False, ray_tracing=False)
    for source in spec['sources_m']:
        room.add_source(source)
    positions = np.repeat(np.asarray(spec['receiver_m'])[:, None], 36, axis=1)
    room.add_microphone_array(pra.MicrophoneArray(positions, sample_rate, directivity=harp_directivities(data_dir)))
    room.compute_rir()
    length = max(len(rir) for microphone in room.rir for rir in microphone)
    output = np.zeros((len(spec['sources_m']), 36, length), dtype=np.float32)
    for channel, microphone in enumerate(room.rir):
        for source, rir in enumerate(microphone):
            output[source, channel, :len(rir)] = rir
    measured = []
    for source in range(len(spec['sources_m'])):
        try:
            measured.append(float(pra.experimental.measure_rt60(output[source, 0], fs=sample_rate, decay_db=30)))
        except (ValueError, RuntimeError):
            measured.append(None)
    return output, {'pyroomacoustics_version': pra.__version__, 'image_order': order, 'sabine_recommended_image_order': int(recommended),
                    'image_order_truncated': order < recommended, 'energy_absorption': float(absorption),
                    'absorption_initialization': initialization, 'rt30_calibration_trials': calibration,
                    'rt30_calibration_is_an_independent_adapter_choice': True,
                    'measured_w_channel_rt30_extrapolated_seconds': measured, 'rir_samples': length,
                    'target_rt60_is_not_a_measured_guarantee': True, 'harp_commit': HARP_COMMIT}


class SceneDataset:
    """Lazy clean ideal HOA targets; no device V and no microphone observations.

    __getitem__ -> {'clean_stft': complex64[36,F,T], 'metadata': dict}.
    Compression H, normalization and network tensors are the trainer's job.
    Use num_workers=0 on small-memory computers; nothing is eagerly rendered.
    """
    def __init__(self, manifest, split='train', sample_rate=16000, n_fft=512, hop=128, frames=32, rir_cache_size=8, max_image_order=None):
        self.path = Path(manifest).resolve(); self.root = self.path.parent
        self.manifest = json.loads(self.path.read_text())
        audio_path = self.root / self.manifest['audio_manifest_path']
        if self.manifest['schema'] != SCHEMA or sha256(audio_path) != self.manifest['audio_manifest_sha256']:
            raise ValueError('Scene/audio manifest identity mismatch')
        self.audio = json.loads(audio_path.read_text())
        split_speakers = {name: {item['speaker'] for item in self.audio['files'] if item['split'] == name}
                          for name in ['train', 'validation', 'test']}
        if any(split_speakers[a] & split_speakers[b] for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]):
            raise ValueError('Speaker leakage across audio splits')
        self.scenes = [scene for scene in self.manifest['scenes'] if scene['split'] == split]
        if not self.scenes: raise ValueError('No scenes for the requested split')
        self.sample_rate, self.n_fft, self.hop, self.frames = sample_rate, n_fft, hop, frames
        if not all(type(v) is int and v > 0 for v in [sample_rate, n_fft, hop, frames]) or hop > n_fft or n_fft % 2:
            raise ValueError('Require positive integer sample rate/frames and even n_fft >= hop')
        self.rir_cache_size, self.max_image_order = max(0, int(rir_cache_size)), max_image_order
        self.cache, self.verified_audio = OrderedDict(), set()

    def __len__(self): return len(self.scenes)

    def __getitem__(self, index):
        import numpy as np
        import soundfile as sf
        from scipy.signal import fftconvolve, resample_poly, stft
        scene = self.scenes[index]
        if scene['id'] not in self.cache:
            value = ideal_arirs(scene, self.root, self.sample_rate, self.max_image_order)
            if self.rir_cache_size:
                self.cache[scene['id']] = value
                while len(self.cache) > self.rir_cache_size: self.cache.popitem(last=False)
        else:
            self.cache.move_to_end(scene['id']); value = self.cache[scene['id']]
        rirs, rir_metadata = value
        waveform, source_samples = None, 0
        for source, audio_index in enumerate(scene['audio_indexes']):
            record = self.audio['files'][audio_index]; path = (self.root / record['path']).resolve()
            if not path.is_relative_to(self.root): raise ValueError('Audio path must remain inside the data directory')
            if record['split'] != scene['split']: raise ValueError('Speaker split leakage in scene manifest')
            if audio_index not in self.verified_audio:
                if sha256(path) != record['sha256']: raise ValueError('Audio SHA-256 mismatch')
                self.verified_audio.add(audio_index)
            speech, rate = sf.read(path, dtype='float32')
            divisor = math.gcd(rate, self.sample_rate)
            speech = resample_poly(speech, self.sample_rate // divisor, rate // divisor)
            source_samples = max(source_samples, len(speech))
            rendered = fftconvolve(rirs[source], speech[None, :], axes=-1)
            if waveform is None: waveform = rendered
            else:
                length = max(waveform.shape[-1], rendered.shape[-1])
                waveform = np.pad(waveform, ((0, 0), (0, length-waveform.shape[-1])))
                waveform[:, :rendered.shape[-1]] += rendered
        samples = self.n_fft + (self.frames - 1) * self.hop
        if waveform.shape[-1] < samples: waveform = np.pad(waveform, ((0, 0), (0, samples-waveform.shape[-1])))
        # Avoid choosing a window solely from a long RIR's silent padded tail.
        last_start = min(waveform.shape[-1] - samples, max(0, source_samples - samples))
        start = int(scene['crop_fraction'] * last_start)
        crop = waveform[:, start:start + samples]
        crop_reselected = False
        if float(np.mean(crop.astype(np.float64)**2)) < 1e-12:
            candidates = range(0, max(1, last_start + 1), self.hop)
            start = max(candidates, key=lambda offset: float(np.sum(waveform[0, offset:offset + samples].astype(np.float64)**2)))
            crop = waveform[:, start:start + samples]
            crop_reselected = True
            if float(np.mean(crop.astype(np.float64)**2)) < 1e-12:
                raise ValueError(f'Scene {scene["id"]} has no usable speech-energy crop; record and skip it')
        _, _, spectra = stft(crop, fs=self.sample_rate, window='hann', nperseg=self.n_fft, noverlap=self.n_fft-self.hop,
                             nfft=self.n_fft, boundary=None, padded=False, axis=-1)
        spectra = np.asarray(spectra, np.complex64)
        if spectra.shape != (36, self.n_fft//2+1, self.frames) or not np.all(np.isfinite(spectra)):
            raise RuntimeError('Unexpected or non-finite target shape')
        return {'clean_stft': spectra, 'metadata': {**scene, **rir_metadata, 'sample_rate': self.sample_rate,
                'n_fft': self.n_fft, 'hop': self.hop, 'frames': self.frames, 'crop_start_sample': start,
                'crop_reselected_to_avoid_silence': crop_reselected,
                'target_sh_order': 5, 'target_normalization': 'N3D', 'target_ordering': 'ACN W,Y,Z,X',
                'source_audio_sha256': [self.audio['files'][i]['sha256'] for i in scene['audio_indexes']],
                'compression_applied': False, 'normalization_applied': False, 'reference_is_array_independent': True}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'fetch', 'manifest', 'smoke'])
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--train-speakers', type=int, default=12)
    parser.add_argument('--validation-speakers', type=int, default=2)
    parser.add_argument('--test-speakers', type=int, default=2)
    parser.add_argument('--utterances', type=int, default=20)
    parser.add_argument('--max-mb', type=float, default=500.)
    parser.add_argument('--train-scenes', type=int, default=20000)
    parser.add_argument('--validation-scenes', type=int, default=100)
    parser.add_argument('--test-scenes', type=int, default=100)
    parser.add_argument('--max-image-order', type=int)
    args = parser.parse_args()
    if args.command == 'plan':
        result = plan_subset(args.data_dir, train_speakers=args.train_speakers, val_speakers=args.validation_speakers,
                             test_speakers=args.test_speakers, utterances=args.utterances)
        print(json.dumps({key: value for key, value in result.items() if key != 'files'}, indent=2))
    elif args.command == 'fetch':
        result = acquire_subset(args.data_dir, int(args.max_mb * 1e6))
        print(json.dumps({'files': len(result['files']), 'transfer_bytes': result['transfer_bytes']}, indent=2))
    elif args.command == 'manifest':
        result = make_scene_manifest(args.data_dir, args.train_scenes, args.validation_scenes, args.test_scenes)
        print(json.dumps(result['planned_scene_counts'], indent=2))
    else:
        started = time.monotonic()
        dataset = SceneDataset(args.data_dir / 'scene-manifest.json', max_image_order=args.max_image_order)
        result = dataset[0]
        print(json.dumps({'shape': list(result['clean_stft'].shape), 'elapsed_seconds': time.monotonic()-started, 'metadata': result['metadata']}, indent=2))


if __name__ == '__main__':
    main()
