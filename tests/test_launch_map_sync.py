import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('sync', Path(__file__).resolve().parents[1]/'sync_launch_map.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class LaunchSync(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root/'launch/test-condo'
        (self.folder/'assets').mkdir(parents=True)
        self.facts = {'name':'Test Condo','address':'1 Test Road','towers':'Two 20-storey blocks','novp':'2030','prices':{'from':100}}
        self.save('launch.json', self.facts)
        (self.folder/'index.html').write_text('<img src="assets/plan.jpg" alt="Site plan"><img src="assets/price.jpg" alt="Prices">')
        (self.folder/'assets/plan.jpg').write_bytes(b'plan version 1')
        (self.folder/'assets/price.jpg').write_bytes(b'price version 1')
        self.catalog = {'asOf':'2026-09-21','projects':[]}

    def save(self, file, data):
        (self.folder/file).write_text(json.dumps(data))

    def compile(self, catalog=None, resolver=lambda _:None):
        return sync.compile_catalog(self.root, catalog or self.catalog, '2026-09-22T00:00:00+00:00', resolver)

    def model(self):
        _, report = self.compile()
        site = [[103.8,1.3],[103.801,1.3],[103.801,1.301],[103.8,1.301],[103.8,1.3]]
        geometry = {'type':'Polygon','coordinates':[copy.deepcopy(site)]}
        return {'sourceFingerprint':report['projects'][0]['sourceFingerprint'],'reviewedAt':'2026-09-22',
                'reviewNote':'Checked against the published site plan and storey schedule.',
                'center':[103.8005,1.3005], 'site':site, 'towers':[{'name':'Block 1','floors':20,'geometry':geometry}]}

    def test_new_launch_without_verified_location_has_no_invented_shape(self):
        catalog, report = self.compile()
        self.assertIsNone(catalog['projects'][0]['center'])
        self.assertEqual(catalog['projects'][0]['towers'], [])
        self.assertEqual(report['projects'][0]['status'], 'awaiting-model')

    def test_exact_location_and_repeat_deduplicate(self):
        catalog, report = self.compile(resolver=lambda _: {'center':[103.8,1.3],'source':'https://www.onemap.gov.sg/'})
        again, _ = self.compile(catalog)
        self.assertEqual(len(again['projects']), 1)
        self.assertEqual(catalog, again)
        self.assertTrue(report['projects'][0]['located'])

    def test_price_only_change_does_not_invalidate_review(self):
        self.save('map-model.json', self.model())
        before, first = self.compile()
        self.facts['prices'] = {'from':500}
        self.save('launch.json', self.facts)
        (self.folder/'assets/price.jpg').write_bytes(b'price version 2')
        (self.folder/'index.html').write_text((self.folder/'index.html').read_text()+'<p>New price $500</p>')
        after, last = self.compile()
        self.assertEqual(first['projects'][0]['sourceFingerprint'], last['projects'][0]['sourceFingerprint'])
        self.assertEqual(last['projects'][0]['status'], 'current')
        self.assertEqual(before['projects'][0]['towers'], after['projects'][0]['towers'])

    def test_same_filename_new_bytes_require_review_and_retain_checked_model(self):
        self.save('map-model.json', self.model())
        before, _ = self.compile()
        (self.folder/'assets/plan.jpg').write_bytes(b'changed tower layout')
        after, report = self.compile()
        self.assertEqual(report['projects'][0]['status'], 'review-required')
        self.assertEqual(before['projects'][0]['towers'], after['projects'][0]['towers'])

    def test_changed_storeys_require_review(self):
        self.save('map-model.json', self.model())
        self.facts['towers'] = 'Two 30-storey blocks'
        self.save('launch.json', self.facts)
        catalog, report = self.compile()
        self.assertEqual(report['projects'][0]['status'], 'review-required')
        self.assertEqual(catalog['projects'][0]['towers'][0]['floors'], 20)

    def test_preview_files_are_ignored(self):
        before, _ = self.compile()
        self.save('launch.preview.json', {'name':'Bad draft'})
        self.save('preview.json', {'sources':['private WhatsApp draft']})
        after, _ = self.compile()
        self.assertEqual(before, after)

    def test_missing_plan_cannot_clear_existing_review(self):
        self.save('map-model.json', self.model())
        before, _ = self.compile()
        (self.folder/'assets/plan.jpg').unlink()
        after, report = self.compile(before)
        self.assertEqual(report['projects'][0]['status'], 'source-unavailable')
        self.assertEqual(before['projects'][0]['towers'], after['projects'][0]['towers'])

    def test_no_plan_is_awaiting_plan(self):
        (self.folder/'index.html').write_text('<p>Plans coming soon</p>')
        _, report = self.compile()
        self.assertEqual(report['projects'][0]['status'], 'awaiting-site-plan')

    def test_bad_geometry_cannot_replace_existing_model(self):
        model = self.model()
        model['towers'][0]['geometry']['coordinates'][0][0] = [0,0]
        self.save('map-model.json', model)
        catalog, report = self.compile()
        self.assertEqual(catalog['projects'][0]['towers'], [])
        self.assertEqual(report['projects'][0]['status'], 'review-required')

    def test_location_failure_does_not_drop_project(self):
        def fail(_): raise TimeoutError()
        catalog, report = self.compile(resolver=fail)
        self.assertEqual(len(catalog['projects']), 1)
        self.assertFalse(report['projects'][0]['located'])

    def test_private_asset_path_is_rejected(self):
        self.save('map-source.json', {'geometryAssets':['../../private.jpg']})
        with self.assertRaises(ValueError): self.compile()


if __name__ == '__main__':
    unittest.main()
