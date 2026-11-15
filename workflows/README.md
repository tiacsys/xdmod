# Workflows

GitHub runs reusable workflows only from `.github/workflows/`, so xdmod's reusable workflow lives in
`../.github/workflows/curatrix-check.yml`. This folder holds the templates that each repo copies
into its own `.github/workflows/` (thin callers, `repo-layouts.md` §1):

| Template | Calls | Does |
|---|---|---|
| `check.yml` | `curatrix-check.yml` | `curatrix check <repo> --stage pr --no-cad` in a workspace built from the manifest's `main` with sibling resolution (D127); uploads `build/*/checks/` and the HTML docs |

First version (task 4.8). Later: PR comments with the summary, caching of the venv, the bump bot
and the full-set build in robarm-manifest, required checks in the org ruleset.
