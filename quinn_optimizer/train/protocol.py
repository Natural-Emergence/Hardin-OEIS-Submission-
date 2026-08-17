"""
QUINN optimizer training protocol.

Trains the same transformer LM from the same random seed with three optimizers
(QUINN, Adam, AdamW) and produces a reproducible comparison.

Usage:
    python train/protocol.py --epochs 20 --device cpu
    python train/protocol.py --quick            # 3 epochs, 1000 samples (~5 min)
"""
import sys
import os
import json
import math
import time
import copy
import argparse

# Allow imports from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

import torch
import torch.nn as nn

from quinn import QUINN
from train.model import ModelConfig, TransformerLM, count_parameters, build_model
from train.data import get_dataloaders


# ─── LR schedule ───────────────────────────────────────────────────────────────

def cosine_lr_with_warmup(step: int, warmup_steps: int, total_steps: int,
                           max_lr: float, min_lr: float = 1e-5) -> float:
    if step < warmup_steps:
        return max_lr * (step + 1) / warmup_steps
    if step >= total_steps:
        return min_lr
    progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * progress))


def set_lr(optimizer: torch.optim.Optimizer, lr: float):
    for pg in optimizer.param_groups:
        pg["lr"] = lr


# ─── Training / evaluation loops ───────────────────────────────────────────────

def train_epoch(
    model: TransformerLM,
    optimizer: torch.optim.Optimizer,
    loader,
    device: str,
    max_steps: int,
    lr_fn,
    step_offset: int,
    opt_name: str,
    epoch: int,
    total_epochs: int,
) -> float:
    model.train()
    total_loss = 0.0
    n = 0
    t0 = time.time()

    for i, (x, y) in enumerate(loader):
        if i >= max_steps:
            break
        x, y = x.to(device), y.to(device)

        global_step = step_offset + i
        set_lr(optimizer, lr_fn(global_step))

        optimizer.zero_grad()
        _, loss = model(x, y)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item()
        n += 1

        elapsed = time.time() - t0
        print(
            f"\r  [{opt_name:5s}] Ep {epoch:2d}/{total_epochs} "
            f"| step {i+1:4d}/{max_steps} "
            f"| loss {loss.item():.4f} "
            f"| {elapsed:.0f}s",
            end="",
            flush=True,
        )

    return total_loss / max(n, 1)


@torch.no_grad()
def eval_epoch(
    model: TransformerLM,
    loader,
    device: str,
    max_steps: int,
) -> float:
    model.eval()
    total_loss = 0.0
    n = 0
    for i, (x, y) in enumerate(loader):
        if i >= max_steps:
            break
        x, y = x.to(device), y.to(device)
        _, loss = model(x, y)
        total_loss += loss.item()
        n += 1
    return total_loss / max(n, 1)


# ─── Single-optimizer full training run ────────────────────────────────────────

