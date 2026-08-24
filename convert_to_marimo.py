"""Convert a Jupyter notebook into a marimo notebook.

Usage:
    python convert_to_marimo.py [input.ipynb] [-o output.py]

Defaults to converting ``data_gen.ipynb`` into ``data_gen_marimo.py``.

marimo ships with its own converter (``marimo convert``); this script simply
locates the marimo executable, runs it, and writes the result to disk.
Install marimo first if needed:  pip install marimo
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def convert(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input notebook not found: {input_path}")

    marimo = shutil.which("marimo")
    if marimo is None:
        raise RuntimeError(
            "marimo is not installed. Install it with:\n    pip install marimo"
        )

    # `marimo convert` prints the generated marimo script to stdout.
    result = subprocess.run(
        [marimo, "convert", str(input_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    output_path.write_text(result.stdout, encoding="utf-8")
    print(f"Wrote marimo notebook to {output_path}")
    print(f"Open it with:  marimo edit {output_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default="data_gen.ipynb",
        help="Path to the .ipynb file to convert (default: data_gen.ipynb)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output .py path (default: <input stem>_marimo.py)",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = (
        Path(args.output)
        if args.output
        else input_path.with_name(f"{input_path.stem}_marimo.py")
    )

    try:
        convert(input_path, output_path)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
