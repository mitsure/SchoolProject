"""Exercise the ASGI application without an extra HTTP client dependency."""
import asyncio
from html.parser import HTMLParser
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode, urlsplit


class HiddenInputs(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.values = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "hidden":
            self.values[attrs["name"]] = attrs.get("value", "")


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "Install app requirements to run ASGI tests")
class ResearchWebTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        with patch.dict(os.environ, {"SPORTDENT_DB_PATH": str(Path(self.directory.name) / "import.sqlite3"),
                                     "SPORTDENT_EXTRACTOR": "rules"}):
            from app import main
        from app.auth import AuthManager
        from app.extractor import RuleBasedExtractor
        from app.storage import ReviewStore
        self.main = main
        self.store = ReviewStore(Path(self.directory.name) / "test.sqlite3")
        for name, value in (("store", self.store), ("extractor", RuleBasedExtractor()),
                            ("auth", AuthManager(username="tester", password="pass", secret="fixed"))):
            patcher = patch.object(main, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def request(self, path, data=None, authenticated=True):
        url = urlsplit(path)
        headers = [(b"host", b"testserver")]
        if authenticated:
            headers.append((b"cookie", f"{self.main.auth.COOKIE_NAME}={self.main.auth.issue_token()}".encode()))
        body = urlencode(data).encode() if data is not None else b""
        headers.extend([(b"content-type", b"application/x-www-form-urlencoded"), (b"content-length", str(len(body)).encode())])
        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}, "http_version": "1.1",
                 "method": "POST" if data is not None else "GET", "scheme": "http", "path": url.path,
                 "raw_path": url.path.encode(), "query_string": url.query.encode(), "root_path": "",
                 "headers": headers, "client": ("127.0.0.1", 123), "server": ("testserver", 80)}
        sent = False
        messages = []

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        await asyncio.wait_for(self.main.app(scope, receive, send), timeout=10)
        start = next(message for message in messages if message["type"] == "http.response.start")
        content = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body").decode()
        return start["status"], dict(start["headers"]), content

    async def save_example(self, text="中2の生徒が転倒し前歯を折った。"):
        status, _, body = await self.request("/analyze", {"text": text})
        self.assertEqual(status, 200)
        hidden = HiddenInputs(body).values
        form = {**hidden, "confirmed": "yes", "injury_type": "聴力障害", "school_type": "中", "grade": "2"}
        status, _, _ = await self.request("/save", form)
        self.assertEqual(status, 200)
        return self.store.research_records()[0], form

    async def test_workflow_snapshot_assessment_dashboard_and_exports(self):
        row, form = await self.save_example()
        self.assertEqual(row["prediction"]["種別"], "歯牙障害")
        self.assertEqual(row["confirmed"]["種別"], "聴力障害")
        self.assertIsNone(row["assessment"])
        status, headers, body = await self.request("/dashboard")
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertIn("算出不可", body)
        status, _, body = await self.request(f"/reviews/{row['id']}/assess")
        self.assertEqual(status, 200)
        self.assertNotIn("value='歯牙障害' selected", body)
        data = {"reviewer": "r1", "dataset": "pilot", "split": "development", "sampling": "consecutive",
                "status": "active", "gold_0": "聴力障害"}
        status, _, _ = await self.request(f"/reviews/{row['id']}/assess", data)
        self.assertEqual(status, 303)
        status, _, _ = await self.request(f"/reviews/{row['id']}/assess", data)
        self.assertEqual(status, 409)
        status, _, body = await self.request("/dashboard/export.json")
        self.assertEqual(status, 200)
        report = json.loads(body)
        self.assertEqual(report["summary"]["screening"]["confusion_matrix"]["fp"], 1)
        status, _, csv = await self.request("/dashboard/errors.csv")
        self.assertEqual(status, 200)
        self.assertIn("歯牙障害", csv)
        self.assertIn("聴力障害", csv)
        _, _, body = await self.request("/dashboard/export.json?dataset=other")
        self.assertEqual(json.loads(body)["summary"]["total"], 0)
        _, _, body = await self.request("/dashboard/export.json?version=other")
        self.assertEqual(json.loads(body)["summary"]["total"], 0)
        form["snapshot_json"] = form["snapshot_json"].replace("歯牙障害", "聴力障害")
        status, _, _ = await self.request("/save", form)
        self.assertEqual(status, 400)
        self.assertEqual(len(self.store.research_records()), 1)

    async def test_authentication_missing_records_invalid_assessment_and_empty_dashboard(self):
        for path in ("/dashboard", "/dashboard/export.json", "/dashboard/errors.csv", "/reviews/1/assess"):
            status, _, _ = await self.request(path, authenticated=False)
            self.assertEqual(status, 303)
        status, _, _ = await self.request("/reviews/1/assess", {}, authenticated=False)
        self.assertEqual(status, 303)
        status, _, body = await self.request("/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("算出不可", body)
        status, _, _ = await self.request("/reviews/123/assess")
        self.assertEqual(status, 404)
        status, _, _ = await self.request("/reviews/123/assess", {})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
