"""Small helpers for the curatrix tests."""
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def git_init(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    return path


def make_ws(tmp: Path, monkeypatch=None) -> Path:
    """A fake workspace root (no west): <tmp>/ws with .venv/bin and an xdmod link."""
    ws = tmp / "ws"
    (ws / ".venv" / "bin").mkdir(parents=True)
    import sys
    (ws / ".venv" / "bin" / "python").symlink_to(sys.executable)
    (ws / "build").mkdir()
    # No xdmod folder in the fake workspace: curatrix falls back to the real xdmod for its data
    # (sysml/, launch/, templates/) but must never treat the real clone as a workspace repo
    # (hooks, git config, .claude links would leak into it).
    if monkeypatch is not None:
        monkeypatch.setenv("XD_WORKSPACE", str(ws))
    return ws
