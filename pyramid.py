from __future__ import annotations


class WaveformPyramid:
    """Incrementally built multi-resolution waveform summary.

    Samples are consumed once, in input order.  A chunk boundary is only a
    delivery boundary: it never closes a partially filled bucket.  Buckets at
    level ``n`` cover ``2 ** n`` consecutive samples, and each level-``n``
    bucket is merged from complete level-``n - 1`` buckets, so appending a
    chunk only touches the buckets at the tail of the pyramid.

    Summaries are plain dictionaries with ``min``, ``max`` and ``count``, and
    only those keys are exposed in the result.
    """

    def __init__(self, levels: int = 3):
        if levels < 0:
            raise ValueError("levels must be non-negative")
        self.levels = levels
        self._buckets: list[list[dict]] = [[] for _ in range(levels)]
        # Partially filled bucket at the tail of each level.
        self._pending: list[dict | None] = [None for _ in range(levels)]
        self._samples = 0
        self._work = 0
        self._finalized = False

    def append(self, chunk) -> "WaveformPyramid":
        """Append the next segment of samples.

        The segment does not reset or drop the tail buckets of any level.
        Only the trailing pending buckets are extended.
        """

        if self._finalized:
            raise ValueError("cannot append after result()")
        self._samples += len(chunk)
        # Work is the number of input samples actually consumed; it must not
        # be multiplied by the number of levels that observe them.
        self._work += len(chunk)
        if self.levels == 0:
            return self

        for sample in chunk:
            leaf = {"min": sample, "max": sample, "count": 1}
            self._buckets[0].append(leaf)
            self._feed(1, leaf)
        return self

    def _feed(self, level: int, child: dict) -> None:
        """Merge one child summary into ``level``'s pending bucket."""

        if level >= self.levels:
            return

        pending = self._pending[level]
        if pending is None:
            pending = {
                "min": child["min"],
                "max": child["max"],
                "count": child["count"],
            }
            self._pending[level] = pending
        else:
            if child["min"] < pending["min"]:
                pending["min"] = child["min"]
            if child["max"] > pending["max"]:
                pending["max"] = child["max"]
            pending["count"] += child["count"]

        width = 1 << level
        if pending["count"] == width:
            # A complete bucket: keep it and incrementally merge it upward.
            self._buckets[level].append(pending)
            self._pending[level] = None
            self._feed(level + 1, pending)

    def _finalize(self) -> None:
        """Close the trailing partial buckets, bottom-up.

        The partial bucket of a level is only flushed when the stream ends,
        so a later chunk can extend it.  Feeding it upward may close the
        parent bucket, which keeps bucket ranges contiguous across levels.
        """

        if self._finalized:
            return
        for level in range(1, self.levels):
            pending = self._pending[level]
            if pending is None:
                continue
            self._pending[level] = None
            self._buckets[level].append(pending)
            self._feed(level + 1, pending)
        self._finalized = True

    def result(self) -> dict:
        self._finalize()
        return {
            "levels": [[dict(bucket) for bucket in level] for level in self._buckets],
            "samples": self._samples,
            "work": self._work,
        }

    def query(self, start: int, end: int, level: int = 0) -> dict:
        """Aggregate sample range ``[start, end)`` at ``level``.

        Only the buckets that overlap the requested range are scanned; the
        returned ``work`` is that number of buckets.
        """

        if not 0 <= level < self.levels:
            raise ValueError("level out of range")
        self._finalize()

        if end <= start:
            return {"min": None, "max": None, "count": 0, "work": 0}
        if start < 0 or end > self._samples:
            raise ValueError("range out of bounds")

        width = 1 << level
        first = start // width
        last = (end - 1) // width
        buckets = self._buckets[level][first:last + 1]

        result = None
        for bucket in buckets:
            if result is None:
                result = {"min": bucket["min"], "max": bucket["max"], "count": bucket["count"]}
            else:
                if bucket["min"] < result["min"]:
                    result["min"] = bucket["min"]
                if bucket["max"] > result["max"]:
                    result["max"] = bucket["max"]
                result["count"] += bucket["count"]
        result["work"] = len(buckets)
        return result


def build(chunks: list[list[int]], levels: int = 3) -> dict:
    """Build the waveform pyramid from consecutive input segments."""

    pyramid = WaveformPyramid(levels)
    for chunk in chunks:
        pyramid.append(chunk)
    return pyramid.result()
