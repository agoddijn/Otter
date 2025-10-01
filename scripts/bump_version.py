#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path

import semver


def get_version_from_pyproject(pyproject_path: Path) -> str:
    with open(pyproject_path) as f:
        content = f.read()
        match = re.search(r'\[project\].*?version\s*=\s*"([^"]+)"', content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not find version in {pyproject_path}")
        return match.group(1)


def update_version_in_pyproject(pyproject_path: Path, new_version: str) -> None:
    with open(pyproject_path) as f:
        content = f.read()

    new_content = re.sub(
        r'(\[project\].*?)version\s*=\s*"[^"]+"', f'\\1version = "{new_version}"', content, flags=re.DOTALL
    )

    with open(pyproject_path, "w") as f:
        f.write(new_content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump versions in both tool service packages")
    parser.add_argument(
        "bump_type", choices=["patch", "minor", "major", "prerelease"], help="Type of version bump to perform"
    )
    args = parser.parse_args()

    # Get paths to both pyproject.toml files
    project_toml = Path("pyproject.toml")

    if not project_toml.exists():
        print("Error: Could not find pyproject.toml file")
        sys.exit(1)

    # Get current versions
    current_version = get_version_from_pyproject(project_toml)

    # Bump the version
    new_version = semver.VersionInfo.parse(current_version).next_version(args.bump_type)
    print(f"Bumping version from {current_version} to {new_version}")

    # Update both pyproject.toml files
    update_version_in_pyproject(project_toml, str(new_version))
    print(f"Updated version in pyproject.toml to {new_version}")


if __name__ == "__main__":
    main()
