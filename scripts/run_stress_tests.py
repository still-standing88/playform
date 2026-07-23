"""Supervisor for stress_test_mpv.py -- runs each phase as its own subprocess
(audio against F:\\music\\music collection, video against F:\\videoes) so a
genuine native crash in one phase doesn't take this process down, and reports
a pass/fail summary plus any captured crash info at the end.
"""
import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DUMP_DIR = os.path.join(SCRIPT_DIR, "mpv_stress", "crashes")
PYTHON = sys.executable

AUDIO_ROOT = r"F:\music\music collection"
VIDEO_ROOT = r"F:\videoes"

PLAN = [
    ("load_spam", AUDIO_ROOT, False, 300),
    ("load_spam", VIDEO_ROOT, True, 150),
    ("seek_spam", AUDIO_ROOT, False, 500),
    ("seek_spam", VIDEO_ROOT, True, 300),
    ("toggle_spam", AUDIO_ROOT, False, 400),
    ("toggle_spam", VIDEO_ROOT, True, 300),
    ("concurrent", AUDIO_ROOT, False, 500),   # iterations/50 = ~10s of concurrent hammering
    ("concurrent", VIDEO_ROOT, True, 400),
    ("playlist_cycle", AUDIO_ROOT, False, 40),
    ("playlist_cycle", VIDEO_ROOT, True, 25),
]


def run_one(phase: str, root: str, video: bool, iterations: int) -> dict:
    args = [
        PYTHON, os.path.join(SCRIPT_DIR, "stress_test_mpv.py"),
        "--phase", phase,
        "--root", root,
        "--iterations", str(iterations),
        "--dump-dir", DUMP_DIR,
    ]
    if video:
        args.append("--video")

    label = f"{phase}[{'video' if video else 'audio'}]"
    print(f"--- running {label} (iterations={iterations}) ---", flush=True)
    start = time.time()
    proc = subprocess.run(args, capture_output=True, text=True, timeout=180)
    elapsed = round(time.time() - start, 2)

    entry = {"label": label, "returncode": proc.returncode, "elapsed_s": elapsed}
    if proc.returncode != 0:
        entry["crashed"] = True
        entry["stdout_tail"] = proc.stdout[-2000:]
        entry["stderr_tail"] = proc.stderr[-2000:]
    else:
        for line in proc.stdout.splitlines():
            if line.startswith("RESULT_JSON:"):
                entry["result"] = json.loads(line[len("RESULT_JSON:"):])
        if "result" not in entry:
            entry["crashed"] = True
            entry["note"] = "exit 0 but no RESULT_JSON found"
            entry["stdout_tail"] = proc.stdout[-2000:]
    return entry


def main():
    os.makedirs(DUMP_DIR, exist_ok=True)
    before_dumps = set(os.listdir(DUMP_DIR))

    results = []
    for phase, root, video, iterations in PLAN:
        try:
            results.append(run_one(phase, root, video, iterations))
        except subprocess.TimeoutExpired:
            results.append({"label": f"{phase}[{'video' if video else 'audio'}]", "crashed": True, "note": "TIMEOUT (hang, not exception)"})

    after_dumps = set(os.listdir(DUMP_DIR))
    new_dumps = sorted(after_dumps - before_dumps)

    print("\n\n================ STRESS TEST SUMMARY ================")
    total_ops = 0
    total_errors = 0
    crashes = 0
    for entry in results:
        label = entry["label"]
        if entry.get("crashed"):
            crashes += 1
            print(f"[CRASH] {label}: returncode={entry.get('returncode')} note={entry.get('note', '')}")
            if entry.get("stderr_tail"):
                print("  stderr tail:", entry["stderr_tail"][-500:])
        else:
            r = entry["result"]
            total_ops += r["ops"]
            total_errors += r["errors"]
            print(f"[OK]    {label}: ops={r['ops']} errors={r['errors']} duration={r['duration_s']}s files={r['file_count']}")
            if r["errors"]:
                for exc in r["exceptions"][:5]:
                    print(f"          - {exc}")

    print(f"\nTotal ops: {total_ops}, total tracked errors: {total_errors}, process crashes: {crashes}")
    if new_dumps:
        print(f"\nNew crash artifacts in {DUMP_DIR}:")
        for name in new_dumps:
            print(f"  {name}")
            if name.endswith(".txt"):
                with open(os.path.join(DUMP_DIR, name), encoding="utf-8") as f:
                    for line in f:
                        print("    " + line.rstrip())
    else:
        print("\nNo new crash dump/summary files were written.")

    with open(os.path.join(SCRIPT_DIR, "mpv_stress", "last_run_report.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
