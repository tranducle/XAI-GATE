#!/usr/bin/env python3
"""Generate paper-facing PDF figures from XAI-SurfaceBench summary CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

PALETTE = {
    "xai_gate": "#0F766E",
    "xai_gate_dark": "#064E3B",
    "baseline": "#A8A29E",
    "baseline_edge": "#78716C",
    "threshold": "#B45309",
    "budget": "#64748B",
    "debt": "#9F1239",
    "coverage": "#0F766E",
    "exposure": "#334155",
    "drop": "#7C2D12",
    "grid": "#E7E5E4",
}

POLICY_LABELS = {
    "always_explain": "Always",
    "budget_only_bexgov": "Budget-only",
    "fifo_explanation": "FIFO",
    "never_explain": "Never",
    "rate_limited": "Rate-limited",
    "static_coarse_full": "Static coarse/full",
    "static_offload": "Static offload",
    "threshold_explain": "Threshold",
    "xai_gate": "XAI-Gate",
}

VARIANT_LABELS = {
    "default": "Default",
    "no_debt": "No debt",
    "no_exposure_budget": "No exposure budget",
    "no_fidelity_control": "No fidelity",
    "no_offload": "No offload",
    "no_rtt_robustness": "No RTT belief",
    "no_suspicion": "No suspicion",
    "threshold_only_scoring": "Threshold score",
    "burst_0.75": "Burst 0.75",
    "burst_1.50": "Burst 1.50",
    "cost_0.80": "Cost 0.80",
    "cost_1.25": "Cost 1.25",
    "detpert_0.10": "Det. pert. 0.10",
    "detpert_0.30": "Det. pert. 0.30",
    "rtt_0.50": "RTT 0.50",
    "rtt_1.50": "RTT 1.50",
    "service_0.85": "Service 0.85",
    "service_1.15": "Service 1.15",
}


def read_rows(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def policy_label(policy: str) -> str:
    return POLICY_LABELS.get(policy, policy.replace("_", " ").title())


def variant_label(variant: str) -> str:
    return VARIANT_LABELS.get(variant, variant.replace("_", " ").title())


def apply_academic_style(root: Path, plt) -> None:
    style_path = root / "styles" / "deepscientist-academic.mplstyle"
    if style_path.exists():
        plt.style.use(str(style_path))
    plt.rcParams.update(
        {
            "axes.titleweight": "semibold",
            "figure.constrained_layout.use": False,
            "savefig.transparent": False,
        }
    )


def save_paper_figure(fig, pdf_path: Path, preview_width_px: int = 1500) -> dict:
    """Save vector PDF plus PNG preview and return catalog metadata."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(pdf_path)
    preview_dir = pdf_path.parent / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    png_path = preview_dir / f"{pdf_path.stem}.png"
    fig.savefig(png_path, dpi=240)
    return {"pdf": str(pdf_path), "png_preview": str(png_path)}


def annotate(ax, text: str, xy, dx=4, dy=4, **kwargs) -> None:
    ax.annotate(
        text,
        xy=xy,
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=7.2,
        color=kwargs.pop("color", "#374151"),
        ha=kwargs.pop("ha", "left"),
        va=kwargs.pop("va", "bottom"),
        **kwargs,
    )


