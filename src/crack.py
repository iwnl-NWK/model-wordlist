import argparse
import csv
import glob
import json
import os
import subprocess
import time


def count_lines(path):
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def run_session(hashcat, mode, hashfile, wordlist, rule_path, pot, out, device, extra):
    for p in (pot, out):
        if os.path.exists(p):
            os.remove(p)
    cmd = [hashcat, "-m", str(mode), "-a", "0", "-O", "-w", "3", "--quiet",
           "--potfile-path", pot, "-o", out, hashfile, wordlist]
    if rule_path:
        cmd += ["-r", rule_path]
    if device:
        cmd += ["-d", str(device)]
    if extra:
        cmd += extra
    t0 = time.time()
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          cwd=os.path.dirname(os.path.abspath(hashcat)))
    elapsed = time.time() - t0
    recovered = count_lines(out) if os.path.exists(out) else 0
    return recovered, elapsed, proc.returncode, proc.stdout.decode("utf-8", "ignore")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hashcat", required=True)
    ap.add_argument("--wordlists-dir", required=True)
    ap.add_argument("--targets-json", required=True)
    ap.add_argument("--rules-json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--potdir", required=True)
    ap.add_argument("--device", default="")
    ap.add_argument("--tag", default="reference")
    ap.add_argument("--extra", nargs=argparse.REMAINDER, default=[])
    args = ap.parse_args()

    with open(args.targets_json, encoding="utf-8") as f:
        targets = json.load(f)
    with open(args.rules_json, encoding="utf-8") as f:
        rules = json.load(f)
    for t in targets:
        t["path"] = os.path.abspath(t["path"])
    for rr in rules:
        if rr.get("path"):
            rr["path"] = os.path.abspath(rr["path"])
    os.makedirs(args.potdir, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    extra = args.extra

    wordlists = sorted(glob.glob(os.path.join(args.wordlists_dir, "*.txt")))
    totals = {t["name"]: count_lines(t["path"]) for t in targets}

    new_file = not os.path.exists(args.out)
    mf = open(args.out, "a", newline="", encoding="utf-8")
    w = csv.writer(mf)
    if new_file:
        w.writerow(["tag", "target", "hash_mode", "wordlist", "rule", "recovered", "total",
                    "recovery_pct", "duration_s", "cracks_per_s", "rc"])

    for t in targets:
        for wl in wordlists:
            wlname = os.path.splitext(os.path.basename(wl))[0]
            for rule in rules:
                sid = "%s__%s__%s__%s" % (args.tag, t["name"], wlname, rule["name"])
                pot = os.path.join(args.potdir, sid + ".pot")
                out = os.path.join(args.potdir, sid + ".out")
                rec, dur, rc, log = run_session(
                    args.hashcat, t["mode"], t["path"], wl, rule.get("path"), pot, out, args.device, extra)
                total = totals[t["name"]]
                pct = round(100.0 * rec / total, 4) if total else 0
                cps = round(rec / dur, 2) if dur > 0 else 0
                w.writerow([args.tag, t["name"], t["mode"], wlname, rule["name"], rec, total, pct, round(dur, 2), cps, rc])
                mf.flush()
                print("CRACK %s | rec=%d/%d (%.3f%%) dur=%.1fs cps=%.1f rc=%d" % (sid, rec, total, pct, dur, cps, rc), flush=True)
                if rc > 1:
                    print(log[-400:], flush=True)
    mf.close()
    print("CRACK_DONE tag=%s" % args.tag, flush=True)


if __name__ == "__main__":
    main()
