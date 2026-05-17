from __future__ import annotations
import argparse, csv
from pathlib import Path

PLOTS = [
    ('decision_grade_score','decision_grade_vs_budget.svg','Decision-grade score vs budget'),
    ('generated_answer_score','generated_answer_score_vs_budget.svg','Generated-answer score vs budget'),
    ('generated_answer_per_1k_tokens','generated_answer_per_1k_vs_budget.svg','Generated-answer score per 1k tokens vs budget'),
    ('distractor_admission_rate','distractor_rate_vs_budget.svg','Distractor admission rate vs budget'),
]

def read_csv(path):
    with Path(path).open(encoding="utf-8") as f: return list(csv.DictReader(f))

def simple_svg(path, rows, metric, title):
    methods = sorted({r['method'] for r in rows})
    budgets = sorted({int(r['budget']) for r in rows})
    W,H,ML,MB=900,520,90,70
    vals=[float(r[f'avg_{metric}']) for r in rows if r.get(f'avg_{metric}','') not in ('','nan')]
    ymin=0; ymax=max(vals+[1.0])
    def x(b): return ML+(b-min(budgets))/(max(budgets)-min(budgets) or 1)*(W-ML-40)
    def y(v): return H-MB-(v-ymin)/(ymax-ymin or 1)*(H-90-MB)
    colors=['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">',f'<text x="{ML}" y="35" font-size="22">{title}</text>',f'<line x1="{ML}" y1="{H-MB}" x2="{W-40}" y2="{H-MB}" stroke="black"/>',f'<line x1="{ML}" y1="50" x2="{ML}" y2="{H-MB}" stroke="black"/>']
    for i,b in enumerate(budgets): parts.append(f'<text x="{x(b)-10:.1f}" y="{H-35}" font-size="12">{b}</text>')
    for mi,m in enumerate(methods):
        pts=[]
        for b in budgets:
            rr=[r for r in rows if r['method']==m and int(r['budget'])==b]
            if rr: pts.append((x(b),y(float(rr[0][f'avg_{metric}']))))
        if len(pts)>1:
            parts.append(f'<polyline fill="none" stroke="{colors[mi%len(colors)]}" stroke-width="2" points="'+' '.join(f'{a:.1f},{bb:.1f}' for a,bb in pts)+'"/>')
        for a,bb in pts: parts.append(f'<circle cx="{a:.1f}" cy="{bb:.1f}" r="3" fill="{colors[mi%len(colors)]}"/>')
        parts.append(f'<text x="{W-260}" y="{65+mi*18}" font-size="12" fill="{colors[mi%len(colors)]}">{m}</text>')
    parts.append('</svg>')
    Path(path).write_text('\n'.join(parts), encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('output_dir'); a=ap.parse_args(); od=Path(a.output_dir); rows=read_csv(od/'budget_curves.csv')
    for metric,name,title in PLOTS: simple_svg(od/name,rows,metric,title)
if __name__=='__main__': main()
