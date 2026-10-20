import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "publish_apps", Path(__file__).parents[1] / "scripts/publish_apps.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublishingTests(unittest.TestCase):
    def test_versions_and_modules(self):
        self.assertEqual(module.identify("googlephotos-devanced-v7.92.0.977185651-all.apk"),
                         ("googlephotos-devanced", "7.92.0.977185651"))
        self.assertEqual(module.identify("twitter-piko-v12.35.0-prod.01-all.apk"),
                         ("twitter-piko", "12.35.0-prod.01"))
        self.assertIsNone(module.identify("googlephotos-devanced-module-v7.92-all.zip"))

    def test_architectures_share_one_versioned_release(self):
        with tempfile.TemporaryDirectory() as directory:
            for arch in ("arm64-v8a", "arm-v7a"):
                Path(directory, f"music-morphe-v9.20.53-{arch}.apk").touch()
            with patch.object(module, "gh", return_value="[]") as gh:
                module.publish(directory, "owner/repo")
                creates = [c.args for c in gh.call_args_list if c.args[1] == "create"]
                self.assertEqual(len(creates), 1)
                self.assertEqual(creates[0][2], "music-morphe-v9.20.53")
                self.assertIn("--latest=false", creates[0])
                self.assertEqual(sum(a.endswith(".apk") for a in creates[0]), 2)

    def test_existing_apk_is_not_overwritten(self):
        name = "googlephotos-devanced-v7.92.0.977185651-all.apk"
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, name).touch()
            with patch.object(module, "gh", side_effect=[
                json.dumps([{"tagName": "7.92.0.977185651"}]),
                json.dumps({"assets": [{"name": name}]}),
                "",
            ]) as gh:
                module.publish(directory, "owner/repo")
                self.assertEqual(gh.call_count, 3)

    def test_photos_publishes_exact_version_and_original_note_name(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "googlephotos-devanced-v7.92.0.977185651-all.apk").touch()
            with patch.object(module, "gh", return_value="[]") as gh:
                module.publish(directory, "owner/repo")
                args = gh.call_args.args
                self.assertEqual(args[:3], ("release", "create", "7.92.0.977185651"))
                self.assertIn("GooglePhotos: 7.92.0.977185651", args[-1])
                self.assertNotIn("--clobber", args)

    def test_backfill_finds_photos_behind_twitter_only_releases(self):
        def release(tag, names):
            return dict(tag_name=tag, draft=False, prerelease=False,
                        assets=[dict(name=name) for name in names])
        pages = [[release("25", ["twitter-piko-v12.35.0-prod.01-all.apk"])], [
            release("16", ["googlephotos-devanced-v7.92-all.apk"]),
            release("15", ["googlephotos-devanced-v7.91-all.apk"]),
            release("googlephotos-devanced-v7.90", ["googlephotos-devanced-v7.90-all.apk"]),
        ]]
        with patch.object(module, "gh", side_effect=[json.dumps(pages), "", ""]) as gh:
            module.backfill("/tmp/unused", "owner/repo")
            downloads = [c.args for c in gh.call_args_list if c.args[1] == "download"]
            self.assertEqual([c[2] for c in downloads], ["25", "16"])


if __name__ == "__main__":
    unittest.main()
