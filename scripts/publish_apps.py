#!/usr/bin/env python3
"""Publish APKs with app-specific tags; keep numeric releases for modules."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

APK = re.compile(r"^(.+)-v(\d[^/]*)-(all|arm64-v8a|arm-v7a|x86_64|x86)\.apk$")


def identify(name):
    match = APK.fullmatch(name)
    return (match[1], match[2]) if match else None


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def publish(directory, repo):
    groups = {}
    for apk in sorted(Path(directory).glob("*.apk")):
        key = identify(apk.name)
        if key is None:
            raise ValueError(f"Unexpected APK name: {apk.name}")
        groups.setdefault(key, []).append(apk)
    existing = {r["tagName"] for r in json.loads(gh(
        "release", "list", "--repo", repo, "--limit", "1000", "--json", "tagName"
    ))}
    for (app, version), files in groups.items():
        tag = f"{app}-v{version}"
        if tag in existing:
            assets = json.loads(gh("release", "view", tag, "--repo", repo,
                                   "--json", "assets"))["assets"]
            names = {a["name"] for a in assets}
            missing = [str(p) for p in files if p.name not in names]
            if missing:
                gh("release", "upload", tag, *missing, "--repo", repo)
        else:
            gh("release", "create", tag, *(str(p) for p in files),
               "--repo", repo, "--title", f"{app} {version}", "--latest=false",
               "--notes", f"{app} {version}\n\nAPK release for Obtainium. "
               "The tag contains the application version, not the module build number.")


def backfill(directory, repo):
    # Read all pages: a slowly changing app can be absent from many recent builds.
    pages = json.loads(gh("api", "--paginate", "--slurp",
                          f"repos/{repo}/releases?per_page=100"))
    releases = [r for page in pages for r in page
                if r["tag_name"].isdigit() and not r["draft"] and not r["prerelease"]]
    releases.sort(key=lambda r: int(r["tag_name"]), reverse=True)
    selected = {}
    for release in releases:
        for asset in release["assets"]:
            key = identify(asset["name"])
            if key is None:
                continue
            app, version = key
            selected.setdefault(app, (version, release["tag_name"]))
            if selected[app] == (version, release["tag_name"]):
                gh("release", "download", release["tag_name"], "--repo", repo,
                   "--pattern", asset["name"], "--dir", str(directory))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="build")
    parser.add_argument("--backfill", action="store_true")
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    if args.backfill:
        with tempfile.TemporaryDirectory() as directory:
            backfill(directory, repo)
            publish(directory, repo)
    else:
        publish(args.directory, repo)


if __name__ == "__main__":
    main()
