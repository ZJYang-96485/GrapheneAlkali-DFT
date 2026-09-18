#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 {cutoff|kpoints|smearing}" >&2
    exit 2
fi
study="$1"
case "$study" in
    cutoff|kpoints|smearing) ;;
    *)
        echo "Unknown convergence study: $study" >&2
        exit 2
        ;;
esac

input_dir="$ROOT_DIR/qe_inputs/convergence/pristine/$study"
output_dir="$ROOT_DIR/results/convergence/pristine/$study"
if [[ ! -d "$input_dir" ]]; then
    echo "Input directory not found: $input_dir" >&2
    exit 2
fi
mapfile -t inputs < <(find "$input_dir" -maxdepth 1 -type f -name '*.in' -print | sort -V)
if (( ${#inputs[@]} == 0 )); then
    echo "No convergence inputs found in $input_dir" >&2
    exit 2
fi

mkdir -p "$output_dir"
for input_path in "${inputs[@]}"; do
    stem="$(basename "${input_path%.in}")"
    output_path="$output_dir/$stem.out"
    echo "=== $study: $stem ==="
    QE_REQUIRE_CALCULATION=scf bash "$SCRIPT_DIR/run_pw_gpu.sh" "$input_path" "$output_path"
done

echo "Completed $study convergence stage (${#inputs[@]} calculations)."
