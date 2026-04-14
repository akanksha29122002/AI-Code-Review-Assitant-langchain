import unittest

from fastapi.testclient import TestClient

from webhook_app import app


class WebDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_home_page_renders_demo(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("AI Code Review Assistant", response.text)
        self.assertIn("Run Review", response.text)

    def test_review_endpoint_returns_structured_result(self) -> None:
        response = self.client.post(
            "/review",
            json={
                "diff_text": (
                    "diff --git a/app.py b/app.py\n"
                    "@@ -1,0 +1,1 @@\n"
                    "+print('debug')\n"
                ),
                "language": "Python",
                "focus_areas": ["Correctness", "Testing"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("overall_risk", payload)
        self.assertTrue(payload["findings"])

    def test_review_endpoint_requires_diff_text(self) -> None:
        response = self.client.post("/review", json={"diff_text": ""})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
