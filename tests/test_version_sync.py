"""Fail if the add-on's version locations have drifted apart.

Six places record the version and they all have to agree:

    package/app.manifest                   info.id.version  <- source of truth
    globalConfig.json                      meta.version
    package/default/app.conf               [launcher] version
    package/default/app.conf               [id] version
    package/bin/ai_governance/__init__.py  _FALLBACK_VERSION
    CHANGELOG.md                           newest "## [x.y.z]" heading

app.manifest is the source of truth because org CI reads it with
``jq -r '.info.id.version'`` and hands the result to ``ucc-gen build
--ta-version`` - it is the version the built package carries.

Runs two ways, so it needs no third-party imports:

    pytest tests/
    python3 tests/test_version_sync.py    # how the pre-commit hook calls it

Org CI runs ``pre-commit run --all-files`` on every pull request, so the hook
is the gate; nothing here may depend on anything outside the standard library.
"""

import ast
import configparser
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_MANIFEST = os.path.join(REPO_ROOT, "package", "app.manifest")
GLOBAL_CONFIG = os.path.join(REPO_ROOT, "globalConfig.json")
APP_CONF = os.path.join(REPO_ROOT, "package", "default", "app.conf")
CONSTANTS = os.path.join(REPO_ROOT, "package", "bin", "ai_governance", "__init__.py")
CHANGELOG = os.path.join(REPO_ROOT, "CHANGELOG.md")

CHANGELOG_HEADING = re.compile(r"^##\s*\[(\d+\.\d+\.\d+)\]")


def _manifest_version():
    with open(APP_MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)["info"]["id"]["version"]


def _global_config_version():
    with open(GLOBAL_CONFIG, encoding="utf-8") as handle:
        return json.load(handle)["meta"]["version"]


def _app_conf_versions():
    parser = configparser.ConfigParser(interpolation=None)
    with open(APP_CONF, encoding="utf-8") as handle:
        parser.read_file(handle)
    return parser["launcher"]["version"], parser["id"]["version"]


def _fallback_version():
    """Read _FALLBACK_VERSION out of the constants module without importing it.

    Importing would resolve ADDON_VERSION from app.manifest and mask the very
    drift this is looking for.
    """
    with open(CONSTANTS, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=CONSTANTS)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_FALLBACK_VERSION":
                return ast.literal_eval(node.value)
    raise AssertionError(f"no _FALLBACK_VERSION assignment in {CONSTANTS}")


def _changelog_version():
    with open(CHANGELOG, encoding="utf-8") as handle:
        for line in handle:
            match = CHANGELOG_HEADING.match(line)
            if match:
                return match.group(1)
    raise AssertionError(f"no '## [x.y.z]' release heading in {CHANGELOG}")


def test_version_locations_agree():
    expected = _manifest_version()
    launcher_version, id_version = _app_conf_versions()
    found = {
        "globalConfig.json meta.version": _global_config_version(),
        "package/default/app.conf [launcher] version": launcher_version,
        "package/default/app.conf [id] version": id_version,
        "package/bin/ai_governance/__init__.py _FALLBACK_VERSION": _fallback_version(),
        "CHANGELOG.md newest release heading": _changelog_version(),
    }
    drifted = [
        f"{where} = {value}"
        for where, value in sorted(found.items())
        if value != expected
    ]
    assert not drifted, "package/app.manifest says {}, but {}".format(
        expected,
        "; ".join(drifted),
    )


def test_addon_version_matches_manifest():
    """ADDON_VERSION must resolve from the manifest, not from the fallback."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "package", "bin"))
    try:
        from ai_governance import ADDON_VERSION
    finally:
        sys.path.pop(0)
    assert ADDON_VERSION == _manifest_version()


CHECKS = (test_version_locations_agree, test_addon_version_matches_manifest)


def _main():
    failures = 0
    for check in CHECKS:
        try:
            check()
        except AssertionError as exc:
            print(f"{check.__name__}: {exc}", file=sys.stderr)
            failures += 1
    if failures:
        return 1
    print(f"version sync OK: {_manifest_version()}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
