# RTX 5080 / WSL2 GPU setup

The repository does not install drivers, CUDA, or Quantum ESPRESSO. Prepare
those outside the project, then use the included scripts to validate and run
the inputs portably on any CUDA-enabled QE installation.

## Host and WSL prerequisites

1. Install a current NVIDIA Windows driver with WSL support and update WSL2.
2. In Ubuntu under WSL2, confirm that `nvidia-smi` sees the RTX 5080.
3. Do **not** install a Linux NVIDIA display driver inside WSL. The Windows
   driver exposes CUDA to WSL. If compiling software in WSL, install a
   toolkit-only CUDA package appropriate for WSL instead of a driver-bearing
   metapackage.
4. Install or build a Quantum ESPRESSO 7.x `pw.x` with NVIDIA GPU support.
   Follow the GPU instructions bundled with that exact QE release and select
   the compute capability reported by the NVIDIA tools. Compiler/CUDA support
   must cover the RTX 5080 architecture.

References:

- NVIDIA CUDA on WSL guide: https://docs.nvidia.com/cuda/wsl-user-guide/
- Quantum ESPRESSO GPU README: https://gitlab.com/QEF/q-e/-/blob/develop/README_GPU.md
- Quantum ESPRESSO build guide: https://www.quantum-espresso.org/Doc/user_guide/node11.html

## Repository checks

Run from WSL in the repository root:

```bash
bash scripts/check_gpu_qe.sh
python scripts/check_pseudopotentials.py
```

`check_gpu_qe.sh` confirms GPU visibility, locates `pw.x`, and asks it for its
version. These facts do not prove that `pw.x` was compiled with GPU support.

For manual verification, run a small monitored calculation and check both:

- the QE output contains `GPU acceleration is ACTIVE` (wording may vary by QE
  release); and
- `nvidia-smi` shows the `pw.x` process using the GPU.

Only after that verification, set `QE_GPU_CONFIRMED=1` when invoking the
runner. This explicit gate prevents an unverified CPU-only `pw.x` from being
used silently.

## Single-GPU execution

The wrapper starts one `pw.x` process and exposes one CUDA device. It does not
start multiple MPI ranks on the same laptop GPU.

```bash
QE_GPU_CONFIRMED=1 \
OMP_NUM_THREADS=4 \
CUDA_VISIBLE_DEVICES=0 \
bash scripts/run_relax_gpu.sh qe_inputs/relaxation/pristine/relax_pristine.in
```

Adjust `OMP_NUM_THREADS` for the laptop CPU and thermal limits. `QE_BIN` may be
set to the path or command name of a different CUDA-enabled `pw.x`. There is no
CPU fallback: missing GPU visibility, a missing executable, unresolved input,
or absent manual GPU confirmation causes a clear failure.
