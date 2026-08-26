import json
import tempfile
import unittest
from pathlib import Path

from hunyuanocr_bench.config import load_machine


class MachineProfileTests(unittest.TestCase):
    def test_template_placeholders_are_not_runnable(self) -> None:
        template = Path(__file__).resolve().parents[1] / "machines" / "templates" / "amd.json"
        with self.assertRaisesRegex(ValueError, "REPLACE_ME"):
            load_machine(template)

    def test_complete_profile_is_accepted(self) -> None:
        profile = {
            "machine_id": "nvidia-test-h20",
            "vendor": "nvidia",
            "accelerator": {"model": "H20", "count": 1, "memory_gib_each": 80},
            "runtime": {
                "framework": "vLLM", "framework_version": "1.0", "inference_method": "ar",
                "base_url": "http://127.0.0.1:8000/v1", "served_model_name": "tencent/HunyuanOCR",
                "container_image": "example/image:test", "container_image_digest": "sha256:test",
                "precision": "bfloat16", "tensor_parallel": 1
            },
            "software": {"os": "Linux", "driver": "x", "compute_stack": "CUDA", "pytorch": "x"}
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "machine.json"
            path.write_text(json.dumps(profile))
            self.assertEqual(load_machine(path)["machine_id"], "nvidia-test-h20")


if __name__ == "__main__":
    unittest.main()
