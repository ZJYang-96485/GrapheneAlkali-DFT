#!/usr/bin/env python3
"""Run one gated Li/C50 GPU pilot followed by one monitored relaxation."""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from parse_qe_output import parse_output


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
QE_BIN = Path.home() / "q-e/bin/pw.x"
LI_MD5 = "e912e257baa3777c20ea3d68f190483c"


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def md5(path):
    result = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_status(path, value):
    value["updated_utc"] = utc_now()
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def diagnostics(run_id):
    return ROOT / "results/phase5/diagnostics" / f"li_c50_hollow_{run_id}"


def paths(run_id):
    stem = f"li_c50_hollow_{run_id}"
    inputs = ROOT / "qe_inputs/adsorption/li_pristine_hollow"
    results = ROOT / "results/adsorption/li_pristine_hollow"
    structures = ROOT / "structures/adsorption/li_pristine_hollow"
    return {
        "stem": stem,
        "manifest": inputs / f"{stem}_manifest.json",
        "pilot_input": inputs / f"{stem}_pilot.in",
        "relax_input": inputs / f"{stem}_relax.in",
        "pilot_output": diagnostics(run_id) / f"{stem}_pilot.out",
        "relax_output": results / f"{stem}_relax.out",
        "start_structure": structures / f"{stem}_start.traj",
        "relaxed_stem": structures / f"{stem}_relaxed",
        "analysis": results / f"{stem}_analysis.json",
        "status": diagnostics(run_id) / "status.json",
    }


def preflight(items):
    if not PYTHON.is_file() or not QE_BIN.is_file():
        raise RuntimeError("Project Python environment or CUDA QE executable is missing")
    manifest = json.loads(items["manifest"].read_text(encoding="utf-8"))
    for key in ("pilot_input", "relax_input", "starting_structure"):
        path = items["start_structure"] if key == "starting_structure" else items[key]
        if sha256(path) != manifest[f"{key}_sha256"]:
            raise RuntimeError(f"Prepared {key} changed since its manifest was written")
    li_upf = ROOT / "pseudopotentials/li_pbe_v1.4.uspp.F.UPF"
    if md5(li_upf) != LI_MD5:
        raise RuntimeError("Li UPF MD5 mismatch")
    if items["pilot_output"].exists() or items["relax_output"].exists():
        raise RuntimeError("An output already exists; refusing to overwrite it")
    for stage in ("pilot", "relax"):
        scratch = ROOT / "qe_scratch/adsorption" / f"{items['stem']}_{stage}"
        if scratch.exists() and any(scratch.iterdir()):
            raise RuntimeError(f"Nonempty scratch already exists: {scratch}")
    running = subprocess.run(["pgrep", "-x", "pw.x"], capture_output=True, text=True)
    if running.returncode == 0:
        raise RuntimeError(f"Another pw.x process is already running: {running.stdout.strip()}")
    checked = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts/check_pseudopotentials.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    if checked.returncode:
        raise RuntimeError("Carbon UPF audit failed: " + checked.stdout + checked.stderr)
    gpu = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    if gpu.returncode:
        raise RuntimeError("nvidia-smi is unavailable: " + gpu.stderr)
    return checked.stdout + "\n" + gpu.stdout


def process_logger(stop_event, destination):
    with destination.open("w", encoding="utf-8", buffering=1) as log:
        while not stop_event.is_set():
            log.write(f"\nUTC {utc_now()}\n")
            result = subprocess.run(
                ["ps", "-eo", "pid,ppid,rss,vsz,%cpu,%mem,stat,comm,args", "--sort=-rss"],
                capture_output=True, text=True,
            )
            log.write("\n".join(result.stdout.splitlines()[:15]) + "\n")
            stop_event.wait(1.0)


def start_monitors(folder, stage):
    monitors = []
    files = []
    for name, command in (
        ("vmstat", ["stdbuf", "-oL", "vmstat", "-t", "1"]),
        (
            "gpu",
            ["nvidia-smi", "--query-gpu=timestamp,memory.used,memory.total,utilization.gpu,power.draw",
             "--format=csv,noheader,nounits", "-l", "1"],
        ),
    ):
        handle = (folder / f"{stage}_{name}.log").open("w", encoding="utf-8")
        files.append(handle)
        monitors.append(subprocess.Popen(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT))
    stop_event = threading.Event()
    thread = threading.Thread(
        target=process_logger, args=(stop_event, folder / f"{stage}_processes.log"), daemon=True
    )
    thread.start()
    return monitors, files, stop_event, thread


def stop_monitors(monitors, files, stop_event, thread):
    stop_event.set()
    thread.join(timeout=3)
    for process in monitors:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for handle in files:
        handle.close()


def peak_gpu_fraction(log_path):
    peak = 0.0
    with log_path.open(encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) < 3:
                continue
            try:
                used = float(row[1].strip())
                total = float(row[2].strip())
            except ValueError:
                continue
            peak = max(peak, used / total)
    return peak


