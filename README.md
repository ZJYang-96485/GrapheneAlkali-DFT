# GrapheneAlkali-DFT
First-principles study of Li and Na adsorption and diffusion on pristine and vacancy-defective graphene using Quantum ESPRESSO.

## Phase 2: Bare-substrate DFT relaxation

Phase 2 begins with fixed-cell `relax` calculations for the validated bare
substrates: pristine graphene and monovacancy graphene.  Pristine graphene is
the baseline test, while the monovacancy must be relaxed before vacancy-
associated Li/Na adsorption sites are finalized.

The input templates are generated from the ASE `.traj` structures:

```bash
python -m pip install -r requirements.txt
python scripts/validate_structures.py
python scripts/generate_qe_inputs.py
```

The generated inputs contain `__QE_UNRESOLVED__` markers for DFT choices that
have not yet been selected.  Edit `config/qe.yaml`, regenerate, and review the
inputs before running `pw.x`.  The runner supports local execution and an
optional MPI process count:

```bash
scripts/run_relax.sh qe_inputs/relaxation/pristine/relax_pristine.in
MPI_NP=4 scripts/run_relax.sh qe_inputs/relaxation/pristine/relax_pristine.in
```

QE output can later be summarized with:

```bash
python scripts/parse_qe_output.py qe_inputs/relaxation/pristine/relax_pristine.out
```