def run_optimizer(
    name: str,
    optimizer: torch.optim.Optimizer,
    model: TransformerLM,
    init_state: dict,
    make_loaders_fn,          # callable() → (train_loader, val_loader)
    n_epochs: int,
    max_train_steps: int,
    max_val_steps: int,
    device: str,
    base_lr: float,
    warmup_steps: int,
    total_steps: int,
) -> list:
    """Train one optimizer from scratch, return list of per-epoch dicts."""
    # Reset model to the shared initial weights
    model.load_state_dict(copy.deepcopy(init_state))
    model.to(device)

    history = []
    step_offset = 0
    lr_fn = lambda s: cosine_lr_with_warmup(s, warmup_steps, total_steps, base_lr)

    # Create loaders once: generator evolves each epoch for different shuffles,
    # but all optimizers start from the same generator seed = reproducible.
    train_loader, val_loader = make_loaders_fn()

    print(f"\n{'='*60}")
    print(f"  Training: {name}")
    print(f"{'='*60}")

    for epoch in range(1, n_epochs + 1):
        t0 = time.time()

        train_loss = train_epoch(
            model, optimizer, train_loader, device,
            max_train_steps, lr_fn, step_offset, name, epoch, n_epochs,
        )
        val_loss = eval_epoch(model, val_loader, device, max_val_steps)
        epoch_time = time.time() - t0

        ppl = math.exp(min(val_loss, 20.0))

        sync_stats: dict = {}
        if hasattr(optimizer, "get_sync_stats"):
            sync_stats = optimizer.get_sync_stats() or {}

        mean_sync = sync_stats.get("mean_sync", float("nan"))
        pct_prec = sync_stats.get("pct_precision", float("nan"))
        s_star = sync_stats.get("s_star", 7 / 9)

        mode = "P" if (not math.isnan(pct_prec) and pct_prec >= 0.5) else (
            "E" if not math.isnan(pct_prec) else "-"
        )

        sync_display = f"{mean_sync:.3f}" if not math.isnan(mean_sync) else "  n/a"
        prec_display = f"{pct_prec*100:.0f}%" if not math.isnan(pct_prec) else " n/a"

        print(
            f"\r  Ep {epoch:2d}/{n_epochs} | {name:5s} "
            f"| Train {train_loss:.4f} | Val {val_loss:.4f} "
            f"| PPL {ppl:7.1f} | Sync {sync_display} ({prec_display} prec) "
            f"| Mode {mode} | {epoch_time:.1f}s"
        )

        history.append(
            {
                "epoch": epoch,
                "train_loss": round(train_loss, 6),
                "val_loss": round(val_loss, 6),
                "ppl": round(ppl, 3),
                "sync": round(mean_sync, 6) if not math.isnan(mean_sync) else None,
                "pct_precision": round(pct_prec, 6) if not math.isnan(pct_prec) else None,
                "time_s": round(epoch_time, 2),
            }
        )

        step_offset += max_train_steps

    return history


# ─── Summary generation ────────────────────────────────────────────────────────

