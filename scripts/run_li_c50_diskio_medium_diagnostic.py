#!/usr/bin/env python3
"""Run one monitored, GPU-only Li/C50 disk_io=medium SCF diagnostic."""

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

from parse_qe_output import parse_output
from run_li_pristine_hollow_overnight import (
    atomic_status, md5, peak_gpu_fraction, sha256, start_monitors, stop_monitors, utc_now,
)


ROOT = Path(__file__).resolve().parents[1]
STEM = "li_c50_diskio_medium_20260920b_e65_k4"
MANIFEST = ROOT / "qe_inputs/convergence/li_c50/li_c50_diskio_medium_20260920b_manifest.json"
DIAG = ROOT / "results/phase5/diagnostics/li_c50_diskio_medium_20260920b"
STATUS = DIAG / "status.json"
SCRATCH = ROOT / "qe_scratch/convergence/li_c50" / STEM
QE = Path.home() / "q-e/bin/pw.x"
PYTHON = ROOT / ".venv/bin/python"
WALL_EXIT_SECONDS = 2.5 * 3600


def content_equal_except_disk_io_and_identity(baseline, diagnostic):
    """Assert no physical/numerical field changed besides disk_io."""
    def normalized(value):
        value = re.sub(r"(?m)^\s*!.*\n", "", value)
        value = re.sub(r"(?m)^\s*disk_io\s*=\s*'medium',\s*\n", "", value)
        value = re.sub(r"(?m)^\s*prefix\s*=\s*'[^']+',", "   prefix = '<isolated>',", value)
        value = re.sub(r"(?m)^\s*outdir\s*=\s*'[^']+',", "   outdir = '<isolated>',", value)
        return "\n".join(line.rstrip() for line in value.splitlines() if line.strip())
    return normalized(baseline) == normalized(diagnostic)


def preflight():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for path_key, hash_key in (
        ("baseline_input", "baseline_input_sha256"),
        ("baseline_output", "baseline_output_sha256"),
        ("diagnostic_input", "diagnostic_input_sha256"),
    ):
        path = ROOT / manifest[path_key]
        if sha256(path) != manifest[hash_key]:
            raise RuntimeError(f"Provenance hash mismatch: {path}")
    before = (ROOT / manifest["baseline_input"]).read_text(encoding="utf-8")
    after = (ROOT / manifest["diagnostic_input"]).read_text(encoding="utf-8")
    if not content_equal_except_disk_io_and_identity(before, after):
        raise RuntimeError("Input differs beyond disk_io and isolated identity paths")
    if not re.search(r"(?m)^\s*disk_io\s*=\s*'medium',\s*$", after):
        raise RuntimeError("disk_io=medium is missing")
    for key in ("diagnostic_output",):
        if (ROOT / manifest[key]).exists():
            raise RuntimeError(f"Refusing to overwrite {manifest[key]}")
    if SCRATCH.exists() or DIAG.exists():
        raise RuntimeError("Fresh scratch or diagnostics path already exists")
    if sha256(QE) != manifest["qe_executable_sha256"]:
        raise RuntimeError("CUDA-enabled pw.x hash mismatch")
    if md5(ROOT / "pseudopotentials/C.pbe-n-kjpaw_psl.1.0.0.UPF") != manifest["carbon_upf_md5"]:
        raise RuntimeError("Carbon UPF hash mismatch")
    if md5(ROOT / "pseudopotentials/li_pbe_v1.4.uspp.F.UPF") != manifest["lithium_upf_md5"]:
        raise RuntimeError("Lithium UPF hash mismatch")
    if not PYTHON.is_file():
        raise RuntimeError("Project Python is missing")
    audit = subprocess.run([str(PYTHON), str(ROOT / "scripts/check_pseudopotentials.py")],
                           cwd=ROOT, capture_output=True, text=True)
    if audit.returncode:
        raise RuntimeError("Pseudopotential audit failed: " + audit.stdout + audit.stderr)
    baseline = parse_output(ROOT / manifest["baseline_output"], calculation="scf")
    if (not baseline["job_completed"] or not baseline["gpu_acceleration_active"]
            or not baseline["all_electronic_cycles_converged"]
            or baseline["final_total_energy_ry"] != manifest["baseline_energy_ry"]):
        raise RuntimeError("Baseline QE result failed strict validation")
    running = subprocess.run(["pgrep", "-x", "pw.x"], capture_output=True, text=True)
    if running.returncode == 0:
        raise RuntimeError("Another pw.x is running: " + running.stdout.strip())
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True)
    if gpu.returncode:
        raise RuntimeError("GPU unavailable: " + gpu.stderr)
    used, total, _ = (float(x.strip()) for x in gpu.stdout.splitlines()[0].split(","))
    if used / total >= 0.30:
        raise RuntimeError("GPU baseline memory usage exceeds 30%")
    return manifest, audit.stdout + "\nGPU memory used,total,utilization: " + gpu.stdout


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