def save_main_frontier(root: Path, plt) -> Path | None:
    rows = read_rows(root / "results" / "main_summary.csv")
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    
    baselines = [row for row in rows if row["policy"] != "xai_gate"]
    xai_gate = [row for row in rows if row["policy"] == "xai_gate"]
    
    # Classify and plot baselines into distinct groups with unique styles
    unconstrained = [row for row in baselines if row["policy"] in ["always_explain", "fifo_explanation", "threshold_explain", "static_coarse_full"]]
    constrained = [row for row in baselines if row["policy"] in ["never_explain", "rate_limited", "budget_only_bexgov", "static_offload"]]
    
    ax.scatter(
        [f(row, "mean_packet_drop_rate") for row in unconstrained],
        [f(row, "mean_high_risk_explanation_coverage") for row in unconstrained],
        label="Unconstrained Baselines",
        s=20,
        marker="^",
        color="#64748B", # Elegant slate
        edgecolor="white",
        linewidth=0.35,
        alpha=0.70,
        zorder=2,
    )
    ax.scatter(
        [f(row, "mean_packet_drop_rate") for row in constrained],
        [f(row, "mean_high_risk_explanation_coverage") for row in constrained],
        label="Constrained Baselines",
        s=20,
        marker="s",
        color="#A8A29E", # Soft brown/warm grey
        edgecolor="white",
        linewidth=0.35,
        alpha=0.70,
        zorder=2,
    )
    
    # Sort XAI-Gate points by packet drop rate to draw a beautiful Pareto frontier curve
    xai_pts = sorted([(f(row, "mean_packet_drop_rate"), f(row, "mean_high_risk_explanation_coverage")) for row in xai_gate], key=lambda p: p[0])
    if xai_pts:
        xs = [p[0] for p in xai_pts]
        ys = [p[1] for p in xai_pts]
        # Smooth line connecting frontier points
        ax.plot(xs, ys, color=PALETTE["xai_gate"], linestyle="-", linewidth=1.5, zorder=3, label="XAI-Gate Frontier")
        # Soft semi-transparent area fill underneath the optimal envelope
        ax.fill_between(xs, ys, 0, color=PALETTE["xai_gate"], alpha=0.08, zorder=1)
        
    ax.scatter(
        [f(row, "mean_packet_drop_rate") for row in xai_gate],
        [f(row, "mean_high_risk_explanation_coverage") for row in xai_gate],
        label="XAI-Gate Points",
        s=36,
        marker="D",
        color=PALETTE["xai_gate"],
        edgecolor=PALETTE["xai_gate_dark"],
        linewidth=0.55,
        zorder=4,
    )
    
    adv = [row for row in xai_gate if row["regime"] == "adversarial_explanation_flood"]
    if adv:
        row = adv[0]
        xy = (f(row, "mean_packet_drop_rate"), f(row, "mean_high_risk_explanation_coverage"))
        ax.scatter([xy[0]], [xy[1]], marker="*", s=90, color="#F59E0B", edgecolor="#B45309", linewidth=0.5, zorder=5, label="Default Adversarial")
        annotate(ax, "default\nadversarial", xy, dx=10, dy=6, va="bottom", color=PALETTE["xai_gate_dark"])
        
    ax.set_xlabel("Packet drop rate")
    ax.set_ylabel("High-risk explanation coverage")
    ax.set_title("Service frontier")
    ax.set_xlim(-0.01, max(0.38, max(f(row, "mean_packet_drop_rate") for row in rows) * 1.05))
    ax.set_ylim(-0.03, 1.05)
    
    # Elegant double-ended arrow visual showing envelope gain relative to Never Explain baseline
    ax.annotate(
        "",
        xy=(0.035, 0.76),
        xytext=(0.035, 0.10),
        arrowprops=dict(arrowstyle="<->", color="#0F766E", lw=0.95, ls="-"),
    )
    ax.text(
        0.05, 0.43,
        "Service Gain Zone",
        color="#0F766E",
        fontsize=7.5,
        fontweight="semibold",
        rotation=90,
        ha="left",
        va="center",
    )
    
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), handletextpad=0.3, frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=7.2, ncol=3)
    path = root / "figures" / "main_packet_explanation_frontier.pdf"
    save_paper_figure(fig, path)
    plt.close(fig)
    return path


