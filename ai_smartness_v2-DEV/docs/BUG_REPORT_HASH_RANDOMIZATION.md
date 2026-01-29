# Bug Report: Thread Continuation Failure Due to Python Hash Randomization

**Date**: 2026-01-29
**Severity**: Critical
**Status**: RESOLVED
**Affected Versions**: ai_smartness_v2 (all versions before fix)

---

## Summary

Thread continuation was completely broken - all threads had exactly 1 message despite processing 150+ captures. The root cause was Python's hash randomization making TF-IDF embeddings incompatible across daemon restarts.

---

## Symptoms

- All 154 threads on KratOs had exactly 1 message
- New captures always created new threads instead of continuing existing ones
- Similarity scores between related content returned 0.0
- Duplicate threads with nearly identical titles (e.g., 4× "Configuration Nœud KratOs")

**Diagnostic logs showed:**
```
DECIDE: best_similarity=0.250, threshold=0.4
DECIDE: NEW_THREAD (best_sim=0.250 < 0.4)
```

---

## Root Cause Analysis

### The Problem

The TF-IDF fallback embedding used Python's built-in `hash()` function:

```python
# embeddings.py (BROKEN)
for word, count in tf.items():
    idx = hash(word) % 384  # ← PROBLEM HERE
    embedding[idx] += value
```

### Why This Breaks

Since **Python 3.3**, string hashing is **randomized by default** for security (hash collision DoS protection). This means:

```bash
$ python3 -c "print(hash('grandpa') % 384)"
322
$ python3 -c "print(hash('grandpa') % 384)"
291
$ python3 -c "print(hash('grandpa') % 384)"
194
```

Each Python process gets a different hash seed, causing:
1. Daemon creates embeddings with hash seed A
2. Daemon restarts with hash seed B
3. New embeddings use completely different indices
4. Cosine similarity between old/new embeddings = 0.0

### Impact

- Embeddings created in one daemon session were **incompatible** with embeddings from another session
- Even identical text would have 0% similarity after daemon restart
- Thread continuation algorithm could never match existing threads

---

## Solution

### Fix Applied

Replaced Python's `hash()` with a deterministic hash using MD5:

```python
# embeddings.py (FIXED)
import hashlib

def _deterministic_hash(word: str) -> int:
    """
    Deterministic hash function that produces the same result
    across Python sessions.
    """
    return int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)

# In _embed_tfidf():
for word, count in tf.items():
    idx = _deterministic_hash(word) % 384  # ← NOW DETERMINISTIC
    embedding[idx] += value
```

### Verification

```bash
$ python3 -c "from ai_smartness_v2.processing.embeddings import _deterministic_hash; print(_deterministic_hash('grandpa') % 384)"
242
$ python3 -c "from ai_smartness_v2.processing.embeddings import _deterministic_hash; print(_deterministic_hash('grandpa') % 384)"
242
$ python3 -c "from ai_smartness_v2.processing.embeddings import _deterministic_hash; print(_deterministic_hash('grandpa') % 384)"
242
```

### Required Migration

After applying the fix, **all existing embeddings must be recalculated** because they were created with the old randomized hash:

```bash
# Option 1: Use CLI command
ai reindex --verbose

# Option 2: Python script
python3 << 'EOF'
import json
from pathlib import Path
from ai_smartness_v2.processing.embeddings import EmbeddingManager

em = EmbeddingManager()
threads_dir = Path('.ai/db/threads')

for f in threads_dir.glob('thread_*.json'):
    data = json.loads(f.read_text())
    text = ' '.join([data['title']] + data.get('topics', []))
    data['embedding'] = em.embed(text)
    f.write_text(json.dumps(data, indent=2))
EOF
```

Then restart the daemon:
```bash
kill $(cat .ai/processor.pid)
# Daemon auto-restarts on next capture
```

---

## Files Modified

| File | Change |
|------|--------|
| `processing/embeddings.py` | Added `_deterministic_hash()`, replaced `hash()` calls |
| `cli/commands/reindex.py` | New file - CLI command to recalculate embeddings |
| `cli/main.py` | Added `reindex` command |
| `intelligence/thread_manager.py` | Added debug logging (KratOs only) |

---

## Test Results After Fix

### Before Fix
```
Test similarity with 'GRANDPA Consensus Actions': 0.000
Thread continuation: NEVER (all threads have 1 message)
```

### After Fix
```
Test similarity with 'GRANDPA Consensus Actions': 0.636
Thread continuation: WORKING

Test capture response:
{
  "status": "ok",
  "thread_id": "thread_20260129_092136_3c354d",
  "thread_title": "GRANDPA Consensus Protocol",
  "action": "continued"  ← Was always "created" before
}
```

---

## Lessons Learned

1. **Never use `hash()` for persistence** - Python's hash randomization breaks cross-session data
2. **Use `hashlib` for deterministic hashing** - MD5/SHA are consistent across sessions
3. **Add debug logging to decision logic** - Would have caught this earlier
4. **Test daemon restart scenarios** - Embeddings worked within a session but broke on restart

---

## Prevention

For future embedding implementations:
- Always use deterministic hash functions (hashlib.md5, hashlib.sha256)
- Or set `PYTHONHASHSEED=0` (not recommended for production)
- Or use proper embedding models (sentence-transformers) which don't have this issue

---

## References

- [Python hash randomization](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED)
- [PEP 456 - Secure and interchangeable hash algorithm](https://peps.python.org/pep-0456/)
