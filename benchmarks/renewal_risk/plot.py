from __future__ import annotations

import argparse
import csv
from pathlib import Path
from collections import defaultdict


def read_csv(path: Path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_simple_svg(path: Path, title: str, series: dict[str, list[tuple[float, float]]], y_label: str) -> None:
    width, height = 860, 520
    margin_l, margin_r, margin_t, margin_b = 82, 30, 60, 72
    xs = [x for pts in series.values() for x, _ in pts]
    ys = [y for pts in series.values() for _, y in pts]
    if not xs or not ys:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = 0.0, max(ys) * 1.08 if max(ys) > 0 else 1.0

    def sx(x):
        if x_max == x_min:
            return margin_l
        return margin_l + (x - x_min) / (x_max - x_min) * (width - margin_l - margin_r)

    def sy(y):
        if y_max == y_min:
            return height - margin_b
        return height - margin_b - (y - y_min) / (y_max - y_min) * (height - margin_t - margin_b)

    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    lines = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"]
    lines.append("<rect width='100%' height='100%' fill='white'/>")
    lines.append(f"<text x='{width/2}' y='30' text-anchor='middle' font-family='Arial' font-size='20'>{title}</text>")
    lines.append(f"<line x1='{margin_l}' y1='{height-margin_b}' x2='{width-margin_r}' y2='{height-margin_b}' stroke='black'/>")
    lines.append(f"<line x1='{margin_l}' y1='{margin_t}' x2='{margin_l}' y2='{height-margin_b}' stroke='black'/>")
    lines.append(f"<text x='{width/2}' y='{height-22}' text-anchor='middle' font-family='Arial' font-size='14'>Token budget</text>")
    lines.append(f"<text transform='translate(24 {height/2}) rotate(-90)' text-anchor='middle' font-family='Arial' font-size='14'>{y_label}</text>")
    for i in range(6):
        y = y_min + (y_max - y_min) * i / 5
        yy = sy(y)
        lines.append(f"<line x1='{margin_l-5}' y1='{yy:.1f}' x2='{width-margin_r}' y2='{yy:.1f}' stroke='#eee'/>")
        lines.append(f"<text x='{margin_l-8}' y='{yy+4:.1f}' text-anchor='end' font-family='Arial' font-size='11'>{y:.2f}</text>")
    for x in sorted(set(xs)):
        xx = sx(x)
        lines.append(f"<text x='{xx:.1f}' y='{height-margin_b+20}' text-anchor='middle' font-family='Arial' font-size='11'>{int(x)}</text>")
    for idx, (name, pts) in enumerate(sorted(series.items())):
        color = palette[idx % len(palette)]
        pts_sorted = sorted(pts)
        path_d = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in pts_sorted)
        lines.append(f"<polyline fill='none' stroke='{color}' stroke-width='2.5' points='{path_d}'/>")
        for x, y in pts_sorted:
            lines.append(f"<circle cx='{sx(x):.1f}' cy='{sy(y):.1f}' r='3' fill='{color}'/>")
        lx = width - margin_r - 250
        ly = margin_t + 20 + idx * 18
        lines.append(f"<line x1='{lx}' y1='{ly-4}' x2='{lx+24}' y2='{ly-4}' stroke='{color}' stroke-width='3'/>")
        lines.append(f"<text x='{lx+30}' y='{ly}' font-family='Arial' font-size='12'>{name}</text>")
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def make_plots(output_dir: Path) -> None:
    curves = read_csv(output_dir / "budget_curves.csv")
    metrics = {
        "avg_evidence_score": ("evidence_score_vs_budget.svg", "Evidence score"),
        "avg_decision_grade_score": ("decision_grade_score_vs_budget.svg", "Decision-grade score"),
        "avg_quality_per_1k_tokens": ("quality_per_1k_vs_budget.svg", "Quality per 1k tokens"),
        "avg_distractor_admission_rate": ("distractor_rate_vs_budget.svg", "Distractor admission rate"),
        "avg_insufficient_evidence_calibration": ("missing_evidence_calibration_vs_budget.svg", "Missing-evidence calibration"),
    }
    for metric, (filename, label) in metrics.items():
        series = defaultdict(list)
        for r in curves:
            series[r["method"]].append((float(r["budget"]), float(r[metric])))
        write_simple_svg(output_dir / filename, filename.replace("_", " ").replace(".svg", ""), series, label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_dir")
    args = ap.parse_args()
    make_plots(Path(args.output_dir))
    print(f"wrote SVG plots to {args.output_dir}")


if __name__ == "__main__":
    main()
