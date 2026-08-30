import argparse
import hashlib
import os
import random
import re
import zipfile

HEX40 = re.compile(rb"^[0-9a-fA-F]{40}[: \t]")
HEX32 = re.compile(rb"^[0-9a-fA-F]{32}[: \t]")


def iter_plaintexts_from_zip(zip_path, hexre):
    with zipfile.ZipFile(zip_path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".txt")][0]
        with z.open(name) as f:
            for raw in f:
                line = raw.rstrip(b"\r\n")
                if not line:
                    continue
                if hexre.match(line):
                    line = re.split(rb"[: \t]", line, 1)[1]
                yield line.decode("utf-8", "ignore")


def iter_plaintexts_from_text(path):
    with open(path, "rb") as f:
        for raw in f:
            line = raw.rstrip(b"\r\n")
            if line:
                yield line.decode("utf-8", "ignore")


def load_unique(gen, limit=None):
    seen = set()
    for p in gen:
        if p and p not in seen:
            seen.add(p)
            if limit and len(seen) >= limit:
                break
    return list(seen)


def write_hashes(plaintexts, algo, out_path):
    h = hashlib.sha1 if algo == "sha1" else hashlib.md5
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for p in plaintexts:
            f.write(h(p.encode("utf-8", "ignore")).hexdigest() + "\n")
    return len(plaintexts)


def write_rockyou_samples(rockyou_path, out_dir, count, samples, seed):
    with open(rockyou_path, "rb") as f:
        lines = [l.rstrip(b"\r\n").decode("utf-8", "ignore") for l in f]
    lines = [l for l in lines if l]
    made = []
    for i in range(samples):
        rnd = random.Random(seed + i)
        take = rnd.sample(lines, min(count, len(lines)))
        p = os.path.join(out_dir, "rockyou_v%d.txt" % (i + 1))
        with open(p, "w", encoding="utf-8", newline="\n") as o:
            o.write("\n".join(take) + "\n")
        made.append(p)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--linkedin-zip", required=True)
    ap.add_argument("--eharmony")
    ap.add_argument("--rockyou", required=True)
    ap.add_argument("--targets-dir", required=True)
    ap.add_argument("--wordlists-dir", required=True)
    ap.add_argument("--sha1-sample", type=int, default=2000000)
    ap.add_argument("--md5-sample", type=int, default=1500000)
    ap.add_argument("--rockyou-count", type=int, default=3000)
    ap.add_argument("--rockyou-samples", type=int, default=3)
    ap.add_argument("--max-load", type=int, default=4000000)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    os.makedirs(args.targets_dir, exist_ok=True)
    os.makedirs(args.wordlists_dir, exist_ok=True)

    linkedin = load_unique(iter_plaintexts_from_zip(args.linkedin_zip, HEX40), args.max_load)
    random.Random(args.seed).shuffle(linkedin)
    half = len(linkedin) // 2
    slice_a, slice_b = linkedin[:half], linkedin[half:]

    sha1_plain = slice_a[:args.sha1_sample]
    n1 = write_hashes(sha1_plain, "sha1", os.path.join(args.targets_dir, "linkedin_sha1.txt"))
    print("linkedin_sha1.txt hashes=%d (SHA1, source=LinkedIn plaintexts)" % n1)

    if args.eharmony and os.path.exists(args.eharmony):
        if args.eharmony.lower().endswith(".zip"):
            ehar = load_unique(iter_plaintexts_from_zip(args.eharmony, HEX32), args.md5_sample)
        else:
            ehar = load_unique(iter_plaintexts_from_text(args.eharmony), args.md5_sample)
        n2 = write_hashes(ehar, "md5", os.path.join(args.targets_dir, "eharmony_md5.txt"))
        print("eharmony_md5.txt hashes=%d (MD5, source=eHarmony)" % n2)
    else:
        md5_plain = slice_b[:args.md5_sample]
        n2 = write_hashes(md5_plain, "md5", os.path.join(args.targets_dir, "md5_target.txt"))
        print("md5_target.txt hashes=%d (MD5, source=disjoint LinkedIn slice; eHarmony unavailable)" % n2)

    made = write_rockyou_samples(args.rockyou, args.wordlists_dir, args.rockyou_count, args.rockyou_samples, args.seed)
    print("rockyou samples: %s" % ", ".join(os.path.basename(m) for m in made))
    print("PREPARE_DONE")


if __name__ == "__main__":
    main()
