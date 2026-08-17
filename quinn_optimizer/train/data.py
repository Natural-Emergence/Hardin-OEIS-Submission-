"""
Data pipeline for QUINN optimizer benchmarking.

Priority order:
  1. WikiText-2 via HuggingFace datasets + tiktoken (BPE, vocab capped at 32K)
  2. WikiText-2 via HuggingFace datasets + char-level encoding (vocab 256)
  3. Synthetic structured dataset (works fully offline, vocab 256)

Returns: (train_loader, val_loader, vocab_size, dataset_name)
"""
import math
import random
from typing import Optional, Tuple

import torch
from torch.utils.data import Dataset, DataLoader

SEQ_LEN = 128
BATCH_SIZE = 32
MAX_VOCAB = 32768  # cap BPE vocab so embedding stays manageable (~8M tokens × d_model)


# ─── Tokenizers ────────────────────────────────────────────────────────────────

def _tiktoken_encode(text: str, max_token_id: int) -> list:
    """Encode with tiktoken cl100k_base; remap tokens >= max_token_id to token 1."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return [t if t < max_token_id else 1 for t in enc.encode(text)]


def _char_encode(text: str) -> list:
    """Byte-level encoding: every byte is a token, vocab size = 256."""
    return list(text.encode("utf-8", errors="replace"))


# ─── Dataset classes ───────────────────────────────────────────────────────────

class TokenDataset(Dataset):
    """Non-overlapping seq_len-length chunks from a flat token list."""

    def __init__(self, tokens: list, seq_len: int = SEQ_LEN,
                 max_samples: Optional[int] = None):
        self.seq_len = seq_len
        n_chunks = (len(tokens) - 1) // seq_len
        if max_samples is not None:
            n_chunks = min(n_chunks, max_samples)
        self.data = torch.tensor(tokens[: n_chunks * seq_len + 1], dtype=torch.long)
        self.n_chunks = n_chunks

    def __len__(self):
        return self.n_chunks

    def __getitem__(self, idx):
        start = idx * self.seq_len
        return self.data[start: start + self.seq_len], self.data[start + 1: start + self.seq_len + 1]


class SyntheticDataset(Dataset):
    """
    Offline fallback: structured text with learnable patterns.

    Mixes:
      - Arithmetic sequences mod vocab  → clean spectral periodicity in weights
      - Repeated-phrase patterns        → harmonic spectral structure
      - Random noise                    → tests QUINN's exploration mode

    A model learning these achieves spectrally coherent weights — the exact
    regime where QUINN's geodesic correction is most active.
    """

    def __init__(self, n_samples: int = 10000, seq_len: int = SEQ_LEN,
                 vocab_size: int = 256, seed: int = 42):
        rng = random.Random(seed)
        self.xs, self.ys = [], []

        for i in range(n_samples):
            mode = i % 3
            if mode == 0:
                # Arithmetic sequence
                start = rng.randint(0, vocab_size - 1)
                step = rng.randint(1, 7)
                seq = [(start + j * step) % vocab_size for j in range(seq_len + 1)]
            elif mode == 1:
                # Repeated phrase
                phrase_len = rng.randint(2, 9)
                phrase = [rng.randint(0, vocab_size - 1) for _ in range(phrase_len)]
                repeats = math.ceil((seq_len + 1) / phrase_len)
                seq = (phrase * repeats)[: seq_len + 1]
            else:
                # Random baseline (harder, tests exploration mode)
                seq = [rng.randint(0, vocab_size - 1) for _ in range(seq_len + 1)]

            self.xs.append(torch.tensor(seq[:seq_len], dtype=torch.long))
            self.ys.append(torch.tensor(seq[1: seq_len + 1], dtype=torch.long))

    def __len__(self):
        return len(self.xs)

    def __getitem__(self, idx):
        return self.xs[idx], self.ys[idx]


# ─── Loader factory ────────────────────────────────────────────────────────────

def _make_loaders(train_ds: Dataset, val_ds: Dataset,
                  batch_size: int, seed: int) -> Tuple[DataLoader, DataLoader]:
    g = torch.Generator()
    g.manual_seed(seed)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        generator=g, drop_last=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, drop_last=True,
    )
    return train_loader, val_loader


def get_dataloaders(
    batch_size: int = BATCH_SIZE,
    seq_len: int = SEQ_LEN,
    max_train_samples: Optional[int] = None,
    max_val_samples: Optional[int] = None,
    seed: int = 42,
    force_synthetic: bool = False,
) -> Tuple[DataLoader, DataLoader, int, str]:
    """
    Return (train_loader, val_loader, vocab_size, dataset_name).

    Tries WikiText-2 (online) first; falls back to synthetic offline dataset.
    All three optimizer runs should call this once and share the resulting
    loaders — the generator state evolves across epochs for varied shuffles.
    """
    if not force_synthetic:
        result = _try_wikitext2(batch_size, seq_len, max_train_samples,
                                max_val_samples, seed)
        if result is not None:
            return result

    # ── Synthetic offline fallback ─────────────────────────────────────────────
    print("[data] Using synthetic offline dataset (char-level, vocab=256)")
    n_train = max_train_samples or 10_000
    n_val = max(256, max_val_samples or 1_000)
    train_ds = SyntheticDataset(n_train, seq_len=seq_len, vocab_size=256, seed=seed)
    val_ds = SyntheticDataset(n_val, seq_len=seq_len, vocab_size=256, seed=seed + 1)
    tr, va = _make_loaders(train_ds, val_ds, batch_size, seed)
    return tr, va, 256, "synthetic"


def _try_wikitext2(
    batch_size: int, seq_len: int,
    max_train_samples: Optional[int],
    max_val_samples: Optional[int],
    seed: int,
) -> Optional[Tuple[DataLoader, DataLoader, int, str]]:
    """Return (train_loader, val_loader, vocab_size, name) or None on failure."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("[data] 'datasets' not installed — falling back to synthetic")
        return None

    try:
        print("[data] Loading WikiText-2 …", end=" ", flush=True)
        ds = load_dataset("wikitext", "wikitext-2-raw-v1", trust_remote_code=False)
        train_text = "\n".join(t for t in ds["train"]["text"] if t.strip())
        val_text = "\n".join(t for t in ds["validation"]["text"] if t.strip())
        print("done")
    except Exception as e:
        print(f"\n[data] WikiText-2 unavailable ({e}) — falling back to synthetic")
        return None

    # Try BPE tokenizer first
    try:
        import tiktoken  # noqa: F401
        print("[data] Tokenizing with tiktoken cl100k_base (vocab capped at 32K) …",
              end=" ", flush=True)
        train_toks = _tiktoken_encode(train_text, MAX_VOCAB)
        val_toks = _tiktoken_encode(val_text, MAX_VOCAB)
        vocab_size = MAX_VOCAB
        name = f"WikiText-2+BPE(vocab={MAX_VOCAB})"
    except Exception:
        print("[data] tiktoken unavailable → char-level")
        train_toks = _char_encode(train_text)
        val_toks = _char_encode(val_text)
        vocab_size = 256
        name = "WikiText-2+char"

    print(f" {len(train_toks):,} train / {len(val_toks):,} val tokens")
    train_ds = TokenDataset(train_toks, seq_len=seq_len, max_samples=max_train_samples)
    val_ds = TokenDataset(val_toks, seq_len=seq_len, max_samples=max_val_samples)
    print(f"[data] {name}: {len(train_ds):,} / {len(val_ds):,} chunks")

    tr, va = _make_loaders(train_ds, val_ds, batch_size, seed)
    return tr, va, vocab_size, name
