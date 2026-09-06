# Pseudopotentials

Download the following files from the official SSSP Efficiency PBE library on
Materials Cloud and place them directly in this directory:

| Element | Expected filename | Current phase |
| --- | --- | --- |
| C | `C.pbe-n-kjpaw_psl.1.0.0.UPF` | Required |
| Li | `li_pbe_v1.4.uspp.F.UPF` | Not required for current phase |
| Na | `na_pbe_v1.5.uspp.F.UPF` | Not required for current phase |

Official source: https://www.materialscloud.org/discover/sssp/table/efficiency

Pseudopotential contents are intentionally not committed to this repository.
Use the archive-provided checksums or metadata to verify downloads. Never
rename an unrelated UPF file to satisfy the expected filename.

Check local availability with:

```bash
python scripts/check_pseudopotentials.py
```

Only carbon is required for the present pristine and monovacancy substrate
relaxations. Li and Na become required in the later adsorption stage.
