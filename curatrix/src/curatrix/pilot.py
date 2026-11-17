"""The OMG SysML v2 Pilot Implementation through jshell (D65; spike sysml_check.py).

jshell's exit code is not reliable (System.exit only ends the remote engine; a failing
statement drops into the prompt), so stdin is /dev/null and the result is a marker line
``SYSML-RESULT errors=N`` that we parse.
"""
from __future__ import annotations

import json
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from curatrix import limits
from curatrix.ws import Workspace

PILOT_VERSION = "0.63.1"


@dataclass
class PilotResult:
    ok: bool
    errors: int
    log: str
    seconds: float
    files: dict[str, str]          # file -> "ok" | "ERRORS"


def _jstr(s) -> str:
    return json.dumps(str(s))      # a JSON string literal is a valid Java string literal here


def paths(ws: Workspace) -> tuple[Path, Path, Path]:
    jshell = ws.opt / "jdk" / "bin" / "jshell"
    pilot = ws.opt / "sysml-pilot"
    jar = next(iter(sorted(pilot.glob("jupyter-sysml-kernel-*-all.jar"))), pilot / f"jupyter-sysml-kernel-{PILOT_VERSION}-all.jar")
    return jshell, pilot, jar


LIBSET = "LIBRARY-SET"
MODELSET = "MODEL-SET"


def libset_map(libraries: list[Path]) -> list[tuple[int, int, Path]]:
    """(first line, last line, file) of each library file in the concatenated set (1-based)."""
    out, start = [], 1
    for f in libraries:
        n = Path(f).read_text().count("\n") + 1      # script() joins the files with one "\n"
        out.append((start, start + n - 1, Path(f).resolve()))
        start += n
    return out


def remap_libset(log: str, libraries: list[Path], label: str = LIBSET) -> str:
    """Rewrite `(N.sysml line : L ...)` in the issue block of the set `label` to `<file> line : l`."""
    if not libraries:
        return log
    spans = libset_map(libraries)

    def fix(m):
        line = int(m.group(1))
        for a, b, f in spans:
            if a <= line <= b:
                return f"({f} line : {line - a + 1}"
        return m.group(0)
    out, inside = [], False
    for ln in log.splitlines():
        if ln.startswith("FILE "):
            inside = ln.startswith(f"FILE {label} ")
        elif inside:
            ln = re.sub(r"\(\d+\.sysml line : (\d+)", fix, ln)
        out.append(ln)
    return "\n".join(out)


def _process_set(lines: list[str], var: str, files: list[Path], label: str):
    parts = ' + "\\n" + '.join(f"Files.readString(Path.of({_jstr(Path(f).resolve())}))" for f in files)
    names = ", ".join(Path(f).name for f in files)
    lines += [
        f"var {var} = si.process({parts});",
        f'System.out.println("FILE {label} [{names}]: " + ({var}.hasErrors() ? "ERRORS" : "ok"));',
        f"if (!{var}.formatIssues().isBlank()) System.out.println({var}.formatIssues());",
        f"if ({var}.hasErrors()) errs++;",
    ]


def script(files: list[Path], library: Path, export: list[str], out: Path | None,
           libraries: list[Path] | None = None, one_set: bool = False) -> str:
    """jshell script: the standard library, then `libraries` as ONE input (so library files may
    refer to each other, e.g. SYSMOD.sysml <-> SYSMOD15288.sysml), then `files`: each in order,
    or with `one_set` as one more input (so their order does not matter, XD-ADR-0130).
    An export result that starts with ``ERROR:`` (a package the Pilot cannot resolve) counts as
    an error and is printed, never written into the JSON."""
    lines = [
        "import org.omg.sysml.interactive.*;",
        "import java.nio.file.*;",
        "var si = SysMLInteractive.getInstance();",
        f"si.loadLibrary({_jstr(str(library) + '/')});",
        "int errs = 0;",
    ]
    if libraries:
        _process_set(lines, "rl", libraries, LIBSET)
    if one_set and files:
        _process_set(lines, "rm", files, MODELSET)
        files = []
    for i, f in enumerate(files):
        p = Path(f).resolve()
        lines += [
            f"var r{i} = si.process(Files.readString(Path.of({_jstr(p)})));",
            f'System.out.println("FILE {p}: " + (r{i}.hasErrors() ? "ERRORS" : "ok"));',
            f"if (!r{i}.formatIssues().isBlank()) System.out.println(r{i}.formatIssues());",
            f"if (r{i}.hasErrors()) errs++;",
        ]
    if out is not None and export:
        for i, pkg in enumerate(export):
            lines += [
                f"var ex{i} = errs == 0 ? String.valueOf(si.export({_jstr(pkg)}, java.util.List.of())) : \"[]\";",
                f'if (ex{i}.startsWith("ERROR:")) {{ System.out.println("EXPORT {pkg}: " + ex{i}); errs++; }}',
            ]
        parts = ' + "," + '.join(f'ex{i}.replaceAll("^\\\\[|\\\\]$", "")' for i in range(len(export)))
        lines.append(f'if (errs == 0) Files.writeString(Path.of({_jstr(Path(out).resolve())}), "[" + {parts} + "]");')
    lines.append('System.out.println("SYSML-RESULT errors=" + errs);')
    lines.append("/exit")
    return "\n".join(lines) + "\n"


def run(ws: Workspace, files: list[Path], export: list[str] | None = None, out: Path | None = None,
        tmpdir: Path | None = None, libraries: list[Path] | None = None, one_set: bool = False) -> PilotResult:
    """Parse and resolve `libraries` as one set, then `files` (in order, or as one set with
    `one_set`); optionally export packages to JSON. Issues inside a set are mapped back to file
    and line in the log."""
    jshell, pilot, jar = paths(ws)
    if not jshell.exists() or not jar.exists():
        raise FileNotFoundError(f"Pilot not installed ({jshell}, {jar}); run `curatrix update`")
    lim = limits.resolve("pilot", ws)
    heap = lim.java_heap or "3g"
    tmpdir = tmpdir or ws.build("curatrix") / "tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
    with tempfile.NamedTemporaryFile("w", suffix=".jsh", dir=tmpdir, delete=False) as t:
        t.write(script(files, pilot / "sysml.library", export or [], out, libraries, one_set))
    t0 = time.time()
    try:
        r = limits.run([str(jshell), "-J-Xmx1g", f"-R-Xmx{heap}", "-R-Xss4m", "--class-path", str(jar), t.name],
                       "pilot", ws, capture_output=True, text=True, stdin=__import__("subprocess").DEVNULL)
    finally:
        Path(t.name).unlink(missing_ok=True)
    raw = (r.stdout or "") + (r.stderr or "")
    log = "\n".join(line for line in raw.splitlines()
                    if not line.startswith(("Reading ", "log4j", "SLF4J", "|  ", "jshell>")))
    log = remap_libset(log, libraries or [])
    if one_set:
        log = remap_libset(log, files, MODELSET)
    m = re.search(r"SYSML-RESULT errors=(\d+)", raw)
    errors = int(m.group(1)) if m else -1
    files_status = dict(re.findall(r"^FILE (.+?): (ok|ERRORS)$", raw, re.M))
    if r.returncode in (124, 137):
        log += f"\n[curatrix] Pilot stopped: {limits.explain_rc(r.returncode)}"
    return PilotResult(ok=(errors == 0 and (out is None or not export or out.exists())), errors=errors,
                       log=log.strip(), seconds=time.time() - t0, files=files_status)
