#!/usr/bin/env python3
# Copyright (c) 2026 Jeffrey S. Hardin. All rights reserved.
# Copyright is claimed only to the extent permitted by law in original
# human-authored expression and protectable human selection, coordination,
# arrangement, revision, modification, and integration. No AI system is
# asserted to be a legal author or coauthor.
# Status: AI-assisted draft - pending human review
# AI-Assisted-By: Claude | AI-Provider: Anthropic | AI-Model: not-recorded
# Human-Review: pending
# ===========================================================================
# GEOMETRIC ATTENTION VARIANTS: BUILD AND TRAIN
#
# Three attention mechanisms, identical everywhere else, trained head-to-head:
#
#   A. vanilla    - standard scaled dot-product causal attention (baseline)
#   B. geodesic   - arccos distance on S^(sphere_dim-1), softmax(-d^2/T)
#                   (from attention_trust_aware.py, which is well-formed)
#   C. km_qutrit  - Kubelka-Munk dual-flux envelope + D3 head weights
#
# CONSTRUCTION NOTES FOR C
#   The submitted KM module had no k_proj/v_proj: K and V were built only from
#   t = arange(positions), so they were input-independent constants, and
#   r_expanded broadcast one scalar across head_dim making V rank 1. A rank-1
#   value space cannot carry gradient into more than one direction, so the
#   block could not train. Two changes make it trainable while KEEPING the
#   geometry:
#     1. real k_proj / v_proj so keys and values carry content
#     2. the KM reflectance envelope becomes an ADDITIVE bias on logits
#        rather than a multiplier. Multiplying pre-softmax logits by
#        exp(-0.1*t) drives them toward 0 and the softmax toward uniform --
#        it erases attention instead of shaping it. An additive bias is a
#        proper positional prior and is what the geometry actually wants.
#   flux_scale is a learnable parameter, so the model can discover the decay
#   rate rather than having 0.05 hardcoded.
#
# HONESTY RULES
#   - identical seed, data, optimizer, schedule, and parameter budget
#   - parameter counts printed; if they differ the comparison is void
#   - held-out validation loss is the metric, not training loss
#   - multiple seeds, mean +/- std reported; single-seed wins are noise
#   - no aggregate "speedup" claim; the loss curves are the result
# ===========================================================================

import math, time, sys
from dataclasses import dataclass
import torch, torch.nn as nn, torch.nn.functional as F

torch.set_num_threads(4)

# ---------------------------------------------------------------- config
@dataclass
class Cfg:
    d_model: int = 128
    n_heads: int = 4
    n_layers: int = 3
    d_ff: int = 256
    seq_len: int = 96
    dropout: float = 0.0
    sphere_dim: int = 20          # S^19, per the trust-manifold spec
    temperature: float = 1.0
    vocab_size: int = 0           # set from data


# ---------------------------------------------------------------- A: vanilla
class VanillaAttention(nn.Module):
    def __init__(s, c):
        super().__init__()
        s.h, s.hd = c.n_heads, c.d_model // c.n_heads
        s.qkv = nn.Linear(c.d_model, 3 * c.d_model, bias=False)
        s.out = nn.Linear(c.d_model, c.d_model, bias=False)

    def forward(s, x):
        B, T, C = x.shape
        q, k, v = s.qkv(x).split(C, dim=2)
        q = q.view(B, T, s.h, s.hd).transpose(1, 2)
        k = k.view(B, T, s.h, s.hd).transpose(1, 2)
        v = v.view(B, T, s.h, s.hd).transpose(1, 2)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(s.hd)
        att = att.masked_fill(torch.tril(torch.ones(T, T, device=x.device)) == 0, float('-inf'))
        y = F.softmax(att, dim=-1) @ v
        return s.out(y.transpose(1, 2).contiguous().view(B, T, C))


# ---------------------------------------------------------------- B: geodesic
class GeodesicAttention(nn.Module):
    """softmax(-d_geo(q,k)^2 / T) with d_geo = arccos on the unit sphere."""
    def __init__(s, c):
        super().__init__()
        s.h, s.hd, s.sd = c.n_heads, c.d_model // c.n_heads, c.sphere_dim
        s.q = nn.Linear(c.d_model, s.h * s.sd, bias=False)
        s.k = nn.Linear(c.d_model, s.h * s.sd, bias=False)
        s.v = nn.Linear(c.d_model, c.d_model, bias=False)
        s.out = nn.Linear(c.d_model, c.d_model, bias=False)
        s.temp = nn.Parameter(torch.tensor(float(c.temperature)))

    def forward(s, x):
        B, T, C = x.shape
        q = F.normalize(s.q(x).view(B, T, s.h, s.sd).transpose(1, 2), dim=-1)
        k = F.normalize(s.k(x).view(B, T, s.h, s.sd).transpose(1, 2), dim=-1)
        v = s.v(x).view(B, T, s.h, s.hd).transpose(1, 2)
        dots = (q @ k.transpose(-2, -1)).clamp(-1 + 1e-6, 1 - 1e-6)
        d = torch.acos(dots)
        att = -(d ** 2) / s.temp.clamp_min(0.05)
        att = att.masked_fill(torch.tril(torch.ones(T, T, device=x.device)) == 0, float('-inf'))
        y = F.softmax(att, dim=-1) @ v
        return s.out(y.transpose(1, 2).contiguous().view(B, T, C))


