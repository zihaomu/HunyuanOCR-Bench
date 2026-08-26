import unittest
from hunyuanocr_bench.config import accuracy_endpoint_config

class AccuracyEndpointTests(unittest.TestCase):
    def test_multi_endpoint_profile(self):
        machine={"runtime":{"base_url":"http://127.0.0.1:18016/v1","accuracy_ports":[18016,18017]}}
        self.assertEqual(accuracy_endpoint_config(machine),("127.0.0.1",[18016,18017]))
    def test_single_endpoint_fallback(self):
        self.assertEqual(accuracy_endpoint_config({"runtime":{"base_url":"http://localhost:8000/v1"}}),("localhost",[8000]))
    def test_duplicate_ports_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"unique"):
            accuracy_endpoint_config({"runtime":{"base_url":"http://127.0.0.1:18016/v1","accuracy_ports":[18016,18016]}})
if __name__ == '__main__': unittest.main()
