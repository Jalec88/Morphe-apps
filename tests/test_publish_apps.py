import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('publisher', Path(__file__).parents[1] / 'scripts/publish_apps.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def release(tag, names=(), prerelease=False):
    return dict(tag_name=tag, draft=False, prerelease=prerelease, body='',
                assets=[dict(name=n) for n in names])


class PublisherTests(unittest.TestCase):
    def test_real_version_without_build_number_or_prefix(self):
        with tempfile.TemporaryDirectory() as d:
            name = 'googlephotos-devanced-v7.92.0.977185651-all.apk'
            Path(d, name).touch()
            with patch.object(p, 'releases', return_value=[]), patch.object(p, 'gh') as gh:
                p.publish(d, 'owner/repo')
                args = gh.call_args.args
                self.assertEqual(args[:3], ('release', 'create', '7.92.0.977185651'))
                self.assertIn('GooglePhotos: 7.92.0.977185651', args[-1])

    def test_two_architectures_one_release(self):
        with tempfile.TemporaryDirectory() as d:
            for arch in ('arm-v7a', 'arm64-v8a'):
                Path(d, f'music-morphe-v9.20.53-{arch}.apk').touch()
            with patch.object(p, 'releases', return_value=[]), patch.object(p, 'gh') as gh:
                p.publish(d, 'owner/repo')
                self.assertEqual(gh.call_count, 1)
                self.assertEqual(sum(a.endswith('.apk') for a in gh.call_args.args), 2)

    def test_existing_apk_is_not_overwritten(self):
        name = 'googlephotos-devanced-v7.92-all.apk'
        with tempfile.TemporaryDirectory() as d:
            Path(d, name).touch()
            old = release('7.92', [name]); old['body'] = 'GooglePhotos: 7.92'
            with patch.object(p, 'releases', return_value=[old]), patch.object(p, 'gh') as gh:
                p.publish(d, 'owner/repo')
                gh.assert_not_called()

    def test_history_remains_readable_after_archiving(self):
        a = release('26', ['googlephotos-devanced-v7.92-all.apk'], True)
        b = release('16', ['googlephotos-devanced-v7.91-all.apk'])
        self.assertEqual(p.latest_assets([b, a]), [('26', a['assets'][0]['name'])])

    def test_no_visibility_changes_until_all_canonical_apks_exist(self):
        names = [f'{app}-v1.2-all.apk' for app in p.LABELS]
        with patch.object(p, 'releases', return_value=[release('26', names)]), patch.object(p, 'gh') as gh:
            with self.assertRaises(RuntimeError):
                p.reconcile_history('owner/repo')
            gh.assert_not_called()

    def test_migration_only_edits_metadata_and_preserves_downloads(self):
        names = [f'{app}-v1.2-all.apk' for app in p.LABELS]
        rows = [release('26', names), release('1.2', names)]
        with patch.object(p, 'releases', return_value=rows), patch.object(p, 'gh') as gh:
            p.reconcile_history('owner/repo')
            self.assertEqual(gh.call_args.args[:3], ('release', 'edit', '26'))
            self.assertEqual(rows[0]['assets'], [dict(name=n) for n in names])
            self.assertIn('--prerelease', gh.call_args.args)

    def test_numeric_tracking_can_hide_real_update_for_existing_user(self):
        # Regression scenario from Obtainium's reconcileTrackedVersion and
        # isAppUpdateable: pseudoversion 26, real installed 7.91, remote 7.92.
        # With versionDetection=false neither same-release collapse applies.
        # hideDowngrades defaults to true, so 26 > 7 hides the update.
        tracked, installed, remote = '26', '7.91', '7.92'
        same_release = lambda a, b: a == b
        if same_release(tracked, remote) or same_release(installed, remote):
            tracked = remote
        self.assertGreater(int(tracked.split('.')[0]), int(remote.split('.')[0]))
        # This is a blocking compatibility finding, not a device/emulator test.


if __name__ == '__main__':
    unittest.main()