# ---------------------------------------------------------------- C: KM qutrit
class KMQutritAttention(nn.Module):
    """
    Kubelka-Munk dual-flux positional prior + D3 head weighting, made trainable.

    KM envelope:  I+ = exp(+a t), I- = exp(-a t), r = I-/I+ = exp(-2a t)
    Used as an ADDITIVE relative-position bias  b(dt) = -gain * (1 - exp(-2a*dt))
    so recent positions get bias ~0 and distant ones a learned penalty.
    D3 head weights [1,1,0.85,0.85] are kept but made learnable.
    Qutrit phase: an additive cos(2*pi*dt/3) term, the Z3 circulation.
    """
    def __init__(s, c):
        super().__init__()
        s.h, s.hd = c.n_heads, c.d_model // c.n_heads
        s.qkv = nn.Linear(c.d_model, 3 * c.d_model, bias=False)
        s.out = nn.Linear(c.d_model, c.d_model, bias=False)
        s.flux = nn.Parameter(torch.full((c.n_heads,), 0.05))     # a, per head
        s.gain = nn.Parameter(torch.ones(c.n_heads))
        s.d3 = nn.Parameter(torch.tensor([1.0, 1.0, 0.85, 0.85][:c.n_heads]))
        s.phase = nn.Parameter(torch.zeros(c.n_heads))            # Z3 amplitude

    def forward(s, x):
        B, T, C = x.shape
        q, k, v = s.qkv(x).split(C, dim=2)
        q = q.view(B, T, s.h, s.hd).transpose(1, 2)
        k = k.view(B, T, s.h, s.hd).transpose(1, 2)
        v = v.view(B, T, s.h, s.hd).transpose(1, 2)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(s.hd)
        att = att * s.d3.view(1, s.h, 1, 1)

        pos = torch.arange(T, device=x.device, dtype=torch.float32)
        dt = (pos.view(T, 1) - pos.view(1, T)).clamp_min(0)        # >=0 causal lag
        a = s.flux.abs().view(s.h, 1, 1)
        r = torch.exp(-2.0 * a * dt.unsqueeze(0))                  # Mobius ratio
        bias = -s.gain.view(s.h, 1, 1) * (1.0 - r)                 # additive prior
        z3 = s.phase.view(s.h, 1, 1) * torch.cos(2 * math.pi * dt.unsqueeze(0) / 3.0)
        att = att + (bias + z3).unsqueeze(0)

        att = att.masked_fill(torch.tril(torch.ones(T, T, device=x.device)) == 0, float('-inf'))
        y = F.softmax(att, dim=-1) @ v
        return s.out(y.transpose(1, 2).contiguous().view(B, T, C))


ATTN = {"vanilla": VanillaAttention, "geodesic": GeodesicAttention, "km_qutrit": KMQutritAttention}


# ---------------------------------------------------------------- model
class Block(nn.Module):
    def __init__(s, c, kind):
        super().__init__()
        s.ln1, s.ln2 = nn.LayerNorm(c.d_model), nn.LayerNorm(c.d_model)
        s.attn = ATTN[kind](c)
        s.fc1 = nn.Linear(c.d_model, c.d_ff, bias=False)
        s.fc2 = nn.Linear(c.d_ff, c.d_model, bias=False)

    def forward(s, x):
        x = x + s.attn(s.ln1(x))
        return x + s.fc2(F.gelu(s.fc1(s.ln2(x))))


class LM(nn.Module):
    def __init__(s, c, kind):
        super().__init__()
        s.tok = nn.Embedding(c.vocab_size, c.d_model)
        s.pos = nn.Embedding(c.seq_len, c.d_model)
        s.blocks = nn.ModuleList([Block(c, kind) for _ in range(c.n_layers)])
        s.lnf = nn.LayerNorm(c.d_model)
        s.head = nn.Linear(c.d_model, c.vocab_size, bias=False)
        s.cfg = c

    def forward(s, idx, targets=None):
        B, T = idx.shape
        x = s.tok(idx) + s.pos(torch.arange(T, device=idx.device))
        for b in s.blocks:
            x = b(x)
        logits = s.head(s.lnf(x))
        if targets is None:
            return logits, None
        return logits, F.cross_entropy(logits.view(-1, logits.size(-1)), targets.reshape(-1))


