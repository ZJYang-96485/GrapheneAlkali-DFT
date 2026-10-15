#!/usr/bin/env python3
"""Run one monitored neutral-atom reference pilot and stop."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from parse_qe_output import parse_output
from run_li_pristine_hollow_overnight import (
    atomic_status,
    md5,
    peak_gpu_fraction,
    sha256,
    start_monitors,
    stop_monitors,
    utc_now,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20260923a_box18"
STEM = f"li_atom_{RUN_ID}"
STAGE = "isolated_li_box18_pilot_only"
INPUT = ROOT / f"qe_inputs/references/isolated_atoms/{STEM}.in"
MANIFEST = ROOT / f"qe_inputs/references/isolated_atoms/{STEM}_manifest.json"
DIAG = ROOT / "results/phase5/diagnostics" / STEM
STATUS = DIAG / "status.json"
OUTPUT = ROOT / "results/references/isolated_atoms" / f"{STEM}.out"
SCRATCH = ROOT / "qe_scratch/references" / STEM
QE = Path.home() / "q-e/bin/pw.x"
PYTHON = ROOT / ".venv/bin/python"
QE_SHA256 = "922fe8820f328e7b63283b9f245dfe2b526fe1be0543a89bcca1f1ef04336fb6"
ELEMENT = "Li"
PSEUDOPOTENTIAL = "li_pbe_v1.4.uspp.F.UPF"
PSEUDOPOTENTIAL_MD5 = "e912e257baa3777c20ea3d68f190483c"
FORBIDDEN_PSEUDOPOTENTIAL_TOKENS = ("C.pbe", "na_pbe")
EXPECTED_MAGNETIZATION = 1.0
WALL_EXIT_SECONDS = 3600
HIGH_VRAM_STOP_FRACTION = 0.80


def latest_gpu_fraction(path):
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]):
        fields = line.split(",")
        if len(fields) >= 3:
            try:
                return float(fields[1]) / float(fields[2])
            except ValueError:
                pass
    return None


def new_make_resident_errors(before_path, after_path):
    before = set(before_path.read_text(encoding="utf-8", errors="replace").splitlines())
    after = after_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line for line in after if line not in before and "dxgkio_make_resident" in line]


def preflight():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if sha256(INPUT) != manifest["input_sha256"]:
        raise RuntimeError("Input provenance hash mismatch")
    if sha256(QE) != QE_SHA256:
        raise RuntimeError("CUDA-enabled pw.x hash mismatch")
    if md5(ROOT / "pseudopotentials" / PSEUDOPOTENTIAL) != PSEUDOPOTENTIAL_MD5:
        raise RuntimeError(f"{ELEMENT} UPF hash mismatch")
    if not PYTHON.is_file():
        raise RuntimeError("Project Python is missing")
    text = INPUT.read_text(encoding="utf-8")
    required = (
        "calculation = 'scf'",
        "tot_charge = 0.0",
        "input_dft = 'PBE'",
        "vdw_corr = 'dft-d3'",
        "dftd3_version = 4",
        "assume_isolated = 'mt'",
        "ecutwfc = 65",
        "ecutrho = 520",
        "nspin = 2",
        "tot_magnetization = 1.0",
        "occupations = 'fixed'",
        "conv_thr = 1.0d-8",
        "mixing_beta = 0.3",
        "diagonalization = 'cg'",
        PSEUDOPOTENTIAL,
        "K_POINTS gamma",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError("Input audit failed; missing: " + ", ".join(missing))
    forbidden = (
        "occupations = 'smearing'",
        "starting_magnetization",
        *FORBIDDEN_PSEUDOPOTENTIAL_TOKENS,
    )
    present = [token for token in forbidden if token in text]
    if present:
        raise RuntimeError("Input audit failed; forbidden: " + ", ".join(present))
    if DIAG.exists() or SCRATCH.exists() or OUTPUT.exists():
        raise RuntimeError("Fresh diagnostics, scratch, or output path already exists")
    if subprocess.run(["pgrep", "-x", "pw.x"], capture_output=True).returncode == 0:
        raise RuntimeError("Another pw.x process is running")
    audit = subprocess.run(
        [
            str(PYTHON),
            str(ROOT / "scripts/check_pseudopotentials.py"),
            "--require",
            ELEMENT,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if audit.returncode:
        raise RuntimeError("Pseudopotential audit failed: " + audit.stdout + audit.stderr)
    gpu = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
    )
    if gpu.returncode:
        raise RuntimeError("GPU unavailable: " + gpu.stderr)
    used, total, _ = (float(field.strip()) for field in gpu.stdout.splitlines()[0].split(","))
    if used / total >= 0.30:
        raise RuntimeError("GPU baseline memory usage exceeds 30%")
    return manifest, audit.stdout + "\nGPU memory used,total,utilization: " + gpu.stdout


def worker():
    manifest, snapshot = preflight()
    DIAG.mkdir(parents=True, exist_ok=False)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    status = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "state": "preflight",
        "stage": STAGE,
        "worker_pid": os.getpid(),
        "input": str(INPUT.relative_to(ROOT)),
        "input_sha256": manifest["input_sha256"],
        "output": str(OUTPUT.relative_to(ROOT)),
        "next_stage_launched": False,
    }
    atomic_status(STATUS, status)
    before_dmesg = DIAG / "dmesg_before.txt"
    after_dmesg = DIAG / "dmesg_after.txt"
    try:
        for command in (
            ["date", "-u"],
            ["uname", "-r"],
            ["free", "-h"],
            ["swapon", "--show"],
            ["df", "-h", str(ROOT)],
        ):
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            snapshot += "\n$ " + " ".join(command) + "\n" + proc.stdout + proc.stderr
        (DIAG / "preflight.txt").write_text(snapshot, encoding="utf-8")
        with before_dmesg.open("w", encoding="utf-8") as handle:
            subprocess.run(["dmesg", "-T"], cwd=ROOT, stdout=handle, stderr=subprocess.DEVNULL)
        SCRATCH.mkdir(parents=True, exist_ok=False)
        monitors = start_monitors(DIAG, "reference")
        environment = os.environ.copy()
        environment.update({"CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "4"})
        started = time.monotonic()
        status.update({"state": "running", "started_utc": utc_now()})
        atomic_status(STATUS, status)
        try:
            with OUTPUT.open("x", encoding="utf-8", buffering=1) as handle:
                runner = subprocess.Popen(
                    [
                        "/usr/bin/time",
                        "-v",
                        "-o",
                        str(DIAG / "time_v.log"),
                        str(QE),
                        "-in",
                        str(INPUT),
                    ],
                    cwd=ROOT,
                    env=environment,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                )
                status["runner_pid"] = runner.pid
                atomic_status(STATUS, status)
                high_vram_checks = 0
                while runner.poll() is None:
                    time.sleep(5)
                    status["elapsed_wall_seconds"] = round(time.monotonic() - started)
                    try:
                        partial = parse_output(OUTPUT, allow_incomplete=True, calculation="scf")
                        status["progress"] = {
                            key: partial.get(key)
                            for key in (
                                "gpu_acceleration_active",
                                "electronic_converged_cycles",
                                "electronic_failed_cycles",
                                "scf_iterations",
                                "final_total_energy_ry",
                                "total_magnetization_bohr_magneton_per_cell",
                                "job_completed",
                            )
                        }
                    except Exception as exc:
                        status["progress_error"] = str(exc)
                    fraction = latest_gpu_fraction(DIAG / "reference_gpu.log")
                    status["last_gpu_memory_fraction"] = fraction
                    high_vram_checks = (
                        high_vram_checks + 1
                        if fraction is not None and fraction >= HIGH_VRAM_STOP_FRACTION
                        else 0
                    )
                    reason = None
                    if time.monotonic() - started >= WALL_EXIT_SECONDS:
                        reason = "one-hour pilot wall limit"
                    elif high_vram_checks >= 3:
                        reason = "GPU memory at or above 80% in three checks"
                    if reason and not status.get("clean_stop_requested_utc"):
                        (SCRATCH / f"{STEM}.EXIT").touch(exist_ok=False)
                        status.update(
                            {
                                "state": "clean_stop_requested",
                                "clean_stop_reason": reason,
                                "clean_stop_requested_utc": utc_now(),
                            }
                        )
                    atomic_status(STATUS, status)
                status["runner_exit_code"] = runner.wait()
        finally:
            stop_monitors(*monitors)
        with after_dmesg.open("w", encoding="utf-8") as handle:
            subprocess.run(["dmesg", "-T"], cwd=ROOT, stdout=handle, stderr=subprocess.DEVNULL)
        status["peak_gpu_fraction"] = peak_gpu_fraction(DIAG / "reference_gpu.log")
        status["output_sha256"] = sha256(OUTPUT)
        status["new_dxg_make_resident_errors"] = new_make_resident_errors(
            before_dmesg, after_dmesg
        )
        if status["runner_exit_code"] != 0:
            raise RuntimeError(f"QE exit code {status['runner_exit_code']}")
        result = parse_output(OUTPUT, calculation="scf")
        status["strict_result"] = {
            key: result.get(key)
            for key in (
                "job_completed",
                "gpu_acceleration_active",
                "all_electronic_cycles_converged",
                "electronic_converged_cycles",
                "electronic_failed_cycles",
                "scf_iterations",
                "final_total_energy_ry",
                "total_magnetization_bohr_magneton_per_cell",
                "absolute_magnetization_bohr_magneton_per_cell",
                "wall_time_seconds",
            )
        }
        if (
            abs(
                result["total_magnetization_bohr_magneton_per_cell"]
                - EXPECTED_MAGNETIZATION
            )
            > 1.0e-6
        ):
            raise RuntimeError(
                f"Neutral-{ELEMENT} total magnetization is not "
                f"{EXPECTED_MAGNETIZATION} Bohr magneton"
            )
        status["state"] = "pilot_complete_host_review_pending"
    except Exception as exc:
        status.update({"state": "error", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        atomic_status(STATUS, status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--daemon", action="store_true")
    group.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        _, snapshot = preflight()
        print(snapshot)
    elif args.daemon:
        preflight()
        launcher = DIAG.parent / f"{STEM}_launcher.log"
        if launcher.exists():
            parser.error("Launcher log already exists; refusing duplicate launch")
        with launcher.open("x", encoding="utf-8") as log:
            child = subprocess.Popen(
                [str(PYTHON), str(Path(sys.argv[0]).resolve()), "--worker"],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print(f"Detached pilot worker PID {child.pid}; status {STATUS.relative_to(ROOT)}")
    else:
        worker()


if __name__ == "__main__":
    main()
