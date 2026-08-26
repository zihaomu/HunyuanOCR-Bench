import unittest

from hunyuanocr_bench.config import load_protocol


class ProtocolTests(unittest.TestCase):
    def test_committed_protocol_artifacts_match_locks(self) -> None:
        protocol = load_protocol()
        self.assertEqual(protocol["dataset"]["expected_images"], 1651)
        self.assertEqual(
            protocol["speed_profiles"]["quick9-c1"]["sample_inventory_sha256"],
            "28f59abf2efbac69a32a3914e184e63d160accb90474036b51105ec7817d72eb",
        )
        self.assertTrue(protocol["speed_profiles"]["quick9-c1"]["publishable"])
        self.assertFalse(protocol["speed_profiles"]["full1651-c1"]["publishable"])
        self.assertEqual(
            protocol["speed_profiles"]["full1651-c1"]["sample_inventory_sha256"],
            "344d236b31d265915b723f3106613bbbeaf37cf988db7f58b76d88cbb7c2a1b4",
        )
        self.assertFalse(protocol["speed_profiles"]["paper930-c1"]["publishable"])


if __name__ == "__main__":
    unittest.main()