# ---------------------------------------------------------------- data
def load_corpus():
    """Real structured text: Python source code."""
    import os
    txt = []

    # Try to load Python files from common locations
    search_paths = [
        "/home/user/Hardin-OEIS-Submission-/geolang_core",
        "/home/user/Hardin-OEIS-Submission-/tests",
        "/root/.local/lib/python*/site-packages",
    ]

    for base_path in search_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    if f.endswith(".py"):
                        try:
                            path = os.path.join(root, f)
                            with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                                txt.append(fp.read())
                        except Exception:
                            pass

    # Fallback: generate synthetic Python-like text
    if not txt:
        txt.append(open(__file__).read())  # This file itself
        txt.append("import torch\nimport numpy as np\ndef forward(x):\n    return x.sum()\n" * 1000)

    s = "\n".join(txt)
    if len(s) < 200000:
        s = (s * (200000 // max(len(s), 1) + 1))
    return s[:400000]


def make_data(cfg):
    text = load_corpus()
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    cfg.vocab_size = len(chars)
    data = torch.tensor([stoi[c] for c in text], dtype=torch.long)
    n = int(0.9 * len(data))
    return data[:n], data[n:], len(chars)


def get_batch(data, cfg, bs, gen):
    ix = torch.randint(len(data) - cfg.seq_len - 1, (bs,), generator=gen)
    x = torch.stack([data[i:i + cfg.seq_len] for i in ix])
    y = torch.stack([data[i + 1:i + 1 + cfg.seq_len] for i in ix])
    return x, y


@torch.no_grad()
def evaluate(model, data, cfg, gen, iters=25, bs=16):
    model.eval()
    tot = 0.0
    for _ in range(iters):
        x, y = get_batch(data, cfg, bs, gen)
        _, loss = model(x, y)
        tot += loss.item()
    model.train()
    return tot / iters


# ---------------------------------------------------------------- train
def run(kind, cfg, tr, va, seed, steps, bs, lr):
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed + 1)
    model = LM(cfg, kind)
    nparam = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps)
    t0 = time.time()
    curve = []
    for it in range(steps):
        x, y = get_batch(tr, cfg, bs, gen)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        if (it + 1) % (steps // 5) == 0:
            ev = evaluate(model, va, cfg, torch.Generator().manual_seed(1234))
            curve.append((it + 1, ev))
    final = evaluate(model, va, cfg, torch.Generator().manual_seed(1234), iters=50)
    return dict(kind=kind, params=nparam, final_val=final,
                curve=curve, secs=time.time() - t0)


def main():
    cfg = Cfg()
    tr, va, V = make_data(cfg)
    print("=" * 78)
    print("GEOMETRIC ATTENTION VARIANTS -- CONTROLLED TRAINING COMPARISON")
    print("=" * 78)
    print(f"corpus: {len(tr)+len(va):,} chars   vocab: {V}   "
          f"train {len(tr):,} / val {len(va):,}")
    print(f"model: d={cfg.d_model} heads={cfg.n_heads} layers={cfg.n_layers} "
          f"seq={cfg.seq_len}")

    STEPS, BS, LR, SEEDS = 300, 16, 3e-3, [0, 1]
    print(f"training: {STEPS} steps, batch {BS}, lr {LR}, seeds {SEEDS}\n")

    results = {}
    for kind in ["vanilla", "geodesic", "km_qutrit"]:
        runs = []
        for sd in SEEDS:
            r = run(kind, cfg, tr, va, sd, STEPS, BS, LR)
            runs.append(r)
            print(f"  {kind:<10} seed {sd}: val {r['final_val']:.4f}  "
                  f"({r['secs']:.0f}s, {r['params']:,} params)")
        results[kind] = runs

    print("\n" + "=" * 78)
    print("VALIDATION LOSS (held out), mean +/- std over seeds")
    print("=" * 78)
    base = None
    print(f"{'variant':<12}{'params':>10}{'val loss':>12}{'std':>9}"
          f"{'vs vanilla':>12}{'sec/run':>10}")
    for kind, runs in results.items():
        vals = torch.tensor([r["final_val"] for r in runs])
        m, sd = vals.mean().item(), vals.std().item()
        if base is None:
            base = m
        delta = m - base
        print(f"{kind:<12}{runs[0]['params']:>10,}{m:>12.4f}{sd:>9.4f}"
              f"{delta:>+12.4f}{sum(r['secs'] for r in runs)/len(runs):>10.0f}")

    pc = {k: v[0]["params"] for k, v in results.items()}
    if max(pc.values()) - min(pc.values()) > 0.02 * min(pc.values()):
        print("\n  WARNING: parameter counts differ by >2%. Comparison is not clean.")
    else:
        print(f"\n  parameter counts within 2% -- comparison is budget-matched.")

    print("\nLearning curves (val loss at checkpoints):")
    for kind, runs in results.items():
        pts = runs[0]["curve"]
        print(f"  {kind:<12}" + "  ".join(f"{s}:{v:.3f}" for s, v in pts))

    print("\nINTERPRETATION")
    print("  A variant only wins if its mean beats vanilla by more than the")
    print("  seed-to-seed std. Differences smaller than that are noise.")


if __name__ == "__main__":
    main()