def save_demand_curves(root: Path, plt) -> Path | None:
    rows = read_rows(root / "results" / "demand_sweep_summary.csv")
    if not rows:
        return None
    grouped = defaultdict(list)
    for row in rows:
        if row["regime"] != "adversarial_explanation_flood":
            continue
        grouped[row["policy"]].append(row)
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4), sharex=True)
    for policy, subset in sorted(grouped.items()):
        subset = sorted(subset, key=lambda row: row["variant"])
        xs = [float(row["variant"].replace("attack_", "")) for row in subset]
        axes[0].plot(xs, [f(row, "mean_mean_explanation_debt") for row in subset], marker="o", label=policy)
        axes[1].plot(xs, [f(row, "mean_packet_drop_rate") for row in subset], marker="o", label=policy)
    axes[0].set_ylabel("Mean explanation debt")
    axes[1].set_ylabel("Packet drop rate")
    for ax in axes:
        ax.set_xlabel("Attack multiplier")
        ax.grid(True, alpha=0.28)
    axes[1].legend(fontsize=7, ncol=1)
    path = root / "figures" / "demand_inflation_debt_drop_curves.pdf"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_demand_coverage_debt_exposure(root: Path, plt) -> Path | None:
    rows = read_rows(root / "results" / "demand_sweep_summary.csv")
    if not rows:
        return None
    grouped = defaultdict(list)
    for row in rows:
        if row["regime"] != "adversarial_explanation_flood":
            continue
        grouped[row["policy"]].append(row)
    if not grouped:
        return None
    subset = sorted(grouped.get("xai_gate", []), key=lambda row: row["variant"])
    if not subset:
        return None
    xs = [float(row["variant"].replace("attack_", "")) for row in subset]
    coverage = [f(row, "mean_high_risk_explanation_coverage") for row in subset]
    exposure = [f(row, "mean_exposure_use") for row in subset]
    debt = [f(row, "mean_mean_explanation_debt") for row in subset]
    
    # Absolute debt values in thousands for the twinx secondary axis
    debt_k = [value / 1000.0 for value in debt]

    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    
    # 1. Primary Y-Axis (Left): Coverage & Exposure Use
    # Shaded soft area fill under High-Risk Coverage
    ax.fill_between(xs, coverage, 0, color=PALETTE["coverage"], alpha=0.08, zorder=1)
    line_cov = ax.plot(xs, coverage, marker="o", color=PALETTE["coverage"], linewidth=1.6, label="Coverage (left)", zorder=3)
    line_exp = ax.plot(xs, exposure, marker="s", color=PALETTE["exposure"], linewidth=1.6, label="Exposure use (left)", zorder=3)
    
    # Budget limits & over-exposure soft red band
    ax.axhline(1.0, color="#EF4444", linestyle="--", linewidth=1.0, alpha=0.6, zorder=2)
    ax.fill_between(xs, 1.0, 1.15, color="#EF4444", alpha=0.03, zorder=1)
    ax.text(xs[0] + 0.05, 1.06, "exposure budget", fontsize=7.2, color="#EF4444", va="bottom", ha="left", fontweight="medium", bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))
    
    ax.set_xlabel("Attack multiplier")
    ax.set_ylabel("Coverage & Exposure Use", color=PALETTE["coverage"], fontweight="semibold")
    ax.set_ylim(-0.03, 1.35)
    ax.set_xticks(xs)
    ax.tick_params(axis='y', labelcolor=PALETTE["coverage"])
    
    # 2. Secondary Y-Axis (Right): Absolute explanation debt in thousands
    ax2 = ax.twinx()
    line_debt = ax2.plot(xs, debt_k, marker="^", color=PALETTE["debt"], linestyle="--", linewidth=1.4, label="Debt, K (right)", zorder=4)
    ax2.set_ylabel("Explanation Debt (thousands)", color=PALETTE["debt"], fontweight="semibold")
    ax2.tick_params(axis='y', labelcolor=PALETTE["debt"])
    ax2.set_ylim(-1.0, max(debt_k) * 1.12 if max(debt_k) > 0 else 5.0)
    ax2.spines['right'].set_color(PALETTE["debt"])
    ax2.spines['right'].set_visible(True)
    
    # Combined legend for both axes
    lines = line_cov + line_exp + line_debt
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc="upper center", bbox_to_anchor=(0.5, -0.20), handletextpad=0.35, frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=7.2, ncol=3, columnspacing=0.8)
    
    ax.set_title("Demand-inflation response")
    path = root / "figures" / "demand_inflation_coverage_debt_exposure.pdf"
    save_paper_figure(fig, path)
    plt.close(fig)
    return path


