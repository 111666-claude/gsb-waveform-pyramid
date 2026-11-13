from __future__ import annotations


def build(chunks: list[list[int]], levels: int = 3) -> dict:
    all_samples = []
    level_data = []
    for level in range(levels):
        width = 2 ** level
        values = []
        for chunk in chunks:
            for start in range(0, len(chunk), width):
                bucket = chunk[start:start + width]
                if bucket:
                    values.append({"min": min(bucket), "max": max(bucket), "count": len(bucket)})
        level_data.append(values)
        all_samples.extend(chunks[0] if level == 0 and chunks else [])
    return {"levels": level_data, "samples": sum(len(chunk) for chunk in chunks), "work": sum(len(chunk) for chunk in chunks)}
