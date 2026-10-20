#!/usr/bin/env python3
"""Publish APKs with app-specific tags; keep numeric releases for modules."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
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
        display_name = "GooglePhotos" if app == "googlephotos-devanced" else app
        tag = version if app == "googlephotos-devanced" else f"{app}-v{version}"
        if tag in existing:
            assets = json.loads(gh("release", "view", tag, "--repo", repo,
                                   "--json", "assets"))["assets"]
            names = {a["name"] for a in assets}
            if app == "googlephotos-devanced":
                gh("release", "edit", tag, "--repo", repo, "--notes",
                   f"GooglePhotos: {version}\n\nOriginal signed Google Photos APK. Version tag matches the app version.")
            missing = [str(p) for p in files if p.name not in names]
            if missing:
                gh("release", "upload", tag, *missing, "--repo", repo)
        else:
            gh("release", "create", tag, *(str(p) for p in files),
               "--repo", repo, "--title", f"{app} {version}", "--latest=false",
               "--notes", f"{display_name}: {version}\n\nAPK release for Obtainium. "
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


def app_notes(directory):
    labels = {"googlephotos-devanced": "GooglePhotos", "youtube-morphe": "YouTube-Morphe",
              "music-morphe": "Music-Morphe", "reddit-morphe": "Reddit-Morphe",
              "twitter-piko": "Twitter"}
    versions = sorted({identify(p.name) for p in Path(directory).glob("*.apk")
                       if identify(p.name)})
    return "\n".join(f"{labels.get(app, app)}: {version}  "
                     for app, version in versions)


def carry_forward(directory, repo):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    current_apps = {identify(p.name)[0] for p in directory.glob("*.apk")
                    if identify(p.name)}
    with tempfile.TemporaryDirectory() as previous:
        backfill(previous, repo)
        for apk in Path(previous).glob("*.apk"):
            if identify(apk.name)[0] not in current_apps:
                shutil.copy2(apk, directory / apk.name)
    with Path("build.md").open("a") as notes:
        notes.write("\nAvailable APKs:\n" + app_notes(directory) + "\n")


def publish_aggregate(directory, repo):
    releases = json.loads(gh("release", "list", "--repo", repo,
                            "--limit", "1000", "--json", "tagName"))
    tags = [int(r["tagName"]) for r in releases if r["tagName"].isdigit()]
    latest = str(max(tags, default=0))
    files = sorted(Path(directory).glob("*.apk"))
    if tags:
        assets = json.loads(gh("release", "view", latest, "--repo", repo,
                              "--json", "assets"))["assets"]
        if {p.name for p in files}.issubset({a["name"] for a in assets}):
            return
    gh("release", "create", str(int(latest) + 1), *(str(p) for p in files),
       "--repo", repo, "--title", "Release", "--latest",
       "--notes", app_notes(directory) + "\n\nCompatibility release for existing Obtainium configurations. "
       "Includes the latest previously published APK for each app, unchanged. "
       "The numeric tag is a build number, not the APK version.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="build")
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--carry-forward", action="store_true")
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    if args.backfill:
        with tempfile.TemporaryDirectory() as directory:
            backfill(directory, repo)
            publish(directory, repo)
            publish_aggregate(directory, repo)
    elif args.carry_forward:
        carry_forward(args.directory, repo)
    else:
        publish(args.directory, repo)


if __name__ == "__main__":
    main()