def worker():
    manifest, snapshot = preflight()
    DIAG.mkdir(parents=True, exist_ok=False)
    status = {"schema_version": 1, "run_id": "20260920b", "state": "preflight",
              "worker_pid": os.getpid(), "sole_case": STEM,
              "diagnostic_output": manifest["diagnostic_output"]}
    atomic_status(STATUS, status)
    try:
        for command in (["date", "-u"], ["uname", "-r"], ["free", "-h"],
                        ["swapon", "--show"], ["df", "-h", str(ROOT)], ["ulimit", "-a"]):
            if command[0] == "ulimit":
                command = ["bash", "-lc", "ulimit -a"]
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            snapshot += "\n$ " + " ".join(command) + "\n" + proc.stdout + proc.stderr
        (DIAG / "preflight.txt").write_text(snapshot, encoding="utf-8")
        subprocess.run(["dmesg", "-T"], cwd=ROOT, stdout=(DIAG / "dmesg_before.txt").open("w"),
                       stderr=subprocess.DEVNULL)
        SCRATCH.mkdir(parents=True, exist_ok=False)
        output_path = ROOT / manifest["diagnostic_output"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        monitors = start_monitors(DIAG, "scf")
        env = os.environ.copy()
        env.update({"CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "4"})
        started = time.monotonic()
        status.update({"state": "running", "started_utc": utc_now()})
        atomic_status(STATUS, status)
        try:
            with output_path.open("x", encoding="utf-8", buffering=1) as handle:
                runner = subprocess.Popen(["/usr/bin/time", "-v", "-o", str(DIAG / "time_v.log"),
                                           str(QE), "-in", str(ROOT / manifest["diagnostic_input"])],
                                          cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
                status["runner_pid"] = runner.pid
                atomic_status(STATUS, status)
                high_vram_checks = 0
                while runner.poll() is None:
                    time.sleep(15)
                    status["elapsed_wall_seconds"] = round(time.monotonic() - started)
                    try:
                        partial = parse_output(output_path, allow_incomplete=True, calculation="scf")
                        status["progress"] = {key: partial.get(key) for key in (
                            "gpu_acceleration_active", "electronic_converged_cycles",
                            "electronic_failed_cycles", "scf_iterations",
                            "final_total_energy_ry", "job_completed")}
                    except Exception as exc:
                        status["progress_error"] = str(exc)
                    fraction = latest_gpu_fraction(DIAG / "scf_gpu.log")
                    status["last_gpu_memory_fraction"] = fraction
                    high_vram_checks = high_vram_checks + 1 if fraction is not None and fraction >= 0.98 else 0
                    reason = None
                    if time.monotonic() - started >= WALL_EXIT_SECONDS:
                        reason = "2.5-hour diagnostic wall limit"
                    elif high_vram_checks >= 3:
                        reason = "GPU memory at or above 98% in three checks"
                    if reason and not status.get("clean_stop_requested_utc"):
                        (SCRATCH / f"{STEM}.EXIT").touch(exist_ok=False)
                        status.update({"state": "clean_stop_requested", "clean_stop_reason": reason,
                                       "clean_stop_requested_utc": utc_now()})
                    atomic_status(STATUS, status)
                status["runner_exit_code"] = runner.wait()
        finally:
            stop_monitors(*monitors)
        subprocess.run(["dmesg", "-T"], cwd=ROOT, stdout=(DIAG / "dmesg_after.txt").open("w"),
                       stderr=subprocess.DEVNULL)
        status["peak_gpu_fraction"] = peak_gpu_fraction(DIAG / "scf_gpu.log")
        status["peak_gpu_mib"] = round(status["peak_gpu_fraction"] * manifest["gpu_total_mib"])
        status["output_sha256"] = sha256(output_path)
        if status["runner_exit_code"] != 0:
            raise RuntimeError(f"QE exit code {status['runner_exit_code']}")
        result = parse_output(output_path, calculation="scf")
        status["strict_result"] = {key: result.get(key) for key in (
            "job_completed", "gpu_acceleration_active", "all_electronic_cycles_converged",
            "electronic_converged_cycles", "electronic_failed_cycles", "scf_iterations",
            "final_total_energy_ry", "wall_time_seconds")}
        delta = result["final_total_energy_ry"] - manifest["baseline_energy_ry"]
        status["delta_energy_ry"] = delta
        status["delta_energy_mev_per_carbon"] = delta * 13605.693122994 / 50
        status["baseline_peak_gpu_mib"] = manifest["baseline_peak_gpu_mib"]
        status["peak_gpu_reduction_mib"] = manifest["baseline_peak_gpu_mib"] - status["peak_gpu_mib"]
        status["state"] = "diagnostic_complete"
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
        launcher = DIAG.parent / "li_c50_diskio_medium_20260920b_launcher.log"
        with launcher.open("x", encoding="utf-8") as log:
            child = subprocess.Popen([str(PYTHON), str(Path(__file__).resolve()), "--worker"],
                                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
        print(f"Detached single-case GPU diagnostic PID {child.pid}; status {STATUS.relative_to(ROOT)}")
    else:
        worker()


if __name__ == "__main__":
    main()
