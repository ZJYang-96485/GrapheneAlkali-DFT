#!/usr/bin/env bash
set -euo pipefail

# Reproducible single-GPU Quantum ESPRESSO 7.6 build inside the NVIDIA
# HPC SDK 26.5 Ubuntu 22.04 development container.  Defaults target A100;
# QE_CUDA_RUNTIME, QE_CUDA_ARCH, and QE_BUILD_JOBS select another GPU safely.

workspace=${1:-/workspace}
qe_dir="${workspace}/q-e-7.6"
log_dir="${workspace}/logs"
build_log="${log_dir}/qe76_gpu_build.log"
expected_commit=9f93ddec427d2b9a45bb72d828c6d324f62fcabd

mkdir -p "${workspace}" "${log_dir}"
exec > >(tee -a "${build_log}") 2>&1

date --iso-8601=seconds
nvidia-smi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates git make python3 rsync time procps \
  libfftw3-dev libopenblas-dev

nvcompilers=/opt/nvidia/hpc_sdk/Linux_x86_64/26.5
# This NVHPC image ships CUDA 12.9 and 13.2 toolkits.  The environment
# overrides let the caller match the pod driver and GPU compute capability.
cuda_runtime=${QE_CUDA_RUNTIME:-12.9}
cuda_arch=${QE_CUDA_ARCH:-80}
build_jobs=${QE_BUILD_JOBS:-$(nproc)}
test -d "${nvcompilers}/cuda/${cuda_runtime}"
[[ "${cuda_arch}" =~ ^[0-9]+$ ]]
[[ "${build_jobs}" =~ ^[1-9][0-9]*$ ]]
export PATH="${nvcompilers}/compilers/bin:${nvcompilers}/cuda/${cuda_runtime}/bin:${PATH}"
export LD_LIBRARY_PATH="${nvcompilers}/cuda/${cuda_runtime}/lib64:${nvcompilers}/compilers/lib:${LD_LIBRARY_PATH:-}"
export F90=nvfortran
export CC=nvc
export CXX=nvc++

if [[ ! -d "${qe_dir}/.git" ]]; then
  git clone --branch qe-7.6 --depth 1 --recurse-submodules --shallow-submodules \
    https://github.com/QEF/q-e.git "${qe_dir}"
fi

git -C "${qe_dir}" submodule update --init --recursive --depth 1
actual_commit=$(git -C "${qe_dir}" rev-parse HEAD)
if [[ "${actual_commit}" != "${expected_commit}" ]]; then
  printf 'QE source mismatch: expected %s, got %s\n' \
    "${expected_commit}" "${actual_commit}" >&2
  exit 2
fi

if [[ ! -x "${qe_dir}/bin/pw.x" ]]; then
  cd "${qe_dir}"
  ./configure \
    --with-gpu=cuda \
    --with-cuda-runtime="${cuda_runtime}" \
    --with-cuda-cc="${cuda_arch}" \
    --with-scalapack=no
  make -j"${build_jobs}" pw
fi

test -x "${qe_dir}/bin/pw.x"
printf 'QE source commit: '
git -C "${qe_dir}" rev-parse HEAD
printf 'QE source tag: '
git -C "${qe_dir}" describe --tags --exact-match HEAD
grep -E '^(CUDA_ARCH|CUDA_RUNTIME|MPIF90|F90|CC)[[:space:]]*=' \
  "${qe_dir}/make.inc"
sha256sum "${qe_dir}/bin/pw.x"
date --iso-8601=seconds
