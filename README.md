# TalentVerse — Skills & Career Intelligence

A full-stack Generative AI mini-project for CA3: Generative AI Foundations. TalentVerse extracts a structured candidate profile from resume text, validates the output, saves it in SQLite, and displays the saved record.

## Chosen automation idea

**Option 9 — TalentVerse:** Transform a resume or audio introduction into a structured skills and experience profile.

All five Option 9 capabilities are implemented:

1. **Resume / audio introduction → structured profile** (pasted text, or an uploaded audio file transcribed by Groq Whisper, then extracted).
2. **Career goal → skill-gap map and milestone learning plan** (`skill-gap`).
3. **Job description → extracted requirements compared with the profile** (`job-match`).
4. **Interests + skills → portfolio project brief** (`portfolio-brief`).
5. **Interview practice notes → strengths, improvement areas, next-practice tasks** (`interview-feedback`).

Every AI result is requested against a response schema, validated on the server, and saved to SQLite before it is returned.

## Architecture

```text
Resume text / audio in browser
        |
        v
Flask POST /api/profiles/extract  (or /audio/extract)
        |
        v
Groq API (JSON mode + schema)
        |
        v
JSON parsing + application validation  ->  per-field validation report
        |
        v
PREVIEW in browser (editable, NOT saved)  --- user clicks Confirm ---+
                                                                      v
                                       Flask POST /api/profiles (create) or PUT /api/profiles/<id> (update)
                                                                      |
                                                  strict re-validation + SQLite INSERT / UPDATE
                                                                      v
                                       Saved/updated record returned and shown with confirmation
```

Nothing is written to the database until the user confirms the preview. The save/update endpoints reject requests without `"confirmed": true` and re-validate the submitted profile, so the browser cannot bypass validation.

## Stack

- Frontend: HTML, CSS, vanilla JavaScript
- Backend: Python + Flask REST API
- Generative AI: Groq API (GPT-OSS 120B in JSON mode, schema supplied in the prompt; Whisper for audio)
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

6. Copy `.env.example` to `.env` and add your Groq API key. Get a key from the [Groq console](https://console.groq.com/keys). Keep `.env` private and do not upload it to GitHub.

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
| POST | `/api/profiles/extract` | Resume text → AI extraction → validated **preview** + validation report (nothing saved) |
| POST | `/api/profiles/audio/extract` | Multipart upload (`audio` field, ≤ 8 MB) → validated **preview** (nothing saved) |
| POST | `/api/profiles` | **Create**: body `{profile, source, confirmed: true}`; strict re-validation, then INSERT |
| PUT | `/api/profiles/<id>` | **Update**: body `{profile, confirmed: true}`; strict re-validation, then UPDATE |
| GET | `/api/profiles` | List the 50 newest saved profiles (email/phone masked) |
| DELETE | `/api/profiles/<id>?confirmed=true` | Delete a profile and its saved analyses |
| GET | `/api/profiles/<id>` | Retrieve one saved profile in full, with its validation report |
| POST | `/api/analyses/<kind>` | `kind` = `skill-gap`, `job-match`, `portfolio-brief` or `interview-feedback`. Body: `profile_id` plus `career_goal` / `job_description` / `interests` / `notes` (profile optional for interview feedback) |
| GET | `/api/analyses?kind=&profile_id=` | List the 50 newest saved analyses |

Example preview request (`POST /api/profiles/extract`):

```json
{
  "resume_text": "Paste resume text with at least 80 characters here..."
}
```

Error handling: input too short/long → `400`; unsupported or oversized audio → `400`; AI service unreachable or erroring → `502`; AI output that fails the schema → `422`; save/update without `confirmed: true` → `400`; unknown profile id → `404`. The frontend shows each message and saves nothing.

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

The model is instructed not to invent missing resume facts: absent values come back as `null` / empty lists and are explained in `missing_information`. The server parses the JSON and checks required fields, field types, the shape of every education/experience/project entry, and email/phone format before anything is stored. An email or phone that is malformed is discarded (and noted) rather than kept; one that does not appear in the source text is flagged as a warning in the preview. If validation or AI processing fails, the API returns an error and does not save the profile.

## Safeguards for sensitive data

- **Preview + explicit confirmation** before any database write (create and update).
- **Raw resume text and audio are never stored** — only the confirmed structured profile is.
- **Data minimisation:** email and phone are not sent to the AI for the career tools (skill gap, job match, etc.).
- **Masked lists:** email/phone are partially hidden in the saved-profiles list and shown in full only when a profile is opened.
- API responses are sent with `Cache-Control: no-store`; uploads and text are size-limited.

## Testing

Run:

```powershell
python -m unittest discover -s tests -v
```

24 tests cover: short/missing input, invalid and malformed AI output, AI-service failure (502, nothing saved), the extract-preview-confirm-save flow, save/update refused without confirmation, update of an existing record, contact masking, and that raw source text is never stored. The AI call is mocked in the tests so they do not consume API quota; the flow was also verified manually against the live Groq API.

For your submission, capture evidence of:
1. **Success flow:** paste the sample resume → preview with validation checks → Confirm → "Saved to database · Profile #N".
2. **Update flow:** Edit profile → change a field → Confirm → "Updated in database".
3. **Error cases:** the short-input error, an invalid email on edit (rejected), and (optional) the AI-unreachable message.
4. The saved-profiles list after refresh (loaded from the database).

## Deployment on Render

1. Push the project folder to a GitHub repository. Do not commit `.env` or `talentverse.db`.
2. In Render, create a new **Web Service** connected to the repository.
3. Use the included `render.yaml`, or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Add `GROQ_API_KEY` in Render's environment settings.
5. Deploy and test the public frontend URL and `/api/health`.

**Database note:** the included Render config points SQLite at `/tmp`, which may be reset when the service restarts or redeploys. This is fine for a short demo but not durable production storage. For a reliable submission, use a persistent disk or a managed PostgreSQL database and update the database layer accordingly. Verify the deployed app yourself before submitting the URL.

## Limitations and responsible use

- Resume content is sent to the Groq API for processing. Use sample/anonymized data during demonstrations and obtain permission before processing another person's resume.
- The project does not authenticate users; do not use it to store sensitive real-world candidate data in a public deployment.
- Extraction can be incomplete or incorrect. Candidates should review the profile before relying on it.
- The app extracts and stores information; it does not make hiring decisions or score candidate worth.
- Input support is pasted text and uploaded audio files. PDF/DOCX parsing, authentication and deleting records are possible future improvements.
- Skill-gap levels, match percentages and project briefs are AI-generated guidance, not assessments of the candidate's worth or hiring decisions.

## CA3 demonstration flow

1. Open the deployed frontend.
2. Paste a sample resume and click **Extract profile**.
3. Explain that the prompt and JSON schema guide the model's output.
4. Show the preview: validation checks, missing fields left empty, editable values. Click **Confirm & save**.
5. Refresh the saved profiles list, open the profile, use **Edit profile** to update it.
6. Submit a very short input and show the validation error.
7. Explain the SQLite table and discuss limitations.

Remember to submit the deployed frontend URL with your report. Deployment is compulsory under the CA3 brief.
