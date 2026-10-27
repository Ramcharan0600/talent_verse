# TalentVerse — Skills & Career Intelligence

A full-stack Generative AI mini-project for CA3: Generative AI Foundations. TalentVerse extracts a structured candidate profile from resume text, validates the output, saves it in SQLite, and displays the saved record.

## Chosen automation idea

**Option 9 — TalentVerse:** Transform a resume or audio introduction into a structured skills and experience profile.

All five Option 9 capabilities are implemented:

1. **Resume / audio introduction → structured profile** (pasted text, or an uploaded audio file transcribed and extracted by Gemini).
2. **Career goal → skill-gap map and milestone learning plan** (`skill-gap`).
3. **Job description → extracted requirements compared with the profile** (`job-match`).
4. **Interests + skills → portfolio project brief** (`portfolio-brief`).
5. **Interview practice notes → strengths, improvement areas, next-practice tasks** (`interview-feedback`).

Every AI result is requested against a response schema, validated on the server, and saved to SQLite before it is returned.

## Architecture

```text
Resume text in browser
        |
        v
Flask POST /api/profiles
        |
        v
Gemini API with JSON response schema
        |
        v
JSON parsing + application validation
        |
        v
SQLite INSERT
        |
        v
Saved profile returned to frontend
        |
        v
Profile + saved-profile list rendered
```

## Stack

- Frontend: HTML, CSS, vanilla JavaScript
- Backend: Python + Flask REST API
- Generative AI: Gemini API with `responseMimeType: application/json` and a defined response schema
- Validation: JSON parsing and server-side field/type checks
- Database: SQLite
- Deployment: Render configuration included

## Run locally on Windows

1. Install Python 3.10 or newer.
2. Extract this project folder and open it in VS Code.
3. Open PowerShell in the `TalentVerse` folder.
4. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

6. Copy `.env.example` to `.env` and add your Gemini API key. Get a key from [Google AI Studio](https://aistudio.google.com/apikey). Keep `.env` private and do not upload it to GitHub.

7. Start the server:

   ```powershell
   python app.py
   ```

8. Open `http://127.0.0.1:5000`.

If PowerShell blocks virtual-environment activation, run `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then `.venv\Scripts\python.exe app.py`.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health status and whether an AI key is configured |
| POST | `/api/profiles` | Extract, validate, and save a resume profile |
| GET | `/api/profiles` | List the 50 newest saved profiles |
| GET | `/api/profiles/<id>` | Retrieve one saved profile |
| POST | `/api/profiles/audio` | Multipart upload (`audio` field, ≤ 8 MB) → extract, validate, save profile |
| POST | `/api/analyses/<kind>` | `kind` = `skill-gap`, `job-match`, `portfolio-brief` or `interview-feedback`. Body: `profile_id` plus `career_goal` / `job_description` / `interests` / `notes` (profile optional for interview feedback) |
| GET | `/api/analyses?kind=&profile_id=` | List the 50 newest saved analyses |

Example request:

```json
{
  "resume_text": "Paste resume text with at least 80 characters here..."
}
```

## Database design

The `profiles` table stores:
- `id`: primary key
- `full_name`, `email`, `phone`
- `professional_summary`
- `skills_json`, `education_json`, `experience_json`, `projects_json`, `certifications_json`, `missing_information_json`
- `source_text`: original submitted text
- `created_at`: UTC timestamp

The arrays/objects are stored as JSON strings in SQLite to keep this mini-project portable. For a larger production application, consider normalized related tables and user authentication.

## Schema-guided output

The backend requests JSON output with these fields:
- `full_name`, `email`, `phone`
- `professional_summary`
- `skills[]`
- `education[]`
- `experience[]`
- `projects[]`
- `certifications[]`
- `missing_information[]`

The model is instructed not to invent missing resume facts. The server parses the JSON and checks required fields, field types, and list structure before inserting anything into the database. If validation or AI processing fails, the API returns an error and does not save the profile.

## Testing

Run:

```powershell
python -m unittest discover -s tests -v
```

Tests cover health status, short/missing input, invalid schema data, and the successful extract/save/retrieve flow (the AI call is mocked in the success test so it does not consume API quota).

For your submission, capture evidence of:
1. A successful resume extraction and the saved profile ID.
2. The saved profiles list after refresh.
3. The short-input validation error.
4. A record in the SQLite database (for example, inspect `talentverse.db` with a SQLite viewer).

## Deployment on Render

1. Push the project folder to a GitHub repository. Do not commit `.env` or `talentverse.db`.
2. In Render, create a new **Web Service** connected to the repository.
3. Use the included `render.yaml`, or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Add `GEMINI_API_KEY` in Render's environment settings.
5. Deploy and test the public frontend URL and `/api/health`.

**Database note:** the included Render config points SQLite at `/tmp`, which may be reset when the service restarts or redeploys. This is fine for a short demo but not durable production storage. For a reliable submission, use a persistent disk or a managed PostgreSQL database and update the database layer accordingly. Verify the deployed app yourself before submitting the URL.

## Limitations and responsible use

- Resume content is sent to the Gemini API for processing. Use sample/anonymized data during demonstrations and obtain permission before processing another person's resume.
- The project does not authenticate users; do not use it to store sensitive real-world candidate data in a public deployment.
- Extraction can be incomplete or incorrect. Candidates should review the profile before relying on it.
- The app extracts and stores information; it does not make hiring decisions or score candidate worth.
- Input support is pasted text and uploaded audio files. PDF/DOCX parsing, authentication, and editing/deleting records are possible future improvements.
- Skill-gap levels, match percentages and project briefs are AI-generated guidance, not assessments of the candidate's worth or hiring decisions.

## CA3 demonstration flow

1. Open the deployed frontend.
2. Paste a sample resume and click **Extract profile**.
3. Explain that the prompt and Gemini response schema guide the model's output.
4. Show the structured fields, server-side validation, and saved confirmation.
5. Refresh the saved profiles list and open the profile.
6. Submit a very short input and show the validation error.
7. Explain the SQLite table and discuss limitations.

Remember to submit the deployed frontend URL with your report. Deployment is compulsory under the CA3 brief.
