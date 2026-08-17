"""
Plot loss curves and QUINN sync trajectory.
Gracefully skips if matplotlib is unavailable.
Reads results/training_results.json — run after protocol.py.

Usage:
    python train/plot.py
    python train/plot.py 2>/dev/null || echo "Skipping plots"
"""
import json
import os
import sys

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend for headless environments
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

RESULTS_FILE = "results/training_results.json"
OUTPUT_FILE = "results/loss_curves.png"

COLORS = {
    "QUINN": "#2196F3",   # blue
    "Adam":  "#FF5722",   # orange-red
    "AdamW": "#4CAF50",   # green
}
LINESTYLES = {
    "QUINN": "-",
    "Adam":  "--",
    "AdamW": "-.",
}


def load_results():
    with open(RESULTS_FILE) as f:
        return json.load(f)


def plot_results(data: dict):
    results = data["results"]
    meta = data.get("meta", {})
    dataset = meta.get("dataset", "unknown")
    n_params = meta.get("n_params", 0)

    has_sync = any(
        any(e.get("sync") is not None for e in h)
        for h in results.values()
    )

    n_axes = 2 if has_sync else 1
    fig, axes = plt.subplots(1, n_axes, figsize=(6 * n_axes, 5))
    if n_axes == 1:
        axes = [axes]

    ax_loss = axes[0]
    ax_sync = axes[1] if has_sync else None

    for name, history in results.items():
        epochs = [e["epoch"] for e in history]
        val_loss = [e["val_loss"] for e in history]
        train_loss = [e["train_loss"] for e in history]
        color = COLORS.get(name, "gray")
        ls = LINESTYLES.get(name, "-")

        ax_loss.plot(epochs, val_loss, color=color, ls=ls, lw=2, label=f"{name} val")
        ax_loss.plot(epochs, train_loss, color=color, ls=ls, lw=1, alpha=0.4, label=f"{name} train")

        if ax_sync is not None:
            syncs = [e.get("sync") for e in history]
            valid_ep = [ep for ep, s in zip(epochs, syncs) if s is not None]
            valid_sy = [s for s in syncs if s is not None]
            if valid_ep and name == "QUINN":
                ax_sync.plot(valid_ep, valid_sy, color=color, lw=2, label="QUINN sync")

    ax_loss.set_xlabel("Epoch")
    ax_loss.set_ylabel("Loss")
    ax_loss.set_title(f"Loss curves\n{dataset} | {n_params/1e6:.1f}M params")
    ax_loss.legend(fontsize=8, ncol=2)
    ax_loss.grid(True, alpha=0.3)
    ax_loss.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    if ax_sync is not None:
        s_star = 7 / 9
        ax_sync.axhline(s_star, color="black", ls=":", lw=1.5, label=f"s*={s_star:.3f}")
        ax_sync.set_xlabel("Epoch")
        ax_sync.set_ylabel("Mean sync score")
        ax_sync.set_title("QUINN sync trajectory\n(above s* = precision mode)")
        ax_sync.set_ylim(0, 1.05)
        ax_sync.legend(fontsize=9)
        ax_sync.grid(True, alpha=0.3)
        ax_sync.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    os.makedirs("results", exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"[plot] saved {OUTPUT_FILE}")


def main():
    if not HAS_MATPLOTLIB:
        print("[plot] matplotlib not available — skipping plots", file=sys.stderr)
        sys.exit(0)

    if not os.path.exists(RESULTS_FILE):
        print(f"[plot] {RESULTS_FILE} not found — run protocol.py first", file=sys.stderr)
        sys.exit(1)

    data = load_results()
    plot_results(data)


if __name__ == "__main__":
    main()
