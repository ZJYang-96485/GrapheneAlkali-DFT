# GrapheneAlkali-DFT — Phase 4
# Real-system convergence, input auditing, and first substrate calculations

Read this entire instruction before modifying or running anything.

Repository:
    ZJYang-96485/GrapheneAlkali-DFT

Current scientific goal:
Establish numerically verified Quantum ESPRESSO settings for the real 5x5
graphene model and then perform the first production substrate relaxation(s).

DO NOT proceed to Li/Na adsorption, DOS, PDOS, or NEB in this phase.

======================================================================
0. CURRENT STATUS — DO NOT REDO COMPLETED INFRASTRUCTURE
======================================================================

The following have already been completed and manually validated:

PROJECT STRUCTURES
- pristine graphene: C50
- monovacancy graphene: C49
- 5x5 graphene supercell
- fixed out-of-plane cell dimension: 18 Å
- structures inspected previously

GPU / SOFTWARE ENVIRONMENT
- Windows 11 host
- WSL2 Ubuntu
- NVIDIA RTX 5080 Laptop GPU
- approximately 16 GB VRAM
- NVIDIA HPC SDK installed
- Quantum ESPRESSO 7.6 compiled with NVIDIA GPU support
- CUDA-enabled executable:
      ~/q-e/bin/pw.x

A real QE calculation has already been executed through this WSL environment.
The output explicitly reported:

    GPU acceleration is ACTIVE

Therefore:

DO NOT:
- reinstall WSL
- reinstall NVIDIA drivers
- reinstall CUDA
- reinstall NVIDIA HPC SDK
- rebuild Quantum ESPRESSO
- replace ~/q-e/bin/pw.x
- create a CPU fallback workflow

The infrastructure has already been validated.

======================================================================
1. KEEP THREE SOURCES OF AUTHORITY SEPARATE
======================================================================

There are THREE different layers in this project.

----------------------------------------------------------------------
A. MSE 404 MIC WALKTHROUGH
----------------------------------------------------------------------

Use the course walkthrough as guidance for:

- understanding pw.x input structure
- auditing every input parameter
- pseudopotential verification
- ecutwfc / ecutrho reasoning
- ATOMIC_SPECIES consistency
- ATOMIC_POSITIONS units
- K_POINTS formatting
- SCF convergence verification
- geometry-relaxation verification
- extracting the FINAL converged total energy
- convergence-study logic
- keeping raw outputs
- checking AI-generated inputs instead of trusting them automatically

DO NOT use the walkthrough as a GPU guide.

The walkthrough uses a generic command such as:

    pw.x < input > output

That command demonstrates QE I/O only.

It does NOT define:
- CUDA configuration
- NVIDIA compiler configuration
- GPU runtime settings
- MPI strategy
- OpenMP strategy
- our QE executable path
- RTX 5080 execution

Also DO NOT copy numerical H2 choices into graphene.

H2-specific settings such as:
- H pseudopotential
- 1x1x1 sampling
- molecular cubic cell
- H atomic positions
- H cutoff values

are NOT project parameters.

----------------------------------------------------------------------
B. GRAPHENE PROJECT METHODOLOGY
----------------------------------------------------------------------

The current repository defines the scientific model.

Current nominal methodology:

- Quantum ESPRESSO 7.6
- PBE exchange-correlation
- DFT-D3 with Becke-Johnson damping
- SSSP Efficiency PBE pseudopotentials

Carbon pseudopotential expected:

    C.pbe-n-kjpaw_psl.1.0.0.UPF

Nominal numerical settings:

    ecutwfc = 50 Ry
    ecutrho = 400 Ry

Relaxation:
    6x6x1 k mesh
    shift 0 0 0
    Marzari-Vanderbilt smearing
    degauss = 0.01 Ry

Later final SCF:
    9x9x1

Later DOS/PDOS:
    12x12x1

Electronic convergence:
    conv_thr = 1.0d-8 Ry
    mixing_beta = 0.3

Ionic convergence:
    forc_conv_thr = 4.0d-4 Ry/Bohr

Geometry:
    fixed cell
    BFGS ionic relaxation
    no vc-relax