def save_frontier_envelope(root: Path, plt) -> Path | None:
    rows = read_rows(root / "results" / "frontier_summary.csv")
    if not rows:
        return None
    selected = [row for row in rows if row["regime"] == "adversarial_explanation_flood"]
    if not selected:
        selected = rows
    grouped = defaultdict(list)
    for row in selected:
        grouped[row["policy"]].append(row)
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    for policy, subset in sorted(grouped.items()):
        subset = sorted(subset, key=lambda row: f(row, "mean_exposure_use"))
        xs = [f(row, "mean_packet_drop_rate") for row in subset]
        ys = [f(row, "mean_high_risk_explanation_coverage") for row in subset]
        ax.plot(xs, ys, marker="o", linewidth=1.2, label=policy)
    ax.set_xlabel("Packet drop rate")
    ax.set_ylabel("High-risk explanation coverage")
    ax.set_title("Budget frontier under adversarial explanation demand")
    ax.grid(True, alpha=0.28)
    ax.legend(fontsize=7, ncol=2)
    path = root / "figures" / "frontier_budget_envelope.pdf"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_ablation_panel(root: Path, plt) -> Path | None:
    rows = read_rows(root / "results" / "ablations_summary.csv")
    if not rows:
        return None
    selected = [row for row in rows if row["regime"] == "adversarial_explanation_flood"]
    if not selected:
        selected = rows
    selected = sorted(selected, key=lambda row: row["variant"])
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    xs = [f(row, "mean_mean_explanation_debt") / 1000.0 for row in selected]
    ys = [f(row, "mean_high_risk_explanation_coverage") for row in selected]
    
    # Find Default XAI-Gate point coordinates for vector displacement calculations
    default_idx = [i for i, row in enumerate(selected) if row["variant"] == "default"]
    if default_idx:
        idx = default_idx[0]
        x_def, y_def = xs[idx], ys[idx]
        
        # Draw sleek vector arrows pointing from Default state to each ablated state
        for i, row in enumerate(selected):
            if i == idx:
                continue
            x_abl, y_abl = xs[i], ys[i]
            ax.annotate(
                "",
                xy=(x_abl, y_abl),
                xytext=(x_def, y_def),
                arrowprops=dict(
                    arrowstyle="->",
                    color="#94A3B8",
                    lw=1.0,
                    ls="--",
                    shrinkA=3,
                    shrinkB=3,
                    connectionstyle="arc3,rad=0.08"
                ),
                zorder=2
            )
            
        # Draw Default point as a large golden-bordered diamond
        ax.scatter(
            [x_def], [y_def],
            s=64,
            marker="D",
            color=PALETTE["xai_gate"],
            edgecolor="#F59E0B",
            linewidth=1.2,
            label="Default XAI-Gate",
            zorder=4
        )
        
        # Draw all other points as standard dots
        abl_xs = [x for i, x in enumerate(xs) if i != idx]
        abl_ys = [y for i, y in enumerate(ys) if i != idx]
        ax.scatter(
            abl_xs, abl_ys,
            s=32,
            marker="o",
            color="#E2E8F0",
            edgecolor="#475569",
            linewidth=0.6,
            label="Ablated Variants",
            zorder=3
        )
    else:
        # Fallback if default is missing
        ax.scatter(xs, ys, s=32, color=PALETTE["xai_gate"], edgecolor="white", linewidth=0.45, zorder=3)

    label_offsets = {
        "default": (-14, 0, "right", "center"),
        "no_exposure_budget": (8, 6, "left", "bottom"),
        "no_debt": (8, -5, "left", "bottom"),
        "no_fidelity_control": (8, -4, "left", "bottom"),
    }
    label_text = {
        "no_exposure_budget": "No budget",
    }
    for row, x, y in zip(selected, xs, ys):
        variant = row["variant"]
        if variant not in label_offsets:
            continue
        dx, dy, ha, va = label_offsets[variant]
        label = label_text.get(variant, variant_label(variant))
        if variant == "default":
            annotate(ax, label, (x, y), dx=dx, dy=dy, ha=ha, va=va, color=PALETTE["xai_gate_dark"], fontweight="semibold")
        else:
            annotate(ax, label, (x, y), dx=dx, dy=dy, ha=ha, va=va)
            
    ax.set_xlabel("Mean explanation debt (thousand)")
    ax.set_ylabel("High-risk coverage")
    ax.set_title("Ablation effects")
    ax.set_ylim(0.24, 0.92)
    ax.set_xlim(-0.4, max(xs) * 1.12)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=7.2, ncol=2)
    path = root / "figures" / "ablation_adversarial_debt_coverage.pdf"
    save_paper_figure(fig, path)
    plt.close(fig)
    return path


