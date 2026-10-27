const resumeText = document.getElementById("resumeText");
const charCount = document.getElementById("charCount");
const extractBtn = document.getElementById("extractBtn");
const statusBox = document.getElementById("status");
const emptyState = document.getElementById("emptyState");
const profileResult = document.getElementById("profileResult");
const saveBadge = document.getElementById("saveBadge");
const savedProfiles = document.getElementById("savedProfiles");

const sampleResume = `A. Ramcharan
Email: ramcharan@example.com | Phone: +91 90000 00000
Professional Summary
Computer Science undergraduate specializing in Generative AI, interested in machine learning, NLP, and building practical AI applications.

Skills
Python, Java, JavaScript, React, Node.js, Flask, Pandas, NumPy, scikit-learn, MySQL, Git, GitHub, REST APIs, prompt engineering.

Education
B.Tech in Computer Science and Engineering (Generative AI), Lovely Professional University, 2024–Present.
Intermediate, Sai Sri Chaitanya Junior College, 2022–2024.

Projects
RAG Document Assistant — Built a retrieval-augmented generation prototype to answer questions from supplied documents. Technologies: Python, embeddings, vector search, LLM API.
Vahan Bazar — Designed a two-wheeler marketplace prototype with search and filtering. Technologies: HTML, CSS, JavaScript, Node.js, MySQL.

Certifications
Microsoft Azure Fundamentals (AZ-900), Azure AI Fundamentals (AI-900), Azure Data Fundamentals (DP-900).`;

resumeText.addEventListener("input", () => {
  charCount.textContent = `${resumeText.value.length.toLocaleString()} / 30,000 characters`;
});

document.getElementById("sampleBtn").addEventListener("click", () => {
  resumeText.value = sampleResume;
  resumeText.dispatchEvent(new Event("input"));
  showStatus("Sample resume loaded. Replace it with your own text before using real information.", "");
});

function showStatus(message, type) {
  statusBox.textContent = message;
  statusBox.className = `status ${type || ""}`;
}

function safeText(value) {
  return value === null || value === undefined || value === "" ? "Not provided" : String(value);
}

function makeElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function addSection(container, title, contentNode) {
  const section = makeElement("section", "result-block");
  section.appendChild(makeElement("h4", "", title));
  section.appendChild(contentNode);
  container.appendChild(section);
}

function renderProfile(profile) {
  emptyState.classList.add("hidden");
  profileResult.classList.remove("hidden");
  profileResult.replaceChildren();

  const top = makeElement("div", "profile-top");
  top.appendChild(makeElement("h3", "", safeText(profile.full_name)));
  top.appendChild(makeElement("div", "contact-line", [profile.email, profile.phone].filter(Boolean).join(" · ") || "No contact details found"));
  top.appendChild(makeElement("div", "saved-confirm", `✓ Saved to database · Profile #${profile.id}`));
  profileResult.appendChild(top);

  addSection(profileResult, "Professional summary", makeElement("p", "", profile.professional_summary));

  const chips = makeElement("div", "chips");
  if (profile.skills.length) profile.skills.forEach(skill => chips.appendChild(makeElement("span", "chip", skill)));
  else chips.appendChild(makeElement("p", "", "No skills were identified."));
  addSection(profileResult, `Skills · ${profile.skills.length}`, chips);

  const education = makeElement("div");
  if (profile.education.length) {
    profile.education.forEach(item => {
      const row = makeElement("div", "detail-item");
      row.appendChild(makeElement("strong", "", safeText(item.qualification)));
      row.appendChild(makeElement("small", "", [item.institution, item.dates].filter(Boolean).join(" · ")));
      if (item.details) row.appendChild(makeElement("small", "", item.details));
      education.appendChild(row);
    });
  } else education.appendChild(makeElement("p", "", "No education details identified."));
  addSection(profileResult, "Education", education);

  const experience = makeElement("div");
  if (profile.experience.length) {
    profile.experience.forEach(item => {
      const row = makeElement("div", "detail-item");
      row.appendChild(makeElement("strong", "", `${safeText(item.role)} — ${safeText(item.organization)}`));
      row.appendChild(makeElement("small", "", safeText(item.dates)));
      if (item.highlights && item.highlights.length) {
        const ul = makeElement("ul", "bullet-list");
        item.highlights.forEach(point => ul.appendChild(makeElement("li", "", point)));
        row.appendChild(ul);
      }
      experience.appendChild(row);
    });
  } else experience.appendChild(makeElement("p", "", "No work experience identified."));
  addSection(profileResult, "Experience", experience);

  const projects = makeElement("div");
  if (profile.projects.length) {
    profile.projects.forEach(item => {
      const row = makeElement("div", "detail-item");
      row.appendChild(makeElement("strong", "", safeText(item.name)));
      row.appendChild(makeElement("small", "", safeText(item.description)));
      if (item.technologies && item.technologies.length) row.appendChild(makeElement("small", "", `Technologies: ${item.technologies.join(", ")}`));
      projects.appendChild(row);
    });
  } else projects.appendChild(makeElement("p", "", "No projects identified."));
  addSection(profileResult, "Projects", projects);

  const certs = makeElement("div", "chips");
  if (profile.certifications.length) profile.certifications.forEach(cert => certs.appendChild(makeElement("span", "chip", cert)));
  else certs.appendChild(makeElement("p", "", "No certifications identified."));
  addSection(profileResult, "Certifications", certs);

  if (profile.missing_information.length) {
    const missing = makeElement("div", "missing-note");
    missing.textContent = "Review missing or unclear information: " + profile.missing_information.join("; ");
    addSection(profileResult, "Review before relying on this profile", missing);
  }
  saveBadge.textContent = "Saved · #" + profile.id;
  saveBadge.classList.add("saved");
  setActiveProfile(profile);
}

