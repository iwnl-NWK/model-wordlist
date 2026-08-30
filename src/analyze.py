import argparse
import csv
import glob
import os
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_many(paths):
    rows = []
    for p in paths:
        if os.path.exists(p):
            rows += read_csv(p)
    return rows


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def bar(path, labels, values, title, xlabel):
    if not HAVE_MPL or not labels:
        return
    plt.figure(figsize=(9, max(3, 0.45 * len(labels))))
    y = range(len(labels))
    plt.barh(list(y), values, color="#3b6ea5")
    plt.yticks(list(y), labels, fontsize=8)
    plt.gca().invert_yaxis()
    plt.xlabel(xlabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-glob", default="results/raw/gen_metrics_*.csv")
    ap.add_argument("--crack", default="results/raw/crack_metrics.csv")
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    os.makedirs(args.results_dir, exist_ok=True)

    gen = read_many(sorted(glob.glob(args.gen_glob)))
    if gen:
        write_csv(os.path.join(args.results_dir, "gen_summary.csv"),
                  ["tier", "model", "prompt", "unique", "calls", "gen_seconds", "tokens", "tok_per_s", "nonconforming"],
                  gen)
        anchor = [r for r in gen if r["model"] == "phi3-mini" and r["prompt"] == "moderate"]
        if anchor:
            labels = [r["tier"] for r in anchor]
            vals = [float(r["tok_per_s"]) for r in anchor]
            bar(os.path.join(args.results_dir, "fig_anchor_tokps.png"), labels, vals,
                "Velocidade de geracao (Phi-3-mini, prompt moderate) por tier", "tokens/s")
        print("== GERACAO (tok/s por tier/modelo/prompt) ==")
        for r in gen:
            print("  %-14s %-12s %-9s unique=%s calls=%s gen_s=%s tok/s=%s noncomp=%s" % (
                r["tier"], r["model"], r["prompt"], r["unique"], r["calls"], r["gen_seconds"], r["tok_per_s"], r["nonconforming"]))

    crack = read_many([args.crack])
    if crack:
        ref = [r for r in crack if r["tag"] == "reference"]
        recovery = defaultdict(dict)
        for r in ref:
            key = r["wordlist"]
            recovery[key]["%s/%s" % (r["target"], r["rule"])] = r["recovered"]
        cols = sorted({k for d in recovery.values() for k in d})
        rows = []
        for wl, d in recovery.items():
            row = {"wordlist": wl}
            row.update({c: d.get(c, "") for c in cols})
            rows.append(row)
        rows.sort(key=lambda x: -max([int(v) for v in x.values() if str(v).isdigit()] or [0]))
        write_csv(os.path.join(args.results_dir, "recovery_summary.csv"), ["wordlist"] + cols, rows)

        for target in sorted({r["target"] for r in ref}):
            sub = [r for r in ref if r["target"] == target and r["rule"] == "onerule"]
            sub.sort(key=lambda r: -int(r["recovered"]))
            sub = sub[:14]
            bar(os.path.join(args.results_dir, "fig_recovery_%s.png" % target),
                [r["wordlist"] for r in sub], [int(r["recovered"]) for r in sub],
                "Senhas recuperadas por wordlist (%s, onerule)" % target, "senhas recuperadas")

        perTier = [r for r in crack if r["tag"] != "reference"]
        if perTier:
            labels = ["%s/%s" % (r["tag"], r["target"]) for r in perTier]
            vals = [float(r["cracks_per_s"]) for r in perTier]
            bar(os.path.join(args.results_dir, "fig_cracks_per_s.png"), labels, vals,
                "Velocidade de cracking (cracks/s) por tier", "cracks/s")
        print("== RECUPERACAO (top wordlists, referencia) ==")
        for row in rows[:14]:
            print("  %-42s %s" % (row["wordlist"], {c: row[c] for c in cols}))
    print("ANALYZE_DONE")


if __name__ == "__main__":
    main()
