# XDMOD — Cross-Domain MODeling

XDMOD is a method and toolset for model-based systems engineering across domains (systems, software,
electrical, mechanical, integration), with traceability from stakeholder needs to verification
evidence. It is used through a west workspace that has this repo as a project (D66). The robot arm
(`robarm-*` repos) is its worked example.

| Folder | What |
|---|---|
| `curatrix/` | the workspace command layer and checker, `curatrix` ([README](curatrix/README.md)) |
| `needs/needs_config.toml` | need types, link types per owning type, fields, schema rules (shared by every document) |
| `sysml/` | SysML v2 library: trace metadata (`NeedRef`, `Trace`), view metadata (`XdView`) |
| `sphinx/` | Sphinx extensions (`xdmod_sphinx`: `sysml-view`, CAD directives, `xd-needimport`, `tracechain`) and the conf helper `xdmod_conf.py` |
| `cmake/xdmod-docs.cmake` | shared zdocs consumer block for `<repo>/docs/CMakeLists.txt` |
| `templates/bootstrap.sh` | workspace bootstrap; copied into the manifest repo as `scripts/bootstrap.sh` (D118) |
| `launch/CLAUDE.md` | workspace rules for agents; copied to the workspace root by the bootstrap (D69) |
| `workflows/` | caller templates for the reusable workflow in `.github/workflows/curatrix-check.yml` |
| `tools.yaml`, `requirements.txt` | pinned tools and pip packages for xdmod's tooling and every doc build (D19) |
| `checks.yaml`, `ids.yaml` | xdmod's own checks and ID ledger (`XD-ADR`, `XD-RULE`, `XD-CHECK`) |

Quick start (in a workspace whose manifest lists xdmod):

```sh
robarm-manifest/scripts/bootstrap.sh --role ee      # .venv, west, curatrix, then `curatrix bootstrap`
curatrix doctor
curatrix check robarm-ee --stage local
```

Licence: Apache-2.0.
