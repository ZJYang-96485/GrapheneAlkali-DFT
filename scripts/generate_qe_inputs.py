#!/usr/bin/env python3
"""Generate production-ready bare-substrate QE relaxation inputs."""

import argparse
from pathlib import Path

import numpy as np
from ase.geometry import find_mic
from ase.io import read

from validate_structures import validate_atoms


ROOT = Path(__file__).resolve().parents[1]
UNRESOLVED = "__QE_UNRESOLVED__"
SYSTEM_NAMES = ("pristine", "monovacancy")
QE_BULK_C_LABEL = "C"
# QE 7.x limits atomic-type labels to three characters, so the conceptual
# C_vac label is rendered as C_v in the actual input.
QE_VACANCY_C_LABEL = "C_v"


def load_config(path):
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PyYAML is required to read config/qe.yaml. "
            "Install project dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if not isinstance(config, dict):
        raise ValueError(f"Configuration must contain a mapping: {path}")
    return config


def repo_path(value):
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def scalar(value):
    if value is None:
        return UNRESOLVED
    if isinstance(value, bool):
        return ".true." if value else ".false."
    if isinstance(value, float):
        rendered = f"{value:.12g}"
        if "e" in rendered.lower():
            mantissa, exponent = rendered.lower().split("e")
            if "." not in mantissa:
                mantissa += ".0"
            rendered = f"{mantissa}d{int(exponent):+d}"
        return rendered
    return str(value)


def quoted(value):
    return f"'{scalar(value)}'"


def qe_scientific(value):
    """Render a real in compact QE/Fortran double-precision notation."""

    mantissa, exponent = f"{float(value):.1e}".split("e")
    return f"{mantissa}d{int(exponent)}"


def qe_relative_path(value):
    path = Path(str(value))
    rendered = path.as_posix()
    if not rendered.startswith("."):
        rendered = f"./{rendered}"
    return rendered


def require_mapping(mapping, key, context):
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{context}.{key} must be a mapping.")
    return value


def require_value(mapping, key, context):
    if key not in mapping or mapping[key] is None or mapping[key] == UNRESOLVED:
        raise ValueError(f"Missing locked configuration value: {context}.{key}")
    return mapping[key]


def format_coordinate(value):
    """Avoid printing ASE's signed zero in the QE cell/coordinates."""

    return f"{0.0 if abs(value) < 5.0e-12 else value:.8f}"


def cell_lines(atoms):
    lines = ["CELL_PARAMETERS angstrom"]
    lines.extend(
        "  " + "  ".join(format_coordinate(value) for value in vector)
        for vector in atoms.cell.array
    )
    return lines


def infer_vacancy_neighbors(pristine, monovacancy):
    """Return the three C indices nearest the geometrically missing lattice site."""

    if len(pristine) != len(monovacancy) + 1:
        raise ValueError("Vacancy inference requires pristine to contain exactly one more atom.")
    if not np.allclose(pristine.cell.array, monovacancy.cell.array, atol=1.0e-7):
        raise ValueError("Vacancy inference requires identical pristine/vacancy cells.")

    nearest_remaining = []
    for position in pristine.positions:
        vectors = monovacancy.positions - position
        _, distances = find_mic(vectors, pristine.cell, pbc=pristine.pbc)
        nearest_remaining.append(float(np.min(distances)))

    missing_index = int(np.argmax(nearest_remaining))
    missing_distance = nearest_remaining[missing_index]
    other_distances = np.delete(np.asarray(nearest_remaining), missing_index)
    if missing_distance < 1.0 or not np.allclose(other_distances, 0.0, atol=1.0e-6):
        raise ValueError(
            "Could not identify one missing pristine lattice site from the structures."
        )

    vacancy_position = pristine.positions[missing_index]
    vectors = monovacancy.positions - vacancy_position
    _, distances = find_mic(vectors, monovacancy.cell, pbc=monovacancy.pbc)
    ordered = np.argsort(distances)
    neighbor_indices = tuple(int(index) for index in ordered[:3])
    neighbor_distances = distances[list(neighbor_indices)]
    fourth_distance = float(distances[ordered[3]])

    if not np.allclose(neighbor_distances, neighbor_distances[0], atol=1.0e-6):
        raise ValueError("The three inferred vacancy neighbors are not equidistant.")
    if fourth_distance <= float(np.max(neighbor_distances)) + 0.25:
        raise ValueError("Vacancy-neighbor shell is not geometrically well separated.")

    return neighbor_indices, vacancy_position, tuple(float(x) for x in neighbor_distances)


