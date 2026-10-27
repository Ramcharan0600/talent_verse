import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import app as talentverse


class TalentVerseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        talentverse.DB_PATH = os.path.join(self.temp_dir.name, "test.db")
        talentverse.init_db()
        self.client = talentverse.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_rejects_short_resume(self):
        response = self.client.post("/api/profiles", json={"resume_text": "Too short"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("80 characters", response.json["error"])

    def test_missing_resume_is_rejected(self):
        response = self.client.post("/api/profiles", json={})
        self.assertEqual(response.status_code, 400)

    def test_profile_validation_rejects_missing_schema_field(self):
        with self.assertRaises(ValueError):
            talentverse.validate_profile({"full_name": "Test"})

    @patch.object(talentverse, "extract_profile")
    def test_successful_profile_is_saved_and_retrievable(self, mock_extract):
        mock_extract.return_value = {
            "full_name": "Alex Example",
            "email": "alex@example.com",
            "phone": None,
            "professional_summary": "Computer science student interested in AI.",
            "skills": ["Python", "SQL"],
            "education": [{"qualification": "B.Tech", "institution": "Example University", "dates": "2024-present", "details": ""}],
            "experience": [],
            "projects": [{"name": "Demo", "description": "A sample project", "technologies": ["Python"]}],
            "certifications": [],
            "missing_information": []
        }
        resume = "This is a sufficiently long example resume " * 5
        response = self.client.post("/api/profiles", json={"resume_text": resume})
        self.assertEqual(response.status_code, 201)
        profile_id = response.json["profile"]["id"]
        self.assertEqual(response.json["profile"]["full_name"], "Alex Example")
        list_response = self.client.get("/api/profiles")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json["profiles"]), 1)
        get_response = self.client.get(f"/api/profiles/{profile_id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json["profile"]["skills"], ["Python", "SQL"])

    def _save_sample_profile(self):
        return talentverse.save_profile({
            "full_name": "Alex Example", "email": None, "phone": None,
            "professional_summary": "Student.", "skills": ["Python"], "education": [],
            "experience": [], "projects": [], "certifications": [], "missing_information": []
        }, "source")["id"]

    def test_analysis_requires_profile_except_interview(self):
        response = self.client.post("/api/analyses/skill-gap", json={"career_goal": "Become an ML engineer in a year"})
        self.assertEqual(response.status_code, 400)

    def test_analysis_unknown_kind_and_short_input(self):
        pid = self._save_sample_profile()
        self.assertEqual(self.client.post("/api/analyses/nope", json={}).status_code, 404)
        short = self.client.post("/api/analyses/job-match", json={"job_description": "short", "profile_id": pid})
        self.assertEqual(short.status_code, 400)
        missing = self.client.post("/api/analyses/job-match", json={"job_description": "x" * 30, "profile_id": 999})
        self.assertEqual(missing.status_code, 404)

    @patch.object(talentverse, "generate_json")
    def test_job_match_is_clamped_saved_and_listed(self, mock_generate):
        mock_generate.return_value = {
            "job_title": "Data Analyst", "required_skills": ["SQL"], "preferred_skills": [],
            "responsibilities": [], "experience_expectation": "0-2 years",
            "matched_skills": [], "missing_skills": ["SQL"], "match_percentage": 140,
            "overall_assessment": "Partial", "recommendations": []
        }
        pid = self._save_sample_profile()
        response = self.client.post("/api/analyses/job-match", json={
            "job_description": "Looking for a data analyst with SQL skills.", "profile_id": pid})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["analysis"]["result"]["match_percentage"], 100)
        listed = self.client.get(f"/api/analyses?kind=job-match&profile_id={pid}")
        self.assertEqual(len(listed.json["analyses"]), 1)

    @patch.object(talentverse, "generate_json")
    def test_incomplete_ai_analysis_is_rejected_and_not_saved(self, mock_generate):
        mock_generate.return_value = {"session_summary": "only this"}
        response = self.client.post("/api/analyses/interview-feedback", json={
            "notes": "I stumbled on the system design question and rambled."})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/analyses").json["analyses"], [])

    def test_audio_rejects_missing_and_bad_type(self):
        self.assertEqual(self.client.post("/api/profiles/audio").status_code, 400)
        bad = self.client.post("/api/profiles/audio", data={"audio": (io.BytesIO(b"hi"), "x.txt")},
                               content_type="multipart/form-data")
        self.assertEqual(bad.status_code, 400)

    @patch.object(talentverse, "extract_profile_from_audio")
    def test_audio_profile_saved(self, mock_extract):
        mock_extract.return_value = {
            "full_name": "Sam", "email": None, "phone": None, "professional_summary": "Spoken intro.",
            "skills": [], "education": [], "experience": [], "projects": [],
            "certifications": [], "missing_information": []
        }
        response = self.client.post("/api/profiles/audio", data={"audio": (io.BytesIO(b"abc"), "intro.mp3", "audio/mpeg")},
                                    content_type="multipart/form-data")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["profile"]["full_name"], "Sam")


if __name__ == "__main__":
    unittest.main()
