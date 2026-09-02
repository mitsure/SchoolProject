import json
import unittest
from unittest.mock import patch

from app.ollama_client import OllamaClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self, _limit): return json.dumps(self.payload).encode()


class OllamaClientTest(unittest.TestCase):
    def test_external_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            OllamaClient("test", "https://example.com")

    @patch("urllib.request.urlopen")
    def test_chat_request_and_json_content(self, urlopen):
        urlopen.return_value = FakeResponse({"message": {"content": '{"ok": true}'}})
        client = OllamaClient("local-model")
        result = client.complete_json("system", {"input_text": "架空例"})
        self.assertEqual(result, {"ok": True})
        request = urlopen.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertFalse(body["stream"])
        self.assertFalse(body["think"])
        self.assertEqual(body["keep_alive"], "10m")
        self.assertEqual(body["options"]["temperature"], 0)
        self.assertIn("遊具等", body["format"]["required"])
        self.assertEqual(set(body["format"]["properties"]["遊具等"]["properties"]), {"value", "evidence_text"})


if __name__ == "__main__":
    unittest.main()