def format_summary(results: dict, dataset_name: str, n_epochs: int, n_params: int) -> str:
    lines = []
    lines.append("QUINN vs Adam Training Comparison")
    lines.append(f"Model: ~{n_params/1e6:.1f}M param transformer | Dataset: {dataset_name} | Epochs: {n_epochs}")
    lines.append("─" * 70)
    lines.append(f"{'Optimizer':<12} {'Final Val':>10} {'Best Val':>10} {'PPL':>8} {'Time/Ep':>10}")

    rows = {}
    for name in ["QUINN", "Adam", "AdamW"]:
        h = results.get(name, [])
        if not h:
            continue
        final_val = h[-1]["val_loss"]
        best_val = min(e["val_loss"] for e in h)
        final_ppl = h[-1]["ppl"]
        avg_time = sum(e["time_s"] for e in h) / len(h)
        rows[name] = (final_val, best_val, final_ppl, avg_time)
        lines.append(
            f"  {name:<10} {final_val:>10.4f} {best_val:>10.4f} {final_ppl:>8.1f} {avg_time:>8.1f}s"
        )

    lines.append("─" * 70)

    # Comparisons
    if "QUINN" in rows and "Adam" in rows:
        q_final, _, _, q_time = rows["QUINN"]
        a_final, _, _, a_time = rows["Adam"]
        diff_pct = (q_final - a_final) / a_final * 100
        direction = "better" if diff_pct < 0 else "worse"
        lines.append(f"QUINN vs Adam:  {abs(diff_pct):.1f}% {direction} final val loss")
        overhead = (q_time - a_time) / a_time * 100 if a_time > 0 else 0
        lines.append(f"QUINN wall-clock overhead vs Adam: {overhead:+.1f}%")

    if "QUINN" in rows and "AdamW" in rows:
        q_final = rows["QUINN"][0]
        aw_final = rows["AdamW"][0]
        diff_pct = (q_final - aw_final) / aw_final * 100
        direction = "better" if diff_pct < 0 else "worse"
        lines.append(f"QUINN vs AdamW: {abs(diff_pct):.1f}% {direction} final val loss")

    # QUINN sync trajectory
    if "QUINN" in results and results["QUINN"]:
        h = results["QUINN"]
        lines.append("")
        lines.append("QUINN Sync Trajectory:")
        checkpoints = [1, max(1, n_epochs // 2), n_epochs]
        for ep_target in checkpoints:
            ep_idx = min(ep_target - 1, len(h) - 1)
            entry = h[ep_idx]
            sync_val = entry.get("sync")
            pct_p = entry.get("pct_precision")
            if sync_val is not None:
                lines.append(
                    f"  Epoch {ep_idx+1:2d}: sync={sync_val:.3f} ({pct_p*100:.0f}% precision mode)"
                )

    # Honest notes
    lines.append("")
    lines.append("Honest notes:")
    if "QUINN" in rows and "Adam" in rows:
        q_best = rows["QUINN"][1]
        a_best = rows["Adam"][1]
        diff = (q_best - a_best) / a_best * 100
        if diff < -1:
            lines.append(f"  + QUINN achieves {abs(diff):.1f}% better best validation loss vs Adam")
        elif diff > 1:
            lines.append(f"  - QUINN achieves {abs(diff):.1f}% worse best validation loss vs Adam")
        else:
            lines.append("  ~ QUINN and Adam perform similarly on best val loss (<1% difference)")

    if "QUINN" in results and results["QUINN"]:
        h = results["QUINN"]
        first_sync = h[0].get("sync")
        last_sync = h[-1].get("sync") if h else None
        s_star = 7 / 9
        if first_sync is not None and last_sync is not None:
            if abs(last_sync - s_star) < 0.05:
                lines.append(f"  + QUINN sync converged toward s*=0.778 (final: {last_sync:.3f})")
            elif last_sync > s_star + 0.05:
                lines.append(f"  ~ QUINN sync settled above s*=0.778 (final: {last_sync:.3f}, precision mode)")
            else:
                lines.append(f"  ~ QUINN sync settled below s*=0.778 (final: {last_sync:.3f}, exploration mode)")

    if "QUINN" in rows and "Adam" in rows:
        q_time = rows["QUINN"][3]
        a_time = rows["Adam"][3]
        overhead = (q_time - a_time) / a_time * 100 if a_time > 0 else 0
        if overhead > 20:
            lines.append(f"  ! QUINN per-epoch overhead is {overhead:.0f}% vs Adam (above 20% target)")
        else:
            lines.append(f"  + QUINN per-epoch overhead is {overhead:.0f}% vs Adam (within 20% target)")

    return "\n".join(lines)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QUINN optimizer training benchmark")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seq-len", type=int, default=128)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps-per-epoch", type=int, default=200,
                        help="Max train batches per epoch (default 200)")
    parser.add_argument("--val-steps", type=int, default=50,
                        help="Max val batches per epoch")
    parser.add_argument("--lambda-geo", type=float, default=0.1)
    parser.add_argument("--sync-threshold", type=float, default=7 / 9)
    parser.add_argument("--synthetic", action="store_true",
                        help="Force synthetic dataset (offline mode)")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test: 3 epochs, 1000 train samples, 200 val samples",
    )
    args = parser.parse_args()

    # --quick overrides
    if args.quick:
        args.epochs = 3
        args.steps_per_epoch = 20
        args.val_steps = 10
        print("[quick] 3 epochs, 20 steps/epoch, 10 val steps")

    torch.manual_seed(args.seed)
    device = args.device
    print(f"[config] device={device}, epochs={args.epochs}, lr={args.lr}, seed={args.seed}")

    # ── Data ──────────────────────────────────────────────────────────────────
    max_train = args.steps_per_epoch * args.batch_size  # approx sample budget
    max_val = args.val_steps * args.batch_size

    train_loader_0, val_loader_0, vocab_size, dataset_name = get_dataloaders(
        batch_size=args.batch_size,
        seq_len=args.seq_len,
        max_train_samples=max_train if args.quick else None,
        max_val_samples=max_val if args.quick else None,
        seed=args.seed,
        force_synthetic=args.synthetic,
    )

    # Factory to create fresh DataLoaders with the same seed each run
    # so all three optimizers see the same batch order
    def make_loaders():
        from torch.utils.data import DataLoader
        g = torch.Generator()
        g.manual_seed(args.seed)
        tr = DataLoader(
            train_loader_0.dataset,
            batch_size=args.batch_size,
            shuffle=True,
            generator=g,
            drop_last=True,
        )
        va = DataLoader(
            val_loader_0.dataset,
            batch_size=args.batch_size,
            shuffle=False,
            drop_last=True,
        )
        return tr, va

    # ── Model ─────────────────────────────────────────────────────────────────
    cfg = ModelConfig(
        n_layers=4,
        n_heads=4,
        d_model=256,
        d_ff=1024,
        vocab_size=vocab_size,
        seq_len=args.seq_len,
        dropout=0.1,
    )
    torch.manual_seed(args.seed)
    model = TransformerLM(cfg).to(device)
    n_params = count_parameters(model)
    print(f"[model] {n_params:,} parameters ({n_params/1e6:.2f}M)")
    print(f"[model] config: {cfg.n_layers}L/{cfg.n_heads}H/{cfg.d_model}d/{cfg.d_ff}ff/vocab={vocab_size}")

    # Save initial weights — all three optimizers start from here
    init_state = copy.deepcopy(model.state_dict())

    # ── LR schedule parameters ────────────────────────────────────────────────
    warmup_steps = 100
    total_steps = args.epochs * args.steps_per_epoch
    print(f"[schedule] warmup={warmup_steps} steps, total={total_steps} steps, cosine decay")

    # ── Build optimizers ──────────────────────────────────────────────────────
    common_kw = dict(lr=args.lr, betas=(0.9, 0.999), eps=1e-8)

    def make_quinn():
        return QUINN(
            model.parameters(),
            lr=args.lr,
            betas=(0.9, 0.999),
            eps=1e-8,
            weight_decay=0.0,
            lambda_geo=args.lambda_geo,
            sync_threshold=args.sync_threshold,
        )

    def make_adam():
        return torch.optim.Adam(model.parameters(), **common_kw)

    def make_adamw():
        return torch.optim.AdamW(model.parameters(), weight_decay=0.01, **common_kw)

    # ── Header ────────────────────────────────────────────────────────────────
    print(f"\n{'Ep':>3} | {'Opt':^5} | {'Train':>8} | {'Val':>8} | {'PPL':>7} | {'Sync':>7} | M | {'Time':>5}")
    print("-" * 70)

    all_results = {}

    run_configs = [
        ("QUINN", make_quinn),
        ("Adam", make_adam),
        ("AdamW", make_adamw),
    ]

    for name, make_opt in run_configs:
        # Rebuild model (reset weights) and optimizer fresh for each run
        torch.manual_seed(args.seed)
        opt = make_opt()

        history = run_optimizer(
            name=name,
            optimizer=opt,
            model=model,
            init_state=init_state,
            make_loaders_fn=make_loaders,
            n_epochs=args.epochs,
            max_train_steps=args.steps_per_epoch,
            max_val_steps=args.val_steps,
            device=device,
            base_lr=args.lr,
            warmup_steps=warmup_steps,
            total_steps=total_steps,
        )
        all_results[name] = history

    # ── Save results ──────────────────────────────────────────────────────────
    os.makedirs("results", exist_ok=True)

    results_payload = {
        "meta": {
            "dataset": dataset_name,
            "n_params": n_params,
            "n_epochs": args.epochs,
            "base_lr": args.lr,
            "seed": args.seed,
            "steps_per_epoch": args.steps_per_epoch,
            "model_config": {
                "n_layers": cfg.n_layers,
                "n_heads": cfg.n_heads,
                "d_model": cfg.d_model,
                "d_ff": cfg.d_ff,
                "vocab_size": cfg.vocab_size,
                "seq_len": cfg.seq_len,
            },
        },
        "results": all_results,
    }

    with open("results/training_results.json", "w") as f:
        json.dump(results_payload, f, indent=2)
    print("\n\n[saved] results/training_results.json")

    summary = format_summary(all_results, dataset_name, args.epochs, n_params)
    with open("results/summary.txt", "w") as f:
        f.write(summary + "\n")
    print("[saved] results/summary.txt\n")
    print(summary)


if __name__ == "__main__":
    main()