Electrostatics:
    assume_isolated = '2D'

Spin:
    pristine: nspin = 1
    monovacancy: nspin = 2

Do not silently change any of these production defaults.

The purpose of Phase 4 is to TEST whether the important numerical choices are
supported by actual calculations.

----------------------------------------------------------------------
C. GPU EXECUTION
----------------------------------------------------------------------

Use the independently validated CUDA QE executable:

    ~/q-e/bin/pw.x

When using the repository wrapper, use:

    QE_BIN=~/q-e/bin/pw.x
    QE_GPU_CONFIRMED=1

GPU verification is separate from the course walkthrough.

For project calculations verify from the QE output that GPU acceleration is
active.

nvidia-smi may also be monitored while a calculation runs, but do not reject a
valid calculation solely because WSL process reporting in nvidia-smi is
incomplete.

The QE output itself is the primary execution evidence.

======================================================================
2. FIRST ACTION: INSPECT THE REPOSITORY
======================================================================

Before editing anything:

- inspect the full repository tree
- inspect config/qe.yaml
- inspect README.md
- inspect the current structure generator
- inspect the current QE input generator
- inspect all validation scripts
- inspect the GPU runner
- inspect the parser
- inspect existing generated QE input files

Do not replace working infrastructure unnecessarily.

Prefer extending existing scripts over creating duplicate implementations.

Record the current Git status.

Do not commit.
Do not push.

======================================================================
3. DOCUMENT THE AI-ASSISTED WORKFLOW
======================================================================

Create:

    docs/codex_prompts/phase4_convergence_and_substrate.md

Save this complete task specification there.

Also create:

    results/phase4/ledger.md

Use the course workflow:

    1. Specify
    2. Generate
    3. Verify
    4. Iterate / attribute

Do not fabricate entries.

Only record a calculation result after the corresponding calculation actually
finishes.

======================================================================
4. VERIFY QE 7.6 SYNTAX FROM THE ACTUAL QE VERSION
======================================================================

This is important.

Do NOT rely solely on AI memory for Quantum ESPRESSO keyword syntax.

Before running production calculations, consult the documentation associated
with the installed QE 7.6 source tree whenever possible.

Check the QE 7.6 INPUT_PW documentation for the exact syntax of at least:

- input_dft
- vdw_corr
- dftd3_version
- dftd3_threebody
- assume_isolated
- occupations
- smearing
- degauss
- starting_magnetization
- forc_conv_thr
- ion_dynamics

In particular, explicitly verify that the repository's implementation of:

    PBE + DFT-D3(BJ)

uses valid QE 7.6 syntax.

The current intended physical choice is DFT-D3 with Becke-Johnson damping.

Do not silently change the physical method.

If the repository syntax does not match QE 7.6 documentation:

STOP before production calculations.

Report:
- existing syntax
- documented QE 7.6 syntax
- exact proposed correction

A clear syntax error can be corrected only after it is documented.

======================================================================
5. PSEUDOPOTENTIAL AUDIT — HARD GATE
======================================================================

The walkthrough specifically warns that AI systems may invent plausible
pseudopotential filenames.

Therefore pseudopotential verification is a HARD gate.

The only approved carbon pseudopotential for the current methodology is:

    C.pbe-n-kjpaw_psl.1.0.0.UPF

Check:

    pseudopotentials/C.pbe-n-kjpaw_psl.1.0.0.UPF

Before running pw.x:

1. verify the exact filename exists;
2. verify the file is readable;
3. inspect the UPF header;
4. verify that the file actually describes carbon;
5. verify that its exchange-correlation metadata is compatible with the
   selected PBE methodology;
6. record the pseudopotential type reported by the UPF file;
7. record any cutoff recommendations present in its metadata if available.

Do NOT determine pseudopotential type merely from the filename.

Do NOT:
- invent a filename
- rename another UPF
- substitute another carbon PP
- download a different PP automatically
- silently switch PP families

If the exact approved file is missing:

STOP.

Tell the user which file is missing.

Do not run the convergence study.

Pseudopotential files remain excluded from Git.

