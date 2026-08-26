import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hunyuanocr_bench.speed import run_speed, summarize_speed


class FakeHandler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, format, *args):
        return

    def do_GET(self):
        body = {"data": [{"id": "tencent/HunyuanOCR"}]}
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        self.__class__.requests.append(request)
        body = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"completion_tokens": 4},
        }
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class SpeedTests(unittest.TestCase):
    def test_paper_equations_use_sum_of_request_latencies(self) -> None:
        summary = summarize_speed(
            [
                {"image": "a.png", "ok": True, "latency_seconds": 1.0, "completion_tokens": 10, "finish_reason": "stop"},
                {"image": "b.png", "ok": True, "latency_seconds": 3.0, "completion_tokens": 30, "finish_reason": "stop"},
            ],
            wall_seconds=5.0,
            protocol_id="p",
            profile_id="full1651-c1",
            sample_sha256="x",
            parameters={},
        )
        self.assertEqual(summary["average_latency_seconds"], 2.0)
        self.assertEqual(summary["page_per_second"], 0.5)
        self.assertEqual(summary["token_per_second"], 10.0)
        self.assertEqual(summary["wall_page_per_second"], 0.4)

    def test_speed_request_against_openai_compatible_api(self) -> None:
        FakeHandler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                image_dir = root / "images"
                image_dir.mkdir()
                for name in ("a.png", "b.png"):
                    (image_dir / name).write_bytes(b"not-a-real-png")
                gt = root / "gt.json"
                gt.write_text(json.dumps([
                    {"page_info": {"image_path": "a.png"}},
                    {"page_info": {"image_path": "b.png"}},
                ]))
                protocol = {
                    "protocol_id": "test",
                    "prompt": "parse",
                    "speed_profiles": {
                        "full1651-c1": {
                            "expected_pages": 2,
                            "warmup_pages": 1,
                            "repetitions": 1,
                            "timeout_seconds": 10,
                            "request": {"temperature": 0.0, "max_tokens": 8, "extra_body": {"top_k": 1}},
                        }
                    },
                }
                machine = {
                    "runtime": {
                        "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                        "served_model_name": "tencent/HunyuanOCR",
                    }
                }
                summary = run_speed(protocol, machine, "full1651-c1", image_dir, root / "out", gt_path=gt)
                self.assertEqual(summary["status"], "PASS")
                self.assertEqual(summary["images"], 2)
                self.assertEqual(len(FakeHandler.requests), 3)
                self.assertEqual(FakeHandler.requests[-1]["top_k"], 1)
                self.assertNotIn("extra_body", FakeHandler.requests[-1])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
