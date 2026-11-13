import unittest

from pyramid import build


class PyramidTests(unittest.TestCase):
    def test_level_zero_keeps_samples(self):
        result = build([[3, -2, 5, 1]], levels=2)
        self.assertEqual(result["levels"][0][1]["min"], -2)
        self.assertEqual(result["samples"], 4)

    def test_empty(self):
        self.assertEqual(build([], levels=2)["samples"], 0)


if __name__ == "__main__":
    unittest.main()
