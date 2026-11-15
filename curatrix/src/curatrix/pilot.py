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


def script(files: list[Path], library: Path, export: list[str], out: Path | None) -> str:
    lines = [
        "import org.omg.sysml.interactive.*;",
        "import java.nio.file.*;",
        "var si = SysMLInteractive.getInstance();",
        f"si.loadLibrary({_jstr(str(library) + '/')});",
        "int errs = 0;",
    ]
    for i, f in enumerate(files):
        p = Path(f).resolve()
        lines += [
            f"var r{i} = si.process(Files.readString(Path.of({_jstr(p)})));",
            f'System.out.println("FILE {p}: " + (r{i}.hasErrors() ? "ERRORS" : "ok"));',
            f"if (!r{i}.formatIssues().isBlank()) System.out.println(r{i}.formatIssues());",
            f"if (r{i}.hasErrors()) errs++;",
        ]
    if out is not None and export:
        parts = ' + "," + '.join(
            f'String.valueOf(si.export({_jstr(pkg)}, java.util.List.of())).replaceAll("^\\\\[|\\\\]$", "")'
            for pkg in export)
        lines.append(f'if (errs == 0) Files.writeString(Path.of({_jstr(Path(out).resolve())}), "[" + {parts} + "]");')
    lines.append('System.out.println("SYSML-RESULT errors=" + errs);')
    lines.append("/exit")
    return "\n".join(lines) + "\n"


def run(ws: Workspace, files: list[Path], export: list[str] | None = None, out: Path | None = None,
        tmpdir: Path | None = None) -> PilotResult:
    """Parse and resolve `files` in order (libraries first); optionally export packages to JSON."""
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
        t.write(script(files, pilot / "sysml.library", export or [], out))
    t0 = time.time()
    try:
        r = limits.run([str(jshell), "-J-Xmx1g", f"-R-Xmx{heap}", "-R-Xss4m", "--class-path", str(jar), t.name],
                       "pilot", ws, capture_output=True, text=True, stdin=__import__("subprocess").DEVNULL)
    finally:
        Path(t.name).unlink(missing_ok=True)
    raw = (r.stdout or "") + (r.stderr or "")
    log = "\n".join(line for line in raw.splitlines()
                    if not line.startswith(("Reading ", "log4j", "SLF4J", "|  ", "jshell>")))
    m = re.search(r"SYSML-RESULT errors=(\d+)", raw)
    errors = int(m.group(1)) if m else -1
    files_status = dict(re.findall(r"^FILE (.+?): (ok|ERRORS)$", raw, re.M))
    if r.returncode in (124, 137):
        log += f"\n[curatrix] Pilot stopped: {limits.explain_rc(r.returncode)}"
    return PilotResult(ok=(errors == 0 and (out is None or not export or out.exists())), errors=errors,
                       log=log.strip(), seconds=time.time() - t0, files=files_status)
