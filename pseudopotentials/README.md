# Pseudopotentials

Download the following files from the official SSSP Efficiency PBE library on
Materials Cloud and place them directly in this directory:

| Element | Expected filename | Current phase |
| --- | --- | --- |
| C | `C.pbe-n-kjpaw_psl.1.0.0.UPF` | Required |
| Li | `li_pbe_v1.4.uspp.F.UPF` | Installed and audited for adsorption |
| Na | `na_pbe_v1.5.uspp.F.UPF` | Installed and audited for adsorption; no Na run launched yet |

Official source: https://www.materialscloud.org/discover/sssp/table/efficiency

Pseudopotential contents are intentionally not committed to this repository.
Use the archive-provided checksums or metadata to verify downloads. Never
rename an unrelated UPF file to satisfy the expected filename.

Check local availability with:

```bash
python scripts/check_pseudopotentials.py --require C Li Na
```

The local Na file was extracted without renaming from the official
[SSSP 1.0 PBE efficiency archive](https://archive.materialscloud.org/records/1dygy-1xb93).
The archive MD5 is `0fc1ac970ab91c2b58aedccd3adb9699`; the extracted
`na_pbe_v1.5.uspp.F.UPF` MD5 is
`44600605ef58000f06b90626533354dc` (local SHA-256
`f84820c4280d21603bd50ae76a08e15c26864391ea055cf50affc4aedefc8f87`).
The UPF identifies Na, PBE, an ultrasoft pseudopotential, nonlinear-core
correction, and nine valence electrons (2s2 2p6 3s1). The SSSP **library
metadata**, not the UPF's legacy 0/0 header placeholders, recommends
40/320 Ry for Na. The project's 65/520 Ry choice is above that recommendation,
but adsorbate-containing numerical convergence remains unverified.

The UPF binaries remain local and excluded from GitHub. Before launching a Na
calculation, the run preflight must recheck the exact Na MD5 and all configured
C/Na species mappings; merely finding the file is insufficient.
