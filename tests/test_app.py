import io
import os
import tempfile
import unittest
from unittest.mock import patch

import app as talentverse

SAMPLE_PROFILE = {
    "full_name": "Alex Example",
    "email": "alex@example.com",
    "phone": "+91 90000 12389",
    "professional_summary": "Computer science student interested in AI.",
    "skills": ["Python", "SQL"],
    "education": [{"qualification": "B.Tech", "institution": "Example University", "dates": "2024-present", "details": ""}],
    "experience": [],
    "projects": [{"name": "Demo", "description": "A sample project", "technologies": ["Python"]}],
    "certifications": [],
    "missing_information": [],
}


class TalentVerseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        talentverse.DB_PATH = os.path.join(self.temp_dir.name, "test.db")
        talentverse.init_db()
        self.client = talentverse.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _profile(self, **overrides):
        return {**SAMPLE_PROFILE, **overrides}

    def _save_sample_profile(self):
        return talentverse.save_profile(self._profile(), "source")["id"]

    # ---- health / input validation -------------------------------------------------------
    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_rejects_short_resume(self):
        response = self.client.post("/api/profiles/extract", json={"resume_text": "Too short"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("80 characters", response.json["error"])

    def test_missing_resume_is_rejected(self):
        response = self.client.post("/api/profiles/extract", json={})
        self.assertEqual(response.status_code, 400)

    # ---- schema validation ---------------------------------------------------------------
    def test_profile_validation_rejects_missing_schema_field(self):
        with self.assertRaises(ValueError):
            talentverse.validate_profile({"full_name": "Test"})

    def test_validation_rejects_malformed_nested_entries(self):
        with self.assertRaises(ValueError):
            talentverse.validate_profile(self._profile(education=["not an object"]))

    def test_invalid_email_from_ai_is_discarded_not_kept(self):
        profile = talentverse.validate_profile(self._profile(email="not-an-email"))
        self.assertIsNone(profile["email"])
        self.assertTrue(any("email" in note for note in profile["missing_information"]))

    def test_invalid_email_from_user_is_rejected_strictly(self):
        with self.assertRaises(ValueError):
            talentverse.validate_profile(self._profile(email="nope"), strict=True)

    def test_email_not_in_source_is_flagged(self):
        profile = talentverse.validate_profile(self._profile(email="invented@example.com"))
        report = talentverse.build_report(profile, "A resume that never mentions any address.")
        self.assertTrue(any(c["field"] == "email" and c["status"] == "warning" for c in report["checks"]))

    # ---- step 1: extract -> preview (nothing saved) --------------------------------------
    @patch.object(talentverse, "extract_profile")
    def test_extract_returns_preview_and_report_without_saving(self, mock_extract):
        mock_extract.return_value = talentverse.validate_profile(self._profile())
        resume = "Alex Example alex@example.com. Python and SQL student. " * 3
        response = self.client.post("/api/profiles/extract", json={"resume_text": resume})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["preview"]["full_name"], "Alex Example")
        self.assertTrue(response.json["validation"]["schema_valid"])
        self.assertEqual(self.client.get("/api/profiles").json["profiles"], [])

    @patch.object(talentverse, "extract_profile")
    def test_ai_failure_returns_502_and_saves_nothing(self, mock_extract):
        mock_extract.side_effect = RuntimeError("Could not reach the AI service.")
        response = self.client.post("/api/profiles/extract", json={"resume_text": "x" * 100})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.client.get("/api/profiles").json["profiles"], [])

    @patch.object(talentverse, "extract_profile")
    def test_invalid_ai_output_returns_422(self, mock_extract):
        mock_extract.side_effect = ValueError("The profile is missing the required field: skills.")
        response = self.client.post("/api/profiles/extract", json={"resume_text": "x" * 100})
        self.assertEqual(response.status_code, 422)

    # ---- step 2: confirm -> create -------------------------------------------------------
    def test_save_requires_confirmation(self):
        response = self.client.post("/api/profiles", json={"profile": SAMPLE_PROFILE})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/profiles").json["profiles"], [])

    def test_save_rejects_invalid_profile(self):
        response = self.client.post("/api/profiles", json={"profile": {"full_name": "x"}, "confirmed": True})
        self.assertEqual(response.status_code, 422)

    def test_confirmed_profile_is_saved_masked_in_list_and_full_on_get(self):
        response = self.client.post("/api/profiles", json={"profile": SAMPLE_PROFILE, "source": "text", "confirmed": True})
        self.assertEqual(response.status_code, 201)
        profile_id = response.json["profile"]["id"]
        listed = self.client.get("/api/profiles").json["profiles"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["email"], "a***@example.com")
        self.assertEqual(listed[0]["phone"], "***89")
        got = self.client.get(f"/api/profiles/{profile_id}")
        self.assertEqual(got.json["profile"]["email"], "alex@example.com")
        self.assertEqual(got.json["profile"]["skills"], ["Python", "SQL"])
        self.assertIn("validation", got.json)

    def test_raw_source_text_is_never_stored(self):
        self.client.post("/api/profiles", json={"profile": SAMPLE_PROFILE, "source": "text", "confirmed": True})
        with talentverse.get_connection() as conn:
            stored = conn.execute("SELECT source_text FROM profiles").fetchone()[0]
        self.assertIn("not stored", stored)

    # ---- update --------------------------------------------------------------------------
    def test_update_changes_the_stored_profile(self):
        created = self.client.post("/api/profiles", json={"profile": SAMPLE_PROFILE, "confirmed": True})
        profile_id = created.json["profile"]["id"]
        edited = self._profile(full_name="Alex Corrected", skills=["Python", "Flask"])
        response = self.client.put(f"/api/profiles/{profile_id}", json={"profile": edited, "confirmed": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["profile"]["full_name"], "Alex Corrected")
        self.assertIsNotNone(response.json["profile"]["updated_at"])
        self.assertEqual(self.client.get(f"/api/profiles/{profile_id}").json["profile"]["skills"], ["Python", "Flask"])
        self.assertEqual(len(self.client.get("/api/profiles").json["profiles"]), 1)

    def test_update_errors(self):
        no_confirm = self.client.put("/api/profiles/1", json={"profile": SAMPLE_PROFILE})
        self.assertEqual(no_confirm.status_code, 400)
        missing = self.client.put("/api/profiles/999", json={"profile": SAMPLE_PROFILE, "confirmed": True})
        self.assertEqual(missing.status_code, 404)
        pid = self._save_sample_profile()
        invalid = self.client.put(f"/api/profiles/{pid}", json={"profile": self._profile(email="bad"), "confirmed": True})
        self.assertEqual(invalid.status_code, 422)

    # ---- delete --------------------------------------------------------------------------
    def test_delete_requires_confirmation_and_removes_profile_and_analyses(self):
        pid = self._save_sample_profile()
        talentverse.save_analysis(pid, "skill-gap", "goal text", {"x": 1})
        self.assertEqual(self.client.delete(f"/api/profiles/{pid}").status_code, 400)
        self.assertEqual(len(self.client.get("/api/profiles").json["profiles"]), 1)
        self.assertEqual(self.client.delete(f"/api/profiles/{pid}?confirmed=true").status_code, 200)
        self.assertEqual(self.client.get("/api/profiles").json["profiles"], [])
        self.assertEqual(self.client.get("/api/analyses").json["analyses"], [])
        self.assertEqual(self.client.get(f"/api/profiles/{pid}").status_code, 404)

    def test_delete_unknown_profile_is_404(self):
        self.assertEqual(self.client.delete("/api/profiles/999?confirmed=true").status_code, 404)

    # ---- career tools --------------------------------------------------------------------
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
    def test_contact_details_are_not_sent_to_the_ai(self, mock_generate):
        mock_generate.return_value = {"session_summary": "only this"}
        pid = self._save_sample_profile()
        self.client.post("/api/analyses/job-match", json={
            "job_description": "Looking for a data analyst with SQL skills.", "profile_id": pid})
        prompt = mock_generate.call_args[0][0][0]["text"]
        self.assertNotIn("alex@example.com", prompt)
        self.assertNotIn("90000", prompt)

    @patch.object(talentverse, "generate_json")
    def test_incomplete_ai_analysis_is_rejected_and_not_saved(self, mock_generate):
        mock_generate.return_value = {"session_summary": "only this"}
        response = self.client.post("/api/analyses/interview-feedback", json={
            "notes": "I stumbled on the system design question and rambled."})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/analyses").json["analyses"], [])

    # ---- audio ---------------------------------------------------------------------------
    def test_audio_rejects_missing_and_bad_type(self):
        self.assertEqual(self.client.post("/api/profiles/audio/extract").status_code, 400)
        bad = self.client.post("/api/profiles/audio/extract", data={"audio": (io.BytesIO(b"hi"), "x.txt")},
                               content_type="multipart/form-data")
        self.assertEqual(bad.status_code, 400)

    @patch.object(talentverse, "extract_profile_from_audio")
    def test_audio_extract_returns_preview_only(self, mock_extract):
        mock_extract.return_value = talentverse.validate_profile(self._profile(full_name="Sam"))
        response = self.client.post("/api/profiles/audio/extract",
                                    data={"audio": (io.BytesIO(b"abc"), "intro.mp3", "audio/mpeg")},
                                    content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["preview"]["full_name"], "Sam")
        self.assertEqual(self.client.get("/api/profiles").json["profiles"], [])


if __name__ == "__main__":
    unittest.main()
