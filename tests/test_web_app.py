"""Integration tests: require a real local MongoDB; never use production data."""

from dataclasses import asdict
from datetime import date
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from src.project_health_agent import ProjectHealthAgent
from src.web_app import app

ROOT = Path(__file__).resolve().parent.parent


class MongoDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_name = f"project_health_test_{uuid4().hex}"
        cls.environment = patch.dict(os.environ, {"MONGODB_DATABASE": cls.database_name})
        cls.environment.start()
        cls.mongo = MongoClient(os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"), serverSelectionTimeoutMS=3000)
        cls.mongo.admin.command("ping")

    @classmethod
    def tearDownClass(cls):
        cls.mongo.drop_database(cls.database_name)
        cls.mongo.close()
        cls.environment.stop()

    def setUp(self):
        self.mongo[self.database_name].reports.delete_many({})
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def samples(self):
        response = self.client.post("/api/reports/samples", json={"as_of": "2026-07-09"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["items"]

    def test_real_mongodb_health_and_frontend(self):
        health = self.client.get("/api/health").json()
        self.assertEqual(health["database"], self.database_name)
        self.assertEqual(health["storage"], "MongoDB")
        self.assertEqual(health["document_count"], 0)
        self.assertIn("Project Health Dashboard", self.client.get("/").text)
        self.assertEqual(self.client.get("/app.js").status_code, 200)

    def test_create_read_update_delete_and_direct_database_evidence(self):
        reports = self.samples()
        self.assertEqual(len(reports), 2)
        report_id = reports[0]["_id"]
        collection = self.mongo[self.database_name].reports
        self.assertEqual(collection.count_documents({}), 2)
        self.assertIsNotNone(collection.find_one({"_id": ObjectId(report_id)}))
        self.assertEqual(self.client.get("/api/reports").json()["total"], 2)
        response = self.client.patch(f"/api/reports/{report_id}", json={"notes": "Professor demo persisted"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(collection.find_one({"_id": ObjectId(report_id)})["notes"], "Professor demo persisted")
        self.assertEqual(self.client.delete(f"/api/reports/{report_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/reports/{report_id}").status_code, 404)
        self.assertEqual(collection.count_documents({}), 1)

    def test_new_application_connection_reads_persisted_record(self):
        report_id = self.samples()[0]["_id"]
        with TestClient(app) as second_client:
            response = second_client.get(f"/api/reports/{report_id}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["_id"], report_id)

    def test_upload_preserves_analyzer_results(self):
        path = ROOT / "S2P Project (1).xlsx"
        with path.open("rb") as stream:
            response = self.client.post(
                "/api/reports/upload",
                data={"as_of": "2026-07-09"},
                files={"file": (path.name, stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        self.assertEqual(response.status_code, 201, response.text)
        report = response.json()
        expected = asdict(ProjectHealthAgent(date(2026, 7, 9)).evaluate(path))
        for key in ("metrics", "signals", "rag", "reason"):
            self.assertEqual(report[key], expected[key])
        self.assertEqual(report["source_file"], path.name)
        self.assertEqual(self.client.get(f"/api/reports/{report['_id']}").status_code, 200)

    def test_invalid_upload_and_size_limit(self):
        for filename in ("bad.txt", "bad.xlsx"):
            response = self.client.post("/api/reports/upload", data={"as_of": "2026-07-09"}, files={"file": (filename, b"not excel")})
            self.assertEqual(response.status_code, 422)
        response = self.client.post("/api/reports/upload", data={"as_of": "2026-07-09"}, files={"file": ("large.xlsx", b"x" * (10 * 1024 * 1024 + 1))})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.mongo[self.database_name].reports.count_documents({}), 0)

    def test_invalid_ids_dates_notes_and_missing_documents(self):
        self.assertEqual(self.client.get("/api/reports/invalid").status_code, 422)
        missing = str(ObjectId())
        self.assertEqual(self.client.get(f"/api/reports/{missing}").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/reports/{missing}").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/reports/{missing}", json={"notes": "test"}).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/reports/{missing}", json={"notes": "x" * 2001}).status_code, 422)
        self.assertEqual(self.client.post("/api/reports/samples", json={"as_of": "bad-date"}).status_code, 422)
        self.assertEqual(self.client.get("/api/reports?page=0").status_code, 422)

    def test_pagination(self):
        reports = self.samples()
        collection = self.mongo[self.database_name].reports
        source = collection.find_one({"_id": ObjectId(reports[0]["_id"])})
        source.pop("_id")
        collection.insert_many([dict(source) for _ in range(21)])
        self.assertEqual(len(self.client.get("/api/reports").json()["items"]), 20)
        page = self.client.get("/api/reports?page=2").json()
        self.assertEqual(len(page["items"]), 3)
        self.assertEqual(page["total"], 23)

    def test_disconnected_database_returns_explicit_503(self):
        with MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=100) as offline:
            original = app.state.database
            try:
                app.state.database = offline[self.database_name]
                response = self.client.get("/api/health")
                self.assertEqual(response.status_code, 503)
                self.assertIn("MongoDB is unavailable", response.json()["detail"])
                self.assertEqual(self.client.get("/api/reports").status_code, 503)
            finally:
                app.state.database = original


if __name__ == "__main__":
    unittest.main()
