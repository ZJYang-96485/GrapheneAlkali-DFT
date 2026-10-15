#!/usr/bin/env python3
"""Gated, monitored fixed-geometry Li/C50 cutoff checks on a 4x4x1 mesh.

These checks do not establish cutoff convergence on the production 6x6x1 mesh.
"""

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from parse_qe_output import parse_output
from run_li_pristine_hollow_overnight import (
    atomic_status, md5, peak_gpu_fraction, sha256, start_monitors, stop_monitors,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20260920a"
STEM = f"li_c50_fixed_validation_{RUN_ID}"
SOURCE_INPUT = ROOT / "qe_inputs/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_relax.in"
SOURCE_OUTPUT = ROOT / "results/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_relax.out"
SOURCE_ANALYSIS = ROOT / "results/adsorption/li_pristine_hollow/li_c50_hollow_20260919b_12h_analysis.json"
INPUT_DIR = ROOT / "qe_inputs/convergence/li_c50"
OUTPUT_DIR = ROOT / "results/convergence/li_c50"
DIAG = ROOT / "results/phase5/diagnostics" / STEM
STATUS = DIAG / "status.json"
MANIFEST = INPUT_DIR / f"{STEM}_manifest.json"
QE = Path.home() / "q-e/bin/pw.x"
PYTHON = ROOT / ".venv/bin/python"
CASES = (("e65_k4", 65, 520), ("e70_k4", 70, 560))
LI_MD5 = "e912e257baa3777c20ea3d68f190483c"
WALL_EXIT_SECONDS = 10.5 * 3600
SECOND_START_LATEST = 6 * 3600
SECOND_PEAK_VRAM_CEILING = 0.88


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def paths(case):
    name = f"{STEM}_{case}"
    return (
        INPUT_DIR / f"{name}.in",
        OUTPUT_DIR / f"{name}.out",
        ROOT / "qe_scratch/convergence/li_c50" / name,
        name,
    )


def replace_once(text, pattern, replacement):
    changed, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise RuntimeError(f"Expected exactly one input field matching {pattern!r}")
    return changed


def source_data():
    analysis = json.loads(SOURCE_ANALYSIS.read_text(encoding="utf-8"))
    if sha256(SOURCE_OUTPUT) != analysis["qe_output_sha256"]:
        raise RuntimeError("Accepted relaxation output differs from its analysis hash")
    result = parse_output(SOURCE_OUTPUT, calculation="relax")
    if not result["ionic_convergence_reached"] or result["final_total_energy_ry"] != -936.96660595:
        raise RuntimeError("Source relaxation is not the accepted converged calculation")
    atoms = analysis["qe_result"]["final_coordinates"]
    if len(atoms) != 51 or sum(a["symbol"] == "C" for a in atoms) != 50 or atoms[-1]["symbol"] != "Li":
        raise RuntimeError("Source final coordinates are not C50+Li")
    if any(a["units"] != "angstrom" for a in atoms):
        raise RuntimeError("Unexpected coordinate units")
    return atoms


def make_input(case, ecutwfc, ecutrho, atoms):
    original = SOURCE_INPUT.read_text(encoding="utf-8")
    before, card = original.split("ATOMIC_POSITIONS angstrom\n", 1)
    _, tail = card.split("\nK_POINTS automatic\n", 1)
    if not re.fullmatch(r"\s*6 6 1 0 0 0\s*", tail):
        raise RuntimeError("Source k-point card changed")
    _, _, scratch, name = paths(case)
    before = replace_once(before, r"^\s*calculation = 'relax',", "   calculation = 'scf',")
    before = replace_once(before, r"^\s*prefix = '[^']+',", f"   prefix = '{name}',")
    before = replace_once(before, r"^\s*outdir = '[^']+',", f"   outdir = './{scratch.relative_to(ROOT).as_posix()}',")
    before = replace_once(before, r"^\s*ecutwfc = 65,", f"   ecutwfc = {ecutwfc},")
    before = replace_once(before, r"^\s*ecutrho = 520,", f"   ecutrho = {ecutrho},")
    before = replace_once(before, r"^\s*max_seconds = 36000,", "   max_seconds = 36000,")
    before = replace_once(before, r"^\s*forc_conv_thr = 4.0d-4,\n", "\n")
    before = replace_once(before, r"^&IONS\n\s*ion_dynamics = 'bfgs',\n/\n", "")
    coordinates = "\n".join(
        f"{atom['symbol']:2s} {atom['x']:18.10f} {atom['y']:18.10f} {atom['z']:18.10f}"
        for atom in atoms
    )
    return (
        f"! Fixed geometry from accepted 20260919b Li/C50 hollow relaxation; {case}.\n"
        "! References: docs/codex_prompts/oct16_2026_final_project_scope.md\n"
        + before + "ATOMIC_POSITIONS angstrom\n" + coordinates
        + "\n\nK_POINTS automatic\n  4 4 1 0 0 0\n"
    )


def prepare():
    atoms = source_data()
    if MANIFEST.exists() or any(paths(case)[0].exists() for case, _, _ in CASES):
        raise RuntimeError("Prepared files already exist; refusing overwrite")
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for case, ecutwfc, ecutrho in CASES:
        input_path, _, _, _ = paths(case)
        input_path.write_text(make_input(case, ecutwfc, ecutrho, atoms), encoding="utf-8")
        inputs[case] = {"file": str(input_path.relative_to(ROOT)), "sha256": sha256(input_path),
                        "ecutwfc_ry": ecutwfc, "ecutrho_ry": ecutrho, "k_mesh": [4, 4, 1]}
    manifest = {
        "run_id": RUN_ID, "purpose": "Fixed-geometry Li/C50 lower-mesh cutoff sensitivity; not production convergence",
        "source_input": str(SOURCE_INPUT.relative_to(ROOT)), "source_input_sha256": sha256(SOURCE_INPUT),
        "source_output": str(SOURCE_OUTPUT.relative_to(ROOT)), "source_output_sha256": sha256(SOURCE_OUTPUT),
        "source_analysis": str(SOURCE_ANALYSIS.relative_to(ROOT)), "source_analysis_sha256": sha256(SOURCE_ANALYSIS),
        "reference_list": "docs/codex_prompts/oct16_2026_final_project_scope.md",
        "atomic_positions": atoms, "inputs": inputs, "second_case_peak_vram_ceiling": SECOND_PEAK_VRAM_CEILING,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {MANIFEST.relative_to(ROOT)}")


def preflight():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key, expected in ((SOURCE_INPUT, manifest["source_input_sha256"]),
                          (SOURCE_OUTPUT, manifest["source_output_sha256"]),
                          (SOURCE_ANALYSIS, manifest["source_analysis_sha256"])):
        if sha256(key) != expected:
            raise RuntimeError(f"Source changed: {key}")
    for case, _, _ in CASES:
        input_path, output_path, scratch, _ = paths(case)
        if sha256(input_path) != manifest["inputs"][case]["sha256"]:
            raise RuntimeError(f"Prepared input changed: {case}")
        if output_path.exists() or (scratch.exists() and any(scratch.iterdir())):
            raise RuntimeError(f"Output or scratch exists: {case}")
    if not QE.is_file() or not PYTHON.is_file():
        raise RuntimeError("QE or project Python is missing")
    if md5(ROOT / "pseudopotentials/li_pbe_v1.4.uspp.F.UPF") != LI_MD5:
        raise RuntimeError("Li pseudopotential hash mismatch")
    audit = subprocess.run([str(PYTHON), str(ROOT / "scripts/check_pseudopotentials.py")],
                           cwd=ROOT, capture_output=True, text=True)
    if audit.returncode:
        raise RuntimeError("Pseudopotential audit failed: " + audit.stdout + audit.stderr)
    if subprocess.run(["pgrep", "-x", "pw.x"], capture_output=True).returncode == 0:
        raise RuntimeError("Another pw.x is running")
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True)
    if gpu.returncode:
        raise RuntimeError("GPU unavailable: " + gpu.stderr)
    used, total, util = (float(x.strip()) for x in gpu.stdout.splitlines()[0].split(","))
    if used / total >= 0.30 or util >= 30:
        raise RuntimeError("GPU is not idle")
    return audit.stdout + "\nGPU: " + gpu.stdout


def latest_gpu_fraction(path):
    if not path.exists():
        return None
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in reversed(handle.readlines()[-5:]):
            fields = line.split(",")
            if len(fields) >= 3:
                try:
                    return float(fields[1]) / float(fields[2])
                except ValueError:
                    pass
    return None


def run_case(case, status, started):
    input_path, output_path, scratch, name = paths(case)
    scratch.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    status.update({"state": "running", "case": case, "case_started_utc": utc_now()})
    atomic_status(STATUS, status)
    monitors = start_monitors(DIAG, case)
    env = os.environ.copy()
    env.update({"CUDA_VISIBLE_DEVICES": "0", "OMP_NUM_THREADS": "4"})
    try:
        with output_path.open("x", encoding="utf-8", buffering=1) as handle:
            runner = subprocess.Popen(["/usr/bin/time", "-v", "-o", str(DIAG / f"{case}_time_v.log"),
                                       str(QE), "-in", str(input_path)],
                                      cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT)
            status["runner_pid"] = runner.pid
            atomic_status(STATUS, status)
            high_vram_checks = 0
            while runner.poll() is None:
                time.sleep(30)
                status["elapsed_wall_seconds"] = round(time.monotonic() - started)
                try:
                    partial = parse_output(output_path, allow_incomplete=True, calculation="scf")
                    status["progress"] = {key: partial.get(key) for key in (
                        "gpu_acceleration_active", "electronic_converged_cycles", "electronic_failed_cycles",
                        "scf_iterations", "final_total_energy_ry", "job_completed")}
                except Exception as exc:
                    status["progress_error"] = str(exc)
                fraction = latest_gpu_fraction(DIAG / f"{case}_gpu.log")
                status["last_gpu_memory_fraction"] = fraction
                high_vram_checks = high_vram_checks + 1 if fraction is not None and fraction >= 0.98 else 0
                reason = None
                if time.monotonic() - started >= WALL_EXIT_SECONDS:
                    reason = "10.5-hour overall wall limit"
                elif high_vram_checks >= 3:
                    reason = "GPU memory at or above 98% in three checks"
                if reason and not status.get("clean_stop_requested_utc"):
                    (scratch / f"{name}.EXIT").touch(exist_ok=False)
                    status.update({"state": "clean_stop_requested", "clean_stop_reason": reason,
                                   "clean_stop_requested_utc": utc_now()})
                atomic_status(STATUS, status)
            status["runner_exit_code"] = runner.wait()
    finally:
        stop_monitors(*monitors)
    status[f"{case}_peak_gpu_fraction"] = peak_gpu_fraction(DIAG / f"{case}_gpu.log")
    if status["runner_exit_code"] != 0:
        raise RuntimeError(f"{case} QE exit code {status['runner_exit_code']}")
    result = parse_output(output_path, calculation="scf")
    status[f"{case}_result"] = {key: result.get(key) for key in (
        "job_completed", "gpu_acceleration_active", "all_electronic_cycles_converged",
        "electronic_converged_cycles", "electronic_failed_cycles", "scf_iterations",
        "final_total_energy_ry", "smearing_contribution_ry", "wall_time_seconds",
        "total_magnetization_bohr_magneton_per_cell")}
    atomic_status(STATUS, status)


def worker():
    DIAG.mkdir(parents=True, exist_ok=False)
    status = {"schema_version": 1, "run_id": RUN_ID, "worker_pid": os.getpid(), "state": "preflight",
              "cases": [case for case, _, _ in CASES]}
    atomic_status(STATUS, status)
    try:
        snapshot = preflight()
        for command in (["date", "-u"], ["uname", "-r"], ["free", "-h"],
                        ["swapon", "--show"], ["df", "-h", str(ROOT)]):
            proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            snapshot += "\n$ " + " ".join(command) + "\n" + proc.stdout + proc.stderr
        (DIAG / "preflight.txt").write_text(snapshot, encoding="utf-8")
        started = time.monotonic()
        run_case("e65_k4", status, started)
        peak = status["e65_k4_peak_gpu_fraction"]
        elapsed = time.monotonic() - started
        if peak >= SECOND_PEAK_VRAM_CEILING or elapsed >= SECOND_START_LATEST:
            status.update({"state": "stopped_after_first", "reason": f"peak VRAM {peak:.3f}; elapsed {elapsed/3600:.2f} h"})
        else:
            run_case("e70_k4", status, started)
            e65 = status["e65_k4_result"]["final_total_energy_ry"]
            e70 = status["e70_k4_result"]["final_total_energy_ry"]
            status["energy_difference_mev_per_c"] = (e70 - e65) * 13605.693122994 / 50
            status["state"] = "accepted_pair"
    except Exception as exc:
        status.update({"state": "error", "error": f"{type(exc).__name__}: {exc}"})
    finally:
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
    elif args.check_only:
        print(preflight())
    elif args.daemon:
        print(preflight())
        if DIAG.exists():
            parser.error("Diagnostics already exist; refusing duplicate launch")
        # The worker creates its own diagnostics directory and status file.
        launcher = ROOT / "results/phase5/diagnostics" / f"{STEM}_launcher.log"
        with launcher.open("x", encoding="utf-8") as log:
            child = subprocess.Popen([str(PYTHON), str(Path(__file__).resolve()), "--worker"],
                                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
        print(f"Detached validation worker PID {child.pid}; status {STATUS.relative_to(ROOT)}")
    else:
        worker()


if __name__ == "__main__":
    main()
