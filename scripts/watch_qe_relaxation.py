#!/usr/bin/env python3
"""Monitor one running QE relaxation and strictly post-process it on success."""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from parse_qe_output import QEOutputParseError, parse_output


FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def as_float(value):
    return float(value.replace("D", "E").replace("d", "e"))


def atomic_json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def process_state(pid):
    command_path = Path(f"/proc/{pid}/cmdline")
    try:
        command = command_path.read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace"
        ).strip()
    except FileNotFoundError:
        return False, None
    except PermissionError:
        return True, None
    return True, command


def last_match(text, pattern, conversion=None):
    matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not matches:
        return None
    value = matches[-1]
    return conversion(value) if conversion else value


def progress_snapshot(output_path):
    if not output_path.is_file():
        return {"output_exists": False}

    text = output_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_output(output_path, allow_incomplete=True, calculation="relax")
    accepted_energies = [
        as_float(value)
        for value in re.findall(
            rf"^!\s+total energy\s*=\s*({FLOAT})\s+Ry",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
    ]
    total_forces = [
        as_float(value)
        for value in re.findall(
            rf"^\s*Total force\s*=\s*({FLOAT})",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
    ]
    stat = output_path.stat()
    return {
        "output_exists": True,
        "output_size_bytes": stat.st_size,
        "output_modified_utc": datetime.fromtimestamp(
            stat.st_mtime, timezone.utc
        ).isoformat(),
        "gpu_acceleration_active": parsed["gpu_acceleration_active"],
        "completed_electronic_cycles": parsed["electronic_converged_cycles"],
        "failed_electronic_cycles": parsed["electronic_failed_cycles"],
        "all_completed_electronic_cycles_converged": parsed[
            "all_electronic_cycles_converged"
        ],
        "total_scf_iterations": parsed["scf_iterations"],
        "last_scf_iteration": last_match(
            text, r"^\s*iteration\s+#\s*(\d+)", int
        ),
        "last_estimated_scf_accuracy_ry": last_match(
            text,
            rf"^\s*estimated scf accuracy\s*<\s*({FLOAT})\s+Ry",
            as_float,
        ),
        "completed_ionic_scf_cycles": len(accepted_energies),
        "last_bfgs_step": parsed["ionic_steps"],
        "last_accepted_energy_ry": accepted_energies[-1]
        if accepted_energies
        else None,
        "accepted_ionic_energies_monotonic_nonincreasing": bool(accepted_energies)
        and all(
            newer <= older
            for older, newer in zip(accepted_energies, accepted_energies[1:])
        ),
        "last_total_force_ry_bohr": total_forces[-1] if total_forces else None,
        "total_magnetization_bohr_magneton_per_cell": parsed[
            "total_magnetization_bohr_magneton_per_cell"
        ],
        "absolute_magnetization_bohr_magneton_per_cell": parsed[
            "absolute_magnetization_bohr_magneton_per_cell"
        ],
        "ionic_convergence_reached": parsed["ionic_convergence_reached"],
        "job_completed": parsed["job_completed"],
    }


def build_status(args, state, command=None, error=None):
    try:
        progress = progress_snapshot(args.qe_output)
        progress_error = None
    except (OSError, QEOutputParseError, ValueError) as exc:
        progress = None
        progress_error = str(exc)
    return {
        "schema_version": 1,
        "updated_utc": utc_now(),
        "state": state,
        "watcher_pid": os.getpid(),
        "watched_qe_pid": args.pid,
        "watched_command": command,
        "qe_output": str(args.qe_output),
        "progress": progress,
        "progress_error": progress_error,
        "terminal_error": error,
    }


def postprocess(args):
    try:
        result = parse_output(args.qe_output, calculation="relax")
    except (OSError, QEOutputParseError) as exc:
        return False, f"Strict QE validation failed: {exc}"

    command = [
        sys.executable,
        str(Path(__file__).with_name("save_relaxed_structure.py")),
        str(args.qe_output),
        "--template",
        str(args.template),
        "--output-stem",
        str(args.output_stem),
        "--analysis-json",
        str(args.analysis_json),
    ]
    if args.pristine:
        command.extend(["--pristine", str(args.pristine)])

    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    args.postprocess_log.parent.mkdir(parents=True, exist_ok=True)
    args.postprocess_log.write_text(
        completed.stdout + completed.stderr, encoding="utf-8"
    )
    if completed.returncode != 0:
        return (
            False,
            f"Structure post-processing exited with status {completed.returncode}; "
            f"see {args.postprocess_log}.",
        )
    return True, result


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qe_output", type=Path)
    parser.add_argument("--pid", type=int, required=True, help="Running pw.x PID.")
    parser.add_argument("--status-json", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output-stem", type=Path, required=True)
    parser.add_argument("--analysis-json", type=Path, required=True)
    parser.add_argument("--postprocess-log", type=Path, required=True)
    parser.add_argument("--pristine", type=Path)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--settle-seconds", type=float, default=5.0)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.poll_seconds < 1 or args.settle_seconds < 0:
        print("error: invalid polling or settle interval.", file=sys.stderr)
        return 2

    lock_path = args.status_json.with_suffix(args.status_json.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"error: another watcher holds {lock_path}.", file=sys.stderr)
            return 2
        lock.write(f"watcher_pid={os.getpid()}\n")
        lock.flush()

        alive, command = process_state(args.pid)
        if alive and command and "pw.x" not in command:
            message = f"PID {args.pid} is not pw.x: {command}"
            atomic_json_write(
                args.status_json,
                build_status(args, "refused_pid_mismatch", command, message),
            )
            print(f"error: {message}", file=sys.stderr)
            return 2

        while alive:
            atomic_json_write(
                args.status_json, build_status(args, "running", command)
            )
            time.sleep(args.poll_seconds)
            alive, current_command = process_state(args.pid)
            if alive and current_command and "pw.x" not in current_command:
                alive = False
                command = current_command
                break
            command = current_command or command

        atomic_json_write(
            args.status_json, build_status(args, "validating", command)
        )
        time.sleep(args.settle_seconds)
        accepted, detail = postprocess(args)
        if not accepted:
            atomic_json_write(
                args.status_json,
                build_status(args, "incomplete_or_failed", command, detail),
            )
            print(f"error: {detail}", file=sys.stderr)
            return 2

        status = build_status(args, "accepted", command)
        status["strict_result"] = {
            key: detail[key]
            for key in (
                "job_completed",
                "gpu_acceleration_active",
                "all_electronic_cycles_converged",
                "electronic_converged_cycles",
                "electronic_failed_cycles",
                "ionic_convergence_reached",
                "ionic_steps",
                "final_total_energy_ry",
                "final_total_force_ry_bohr",
                "maximum_force_ry_bohr",
                "total_magnetization_bohr_magneton_per_cell",
                "absolute_magnetization_bohr_magneton_per_cell",
                "wall_time_seconds",
            )
        }
        status["analysis_json"] = str(args.analysis_json)
        status["postprocess_log"] = str(args.postprocess_log)
        atomic_json_write(args.status_json, status)
        print(f"Accepted QE relaxation; status written to {args.status_json}.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
