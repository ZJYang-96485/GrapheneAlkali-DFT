#!/usr/bin/env python3
"""Run one gated Na/C50 GPU pilot and, only if accepted, one relaxation."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from parse_qe_output import parse_output
from run_li_c49_vacancy_pilot import latest_gpu_fraction, new_make_resident_errors
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
PYTHON = ROOT / ".venv/bin/python"
QE = Path.home() / "q-e/bin/pw.x"
QE_SHA256 = "922fe8820f328e7b63283b9f245dfe2b526fe1be0543a89bcca1f1ef04336fb6"
C_MD5 = "8e281b34a927efac7e739263a90d7aed"
NA_MD5 = "44600605ef58000f06b90626533354dc"
GPU_BASELINE_LIMIT = 0.30
GPU_RUN_LIMIT = 0.90
PILOT_WALL_SECONDS = 3.0 * 3600
RELAX_WALL_SECONDS = 10.5 * 3600


def paths(run_id):
    stem = f"na_c50_hollow_{run_id}"
    inputs = ROOT / "qe_inputs/adsorption/na_pristine_hollow"
    structures = ROOT / "structures/adsorption/na_pristine_hollow"
    results = ROOT / "results/adsorption/na_pristine_hollow"
    diagnostics = ROOT / "results/phase5/diagnostics" / stem
    return {
        "stem": stem,
        "manifest": inputs / f"{stem}_manifest.json",
        "pilot_input": inputs / f"{stem}_pilot.in",
        "relax_input": inputs / f"{stem}_relax.in",
        "start_structure": structures / f"{stem}_start.traj",
        "pilot_output": diagnostics / f"{stem}_pilot.out",
        "relax_output": results / f"{stem}_relax.out",
        "pilot_scratch": ROOT / "qe_scratch/adsorption" / f"{stem}_pilot",
        "relax_scratch": ROOT / "qe_scratch/adsorption" / f"{stem}_relax",
        "relaxed_stem": structures / f"{stem}_relaxed",
        "analysis": results / f"{stem}_analysis.json",
        "diagnostics": diagnostics,
        "status": diagnostics / "status.json",
    }


def preflight(items):
    if not PYTHON.is_file() or not QE.is_file():
        raise RuntimeError("Project Python environment or CUDA-enabled pw.x is missing")
    if sha256(QE) != QE_SHA256:
        raise RuntimeError("CUDA-enabled pw.x hash mismatch")
    manifest = json.loads(items["manifest"].read_text(encoding="utf-8"))
    checks = {
        "source_structure": ROOT / manifest["source_structure"],
        "source_qe_output": ROOT / manifest["source_qe_output"],
        "starting_structure": items["start_structure"],
        "pilot_input": items["pilot_input"],
        "relax_input": items["relax_input"],
    }
    for key, path in checks.items():
        if not path.is_file() or sha256(path) != manifest[f"{key}_sha256"]:
            raise RuntimeError(f"Provenance hash mismatch: {key}")
    if md5(ROOT / "pseudopotentials/C.pbe-n-kjpaw_psl.1.0.0.UPF") != C_MD5:
        raise RuntimeError("Carbon UPF hash mismatch")
    if md5(ROOT / "pseudopotentials/na_pbe_v1.5.uspp.F.UPF") != NA_MD5:
        raise RuntimeError("Sodium UPF hash mismatch")

    source = parse_output(checks["source_qe_output"], calculation="relax")
    if not all(
        source[key] is True
        for key in (
            "job_completed",
            "gpu_acceleration_active",
            "all_electronic_cycles_converged",
            "ionic_convergence_reached",
        )
    ):
        raise RuntimeError("Accepted C50 source failed strict validation")
    if source["final_total_energy_ry"] != -922.52166623:
        raise RuntimeError("Accepted C50 source energy changed")

    if items["diagnostics"].exists() or items["pilot_output"].exists() or items["relax_output"].exists():
        raise RuntimeError("Fresh diagnostics and output paths are required")
    for scratch in (items["pilot_scratch"], items["relax_scratch"]):
        if scratch.exists():
            raise RuntimeError(f"Fresh scratch path is required: {scratch}")
    running = subprocess.run(["pgrep", "-x", "pw.x"], capture_output=True, text=True)
    if running.returncode == 0:
        raise RuntimeError(f"Another pw.x process is running: {running.stdout.strip()}")

    audit = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts/check_pseudopotentials.py"), "--require", "C", "Na"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if audit.returncode:
        raise RuntimeError("C/Na pseudopotential audit failed: " + audit.stdout + audit.stderr)
    gpu = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
    )
    if gpu.returncode:
        raise RuntimeError("GPU unavailable: " + gpu.stderr)
    used, total, _, _ = (float(field.strip()) for field in gpu.stdout.splitlines()[0].split(","))
    if used / total >= GPU_BASELINE_LIMIT:
        raise RuntimeError(f"GPU baseline memory usage is {used / total:.1%}, above the 30% gate")
    return manifest, audit.stdout + "\nGPU baseline used,total,utilization,temp: " + gpu.stdout


def system_snapshot():
    text = ""
    for command in (
        ["date", "-u"],
        ["uname", "-r"],
        ["free", "-h"],
        ["swapon", "--show"],
        ["df", "-h", str(ROOT)],
        ["bash", "-c", "ulimit -a"],
    ):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        text += "\n$ " + " ".join(command) + "\n" + result.stdout + result.stderr
    return text


def dmesg_to(path):
    with path.open("w", encoding="utf-8") as handle:
        subprocess.run(["dmesg", "-T"], cwd=ROOT, stdout=handle, stderr=subprocess.DEVNULL)


def stage_result(result):
    keys = (
        "job_completed",
        "gpu_acceleration_active",
        "all_electronic_cycles_converged",
        "electronic_converged_cycles",
        "electronic_failed_cycles",
        "scf_iterations",
        "ionic_convergence_reached",
        "ionic_steps",
        "final_total_energy_ry",
        "final_total_force_ry_bohr",
        "maximum_force_ry_bohr",
        "total_magnetization_bohr_magneton_per_cell",
        "absolute_magnetization_bohr_magneton_per_cell",
        "wall_time_seconds",
    )
    return {key: result.get(key) for key in keys}


def run_stage(items, status, stage):
    folder = items["diagnostics"]
    input_path = items[f"{stage}_input"]
    output_path = items[f"{stage}_output"]
    scratch = items[f"{stage}_scratch"]
    wall_limit = PILOT_WALL_SECONDS if stage == "pilot" else RELAX_WALL_SECONDS
    calculation = "scf" if stage == "pilot" else "relax"
    dmesg_before = folder / f"{stage}_dmesg_before.txt"
    dmesg_after = folder / f"{stage}_dmesg_after.txt"

    scratch.mkdir(parents=True, exist_ok=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dmesg_to(dmesg_before)
    monitors = start_monitors(folder, stage)
    environment = os.environ.copy()
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": "0",
            "OMP_NUM_THREADS": "4",
            "QE_BIN": str(QE),
            "PYTHON_BIN": str(PYTHON),
            "QE_GPU_CONFIRMED": "1",
        }
    )
    started = time.monotonic()
    status.update({"state": "running", "stage": stage, "stage_started_utc": utc_now()})
    atomic_status(items["status"], status)
    try:
        with (folder / f"{stage}_runner.log").open("x", encoding="utf-8", buffering=1) as log:
            runner = subprocess.Popen(
                [
                    "/usr/bin/time",
                    "-v",
                    "-o",
                    str(folder / f"{stage}_time_v.log"),
                    "bash",
                    str(ROOT / "scripts/run_pw_gpu.sh"),
                    str(input_path),
                    str(output_path),
                ],
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            status["runner_pid"] = runner.pid
            atomic_status(items["status"], status)
            high_vram_checks = 0
            while runner.poll() is None:
                time.sleep(15)
                elapsed = time.monotonic() - started
                status["elapsed_wall_seconds"] = round(elapsed)
                try:
                    partial = parse_output(output_path, allow_incomplete=True, calculation=calculation)
                    status["progress"] = {
                        key: partial.get(key)
                        for key in (
                            "gpu_acceleration_active",
                            "electronic_converged_cycles",
                            "electronic_failed_cycles",
                            "scf_iterations",
                            "final_total_energy_ry",
                            "ionic_steps",
                            "ionic_convergence_reached",
                            "job_completed",
                        )
                    }
                    status.pop("progress_error", None)
                except Exception as exc:
                    status["progress_error"] = str(exc)
                fraction = latest_gpu_fraction(folder / f"{stage}_gpu.log")
                status["last_gpu_memory_fraction"] = fraction
                high_vram_checks = (
                    high_vram_checks + 1
                    if fraction is not None and fraction >= GPU_RUN_LIMIT
                    else 0
                )
                reason = None
                if high_vram_checks >= 3:
                    reason = f"GPU memory at or above {GPU_RUN_LIMIT:.0%} in three checks"
                elif elapsed >= wall_limit:
                    reason = f"{wall_limit / 3600:g}-hour wall-clock clean-stop request"
                if reason and not status.get("clean_stop_requested_utc"):
                    (scratch / f"{items['stem']}_{stage}.EXIT").touch(exist_ok=False)
                    status.update(
                        {
                            "state": "clean_stop_requested",
                            "clean_stop_reason": reason,
                            "clean_stop_requested_utc": utc_now(),
                        }
                    )
                atomic_status(items["status"], status)
            status[f"{stage}_runner_exit_code"] = runner.wait()
    finally:
        stop_monitors(*monitors)
        dmesg_to(dmesg_after)

    status[f"{stage}_peak_gpu_fraction"] = peak_gpu_fraction(folder / f"{stage}_gpu.log")
    status[f"{stage}_output_sha256"] = sha256(output_path) if output_path.exists() else None
    status[f"{stage}_new_dxg_make_resident_errors"] = new_make_resident_errors(
        dmesg_before, dmesg_after
    )
    atomic_status(items["status"], status)
    if status[f"{stage}_runner_exit_code"] != 0:
        raise RuntimeError(f"{stage} runner exited {status[f'{stage}_runner_exit_code']}")

    try:
        strict = parse_output(output_path, calculation=calculation)
    except Exception:
        incomplete = parse_output(output_path, allow_incomplete=True, calculation=calculation)
        status[f"{stage}_incomplete_result"] = stage_result(incomplete)
        atomic_status(items["status"], status)
        raise RuntimeError(f"{stage} stopped without all strict completion markers")
    status[f"{stage}_strict_result"] = stage_result(strict)
    atomic_status(items["status"], status)
    return strict


def stage_passed(status, stage, result):
    scientific = (
        result["job_completed"]
        and result["gpu_acceleration_active"]
        and result["all_electronic_cycles_converged"]
        and result["final_total_energy_ry"] is not None
    )
    if stage == "relax":
        scientific = scientific and result["ionic_convergence_reached"] is True
    return (
        scientific
        and status[f"{stage}_peak_gpu_fraction"] < GPU_RUN_LIMIT
        and not status[f"{stage}_new_dxg_make_resident_errors"]
    )


def worker(run_id):
    items = paths(run_id)
    manifest, snapshot = preflight(items)
    items["diagnostics"].mkdir(parents=True, exist_ok=False)
    status = {
        "schema_version": 1,
        "run_id": run_id,
        "state": "preflight",
        "stage": None,
        "worker_pid": os.getpid(),
        "pilot_input": str(items["pilot_input"].relative_to(ROOT)),
        "pilot_input_sha256": manifest["pilot_input_sha256"],
        "pilot_output": str(items["pilot_output"].relative_to(ROOT)),
        "relax_input": str(items["relax_input"].relative_to(ROOT)),
        "relax_input_sha256": manifest["relax_input_sha256"],
        "relax_output": str(items["relax_output"].relative_to(ROOT)),
        "gpu_memory_gate_fraction": GPU_RUN_LIMIT,
        "next_stage_launched": False,
    }
    atomic_status(items["status"], status)
    (items["diagnostics"] / "preflight.txt").write_text(
        snapshot + system_snapshot(), encoding="utf-8"
    )
    try:
        pilot = run_stage(items, status, "pilot")
        if not stage_passed(status, "pilot", pilot):
            status["state"] = "pilot_scientifically_complete_resource_gate_failed"
            if status["pilot_peak_gpu_fraction"] >= GPU_RUN_LIMIT:
                status["gate_failure"] = "pilot GPU-memory peak reached the 90% limit"
            elif status["pilot_new_dxg_make_resident_errors"]:
                status["gate_failure"] = "new WSL GPU-residency error during pilot"
            else:
                status["gate_failure"] = "pilot scientific acceptance markers failed"
            return
        status.update(
            {
                "state": "pilot_accepted_relaxation_launching",
                "stage": None,
                "next_stage_launched": True,
            }
        )
        status.pop("clean_stop_requested_utc", None)
        status.pop("clean_stop_reason", None)
        atomic_status(items["status"], status)

        relax = run_stage(items, status, "relax")
        if not stage_passed(status, "relax", relax):
            status["state"] = "relaxation_complete_acceptance_gate_failed"
            return
        save = subprocess.run(
            [
                str(PYTHON),
                str(ROOT / "scripts/save_relaxed_structure.py"),
                str(items["relax_output"]),
                "--template",
                str(items["start_structure"]),
                "--output-stem",
                str(items["relaxed_stem"]),
                "--analysis-json",
                str(items["analysis"]),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        (items["diagnostics"] / "postprocess.log").write_text(
            save.stdout + save.stderr, encoding="utf-8"
        )
        if save.returncode:
            raise RuntimeError("Relaxation passed QE gates but structure postprocessing failed")
        status.update(
            {
                "state": "accepted",
                "stage": None,
                "analysis": str(items["analysis"].relative_to(ROOT)),
            }
        )
    except Exception as exc:
        clean_stop = status.get("clean_stop_requested_utc") is not None
        status.update(
            {
                "state": "stopped_cleanly_unconverged" if clean_stop else "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    finally:
        atomic_status(items["status"], status)
        print(
            json.dumps(
                {key: status.get(key) for key in ("state", "stage", "gate_failure", "error")},
                indent=2,
            ),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--daemon", action="store_true")
    group.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    items = paths(args.run_id)
    if args.check_only:
        _, snapshot = preflight(items)
        print(snapshot)
        print("Na/C50 launch preflight passed; no calculation was started.")
    elif args.daemon:
        preflight(items)
        launcher = items["diagnostics"].parent / f"{items['stem']}_launcher.log"
        if launcher.exists():
            parser.error("Launcher log already exists; refusing duplicate launch")
        with launcher.open("x", encoding="utf-8") as log:
            child = subprocess.Popen(
                [str(PYTHON), str(Path(sys.argv[0]).resolve()), args.run_id, "--worker"],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        print(f"Detached Na/C50 worker PID {child.pid}; status {items['status'].relative_to(ROOT)}")
    else:
        worker(args.run_id)


if __name__ == "__main__":
    main()
