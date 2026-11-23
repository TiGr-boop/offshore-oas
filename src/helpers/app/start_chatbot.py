import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
app_path = project_root / "src" / "helpers" / "app" / "chainlit.py"


def start_chainlit():
    subprocess.run(
        [
            sys.executable,
            "-m",
            "chainlit",
            "run",
            str(app_path),
            "--port",
            "8000",
        ],
        cwd=project_root,
        check=True,
    )
