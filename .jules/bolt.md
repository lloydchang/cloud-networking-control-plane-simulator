## 2024-08-16 - Non-Cryptographic Hashing for State Comparison

**Learning:** When comparing dictionary-based state within a single-threaded reconciliation loop, using `hashlib.md5` is overkill. The overhead of JSON serialization and cryptographic hashing is significant. Python's built-in `hash()` on a `frozenset` of the dictionary's items is a much faster alternative.

**Action:** For internal state comparison where cryptographic guarantees are not required, always prefer Python's built-in `hash()` function. It's an order of magnitude faster and avoids unnecessary serialization.
