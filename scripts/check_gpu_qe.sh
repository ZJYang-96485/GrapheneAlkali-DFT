#!/usr/bin/env bash
set -u

QE_BIN="${QE_BIN:-pw.x}"
failed=0

echo "Checking WSL/NVIDIA visibility..."
if [[ "$(uname -r 2>/dev/null || true)" == *[Mm]icrosoft* ]]; then
    echo "  OK: running under WSL."
else
    echo "  NOTE: this kernel does not identify itself as WSL."
fi

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1)"
    echo "  OK: NVIDIA GPU visible${gpu_name:+ - $gpu_name}"
else
    echo "  FAIL: nvidia-smi is unavailable or cannot communicate with the GPU."
    failed=1
fi

echo "Checking Quantum ESPRESSO..."
if command -v "$QE_BIN" >/dev/null 2>&1; then
    qe_path="$(command -v "$QE_BIN")"
    echo "  OK: executable found - $qe_path"
    # Some QE 7.6 builds do not implement --version as an early-exit option:
    # they print the normal PWSCF banner, then try to read an input file and
    # return nonzero. Probe in an isolated temporary directory so any CRASH
    # file stays out of the repository, and accept only a recognizable banner.
    qe_probe_dir="$(mktemp -d)"
    qe_version="$(cd "$qe_probe_dir" && "$qe_path" --version </dev/null 2>&1)"
    qe_status=$?
    rm -rf -- "$qe_probe_dir"
    qe_banner="$(printf '%s\n' "$qe_version" | sed -n '/Program PWSCF v\./p' | head -n 1)"
    if [[ -n "$qe_banner" ]]; then
        echo "  OK: ${qe_banner#${qe_banner%%[![:space:]]*}}"
        if (( qe_status != 0 )); then
            echo "  NOTE: this build printed its version banner but returned $qe_status for --version."
        fi
    else
        echo "  FAIL: $QE_BIN did not print a recognizable PWSCF version banner."
        failed=1
    fi
else
    echo "  FAIL: $QE_BIN was not found in PATH."
    failed=1
fi

echo
echo "GPU-build status: NOT PROVEN by these checks."
echo "nvidia-smi and a usable pw.x do not establish that QE was compiled with CUDA."
echo "Verify the build configuration and confirm GPU use with a monitored benchmark."

if (( failed != 0 )); then
    echo "Environment check failed; do not start a production run." >&2
    exit 1
fi

echo "Basic environment checks passed; manual GPU-build verification is still required."