======================================================================
6. QE INPUT FORMAT AUDIT — HARD GATE
======================================================================

Every generated input must be audited before execution.

The course walkthrough is used here as the auditing philosophy, but the actual
syntax must be valid for QE 7.6 and appropriate for this graphene system.

For a fixed-cell SCF calculation, verify the required namelists/cards include
the appropriate equivalents of:

    &CONTROL
    &SYSTEM
    &ELECTRONS

    ATOMIC_SPECIES
    ATOMIC_POSITIONS
    K_POINTS
    CELL_PARAMETERS

because this project uses:

    ibrav = 0

For a structural relaxation additionally require:

    &IONS

with:

    ion_dynamics = 'bfgs'

Do NOT use:

    vc-relax

----------------------------------------------------------------------
UNITS
----------------------------------------------------------------------

Never leave coordinate or cell units implicit.

Project convention:

    CELL_PARAMETERS angstrom
    ATOMIC_POSITIONS angstrom

unless an existing validated file is intentionally using another explicit
representation.

Do not silently mix:

- bohr
- angstrom
- alat
- crystal

Do not silently rescale coordinates.

----------------------------------------------------------------------
ATOM COUNTS
----------------------------------------------------------------------

Pristine:

    nat = 50

and exactly 50 atomic-position records.

Monovacancy:

    nat = 49

and exactly 49 atomic-position records.

No Li or Na atoms may appear in Phase 4.

----------------------------------------------------------------------
ATOMIC TYPES
----------------------------------------------------------------------

For pristine graphene:

    ntyp = 1

unless a documented technical reason requires otherwise.

For the spin-seeded vacancy calculation, multiple QE carbon type labels may be
used solely to initialize different starting magnetizations.

If two carbon labels are used:

- both must represent carbon;
- both must point to the SAME approved carbon UPF;
- the distinction must not change the chemical species;
- starting magnetization is only an initial SCF seed;
- final magnetization must remain unconstrained.

Check:

number of ATOMIC_SPECIES records == ntyp

and every label in ATOMIC_POSITIONS must exist in ATOMIC_SPECIES.

----------------------------------------------------------------------
K POINTS
----------------------------------------------------------------------

Do NOT use the H2 walkthrough's Gamma-only sampling.

This is a condensed graphene system.

For automatic sampling require exactly:

    K_POINTS automatic
    nkx nky nkz sx sy sz

For example:

    K_POINTS automatic
    6 6 1 0 0 0

Do not silently substitute Gamma-only sampling.

----------------------------------------------------------------------
CUTOFFS
----------------------------------------------------------------------

Always explicitly provide both:

    ecutwfc
    ecutrho

Do not rely on a QE default for ecutrho.

Do NOT import the walkthrough statement about ultrasoft 8–12x charge-density
cutoffs as an automatic rule for this carbon PP.

Instead:

- inspect the actual carbon UPF type;
- retain the project's tested ecutrho values;
- establish adequacy numerically.

----------------------------------------------------------------------
SCRATCH / PREFIX
----------------------------------------------------------------------

Every convergence point must have isolated scratch data.

Do not allow different calculations to contaminate one another through reused
incompatible .save directories.

Use unique prefix and/or outdir values for different parameter points.

Ensure outdir is writable.

======================================================================
7. RUN EXISTING VALIDATION TOOLS
======================================================================

From the repository root, run the existing validation utilities where
applicable.

At minimum inspect/run equivalents of:

    python scripts/validate_structures.py
    python scripts/generate_qe_inputs.py
    python scripts/validate_qe_inputs.py
    python scripts/check_pseudopotentials.py
    bash scripts/check_gpu_qe.sh

Use:

    ~/q-e/bin/pw.x

as the actual project QE executable.

Do not assume that another pw.x found first on PATH is equivalent.

If any validation fails:

STOP.

Report the failure before starting expensive calculations.

======================================================================
8. PRISTINE C50 CONVERGENCE STUDY
======================================================================

Use the FIXED pristine C50 structure.

Do not relax atomic coordinates during convergence testing.

Do not alter the 18 Å cell.