def save_robustness_panel(root: Path, plt) -> Path | None:
    rows = read_rows(root / "results" / "robustness_summary.csv")
    if not rows:
        return None
    xai_rows = [row for row in rows if row["policy"] == "xai_gate"]
    if not xai_rows:
        return None

    # Select one representative/worst service point per variant to avoid repeated
    # vertical stacks from regime-crossed robustness sweeps.
    by_variant = defaultdict(list)
    for row in xai_rows:
        by_variant[row["variant"]].append(row)
    selected = [max(group, key=lambda row: f(row, "mean_packet_drop_rate")) for group in by_variant.values()]
    selected = sorted(selected, key=lambda row: (f(row, "mean_packet_drop_rate"), f(row, "mean_exposure_use")))

    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    xs = [f(row, "mean_packet_drop_rate") for row in selected]
    ys = [f(row, "mean_exposure_use") for row in selected]
    
    # Determine plot bounds to position operational zones perfectly
    max_x = max(xs) * 1.15 if xs else 0.3
    ax.set_xlim(-0.01, max_x)
    ax.set_ylim(0.44, 1.08)
    
    # 1. Overlay operational background zones
    # Feasible & Budget-Secure Zone: Y <= 1.0, X <= 0.05 (soft green)
    ax.axvspan(-0.01, 0.05, ymin=0, ymax=(1.0 - 0.44)/(1.08 - 0.44), color="#10B981", alpha=0.06, zorder=1)
    ax.text(0.002, 0.57, "Feasible &\nSecure", color="#047857", fontsize=7.0, fontweight="semibold", zorder=2)
    
    # Packet Degradation Zone: Y <= 1.0, X > 0.05 (soft amber)
    ax.axvspan(0.05, max_x, ymin=0, ymax=(1.0 - 0.44)/(1.08 - 0.44), color="#F59E0B", alpha=0.06, zorder=1)
    ax.text(0.065, 0.48, "Packet\nDegradation", color="#B45309", fontsize=7.0, fontweight="semibold", zorder=2)
    
    # Constraint Violation Zone: Y > 1.0 (soft red)
    ax.axhspan(1.0, 1.08, color="#EF4444", alpha=0.06, zorder=1)
    ax.text(0.003, 1.03, "Constraint Violation", color="#B91C1C", fontsize=7.0, fontweight="semibold", zorder=2)
    
    # 2. Scatter the robust points with shape coding for different stress domains
    # RTT / capacity / burstiness / cost stress classification
    burst_pts = [r for r in selected if "burst" in r["variant"]]
    cost_pts = [r for r in selected if "cost" in r["variant"]]
    rtt_pts = [r for r in selected if "rtt" in r["variant"]]
    default_pt = [r for r in selected if r["variant"] == "default"]
    other_pts = [r for r in selected if r not in burst_pts + cost_pts + rtt_pts + default_pt]
    
    styles = [
        (default_pt, "D", "#0D9488", "#064E3B", "Default"),
        (burst_pts, "o", "#3B82F6", "#1D4ED8", "Burst Stress"),
        (cost_pts, "^", "#E11D48", "#9F1239", "Cost Stress"),
        (rtt_pts, "s", "#8B5CF6", "#5B21B6", "RTT Stress"),
        (other_pts, "v", "#6B7280", "#374151", "Other Perturbations"),
    ]
    
    for pts, marker, color, edgecolor, label in styles:
        if not pts:
            continue
        ax.scatter(
            [f(r, "mean_packet_drop_rate") for r in pts],
            [f(r, "mean_exposure_use") for r in pts],
            s=28,
            marker=marker,
            color=color,
            edgecolor=edgecolor,
            linewidth=0.45,
            zorder=3,
            label=label
        )
        
    ax.axhline(1.0, color="#EF4444", linestyle="--", linewidth=1.0, alpha=0.6, zorder=2)
    
    labels_to_place = {
        "burst_1.50": ("Burst 1.50", 8, -16, "left", "bottom"),
        "default": ("near-budget\ncluster", -75, -35, "right", "bottom"),
    }
    for row in selected:
        if row["variant"] in labels_to_place:
            text, dx, dy, ha, va = labels_to_place[row["variant"]]
            xy = (f(row, "mean_packet_drop_rate"), f(row, "mean_exposure_use"))
            if row["variant"] == "default":
                annotate(ax, text, xy, dx=dx, dy=dy, ha=ha, va=va,
                         arrowprops=dict(arrowstyle="->", color="#64748B", lw=0.6, shrinkA=3, shrinkB=3))
            else:
                annotate(ax, text, xy, dx=dx, dy=dy, ha=ha, va=va)
            
    ax.set_xlabel("Packet drop rate")
    ax.set_ylabel("Exposure use")
    ax.set_title("Robustness boundary")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), frameon=True, facecolor="white", edgecolor="#E2E8F0", fontsize=7.2, ncol=3, handletextpad=0.3)
    path = root / "figures" / "robustness_xai_gate_drop_exposure.pdf"
    save_paper_figure(fig, path)
    plt.close(fig)
    return path