def position_lines(atoms, vacancy_neighbor_indices=()):
    vacancy_neighbor_indices = set(vacancy_neighbor_indices)
    lines = ["ATOMIC_POSITIONS angstrom"]
    for index, position in enumerate(atoms.positions):
        label = QE_VACANCY_C_LABEL if index in vacancy_neighbor_indices else QE_BULK_C_LABEL
        lines.append(
            f"{label:<3} " + " ".join(format_coordinate(value) for value in position)
        )
    return lines


def k_point_lines(section, context):
    k_points = require_mapping(section, "k_points", context)
    mesh = require_value(k_points, "mesh", f"{context}.k_points")
    shift = require_value(k_points, "shift", f"{context}.k_points")
    if len(mesh) != 3 or len(shift) != 3:
        raise ValueError(f"{context}.k_points mesh and shift must have three entries.")

    return [
        "K_POINTS automatic",
        "  " + "  ".join(scalar(value) for value in (*mesh, *shift)),
    ]


def validate_locked_methodology(dft, relaxation):
    required_dft = (
        "software",
        "xc_functional",
        "ecutwfc_ry",
        "ecutrho_ry",
        "occupations",
        "smearing",
        "conv_thr",
        "mixing_beta",
        "assume_isolated",
    )
    for key in required_dft:
        require_value(dft, key, "dft")
    for key in ("calculation", "degauss_ry", "forc_conv_thr", "ion_dynamics"):
        require_value(relaxation, key, "relaxation")

    dispersion = require_mapping(dft, "dispersion", "dft")
    if (
        dispersion.get("method") != "D3"
        or dispersion.get("damping") != "BJ"
        or dispersion.get("qe_vdw_corr") != "dft-d3"
        or dispersion.get("qe_dftd3_version") != 4
    ):
        raise ValueError("Locked dispersion must be QE DFT-D3 with BJ damping (version 4).")
    if dft.get("xc_functional") != "PBE":
        raise ValueError("Locked exchange-correlation functional must be PBE.")
    if dft.get("assume_isolated") != "2D":
        raise ValueError("Locked slab electrostatics must use assume_isolated: 2D.")
    if relaxation.get("calculation") != "relax":
        raise ValueError("Only fixed-cell calculation='relax' is supported.")
    if relaxation.get("ion_dynamics") != "bfgs":
        raise ValueError("Locked ionic dynamics must be BFGS.")