async function createProfile() {
  const text = resumeText.value.trim();
  if (text.length < 80) {
    showStatus("Please paste at least 80 characters of resume text before extracting.", "error");
    return;
  }
  extractBtn.disabled = true;
  extractBtn.classList.add("loading");
  extractBtn.querySelector("span").textContent = "Extracting";
  showStatus("Sending resume to the AI, validating the structured result, and saving it…", "");
  try {
    const response = await fetch("/api/profiles", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({resume_text: text})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The request failed.");
    renderProfile(result.profile);
    showStatus(result.message, "success");
    await loadSavedProfiles();
  } catch (error) {
    showStatus(error.message || "Something went wrong. Please try again.", "error");
  } finally {
    extractBtn.disabled = false;
    extractBtn.classList.remove("loading");
    extractBtn.querySelector("span").textContent = "Extract profile";
  }
}

async function loadSavedProfiles() {
  savedProfiles.replaceChildren(makeElement("div", "loading-line", "Loading saved profiles…"));
  try {
    const response = await fetch("/api/profiles");
    const data = await response.json();
    savedProfiles.replaceChildren();
    if (!response.ok) throw new Error(data.error || "Could not load saved profiles.");
    if (!data.profiles.length) {
      savedProfiles.appendChild(makeElement("div", "no-saved", "No profiles saved yet. Extract a resume to create the first record."));
      return;
    }
    data.profiles.forEach(profile => {
      const card = makeElement("article", "saved-card");
      card.classList.toggle("selected", profile.id === activeProfileId);
      card.appendChild(makeElement("h3", "", safeText(profile.full_name)));
      card.appendChild(makeElement("p", "", `${profile.skills.length} skills · ${profile.projects.length} projects`));
      card.appendChild(makeElement("p", "", new Date(profile.created_at).toLocaleString()));
      const button = makeElement("button", "", "View profile");
      button.type = "button";
      button.addEventListener("click", () => {
        renderProfile(profile);
        document.querySelectorAll(".saved-card").forEach(c => c.classList.toggle("selected", c === card));
        document.querySelector(".results-panel").scrollIntoView({behavior: "smooth", block: "start"});
      });
      card.appendChild(button);
      savedProfiles.appendChild(card);
    });
  } catch (error) {
    savedProfiles.replaceChildren(makeElement("div", "no-saved", error.message));
  }
}

extractBtn.addEventListener("click", createProfile);
document.getElementById("refreshBtn").addEventListener("click", loadSavedProfiles);
loadSavedProfiles();

// ---------------------------------------------------------------- audio intake
const audioFile = document.getElementById("audioFile");
const audioBtn = document.getElementById("audioBtn");

audioBtn.addEventListener("click", async () => {
  const file = audioFile.files[0];
  if (!file) { showStatus("Choose an audio file first.", "error"); return; }
  if (file.size > 8 * 1024 * 1024) { showStatus("Audio file is too large. Keep it under 8 MB.", "error"); return; }
  audioBtn.disabled = true;
  showStatus("Uploading audio, extracting the profile, and saving it…", "");
  try {
    const form = new FormData();
    form.append("audio", file);
    const response = await fetch("/api/profiles/audio", {method: "POST", body: form});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The request failed.");
    renderProfile(result.profile);
    showStatus(result.message, "success");
    await loadSavedProfiles();
  } catch (error) {
    showStatus(error.message || "Something went wrong. Please try again.", "error");
  } finally {
    audioBtn.disabled = false;
  }
});

// ---------------------------------------------------------------- career tools
const TOOLS = {
  "skill-gap": {field: "career_goal", label: "YOUR CAREER GOAL", placeholder: "e.g. Become a machine learning engineer at a product company within 12 months.", button: "Build skill-gap map", render: renderSkillGap},
  "job-match": {field: "job_description", label: "JOB DESCRIPTION", placeholder: "Paste the full job description here…", button: "Compare with profile", render: renderJobMatch},
  "portfolio-brief": {field: "interests", label: "YOUR INTERESTS", placeholder: "e.g. I enjoy NLP and want a project that helps students with their studies.", button: "Create project brief", render: renderPortfolio},
  "interview-feedback": {field: "notes", label: "INTERVIEW PRACTICE NOTES", placeholder: "Paste your notes: questions asked, how you answered, where you struggled…", button: "Structure my feedback", render: renderInterview},
};
const toolInput = document.getElementById("toolInput");
const toolLabel = document.getElementById("toolLabel");
const toolBtn = document.getElementById("toolBtn");
const toolStatus = document.getElementById("toolStatus");
const toolResult = document.getElementById("toolResult");
const activeProfileLabel = document.getElementById("activeProfile");
let activeKind = "skill-gap";
let activeProfileId = null;

function setActiveProfile(profile) {
  activeProfileId = profile.id;
  activeProfileLabel.textContent = `Profile #${profile.id} · ${safeText(profile.full_name)}`;
}

function setTool(kind) {
  activeKind = kind;
  const tool = TOOLS[kind];
  document.querySelectorAll(".tab").forEach(tab => {
    const on = tab.dataset.kind === kind;
    tab.classList.toggle("active", on);
    tab.setAttribute("aria-selected", String(on));
  });
  toolLabel.textContent = tool.label;
  toolInput.placeholder = tool.placeholder;
  toolInput.value = "";
  toolBtn.querySelector("span").textContent = tool.button;
  toolStatus.textContent = "";
  toolStatus.className = "status";
}
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => setTool(tab.dataset.kind)));