Keep the physical method identical across parameter sweeps.

Use:

- PBE
- DFT-D3(BJ)
- approved carbon PP
- assume_isolated = '2D'
- nspin = 1
- conv_thr = 1.0d-8

Create organized directories, for example:

    qe_inputs/convergence/pristine/cutoff/
    qe_inputs/convergence/pristine/kpoints/
    qe_inputs/convergence/pristine/smearing/

    results/convergence/pristine/cutoff/
    results/convergence/pristine/kpoints/
    results/convergence/pristine/smearing/

Create or extend reusable scripts.

Do not create dozens of manually duplicated inputs if the existing generator
can be extended safely.

======================================================================
9. CUTOFF CONVERGENCE
======================================================================

Run SCF calculations at:

    ecutwfc = 40 Ry
    ecutrho = 320 Ry

    ecutwfc = 45 Ry
    ecutrho = 360 Ry

    ecutwfc = 50 Ry
    ecutrho = 400 Ry

    ecutwfc = 55 Ry
    ecutrho = 440 Ry

Keep:

    k mesh = 6x6x1
    shift = 0 0 0
    degauss = 0.01 Ry
    smearing = 'mv'

Save every input and raw output.

For each calculation extract:

- final converged total energy in Ry
- final converged total energy in eV
- energy per carbon atom
- difference from the 55/440 result
- number of SCF iterations
- wall time
- GPU acceleration status
- SCF convergence status
- JOB DONE status

IMPORTANT:

Do NOT take the first line containing "total energy".

The parser must select the final converged QE result.

Use approximately:

    1 meV/atom

as the working energy-convergence criterion for this project stage.

Evaluate whether:

    50/400 Ry

is converged relative to:

    55/440 Ry.

The H2 walkthrough discusses variational lowering of energy with increasing
basis size.

Use that as a useful sanity check, NOT as an inflexible law that causes an
automatic failure for tiny numerical deviations in this more complicated
periodic calculation.

If meaningful non-monotonic behavior appears:

investigate:
- SCF convergence
- parser behavior
- input consistency
- FFT/grid effects
- smearing
- scratch contamination

before interpreting the data.

Do not silently change the production cutoff.

If 50/400 clearly fails the convergence criterion:

STOP and report the data for user review.

======================================================================
10. K-POINT CONVERGENCE
======================================================================

Only continue after the cutoff stage is valid.

Using:

    ecutwfc = 50 Ry
    ecutrho = 400 Ry
    degauss = 0.01 Ry

run:

    3x3x1
    6x6x1
    9x9x1
    12x12x1

all with:

    shift = 0 0 0

Record the same output quantities.

Compare energies per atom relative to the densest mesh.

The questions are:

1. Is 6x6x1 adequate for structural relaxation?
2. Is 9x9x1 adequately converged for later final single-point energies?

Do not require the k-point energies to decrease monotonically.

K-point integration does not have the same simple variational interpretation
as plane-wave basis enlargement.

Evaluate numerical convergence by differences relative to dense sampling.

If the existing 6x6x1 or 9x9x1 settings clearly fail:

STOP.

Report rather than silently changing config/qe.yaml.

======================================================================
11. SMEARING SENSITIVITY
======================================================================

Only continue after cutoff and k-point studies are internally consistent.

Use:

    ecutwfc = 50 Ry
    ecutrho = 400 Ry
    k mesh = 6x6x1
    shift = 0 0 0
    smearing = 'mv'

Compare:

    degauss = 0.005 Ry
    degauss = 0.010 Ry
    degauss = 0.020 Ry

Record from QE exactly what QE reports, including when available:

- final total energy
- smearing contribution
- Fermi energy
- SCF iterations
- wall time

Do NOT invent or label an "internal energy" unless QE explicitly reports that
quantity or it is calculated using a documented QE definition.

Do not interpret numerical smearing entropy as a physical adsorption effect.

This test validates the current pristine relaxation setting only.

Later Li/Na and vacancy systems may require an additional sensitivity check if
their electronic character changes.

======================================================================
12. CONVERGENCE ANALYSIS
======================================================================