def render_input(
    label,
    atoms,
    system,
    dft,
    relaxation,
    paths,
    pseudopotentials,
    vacancy_neighbor_indices=(),
):
    nspin = system.get("nspin")
    if nspin not in (1, 2):
        raise ValueError(f"{label}: nspin must be 1 or 2.")

    dispersion = dft["dispersion"]
    pseudo_files = require_mapping(pseudopotentials, "files", "pseudopotentials")
    carbon_pseudo = require_value(pseudo_files, "C", "pseudopotentials.files")
    is_vacancy = label == "monovacancy"
    if is_vacancy and len(vacancy_neighbor_indices) != 3:
        raise ValueError("Monovacancy input requires exactly three local magnetic seeds.")
    if not is_vacancy and vacancy_neighbor_indices:
        raise ValueError("Pristine input cannot contain vacancy-neighbor labels.")

    ntyp = 2 if is_vacancy else 1
    lines = [
        "! Production bare-substrate QE relaxation generated from an ASE structure.",
        f"! System: {label}",
        "! Method: PBE-D3(BJ); dftd3_version=4 selects Becke-Johnson damping.",
        f"! Pseudopotential family: {pseudopotentials['family']}",
    ]
    if is_vacancy:
        lines.append(
            "! C_v is the QE-valid (3-character) label for vacancy-adjacent C atoms."
        )
        lines.append("! Starting magnetizations are unconstrained initial seeds only.")

    lines.extend(
        [
            "",
            "&CONTROL",
            f"   calculation = {quoted(relaxation['calculation'])},",
            f"   prefix = {quoted(system['prefix'])},",
            f"   pseudo_dir = {quoted(qe_relative_path(paths['pseudo_dir']))},",
            f"   outdir = {quoted(qe_relative_path(Path(paths['scratch_root']) / label))},",
            "   tstress = .true.,",
            "   tprnfor = .true.,",
            f"   forc_conv_thr = {qe_scientific(relaxation['forc_conv_thr'])},",
            "/",
            "",
            "&SYSTEM",
            "   ibrav = 0,",
            f"   nat = {len(atoms)},",
            f"   ntyp = {ntyp},",
            f"   input_dft = {quoted(dft['xc_functional'])},",
            f"   vdw_corr = {quoted(dispersion['qe_vdw_corr'])},",
            f"   dftd3_version = {dispersion['qe_dftd3_version']},",
            f"   dftd3_threebody = {scalar(dispersion.get('threebody', True))},",
            f"   assume_isolated = {quoted(dft['assume_isolated'])},",
            f"   ecutwfc = {scalar(dft['ecutwfc_ry'])},",
            f"   ecutrho = {scalar(dft['ecutrho_ry'])},",
            f"   nspin = {nspin},",
            f"   occupations = {quoted(dft['occupations'])},",
            f"   smearing = {quoted(dft['smearing'])},",
            f"   degauss = {scalar(relaxation['degauss_ry'])},",
        ]
    )

    if is_vacancy:
        magnetization = require_mapping(system, "starting_magnetization", label)
        lines.extend(
            [
                f"   starting_magnetization(1) = {scalar(magnetization['bulk_C'])},",
                f"   starting_magnetization(2) = {scalar(magnetization['vacancy_neighbor_C'])},",
            ]
        )

    nbnd = dft.get("nbnd")
    if nbnd is not None:
        lines.append(f"   nbnd = {scalar(nbnd)},")

    lines.extend(
        [
            "/",
            "",
            "&ELECTRONS",
            f"   conv_thr = {qe_scientific(dft['conv_thr'])},",
            f"   mixing_beta = {scalar(dft['mixing_beta'])},",
            "/",
            "",
            "&IONS",
            f"   ion_dynamics = {quoted(relaxation['ion_dynamics'])},",
            "/",
            "",
            "ATOMIC_SPECIES",
            f"{QE_BULK_C_LABEL:<3} 12.011  {carbon_pseudo}",
        ]
    )
    if is_vacancy:
        lines.append(f"{QE_VACANCY_C_LABEL:<3} 12.011  {carbon_pseudo}")

    lines.extend(
        [
            "",
            *cell_lines(atoms),
            "",
            *position_lines(atoms, vacancy_neighbor_indices),
            "",
            *k_point_lines(relaxation, "relaxation"),
            "",
        ]
    )
    return "\n".join(lines)


def generate(config_path, output_root=None):
    config = load_config(config_path)
    paths = require_mapping(config, "paths", "config")
    pseudopotentials = require_mapping(config, "pseudopotentials", "config")
    dft = require_mapping(config, "dft", "config")
    relaxation = require_mapping(config, "relaxation", "config")
    systems = require_mapping(config, "systems", "config")
    validate_locked_methodology(dft, relaxation)

    input_root = repo_path(output_root) if output_root else repo_path(
        paths.get("input_root", "qe_inputs/relaxation")
    )
    generated = []

    for label in SYSTEM_NAMES:
        if label not in systems:
            raise ValueError(f"Missing system configuration: {label}")
        system = systems[label]
        atoms = read(repo_path(system["structure"]))
        validate_atoms(atoms, label)

        vacancy_neighbor_indices = ()
        if label == "monovacancy":
            pristine = read(repo_path(system["pristine_reference"]))
            validate_atoms(pristine, "pristine")
            vacancy_neighbor_indices, _, _ = infer_vacancy_neighbors(pristine, atoms)

        target_dir = input_root / label
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"relax_{label}.in"
        content = render_input(
            label,
            atoms,
            system,
            dft,
            relaxation,
            {
                "pseudo_dir": paths.get("pseudo_dir", "pseudopotentials"),
                "scratch_root": paths.get("scratch_root", "qe_scratch"),
            },
            pseudopotentials,
            vacancy_neighbor_indices,
        )
        if UNRESOLVED in content:
            raise ValueError(f"{label}: generated input contains {UNRESOLVED}.")
        target.write_text(content, encoding="utf-8")
        generated.append(target)

    return generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config/qe.yaml",
        help="YAML configuration file.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Optional override for the generated input root.",
    )
    args = parser.parse_args()

    try:
        generated = generate(args.config, args.output_root)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))

    for path in generated:
        try:
            display_path = path.relative_to(ROOT)
        except ValueError:
            display_path = path
        print(f"Generated {display_path}")
        print(f"  unresolved placeholders: {path.read_text(encoding='utf-8').count(UNRESOLVED)}")
    print("No pw.x calculation was run.")


if __name__ == "__main__":
    main()