function listNode(items) {
  const ul = makeElement("ul", "bullet-list");
  items.forEach(item => ul.appendChild(makeElement("li", "", item)));
  return ul;
}

function chipsNode(items) {
  const wrap = makeElement("div", "chips");
  if (!items.length) wrap.appendChild(makeElement("p", "", "None identified."));
  items.forEach(item => wrap.appendChild(makeElement("span", "chip", item)));
  return wrap;
}

function itemNode(title, lines) {
  const row = makeElement("div", "detail-item");
  row.appendChild(makeElement("strong", "", title));
  lines.filter(Boolean).forEach(line => row.appendChild(makeElement("small", "", line)));
  return row;
}

function stack(items) {
  const wrap = makeElement("div");
  items.forEach(node => wrap.appendChild(node));
  return wrap;
}

function renderSkillGap(r) {
  addSection(toolResult, `Target role · ${r.target_role}`, makeElement("p", "", r.readiness_summary));
  addSection(toolResult, "Strengths to leverage", chipsNode(r.strengths_to_leverage));
  addSection(toolResult, "Skill gaps", stack(r.skill_gaps.map(g => {
    const row = itemNode(g.skill, [`${g.current_level} → ${g.required_level}`, g.reason]);
    row.firstChild.appendChild(makeElement("span", `tag-${g.priority}`, `  · ${g.priority} priority`));
    return row;
  })));
  addSection(toolResult, "Milestone plan", stack(r.milestones.map((m, i) => {
    const row = itemNode(`${i + 1}. ${m.title} (${m.timeframe})`, [`Focus: ${m.focus_skills.join(", ")}`]);
    row.appendChild(listNode(m.activities));
    row.appendChild(makeElement("small", "", `Done when: ${m.success_criteria}`));
    return row;
  })));
}

