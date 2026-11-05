import argparse
import ast
import configparser
from pathlib import Path
import re
import tomllib


def check(root, tag=None, publish=False):
    configuration = configparser.ConfigParser()
    configuration.read(root / "setup.cfg", encoding="utf-8")
    python_version = configuration["metadata"]["version"]
    manifest = tomllib.loads((root / "Cargo.toml").read_text(encoding="utf-8"))
    package = manifest["package"]
    module = ast.parse((root / "python/suye/__init__.py").read_text(encoding="utf-8"))
    versions = [
        ast.literal_eval(statement.value)
        for statement in module.body
        if isinstance(statement, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__" for target in statement.targets)
    ]
    if versions != [python_version] or package["version"] != python_version:
        raise ValueError("Versions in setup.cfg, Cargo.toml and suye.__version__ must match.")
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", python_version):
        raise ValueError("This workflow supports stable MAJOR.MINOR.PATCH versions only.")
    if tag is not None and tag != f"v{python_version}":
        raise ValueError("The release tag must be v followed by the package version.")
    if publish:
        if tag is None:
            raise ValueError("Publishing requires an explicit version tag.")
        license_name = configuration["metadata"].get("license", "").strip()
        license_file = root / "LICENSE"
        if not license_name or package.get("license") != license_name:
            raise ValueError("Set the same user-approved SPDX license expression in setup.cfg and Cargo.toml.")
        if not license_file.is_file() or not license_file.read_text(encoding="utf-8").strip():
            raise ValueError("Add the user-approved license text in LICENSE.")
        if package.get("publish") != ["crates-io"]:
            raise ValueError('After approval, set Cargo.toml publish = ["crates-io"].')
    return python_version


def main():
    parser = argparse.ArgumentParser(description="Validate SUYE versions and publishing prerequisites.")
    parser.add_argument("--tag")
    parser.add_argument("--publish", action="store_true")
    arguments = parser.parse_args()
    try:
        version = check(Path(__file__).resolve().parents[1], arguments.tag, arguments.publish)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(f"Release metadata validated: {version}")


if __name__ == "__main__":
    main()
