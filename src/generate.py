import argparse
import csv
import json
import os
import subprocess
import threading
import time
import urllib.request

from adherence import parse_candidates, count_nonconforming

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_prompt(cfg, name, count):
    rel = cfg["prompt_files"][name]
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read().replace("{count}", str(count))


def server_env(server_path):
    env = dict(os.environ)
    d = os.path.dirname(os.path.abspath(server_path))
    if os.name == "nt":
        env["PATH"] = d + os.pathsep + env.get("PATH", "")
    else:
        env["LD_LIBRARY_PATH"] = d + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    return env


def wait_health(host, port, timeout=300):
    url = "http://%s:%d/health" % (host, port)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if json.loads(r.read().decode()).get("status") == "ok":
                    return True
        except Exception:
            time.sleep(2)
    return False


def start_server(server_path, model_path, host, port, ctx, ngl, log_path):
    args = [server_path, "-m", model_path, "--host", host, "--port", str(port),
            "-c", str(ctx), "-ngl", str(ngl), "--no-webui"]
    logf = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(args, stdout=logf, stderr=subprocess.STDOUT, env=server_env(server_path))
    return proc, logf


def stop_server(proc, logf):
    try:
        proc.terminate()
        proc.wait(timeout=20)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        logf.close()
    except Exception:
        pass


def chat_once(host, port, prompt, temperature, top_p, n_predict, retries=3):
    url = "http://%s:%d/v1/chat/completions" % (host, port)
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": n_predict,
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                obj = json.loads(r.read().decode())
            content = obj["choices"][0]["message"]["content"]
            toks = obj.get("usage", {}).get("completion_tokens", 0)
            return content, toks
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def generate_wordlist(host, port, prompt, temperature, top_p, count, n_predict, parallel, max_rounds, stall_limit, out_path):
    seen = set()
    ordered = []
    calls = 0
    tokens = 0
    stalls = 0
    rounds = 0
    t0 = time.time()
    while len(ordered) < count and rounds < max_rounds:
        rounds += 1
        results = [("", 0)] * parallel

        def work(i):
            try:
                results[i] = chat_once(host, port, prompt, temperature, top_p, n_predict)
            except Exception:
                results[i] = ("", 0)

        threads = [threading.Thread(target=work, args=(i,)) for i in range(parallel)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        added = 0
        for content, toks in results:
            calls += 1
            tokens += toks
            for cand in parse_candidates(content):
                if cand not in seen:
                    seen.add(cand)
                    ordered.append(cand)
                    added += 1
                    if len(ordered) >= count:
                        break
            if len(ordered) >= count:
                break
        if added == 0:
            stalls += 1
            if stalls >= stall_limit:
                break
        else:
            stalls = 0
    elapsed = time.time() - t0
    ordered = ordered[:count]
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(ordered) + "\n")
    return {
        "unique": len(ordered),
        "calls": calls,
        "gen_seconds": round(elapsed, 2),
        "tokens": tokens,
        "tok_per_s": round(tokens / elapsed, 2) if elapsed > 0 else 0,
        "nonconforming": count_nonconforming(ordered),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "experiment.json"))
    ap.add_argument("--tier", required=True)
    ap.add_argument("--llama-server", required=True)
    ap.add_argument("--models-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--ngl", type=int, default=99)
    ap.add_argument("--calibrate", action="store_true")
    args = ap.parse_args()

    cfg = load_json(args.config)
    tier = cfg["tiers"][args.tier]
    host, port = tier["host"], tier["port"]
    parallel = cfg.get("parallel", 4)
    max_rounds = cfg.get("max_rounds", 8)
    stall_limit = cfg.get("stall_limit", 3)
    temp, top_p, count = cfg["temperature"], cfg["top_p"], cfg["count"]
    os.makedirs(args.out_dir, exist_ok=True)
    logs_dir = os.path.join(args.out_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    metrics_path = os.path.join(args.out_dir, "gen_metrics.csv")
    new_file = not os.path.exists(metrics_path)
    mf = open(metrics_path, "a", newline="", encoding="utf-8")
    writer = csv.writer(mf)
    if new_file:
        writer.writerow(["tier", "model", "prompt", "unique", "calls", "gen_seconds", "tokens", "tok_per_s", "nonconforming"])
        mf.flush()

    for model in tier["models"]:
        model_path = os.path.join(args.models_dir, model["file"])
        if not os.path.exists(model_path):
            print("MISSING model %s, skipping" % model_path, flush=True)
            continue
        n_predict = min(cfg["n_predict"], model["ctx"] - 768)
        log_path = os.path.join(logs_dir, "server_%s.log" % model["name"])
        try:
            proc, logf = start_server(args.llama_server, model_path, host, port, model["ctx"], args.ngl, log_path)
        except Exception as e:
            print("server start error for %s: %s" % (model["name"], e), flush=True)
            continue
        if not wait_health(host, port):
            print("server failed for %s (see %s)" % (model["name"], log_path), flush=True)
            stop_server(proc, logf)
            continue
        prompts = model["prompts"][:1] if args.calibrate else model["prompts"]
        for pname in prompts:
            prompt = read_prompt(cfg, pname, count)
            if args.calibrate:
                tc = time.time()
                content, toks = chat_once(host, port, prompt, temp, top_p, 512)
                dt = time.time() - tc
                print("CALIB tier=%s model=%s prompt=%s tokens=%d dt=%.1fs tok_s=%.1f lines=%d" % (
                    args.tier, model["name"], pname, toks, dt, (toks / dt if dt > 0 else 0), len(parse_candidates(content))), flush=True)
                continue
            out_path = os.path.join(args.out_dir, "%s__%s__%s.txt" % (args.tier, model["name"], pname))
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                print("SKIP existing %s" % os.path.basename(out_path), flush=True)
                continue
            try:
                m = generate_wordlist(host, port, prompt, temp, top_p, count, n_predict, parallel, max_rounds, stall_limit, out_path)
            except Exception as e:
                print("WORDLIST FAILED %s: %s" % (os.path.basename(out_path), e), flush=True)
                continue
            writer.writerow([args.tier, model["name"], pname, m["unique"], m["calls"],
                             m["gen_seconds"], m["tokens"], m["tok_per_s"], m["nonconforming"]])
            mf.flush()
            print("WORDLIST %s | unique=%d calls=%d gen_s=%.1f tok/s=%.1f noncompliant=%d" % (
                os.path.basename(out_path), m["unique"], m["calls"], m["gen_seconds"], m["tok_per_s"], m["nonconforming"]), flush=True)
        stop_server(proc, logf)
        if args.calibrate:
            break

    mf.close()
    print("GENERATION_DONE tier=%s" % args.tier, flush=True)


if __name__ == "__main__":
    main()
