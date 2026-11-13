import unittest

from pyramid import WaveformPyramid, build


class PyramidTests(unittest.TestCase):
    def test_level_zero_keeps_samples(self):
        result = build([[3, -2, 5, 1]], levels=2)
        self.assertEqual(result["levels"][0][1]["min"], -2)
        self.assertEqual(result["samples"], 4)

    def test_empty(self):
        self.assertEqual(build([], levels=2)["samples"], 0)

    def test_chunk_boundary_does_not_reset_partial_bucket(self):
        result = build([[3, -2, 5], [1, -7, 4, 2]])
        self.assertEqual(
            result["levels"][1],
            [
                {"min": -2, "max": 3, "count": 2},
                {"min": 1, "max": 5, "count": 2},
                {"min": -7, "max": 4, "count": 2},
                {"min": 2, "max": 2, "count": 1},
            ],
        )
        self.assertEqual(result["samples"], 7)
        self.assertEqual(result["work"], 7)

    def test_peaks_keep_negative_and_single_sample_extremes(self):
        result = build([[-10, -3], [8, 12]])
        self.assertEqual(result["levels"][1][0], {"min": -10, "max": -3, "count": 2})
        self.assertEqual(result["levels"][1][1], {"min": 8, "max": 12, "count": 2})
        self.assertEqual(result["levels"][2], [{"min": -10, "max": 12, "count": 4}])
        self.assertEqual(result["work"], 4)

    def test_empty_chunks_are_ignored(self):
        result = build([[3, -2], [], [5, 1], []])
        self.assertEqual(result["levels"][0], [
            {"min": 3, "max": 3, "count": 1},
            {"min": -2, "max": -2, "count": 1},
            {"min": 5, "max": 5, "count": 1},
            {"min": 1, "max": 1, "count": 1},
        ])
        self.assertEqual(result["samples"], 4)
        self.assertEqual(result["work"], 4)

    def test_incremental_append_matches_rebuild(self):
        chunks = [[3, -2, 5], [1, -7, 4, 2], [], [9], [-4, -6, 0, 8, 7]]
        rebuilt = build(chunks, levels=4)
        pyramid = WaveformPyramid(levels=4)
        for chunk in chunks:
            pyramid.append(chunk)
        self.assertEqual(pyramid.result(), rebuilt)

    def test_append_does_not_rebuild_completed_buckets(self):
        pyramid = WaveformPyramid(levels=3)
        pyramid.append([3, -2, 5, 1])
        before = [list(level) for level in pyramid._buckets]
        pyramid.append([-7, 4, 2])
        after = pyramid._buckets
        for level in range(3):
            self.assertEqual(after[level][: len(before[level])], before[level])
        self.assertEqual(pyramid.result()["samples"], 7)

    def test_levels_cover_contiguous_ranges(self):
        chunks = [[3, -2, 5], [1, -7, 4, 2], [9, -1, 0]]
        pyramid = WaveformPyramid(levels=4)
        for chunk in chunks:
            pyramid.append(chunk)
        pyramid.result()
        total = sum(len(chunk) for chunk in chunks)
        width = 1
        for level in pyramid._buckets:
            self.assertEqual(sum(bucket["count"] for bucket in level), total)
            full = [bucket["count"] for bucket in level[:-1]]
            self.assertTrue(all(count == width for count in full))
            self.assertLessEqual(level[-1]["count"], width)
            width *= 2

    def test_query_scans_only_hit_buckets(self):
        pyramid = WaveformPyramid(levels=3)
        pyramid.append([3, -2, 5, 1, -7, 4, 2])

        leaf = pyramid.query(2, 3)
        self.assertEqual(leaf, {"min": 5, "max": 5, "count": 1, "work": 1})

        paired = pyramid.query(4, 6, level=1)
        self.assertEqual(paired, {"min": -7, "max": 4, "count": 2, "work": 1})

        across = pyramid.query(0, 7, level=1)
        self.assertEqual(across["count"], 7)
        self.assertEqual(across["work"], 4)

        self.assertEqual(pyramid.query(3, 3), {"min": None, "max": None, "count": 0, "work": 0})

    def test_work_is_not_multiplied_by_levels(self):
        result = build([[3, -2, 5], [1, -7, 4, 2]], levels=5)
        self.assertEqual(result["work"], result["samples"])
        self.assertEqual(result["work"], 7)


if __name__ == "__main__":
    unittest.main()
