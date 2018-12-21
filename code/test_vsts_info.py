import unittest
from VSTSInfo import VstsInfo

class TestVstsInfo(unittest.TestCase):

    def test_can_get_url_from_config(self):
        info = VstsInfo(None, None)
        base = info.instance_base
        self.assertNotEqual(base, None)

    def test_has_cash_prefix(self):
        info = VstsInfo(None, None)
        base = info.cash_prefix
        self.assertNotEqual(base, None)

    def test_can_get_filename_for_cache(self):
        info = VstsInfo(None, None)
        info.config['DEFAULT']['vsts_instance_base'] = "company.visualstudio.com"
        info.config['DEFAULT']['cash_prefix'] = "vsts"
        url = "https://" + info.instance_base + "/my_project"+ "?foo=bar&foofoo=barbar"
        expected = info.cache_folder + "\\" + info.cash_prefix +".my_project" + "(qm)" + "foo=bar&foofoo=barbar" +".json"
        cache_file_name = info.build_file_name(url)
        self.assertEqual(cache_file_name, expected)

    def test_get_request_settings(self):
        info = VstsInfo(None, None)
        settings = info.get_request_settings()
        self.assertEqual(settings['instance'], info.instance )

    def test_personal_access_token_starts_with_colon(self):
        info = VstsInfo(None, None)
        actual = info.personal_access_token
        self.assertTrue(actual.startswith(':'))

if __name__ == '__main__':
    unittest.main()