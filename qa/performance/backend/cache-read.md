# Memory cache read benchmark

Run `AINT_Venv/bin/python qa/performance/backend/cache-read.py` from the root,
or substitute your Python interpreter. An optional argument selects another
cache_manager.py implementation for comparison.

Synthetic integer values, live 600-second TTLs, 10,000 reads per batch, seven
batches per size. Reported values are median microseconds per read, including
key construction and a correctness assertion. No AI calls or user data are used.

| Entries | Before | After | Approximate speedup |
|---|---:|---:|---:|
| 100 | 1.133 µs | 0.177 µs | 6× |
| 1,000 | 8.939 µs | 0.182 µs | 49× |
| 10,000 | 87.105 µs | 0.193 µs | 451× |

Measured locally on 2026-09-12. These are microbenchmarks, not overall app or
provider latency claims. There is no portable absolute latency gate yet.
Reads now check only the requested key's expiry; eviction uses ordered LRU
tracking. Insertions at capacity can still scan expiration deadlines.

Correctness gate: `AINT_Venv/bin/python -m pytest backend/tests/test_cache_manager.py -q`.
All 39 tests passed, including small capacities, overwrite at capacity, expiry
at the deadline, persistent entries, expired-key enumeration, and LRU ordering.
