import unittest
from mvp import metrics, pair

class MVPTests(unittest.TestCase):
    def test_ranking(self):
        rows = [{"group":"a","label":"relevant"},{"group":"a","label":"irrelevant"}]
        result = metrics(rows, [[.1,.9],[.9,.1]], ["irrelevant","relevant"], "ranking")
        self.assertEqual(result["mrr"], 1)
        self.assertEqual(result["accuracy"], 1)
    def test_pair(self):
        with self.assertRaises(ValueError):
            pair({"input":{}})
