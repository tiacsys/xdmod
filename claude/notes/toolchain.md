# Toolchain notes

Tools are installed into the workspace venv `/home/tobias/z/wrk/ws-syseng/.venv`.
Tools that pip can't install live under `.venv/opt/<tool>/`, with a link in `.venv/bin/`.
Each repo also lists the tools it needs (`requirements.txt`, `tools.yaml`).

| Tool | Version | Source | Location | Needed by | Installed |
|---|---|---|---|---|---|
| drawio desktop | 31.7.0 | system package `drawio-desktop` (pacman) | `/usr/bin/drawio` | robarm-syseng (views), people | already installed (D97) |
| GitHub CLI (`gh`) | 2.103.3 | https://github.com/cli/cli/releases/tag/v2.103.3 (linux_amd64 tarball, sha256 checked against `gh_2.103.3_checksums.txt`) | `.venv/opt/gh`, link `.venv/bin/gh` | robarm-manifest (workspace setup, bump bot), all repos (PRs) | 2026-11-14 |

Notes:
- We chose 2.103.3 rather than 2.104.0, because 2.104.0 was only 2 days old.

## Resource limits (D71)

Run every tool through `.venv/bin/xd-limit [-m MEM] [-t TIME] -- CMD ...`.
It starts a systemd user scope with `MemoryMax=MEM` and `MemorySwapMax=0`, then runs `timeout --kill-after=10s TIME CMD`.
Exit codes: 124 = timeout, 137 = killed (usually out of memory). Tested 2026-11-14: a 1 GiB allocation under `-m 256M` was killed (137), and `sleep 10` under `-t 2` timed out (124).

Starting values (the machine has 16 cores and 29 GiB RAM; several agents may run at once):

| Use | Memory | Timeout |
|---|---|---|
| Docs build (zdocs/Sphinx) | 4G | 15m |
| SysML Pilot via jshell (also pass `-J-Xmx3g`) | 4G | 10m |
| kicad-cli export/ERC | 2G | 5m |
| FreeCADCmd export / offscreen GUI | 4G | 10m |
| Headless Firefox SVG export | 2G | 5m |
| west build (firmware) | 4G | 20m |
| Test suites (pytest, twister on host) | 4G | 30m |
| Small scripts, extractors, needs-diff | 1G | 5m |

## Inventory (task 4.1, 2026-11-15)

**System packages (pacman, CachyOS — rolling; curatrix doctor checks versions, 4.4b):**

| Tool | Version | Used by |
|---|---|---|
| KiCad (`kicad-cli`) | 10.0.8 | robarm-ee |
| FreeCAD (`freecad`, `freecadcmd`) | 1.1.4 (rev 45040) | robarm-me |
| drawio desktop | 31.7.0 | views (D97) |
| graphviz | 16.1.1 | needflow (D95) |
| Doxygen | 1.18.0 (≥ 1.16: native `\satisfies`/`\verifies`) | robarm-sw API docs |
| CMake / Ninja | 4.5.0 / 1.13.2 | zdocs, Zephyr |
| OpenOCD | 0.12.0 | HIL flashing (Phase 6) |
| dtc | 1.8.1 | devicetree |
| Firefox | 160.0 | headless SVG render of views |
| Node.js | 26.13.1 | elkjs layout |
| Python | 3.14.10 | everything |

**Workspace `.venv` (and `.venv/opt`):**

| Tool | Version | Location |
|---|---|---|
| west | 1.4.0 | `.venv/bin/west` |
| sphinx / sphinx-needs / sphinx-test-reports | 9.1.0 / 9.2.0 / 4.0.0 | `.venv` |
| JDK | 21.0.13 | `.venv/opt/jdk` |
| SysML v2 Pilot | 0.63.1 | `.venv/opt/sysml-pilot` |
| drawio viewer (static) | pinned by the spike | `.venv/opt/drawio-viewer` |
| elkjs, puppeteer-core | pinned by the spike | `.venv/opt/node` |
| gh | 2.103.3 | `.venv/opt/gh` |
| **Zephyr SDK** | **1.0.1, ARM only (D138)**: minimal bundle + `toolchain_gnu_linux-x86_64_arm-zephyr-eabi`, sha256 checked against the release's `sha256.sum`; `arm-zephyr-eabi-gcc` 14.3.0; 826 MB; no `setup.sh` run (no CMake package registration in `~`), use `ZEPHYR_SDK_INSTALL_DIR` | `.venv/opt/zephyr-sdk-1.0.1`, link `.venv/opt/zephyr-sdk` |

**Not installed (not needed in Phase 4):** git-lfs, xvfb-run, pyocd, STM32CubeProgrammer, LaTeX (PDF set is iteration 2).