def write_catalog(root: Path, generated: list[Path]) -> None:
    metadata = {
        "surface_class": "paper_main",
        "generating_script": "scripts/make_figures.py",
        "source_data_dir": "results/",
        "style": "styles/deepscientist-academic.mplstyle",
        "figures": [
            {
                "name": "main_packet_explanation_frontier",
                "pdf": "figures/main_packet_explanation_frontier.pdf",
                "png_preview": "figures/previews/main_packet_explanation_frontier.png",
                "main_claim": "XAI-Gate is compared as a service-frontier policy rather than a detector-accuracy method.",
                "self_review_note": "Baseline points were neutralized and XAI-Gate was highlighted directly.",
            },
            {
                "name": "demand_inflation_coverage_debt_exposure",
                "pdf": "figures/demand_inflation_coverage_debt_exposure.pdf",
                "png_preview": "figures/previews/demand_inflation_coverage_debt_exposure.png",
                "main_claim": "Demand inflation trades high-risk coverage against debt and exposure pressure.",
                "self_review_note": "Crowded multi-policy three-panel plot was reduced to a single XAI-Gate response panel.",
            },
            {
                "name": "ablation_adversarial_debt_coverage",
                "pdf": "figures/ablation_adversarial_debt_coverage.pdf",
                "png_preview": "figures/previews/ablation_adversarial_debt_coverage.png",
                "main_claim": "Removing state variables changes the debt-coverage operating point.",
                "self_review_note": "Dual-axis bar/line chart was replaced by a direct debt-versus-coverage operating-point plot.",
            },
            {
                "name": "robustness_xai_gate_drop_exposure",
                "pdf": "figures/robustness_xai_gate_drop_exposure.pdf",
                "png_preview": "figures/previews/robustness_xai_gate_drop_exposure.png",
                "main_claim": "Robustness sweeps delimit the exposure/drop boundary under stressed variants.",
                "self_review_note": "Repeated vertical stacks were replaced by a representative worst-drop boundary scatter.",
            },
        ],
        "generated_pdf_paths": [
            str(path.relative_to(root)) if path is not None and path.is_relative_to(root) else str(path)
            for path in generated
            if path is not None
        ],
    }
    (root / "figures" / "figure_catalog.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    (root / "figures").mkdir(parents=True, exist_ok=True)
    import matplotlib.pyplot as plt
    apply_academic_style(root, plt)

    paths = [
        save_main_frontier(root, plt),
        save_demand_curves(root, plt),
        save_demand_coverage_debt_exposure(root, plt),
        save_frontier_envelope(root, plt),
        save_ablation_panel(root, plt),
        save_robustness_panel(root, plt),
    ]
    for path in paths:
        if path is not None:
            print(f"figure={path}")
    write_catalog(root, [path for path in paths if path is not None])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
