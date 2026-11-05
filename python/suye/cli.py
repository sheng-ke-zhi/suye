import argparse
import os
import shutil

from . import __version__


TOOLS = ("git", "python3", "cargo", "rustc")


def doctor():
    missing = False
    for tool in TOOLS:
        available = shutil.which(tool, path=os.environ.get("PATH", "")) is not None
        print(f"[{'OK' if available else 'MISSING'}] {tool}")
        missing |= not available
    if missing:
        print("Make missing tools executable and available on PATH, then rerun suye doctor.")
    return int(missing)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="suye", description="Read-only development toolchain diagnostics."
    )
    parser.add_argument("--version", action="version", version=f"suye {__version__}")
    parser.add_argument("command", choices=("doctor",))
    parser.parse_args(argv)
    return doctor()