function renderJobMatch(r) {
  const head = makeElement("div");
  head.appendChild(makeElement("div", "score", `${r.match_percentage}%`));
  head.appendChild(makeElement("p", "", r.overall_assessment));
  addSection(toolResult, `Match · ${r.job_title}`, head);
  addSection(toolResult, "Required skills", chipsNode(r.required_skills));
  addSection(toolResult, "Preferred skills", chipsNode(r.preferred_skills));
  addSection(toolResult, "Matched in your profile", stack(r.matched_skills.map(m => itemNode(m.skill, [m.evidence]))));
  addSection(toolResult, "Missing skills", chipsNode(r.missing_skills));
  addSection(toolResult, "Responsibilities", listNode(r.responsibilities));
  addSection(toolResult, "Experience expected", makeElement("p", "", r.experience_expectation));
  addSection(toolResult, "Recommendations", listNode(r.recommendations));
}

function renderPortfolio(r) {
  addSection(toolResult, r.title, makeElement("p", "", r.pitch));
  addSection(toolResult, "Problem", makeElement("p", "", r.problem_statement));
  addSection(toolResult, "Target users", makeElement("p", "", r.target_users));
  addSection(toolResult, "Core features", listNode(r.core_features));
  addSection(toolResult, "Stretch features", listNode(r.stretch_features));
  addSection(toolResult, "Tech stack", chipsNode(r.tech_stack));
  addSection(toolResult, "Skills demonstrated", chipsNode(r.skills_demonstrated));
  addSection(toolResult, "New skills to learn", chipsNode(r.new_skills_to_learn));
  addSection(toolResult, "Build steps", stack(r.build_steps.map(s => itemNode(s.step, [s.estimated_time]))));
  addSection(toolResult, "Deliverables", listNode(r.deliverables));
  addSection(toolResult, "Evaluation criteria", listNode(r.evaluation_criteria));
}

function renderInterview(r) {
  addSection(toolResult, "Session summary", makeElement("p", "", r.session_summary));
  addSection(toolResult, "Strengths", stack(r.strengths.map(s => itemNode(s.point, [s.evidence]))));
  addSection(toolResult, "Improvement areas", stack(r.improvement_areas.map(a => itemNode(a.area, [a.issue, `Try: ${a.suggestion}`]))));
  addSection(toolResult, "Next practice tasks", stack(r.next_practice_tasks.map(t => itemNode(t.task, [`Goal: ${t.goal}`, t.duration]))));
}

function setToolStatus(message, type) {
  toolStatus.textContent = message;
  toolStatus.className = `status ${type || ""}`;
}

toolBtn.addEventListener("click", async () => {
  const tool = TOOLS[activeKind];
  const text = toolInput.value.trim();
  if (activeKind !== "interview-feedback" && activeProfileId === null) {
    setToolStatus("Select a saved profile first (View profile on a card below, or extract a new one).", "error");
    return;
  }
  if (text.length < 20) { setToolStatus("Please enter at least 20 characters.", "error"); return; }
  toolBtn.disabled = true;
  toolBtn.classList.add("loading");
  setToolStatus("Generating and saving…", "");
  try {
    const body = {[tool.field]: text};
    if (activeProfileId !== null) body.profile_id = activeProfileId;
    const response = await fetch(`/api/analyses/${activeKind}`, {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The request failed.");
    toolResult.replaceChildren();
    tool.render(data.analysis.result);
    setToolStatus(`${data.message} (#${data.analysis.id})`, "success");
  } catch (error) {
    setToolStatus(error.message || "Something went wrong. Please try again.", "error");
  } finally {
    toolBtn.disabled = false;
    toolBtn.classList.remove("loading");
  }
});

setTool("skill-gap");

// ---------------------------------------------------------------- AI status
(async function showAiStatus() {
  const pill = document.getElementById("aiStatus");
  const text = document.getElementById("aiStatusText");
  try {
    const health = await (await fetch("/api/health")).json();
    pill.classList.add(health.ai_configured ? "ok" : "warn");
    text.textContent = health.ai_configured ? "AI ready" : "AI key missing";
    pill.title = health.ai_configured ? "Gemini API key detected" : "Add GEMINI_API_KEY to .env and restart the server";
  } catch {
    pill.classList.add("warn");
    text.textContent = "Server unreachable";
  }
})();
