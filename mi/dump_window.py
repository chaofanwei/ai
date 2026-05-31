#!/Users/weichaofan/miniconda3/envs/py3.11/bin/python
"""Dump the current Android UI hierarchy to a formatted XML file.

Example:
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python dump_window.py window3.xml
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import xml.dom.minidom as minidom
from pathlib import Path


DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
REMOTE_XML = "/sdcard/window.xml"


def run_adb(adb: str, args: list[str], timeout: int = 15, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    cmd = [adb, *args]
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and proc.returncode != 0:
        stdout = proc.stdout.decode("utf-8", "replace").strip()
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"adb {' '.join(args)} failed: {stderr or stdout}")
    return proc


def format_xml(xml_bytes: bytes) -> str:
    doc = minidom.parseString(xml_bytes)
    pretty = doc.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    lines = [line for line in pretty.splitlines() if line.strip()]
    return "\n".join(lines) + "\n"


def output_path(script_dir: Path, name: str) -> Path:
    path = Path(name)
    if path.name != name:
        raise ValueError("output name must be a file name only, not a path")
    if path.suffix.lower() != ".xml":
        path = path.with_suffix(".xml")
    return script_dir / path.name


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump and format the current Android UI hierarchy.")
    parser.add_argument("name", help="Output XML file name under this script directory, e.g. window3.xml")
    parser.add_argument("--adb", default=DEFAULT_ADB)
    args = parser.parse_args()

    adb = Path(args.adb)
    if not adb.exists():
        raise FileNotFoundError(adb)

    script_dir = Path(__file__).resolve().parent
    target = output_path(script_dir, args.name)

    dump = run_adb(str(adb), ["shell", "uiautomator", "dump", REMOTE_XML], timeout=15, check=False)
    dump_text = dump.stdout + dump.stderr
    if dump.returncode != 0 and b"UI hierchary dumped to:" not in dump_text:
        stdout = dump.stdout.decode("utf-8", "replace").strip()
        stderr = dump.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"uiautomator dump failed: {stderr or stdout}")

    xml = run_adb(str(adb), ["exec-out", "cat", REMOTE_XML], timeout=15).stdout
    target.write_text(format_xml(xml), encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