Generate:

    results/convergence/pristine/summary.csv
    results/convergence/pristine/summary.md

and figures such as:

    figures/convergence/cutoff_convergence.png
    figures/convergence/kpoint_convergence.png
    figures/convergence/smearing_sensitivity.png

Each plot must contain:

- clearly labeled axes
- units
- raw data points
- useful energy differences
- convergence threshold where appropriate

The Markdown report must answer explicitly:

- Is 50/400 Ry supported?
- Is 6x6x1 supported for relaxation?
- Is 9x9x1 supported for later final SCF?
- Is 0.01 Ry smearing reasonable for the present pristine system?

Also report actual RTX 5080 wall times.

This replaces our previous rough runtime estimates with measured values.

======================================================================
13. PRISTINE GRAPHENE PRODUCTION RELAXATION
======================================================================

Proceed ONLY if the convergence study supports the current settings.

Regenerate and re-audit:

    qe_inputs/relaxation/pristine/relax_pristine.in

before running it.

Confirm:

- calculation = 'relax'
- ibrav = 0
- nat = 50
- correct ntyp
- nspin = 1
- correct PBE setting
- verified D3(BJ) syntax
- assume_isolated = '2D'
- ecutwfc = 50
- ecutrho = 400
- occupations = 'smearing'
- smearing = 'mv'
- degauss = 0.01
- 6x6x1, shift 0 0 0
- conv_thr = 1.0d-8
- forc_conv_thr = 4.0d-4
- &IONS present
- ion_dynamics = 'bfgs'
- explicit cell units
- explicit coordinate units
- exactly 50 atoms
- no Li
- no Na
- approved carbon UPF exists

Run with the validated GPU executable.

Use the existing GPU wrapper when possible:

    QE_BIN=~/q-e/bin/pw.x
    QE_GPU_CONFIRMED=1

Do not introduce MPI unless there is a separately demonstrated reason.

Verify after completion:

- GPU acceleration reported
- SCF cycles converged
- BFGS completed successfully
- JOB DONE
- final force satisfies the requested threshold
- cell vectors remained fixed
- atom count remains 50
- no unintended chemical species appeared

Extract:

- final energy
- number of ionic steps
- final force
- wall time
- final coordinates

Save relaxed structures without overwriting the original:

    structures/relaxed/pristine/graphene_5x5_pristine_relaxed.traj
    structures/relaxed/pristine/graphene_5x5_pristine_relaxed.xyz

Keep the original C50 structure unchanged.

======================================================================
14. MONOVACANCY: PERFORM A SYMMETRY PRE-FLIGHT BEFORE RELAXATION
======================================================================

Do NOT automatically launch the C49 vacancy relaxation immediately after the
pristine result.

The graphene monovacancy can reconstruct.

An exactly symmetric initial defect may remain artificially trapped in a
symmetric configuration if the computational symmetry treatment prevents the
symmetry-breaking mode from developing.

Therefore first inspect:

    qe_inputs/relaxation/monovacancy/relax_monovacancy.in

and the C49 starting geometry.

Check:

- nat = 49
- nspin = 2
- vacancy-neighbor identification
- carbon atomic-type labels
- both carbon labels reference the same approved UPF
- starting_magnetization values
- QE symmetry settings
- whether the three initial vacancy-neighbor atoms are geometrically exactly
  symmetry-equivalent

Do NOT automatically:

- manually reconstruct the vacancy
- perturb an atom
- set nosym
- change atomic coordinates
- constrain a magnetic moment

If the initial structure is exactly symmetric and there is a meaningful risk
that QE symmetry will prevent the known symmetry-breaking relaxation:

STOP before the production vacancy relaxation.

Write a short diagnostic explaining:

- current symmetry situation
- whether QE will use symmetry
- whether a symmetry-breaking perturbation and/or nosym setting may be needed
- what specific change would be proposed

Ask for user approval before changing the vacancy starting configuration.

If the existing setup is demonstrably capable of allowing reconstruction
without intervention, document why before running it.

======================================================================
15. IF APPROVED / SAFE: MONOVACANCY RELAXATION
======================================================================