def stage_run(items, folder, status, stage):
    input_path = items[f"{stage}_input"]
    output_path = items[f"{stage}_output"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    status.update({"state": "running", "stage": stage, "stage_started_utc": utc_now()})
    atomic_status(items["status"], status)
    monitors, files, stop_event, thread = start_monitors(folder, stage)
    env = os.environ.copy()
    env.update({
        "QE_BIN": str(QE_BIN),
        "PYTHON_BIN": str(PYTHON),
        "QE_GPU_CONFIRMED": "1",
        "CUDA_VISIBLE_DEVICES": "0",
        "OMP_NUM_THREADS": "4",
    })
    command = [
        "/usr/bin/time", "-v", "-o", str(folder / f"{stage}_time_v.log"),
        "bash", str(ROOT / "scripts/run_pw_gpu.sh"), str(input_path), str(output_path),
    ]
    try:
        with (folder / f"{stage}_runner.log").open("w", encoding="utf-8", buffering=1) as log:
            runner = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            status["runner_pid"] = runner.pid
            atomic_status(items["status"], status)
            while runner.poll() is None:
                time.sleep(10)
                if output_path.exists():
                    partial = parse_output(output_path, allow_incomplete=True, calculation="scf" if stage == "pilot" else "relax")
                    status["progress"] = {
                        key: partial[key] for key in (
                            "gpu_acceleration_active", "electronic_converged_cycles",
                            "electronic_failed_cycles", "scf_iterations", "final_total_energy_ry",
                            "ionic_steps", "ionic_convergence_reached", "job_completed",
                        )
                    }
                    atomic_status(items["status"], status)
            status["runner_exit_code"] = runner.wait()
            atomic_status(items["status"], status)
    finally:
        stop_monitors(monitors, files, stop_event, thread)
    if status["runner_exit_code"] != 0:
        raise RuntimeError(f"{stage} runner exited {status['runner_exit_code']}; see raw and runner logs")
    result = parse_output(output_path, calculation="scf" if stage == "pilot" else "relax")
    status[f"{stage}_strict_result"] = {
        key: result[key] for key in (
            "job_completed", "gpu_acceleration_active", "all_electronic_cycles_converged",
            "electronic_converged_cycles", "electronic_failed_cycles", "scf_iterations",
            "ionic_convergence_reached", "ionic_steps", "final_total_energy_ry",
            "final_total_force_ry_bohr", "maximum_force_ry_bohr", "wall_time_seconds",
            "total_magnetization_bohr_magneton_per_cell",
        )
    }
    status[f"{stage}_peak_gpu_fraction"] = peak_gpu_fraction(folder / f"{stage}_gpu.log")
    atomic_status(items["status"], status)
    return result


def worker(run_id):
    items = paths(run_id)
    folder = diagnostics(run_id)
    folder.mkdir(parents=True, exist_ok=True)
    status = {
        "schema_version": 1,
        "run_id": run_id,
        "state": "preflight",
        "stage": None,
        "worker_pid": os.getpid(),
        "pilot_output": str(items["pilot_output"].relative_to(ROOT)),
        "relax_output": str(items["relax_output"].relative_to(ROOT)),
    }
    atomic_status(items["status"], status)
    try:
        snapshot = preflight(items)
        for command in (["date", "-u"], ["uname", "-r"], ["free", "-h"],
                        ["swapon", "--show"], ["df", "-h", str(ROOT)],
                        ["bash", "-c", "ulimit -a"]):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            snapshot += "\n$ " + " ".join(command) + "\n" + result.stdout + result.stderr
        (folder / "preflight.txt").write_text(snapshot, encoding="utf-8")
        stage_run(items, folder, status, "pilot")
        if status["pilot_peak_gpu_fraction"] >= 0.98:
            raise RuntimeError("Pilot peak GPU memory reached at least 98%; stopping before relaxation")
        status.update({"state": "pilot_accepted", "stage": None})
        atomic_status(items["status"], status)
        stage_run(items, folder, status, "relax")
        command = [
            str(PYTHON), str(ROOT / "scripts/save_relaxed_structure.py"),
            str(items["relax_output"]), "--template", str(items["start_structure"]),
            "--output-stem", str(items["relaxed_stem"]),
            "--analysis-json", str(items["analysis"]),
        ]
        saved = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (folder / "postprocess.log").write_text(saved.stdout + saved.stderr, encoding="utf-8")
        if saved.returncode:
            raise RuntimeError("Relaxation passed QE gates but structure postprocessing failed")
        status.update({"state": "accepted", "stage": None, "analysis": str(items["analysis"].relative_to(ROOT))})
    except Exception as exc:
        status.update({"state": "stopped", "error": f"{type(exc).__name__}: {exc}"})
    atomic_status(items["status"], status)
    print(json.dumps({key: status.get(key) for key in ("state", "stage", "error")}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    folder = diagnostics(args.run_id)
    if args.check_only:
        print(preflight(paths(args.run_id)))
        print("Li/C50 launch preflight passed; no calculation was started.")
        return
    if args.daemon:
        if folder.exists() and any(folder.iterdir()):
            parser.error(f"diagnostics already exist; refusing duplicate launch: {folder}")
        folder.mkdir(parents=True)
        with (folder / "launcher.log").open("w", encoding="utf-8") as log:
            child = subprocess.Popen(
                [str(PYTHON), str(Path(__file__).resolve()), args.run_id, "--worker"],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print(f"Detached Li/C50 worker PID {child.pid}; status: {folder / 'status.json'}")
        return
    worker(args.run_id)


if __name__ == "__main__":
    main()
