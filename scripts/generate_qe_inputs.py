#!/usr/bin/env python3
"""Generate bare-substrate Quantum ESPRESSO relaxation templates."""

import argparse
from pathlib import Path

from ase.io import read

from validate_structures import validate_atoms


ROOT = Path(__file__).resolve().parents[1]
UNRESOLVED = "__QE_UNRESOLVED__"
SYSTEM_NAMES = ("pristine", "monovacancy")


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
    """Render a scalar without hiding unresolved configuration."""

    if value is None:
        return UNRESOLVED
    if isinstance(value, bool):
        return ".true." if value else ".false."
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def quoted(value):
    return f"'{scalar(value)}'"


def qe_relative_path(value):
    path = Path(str(value))
    rendered = path.as_posix()
    if not rendered.startswith("."):
        rendered = f"./{rendered}"
    return rendered


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


def position_lines(atoms):
    lines = ["ATOMIC_POSITIONS angstrom"]
    for symbol, position in zip(atoms.get_chemical_symbols(), atoms.positions):
        lines.append(
            f"{symbol:<2} " + " ".join(format_coordinate(value) for value in position)
        )
    return lines


def k_point_lines(dft):
    k_points = dft.get("k_points", {})
    mesh = k_points.get("mesh", [UNRESOLVED] * 3)
    shift = k_points.get("shift", [UNRESOLVED] * 3)
    if len(mesh) != 3 or len(shift) != 3:
        raise ValueError("k_points.mesh and k_points.shift must have three entries.")

    return [
        "K_POINTS automatic",
        "  " + "  ".join(scalar(value) for value in (*mesh, *shift)),
    ]


def render_input(label, atoms, system, dft, paths):
    calculation = dft.get("calculation", "relax")
    if calculation != "relax":
        raise ValueError(
            f"{label}: calculation must be 'relax'; vc-relax is intentionally unsupported."
        )

    nspin = system.get("nspin")
    if nspin not in (1, 2):
        raise ValueError(f"{label}: nspin must be 1 or 2.")

    pseudo = dft.get("pseudopotentials", {}).get("C", UNRESOLVED)
    lines = [
        "! Bare-substrate QE relaxation template generated from an ASE structure.",
        f"! System: {label}",
        "! Replace every __QE_UNRESOLVED__ value before running pw.x.",
        f"! pseudopotential_family = {scalar(dft.get('pseudopotential_family'))}",
        "",
        "&CONTROL",
        f"   calculation = {quoted(calculation)},",
        f"   prefix = {quoted(system['prefix'])},",
        f"   pseudo_dir = {quoted(qe_relative_path(paths['pseudo_dir']))},",
        f"   outdir = {quoted(qe_relative_path(Path(paths['scratch_root']) / label))},",
        "   tstress = .true.,",
        "   tprnfor = .true.,",
        f"   forc_conv_thr = {scalar(dft.get('forc_conv_thr'))},",
        "/",
        "",
        "&SYSTEM",
        "   ibrav = 0,",
        f"   nat = {len(atoms)},",
        "   ntyp = 1,",
        f"   input_dft = {quoted(dft.get('exchange_correlation'))},",
        f"   ecutwfc = {scalar(dft.get('ecutwfc_ry'))},",
        f"   ecutrho = {scalar(dft.get('ecutrho_ry'))},",
        f"   nspin = {nspin},",
        f"   occupations = {quoted(dft.get('occupations'))},",
    ]

    if nspin == 2:
        lines.append(
            f"   starting_magnetization(1) = "
            f"{scalar(system.get('starting_magnetization'))},"
        )

    for key, config_key in (("smearing", "smearing"), ("degauss", "degauss_ry")):
        value = dft.get(config_key)
        if value is not None:
            lines.append(f"   {key} = {quoted(value) if key == 'smearing' else scalar(value)},")
        else:
            lines.append(f"   ! {key} omitted; set it if required by occupations.")

    nbnd = dft.get("nbnd")
    if nbnd is not None:
        lines.append(f"   nbnd = {scalar(nbnd)},")

    lines.extend(
        [
            "/",
            "",
            "&ELECTRONS",
            f"   conv_thr = {scalar(dft.get('conv_thr'))},",
            f"   mixing_beta = {scalar(dft.get('mixing_beta'))},",
        ]
    )

    lines.extend(
        [
            "/",
            "",
            "ATOMIC_SPECIES",
            f"C  12.011  {pseudo}",
            "",
            *cell_lines(atoms),
            "",
            *position_lines(atoms),
            "",
            *k_point_lines(dft),
            "",
        ]
    )
    return "\n".join(lines)


def generate(config_path, output_root=None):
    config = load_config(config_path)
    dft = config.get("dft", {})
    paths = config.get("paths", {})
    systems = config.get("systems", {})

    input_root = repo_path(output_root) if output_root else repo_path(
        paths.get("input_root", "qe_inputs/relaxation")
    )
    generated = []

    for label in SYSTEM_NAMES:
        if label not in systems:
            raise ValueError(f"Missing system configuration: {label}")
        system = systems[label]
        structure_path = repo_path(system["structure"])
        atoms = read(structure_path)
        validate_atoms(atoms, label)

        target_dir = input_root / label
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"relax_{label}.in"
        content = render_input(
            label,
            atoms,
            system,
            dft,
            {
                "pseudo_dir": paths.get("pseudo_dir", "pseudopotentials"),
                "scratch_root": paths.get("scratch_root", "qe_scratch"),
            },
        )
        target.write_text(content, encoding="utf-8")
        generated.append(target)

    return generated


def main():
    parser = argparse.ArgumentParser(
        description="Generate pristine and monovacancy QE relaxation templates."
    )
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
