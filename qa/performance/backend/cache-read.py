"""Synthetic cache-hit microbenchmark; reports median microseconds per read."""
import importlib.util, statistics, time, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('bench_cache', sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[3] / 'backend/modules/ai/cache_manager.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = {}
for size in (100, 1000, 10000):
    cache = module.MemoryCache(max_size=size)
    for i in range(size): cache.set(str(i), i, ttl=600)
    samples = []
    for _ in range(7):
        start = time.perf_counter()
        for i in range(10000):
            assert cache.get(str(i % size)) == i % size
        samples.append((time.perf_counter() - start) * 1e6 / 10000)
    results[size] = round(statistics.median(samples), 3)
print(json.dumps(results))
