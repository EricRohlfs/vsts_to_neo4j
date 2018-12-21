"""
Unit tests for CommentsWorker
"""
import unittest
from Comments import CommentsWorker

class CommentsUnitTest(unittest.TestCase):
    """
    Unit tests for CommentsWorker
    """

    def test_given_empty_raw_id_does_not_do_db(self):
        request_info = {}
        worker = CommentsWorker(request_info)
        vsts_data = {}
        thread_id = None
        result = worker.make_comment_node(vsts_data, thread_id)
        self.assertFalse(result)

    def test_maps_raw_to_comment(self):
        request_info = {}
        worker = CommentsWorker(request_info)
        vsts_data = {}
        vsts_data['id'] = 56789
        thread_id = 123456
        result = worker.make_comment_node(vsts_data, thread_id)
        self.assertTrue(str(vsts_data['id']) in result.Id)

if __name__ == '__main__':
    #suite = unittest.TestLoader().loadTestsFromTestCase(CommentsUnitTest)
    #unittest.TextTestRunner(verbosity=2).run(suite)
    unittest.main()
