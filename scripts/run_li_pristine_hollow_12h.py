#!/usr/bin/env python3
"""Time-boxed Li/C50 relaxation from the last printed BFGS geometry.

This is a new relaxation after an unclean Windows crash, not a QE restart.
It preserves the original input and scratch and requests a clean stop before
the 12-hour wall-time target.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from parse_qe_output import parse_output
from run_li_pristine_hollow_overnight import (
    atomic_status,
    md5,
    sha256,
    start_monitors,
    stop_monitors,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20260919b_12h"
STEM = f"li_c50_hollow_{RUN_ID}"
OLD_STEM = "li_c50_hollow_20260919a"
INPUT_DIR = ROOT / "qe_inputs/adsorption/li_pristine_hollow"
RESULT_DIR = ROOT / "results/adsorption/li_pristine_hollow"
FOLDER = ROOT / "results/phase5/diagnostics" / STEM
OLD_INPUT = INPUT_DIR / f"{OLD_STEM}_relax.in"
OLD_OUTPUT = RESULT_DIR / f"{OLD_STEM}_relax.out"
OLD_MANIFEST = INPUT_DIR / f"{OLD_STEM}_manifest.json"
INPUT = INPUT_DIR / f"{STEM}_relax.in"
OUTPUT = RESULT_DIR / f"{STEM}_relax.out"
MANIFEST = INPUT_DIR / f"{STEM}_manifest.json"
SCRATCH = ROOT / "qe_scratch/adsorption" / f"{STEM}_relax"
STATUS = FOLDER / "status.json"
QE_BIN = Path.home() / "q-e/bin/pw.x"
PYTHON = ROOT / ".venv/bin/python"
LAST_CONVERGED_ENERGY_RY = -936.96656397
LI_MD5 = "e912e257baa3777c20ea3d68f190483c"
MAX_SECONDS_CPU = 36000  # Ten hours; leaves time for QE to stop cleanly.
EXIT_AFTER_WALL_SECONDS = 10.5 * 3600
TARGET_WALL_SECONDS = 12 * 3600


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def prepared_input():
    old_manifest = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    if sha256(OLD_INPUT) != old_manifest["relax_input_sha256"]:
        raise RuntimeError("Original Li/C50 input differs from its manifest")
    raw = OLD_OUTPUT.read_text(encoding="utf-8", errors="replace")
    if "JOB DONE." in raw or "ionic convergence has been achieved" in raw:
        raise RuntimeError("Source relaxation is no longer the expected interrupted run")
    blocks = list(re.finditer(r"^ATOMIC_POSITIONS \(angstrom\)\s*$", raw, re.M))
    if not blocks:
        raise RuntimeError("No printed geometry in the interrupted relaxation")
    last = blocks[-1]
    preceding = raw[:last.start()]
    bfgs_steps = re.findall(r"number of bfgs steps\s*=\s*(\d+)", preceding)
    if not bfgs_steps or int(bfgs_steps[-1]) != 19:
        raise RuntimeError("Last printed geometry is not the expected BFGS step 19")
    if "CASE: energy            _new < energy            _old" not in preceding[-700:]:
        raise RuntimeError("Last BFGS step lacks the expected accepted-energy marker")
    positions = raw[last.end():].splitlines()
    positions = [line.strip() for line in positions if line.strip()][:51]
    if len(positions) != 51 or [line.split()[0] for line in positions].count("C") != 50:
        raise RuntimeError("Printed geometry is not C50+Li")
    if positions[-1].split()[0] != "Li" or any(len(line.split()) != 4 for line in positions):
        raise RuntimeError("Printed geometry is malformed")

    original = OLD_INPUT.read_text(encoding="utf-8")
    old_positions = original.split("ATOMIC_POSITIONS angstrom\n", 1)
    if len(old_positions) != 2 or "\nK_POINTS automatic" not in old_positions[1]:
        raise RuntimeError("Original input cards are not in the expected layout")
    before, after = old_positions
    after = after.split("\nK_POINTS automatic", 1)[1]
    before, n = re.subn(
        rf"prefix\s*=\s*'{OLD_STEM}_relax'",
        f"prefix = '{STEM}_relax'", before,
    )
    if n != 1:
        raise RuntimeError("Could not isolate original prefix")
    before, n = re.subn(
        rf"outdir\s*=\s*'\./qe_scratch/adsorption/{OLD_STEM}_relax'",
        f"outdir = './qe_scratch/adsorption/{STEM}_relax'", before,
    )
    if n != 1:
        raise RuntimeError("Could not isolate original scratch directory")
    before = before.replace(
        "   forc_conv_thr = 4.0d-4,\n",
        f"   forc_conv_thr = 4.0d-4,\n   max_seconds = {MAX_SECONDS_CPU},\n",
        1,
    )
    if f"max_seconds = {MAX_SECONDS_CPU}" not in before:
        raise RuntimeError("Could not add the clean-stop CPU time limit")
    note = (
        f"! Fresh relaxation from accepted BFGS step 19 of {OLD_STEM}; "
        "crash-interrupted QE scratch is not reused.\n"
    )
    result = note + before + "ATOMIC_POSITIONS angstrom\n"
    result += "\n".join(positions) + "\n\nK_POINTS automatic" + after
    return result, positions


def prepare():
    if INPUT.exists() or MANIFEST.exists():
        raise RuntimeError("Continuation input/manifest already exists; refusing overwrite")
    content, positions = prepared_input()
    INPUT.write_text(content, encoding="utf-8")
    manifest = {
        "run_id": RUN_ID,
        "type": "fresh relaxation from last BFGS geometry after unclean host crash",
        "source_input": str(OLD_INPUT.relative_to(ROOT)),
        "source_input_sha256": sha256(OLD_INPUT),
        "source_output": str(OLD_OUTPUT.relative_to(ROOT)),
        "source_output_sha256": sha256(OLD_OUTPUT),
        "source_bfgs_step": 19,
        "source_last_electronic_energy_ry": LAST_CONVERGED_ENERGY_RY,
        "starting_positions": positions,
        "input": str(INPUT.relative_to(ROOT)),
        "input_sha256": sha256(INPUT),
        "reference_list": "docs/codex_prompts/oct16_2026_final_project_scope.md",
        "max_seconds_cpu": MAX_SECONDS_CPU,
        "exit_after_wall_seconds": EXIT_AFTER_WALL_SECONDS,
        "target_wall_seconds": TARGET_WALL_SECONDS,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def preflight():
    if not INPUT.is_file() or not MANIFEST.is_file():
        raise RuntimeError("Run input and manifest have not been prepared")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if sha256(INPUT) != manifest["input_sha256"]:
        raise RuntimeError("Prepared input changed since manifest was written")
    if sha256(OLD_OUTPUT) != manifest["source_output_sha256"]:
        raise RuntimeError("Source output changed since geometry was extracted")
    if not QE_BIN.is_file() or not PYTHON.is_file():
        raise RuntimeError("CUDA-enabled QE or project Python is missing")
    if md5(ROOT / "pseudopotentials/li_pbe_v1.4.uspp.F.UPF") != LI_MD5:
        raise RuntimeError("Li pseudopotential checksum mismatch")
    audit = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts/check_pseudopotentials.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    if audit.returncode:
        raise RuntimeError("Carbon pseudopotential audit failed: " + audit.stdout + audit.stderr)
    if OUTPUT.exists() or (SCRATCH.exists() and any(SCRATCH.iterdir())):
        raise RuntimeError("Output or nonempty scratch exists; refusing overwrite/reuse")
    if subprocess.run(["pgrep", "-x", "pw.x"], capture_output=True).returncode == 0:
        raise RuntimeError("Another pw.x process is running")
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"], capture_output=True, text=True,
    )
    if gpu.returncode:
        raise RuntimeError("WSL cannot see the NVIDIA GPU: " + gpu.stderr)
    used, total, util = [float(x.strip()) for x in gpu.stdout.splitlines()[0].split(",")]
    if used / total >= 0.30 or util >= 30:
        raise RuntimeError("GPU is not idle enough for this near-VRAM-limit run")
    return audit.stdout + "\nGPU baseline: " + gpu.stdout


def gpu_fraction(log_path):
    if not log_path.exists():
        return None
    with log_path.open(encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    for line in reversed(lines[-5:]):
        fields = line.split(",")
        if len(fields) >= 3:
            try:
                return float(fields[1]) / float(fields[2])
            except ValueError:
                pass
    return None


def worker():
    FOLDER.mkdir(parents=True, exist_ok=True)
    status = {
        "run_id": RUN_ID,
        "state": "preflight",
        "worker_pid": os.getpid(),
        "input": str(INPUT.relative_to(ROOT)),
        "output": str(OUTPUT.relative_to(ROOT)),
        "source_bfgs_step": 19,
        "target_wall_hours": 12,
    }
    atomic_status(STATUS, status)
    monitors = None
    try:
        snapshot = preflight()
        for command in (["date", "-u"], ["uname", "-r"], ["free", "-h"],
                        ["swapon", "--show"], ["df", "-h", str(ROOT)]):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            snapshot += "\n$ " + " ".join(command) + "\n" + result.stdout + result.stderr
        (FOLDER / "preflight.txt").write_text(snapshot, encoding="utf-8")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        monitors = start_monitors(FOLDER, "relax")
        env = os.environ.copy()
        env.update({"CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "4"})
        status.update({
            "state": "running",
            "started_utc": utc_now(),
            "target_end_utc": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
        })
        atomic_status(STATUS, status)
        started = time.monotonic()
        with OUTPUT.open("x", encoding="utf-8", buffering=1) as out:
            runner = subprocess.Popen(
                ["/usr/bin/time", "-v", "-o", str(FOLDER / "relax_time_v.log"),
                 str(QE_BIN), "-in", str(INPUT)],
                cwd=ROOT, env=env, stdout=out, stderr=subprocess.STDOUT,
            )
            status["runner_pid"] = runner.pid
            atomic_status(STATUS, status)
            high_vram_checks = 0
            while runner.poll() is None:
                time.sleep(30)
                elapsed = time.monotonic() - started
                status["elapsed_wall_seconds"] = round(elapsed)
                fraction = gpu_fraction(FOLDER / "relax_gpu.log")
                status["last_gpu_memory_fraction"] = fraction
                if fraction is not None and fraction >= 0.98:
                    high_vram_checks += 1
                else:
                    high_vram_checks = 0
                if OUTPUT.exists():
                    partial = parse_output(OUTPUT, allow_incomplete=True, calculation="relax")
                    status["progress"] = {
                        key: partial.get(key) for key in (
                            "gpu_acceleration_active", "electronic_converged_cycles",
                            "electronic_failed_cycles", "ionic_steps", "final_total_energy_ry",
                            "ionic_convergence_reached", "job_completed",
                        )
                    }
                reason = None
                if elapsed >= EXIT_AFTER_WALL_SECONDS:
                    reason = "10.5-hour wall-clock clean-stop request"
                elif high_vram_checks >= 3:
                    reason = "GPU memory at or above 98% in three checks"
                elif elapsed >= 900 and not status.get("progress", {}).get("gpu_acceleration_active"):
                    reason = "GPU acceleration not confirmed within 15 minutes"
                if reason and "clean_stop_requested_utc" not in status:
                    (SCRATCH / f"{STEM}_relax.EXIT").touch(exist_ok=False)
                    status.update({"state": "clean_stop_requested", "clean_stop_reason": reason,
                                   "clean_stop_requested_utc": utc_now()})
                if elapsed >= TARGET_WALL_SECONDS and runner.poll() is None:
                    status["state"] = "clean_stop_overrun"
                atomic_status(STATUS, status)
            status["runner_exit_code"] = runner.wait()
        partial = parse_output(OUTPUT, allow_incomplete=True, calculation="relax")
        status["progress"] = {
            key: partial.get(key) for key in (
                "gpu_acceleration_active", "all_electronic_cycles_converged",
                "electronic_converged_cycles", "electronic_failed_cycles",
                "ionic_steps", "final_total_energy_ry", "final_total_force_ry_bohr",
                "ionic_convergence_reached", "job_completed",
            )
        }
        if status["runner_exit_code"] == 0 and partial["job_completed"] and partial["ionic_convergence_reached"]:
            strict = parse_output(OUTPUT, calculation="relax")
            status["strict_result"] = strict
            original = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
            saved = subprocess.run(
                [str(PYTHON), str(ROOT / "scripts/save_relaxed_structure.py"),
                 str(OUTPUT), "--template", str(ROOT / original["starting_structure"]),
                 "--output-stem", str(ROOT / "structures/adsorption/li_pristine_hollow" / f"{STEM}_relaxed"),
                 "--analysis-json", str(RESULT_DIR / f"{STEM}_analysis.json")],
                cwd=ROOT, capture_output=True, text=True,
            )
            (FOLDER / "postprocess.log").write_text(saved.stdout + saved.stderr, encoding="utf-8")
            if saved.returncode:
                raise RuntimeError("QE converged but final structure postprocessing failed")
            status["state"] = "accepted"
        elif status["runner_exit_code"] == 0 and partial["job_completed"]:
            status["state"] = "stopped_unconverged"
            status["scratch_preserved"] = True
        else:
            status["state"] = "incomplete"
            status["scratch_preserved"] = True
    except Exception as exc:
        status.update({"state": "error", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        if monitors is not None:
            stop_monitors(*monitors)
        atomic_status(STATUS, status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-only", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--daemon", action="store_true")
    group.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
        print(f"Prepared {INPUT}")
    elif args.check_only:
        print(preflight())
        print("Time-boxed Li/C50 preflight passed; no calculation started.")
    elif args.daemon:
        preflight()
        if FOLDER.exists() and any(FOLDER.iterdir()):
            parser.error("Diagnostics already exist; refusing duplicate launch")
        FOLDER.mkdir(parents=True, exist_ok=True)
        with (FOLDER / "launcher.log").open("w", encoding="utf-8") as log:
            child = subprocess.Popen(
                [str(PYTHON), str(Path(__file__).resolve()), "--worker"],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print(f"Detached Li/C50 12-hour worker PID {child.pid}; status: {STATUS}")
    else:
        worker()


if __name__ == "__main__":
    main()