Only when the symmetry issue has been resolved, run the C49 relaxation.

Before launch verify:

- nat = 49
- nspin = 2
- correct PBE
- verified D3(BJ)
- assume_isolated = '2D'
- 50/400 Ry
- 6x6x1
- 0.01 Ry MV smearing
- BFGS
- fixed cell
- same approved carbon PP for all carbon labels
- local starting magnetization is only an initial seed

After completion verify:

- GPU acceleration
- electronic convergence
- ionic convergence
- JOB DONE
- final force criterion
- fixed cell
- exactly 49 atoms

Record:

- final energy
- wall time
- ionic steps
- final forces
- total magnetization if QE reports it
- absolute magnetization if QE reports it
- final coordinates

For the three vacancy-neighbor carbon atoms calculate and report their three
pair distances.

Use those distances to describe whether a vacancy reconstruction occurred.

Do not impose a reconstruction after the calculation.

Save:

    structures/relaxed/monovacancy/graphene_5x5_monovacancy_relaxed.traj
    structures/relaxed/monovacancy/graphene_5x5_monovacancy_relaxed.xyz

Do not overwrite the original C49 structure.

======================================================================
16. OUTPUT PARSER REQUIREMENTS
======================================================================

Extend the current parser rather than replacing it unnecessarily.

For SCF runs parse:

- final converged total energy
- convergence achieved status
- number of iterations
- wall time
- GPU active status
- JOB DONE

For relaxation additionally parse:

- geometry optimization completion
- number of ionic steps
- final force
- final coordinates
- magnetization when present

Never silently accept:

- an unconverged SCF
- an incomplete relaxation
- an output missing JOB DONE
- the first intermediate total-energy line

Keep raw outputs.

The parser is an analysis convenience, not a replacement for inspecting QE
output.

======================================================================
17. SCIENTIFIC GUARDRAILS
======================================================================

In Phase 4 DO NOT:

- add Li
- add Na
- create adsorption structures
- calculate adsorption energies
- calculate bulk Li reference energy
- calculate bulk Na reference energy
- run DOS
- run PDOS
- run band structures
- create NEB paths
- run NEB
- change the 5x5 supercell
- change the 18 Å cell height
- use vc-relax
- switch pseudopotential families
- automatically change production cutoffs
- automatically change production k meshes
- automatically change the vacancy geometry
- overwrite original structures
- commit
- push

Do not make a scientific decision simply because a calculation ran without an
error.

A calculation that finishes may still be wrong.

======================================================================
18. FAILURE POLICY
======================================================================

STOP rather than improvising if any of the following occurs:

- approved carbon UPF missing
- PP identity inconsistent
- QE syntax uncertain
- D3(BJ) syntax inconsistent with QE 7.6 docs
- unresolved input placeholder
- nat does not match coordinate count
- ntyp does not match species
- coordinate units ambiguous
- cell units ambiguous
- wrong k-point format
- wrong executable
- GPU acceleration absent
- SCF does not converge
- output lacks JOB DONE
- 50/400 clearly fails convergence
- 6x6x1 clearly fails convergence
- vacancy symmetry treatment is scientifically ambiguous

Report the issue and the evidence.

Do not "fix" a scientific problem invisibly.

======================================================================
19. FINAL CODEX REPORT
======================================================================

At the end, report concisely:

1. repository files inspected;
2. files created;
3. files modified;
4. exact carbon pseudopotential identity;
5. PP metadata/type found in the UPF;
6. QE 7.6 syntax audit outcome;
7. cutoff-convergence table;
8. k-point-convergence table;
9. smearing-sensitivity table;
10. whether 50/400 Ry is supported;
11. whether 6x6x1 is supported for relaxation;
12. whether 9x9x1 is supported for later final SCF;
13. actual RTX 5080 wall times;
14. pristine relaxation status and final structural quantities;
15. vacancy symmetry pre-flight outcome;
16. monovacancy relaxation result only if it was scientifically safe to run;
17. all warnings or suspicious behavior;
18. exact next decision required from the user.

End the phase there.

DO NOT proceed to Li/Na adsorption without explicit user approval.