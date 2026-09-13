"""Aggregation/record integrity tests for additional paper-metric scoring."""
import csv
import io
import tempfile
import unittest
from pathlib import Path

from rescore_paper_comparison import KEYS, PROFILES, aggregate_profiles, checked_file, complete_mean, csv_bytes, sha


class ReScoring(unittest.TestCase):
    def test_no_missing_scene_deletion(self):
        self.assertIsNone(complete_mean([3., None, 4.]))
        self.assertIsNone(complete_mean([float('nan')]))
        self.assertEqual(complete_mean([1., 2., 6.]), 3.)

    def test_hash_mismatch_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.npz'
            path.write_bytes(b'original')
            expected = sha(path)
            checked_file(path, expected)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                checked_file(path, expected)

    def test_complete_aggregate_and_csv_keep_undefineds_and_profiles(self):
        scenes = []
        for i, score in enumerate([3., None]):
            result = {'metrics': {key: score for key in KEYS},
                      'curves': {key: [score, 2.] for key in ('spectral_error_db', 'coherence')}}
            scenes.append({'id': str(i), 'cluster_id': 'pair',
                'profiles': {p: {'method': result} for p in PROFILES}})
        profiles = aggregate_profiles(scenes, ['method'])
        self.assertIsNone(profiles['strict']['means']['method']['si_sdr_db'])
        self.assertEqual(profiles['strict']['finite_scene_counts']['method']['si_sdr_db'], 1)
        self.assertEqual(profiles['strict']['curves']['method']['coherence'], [None, 2.])
        report = {'scenes': scenes, 'profiles': profiles, 'methods': [{'id': 'method'}]}
        rows = list(csv.DictReader(io.StringIO(csv_bytes(report).decode('utf-8-sig'))))
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]['si_sdr_db'], '')
        self.assertEqual({row['profile'] for row in rows}, set(PROFILES))


if __name__ == '__main__':
    unittest.main()
