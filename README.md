# AI Red Teaming Lab

Graduate AI security lab with two FastAPI environments:

- `lab-vuln`: intentionally vulnerable
- `lab-secure`: same user workflow with guardrails

The lab now runs as a four-level CTF. Students interact with the assistant, recover flags in the format `ENPM604{...}`, and submit them to unlock the next level. The secure environment preserves the same functionality, but blocks or redacts the unsafe behavior.

## What Changed

- Student view is now challenge-first and chat-first.
- Starter prompts are not exposed in the UI.
- Raw LLM traces moved to instructor-only debug routes.
- Four challenge levels map directly to four OWASP LLM Top 10 risks.
- Ollama is now the default backend, with deterministic fallback behavior if Ollama is unavailable.
- Direct "give me the flag" style prompts, reverse-order tricks, and story/song bypasses are intentionally resisted.

## Challenge Map

1. `LLM01 Prompt Injection`
   Level 1: `Poisoned Vendor Bulletin`
2. `LLM02 Insecure Output Handling`
   Level 2: `Unsafe Query Pivot`
3. `LLM06 Sensitive Information Disclosure`
   Level 3: `Secret Archive Disclosure`
4. `LLM08 Excessive Agency`
   Level 4: `Unauthorized Support Handoff`

Each level contains a hidden flag in the format `ENPM604{...}`.

## Student Routes

- Vulnerable lab: [http://localhost:8000/vuln](http://localhost:8000/vuln)
- Secure lab: [http://localhost:8001/secure](http://localhost:8001/secure)

## Instructor Debug Routes

- Vulnerable debug: [http://localhost:8000/vuln/debug](http://localhost:8000/vuln/debug)
- Secure debug: [http://localhost:8001/secure/debug](http://localhost:8001/secure/debug)

The debug pages expose LLM input, LLM output, tool calls, and policy decisions. The student pages do not.

## Folder Structure

```text
.
├── Dockerfile
├── README.md
├── docker-compose.yml
├── requirements.txt
├── data
│   ├── documents
│   │   ├── compliance_digest.txt
│   │   ├── operations_playbook.txt
│   │   ├── product_faq.txt
│   │   ├── support_handoff.txt
│   │   └── vendor_bulletin.txt
│   └── secrets.txt
├── lab
│   ├── apps
│   │   ├── common.py
│   │   ├── secure.py
│   │   └── vuln.py
│   ├── secure
│   │   ├── context_filter.py
│   │   ├── policy.py
│   │   ├── prompts.py
│   │   ├── service.py
│   │   ├── tools.py
│   │   └── validators.py
│   ├── shared
│   │   ├── challenges.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging_utils.py
│   │   ├── rag.py
│   │   ├── runtime.py
│   │   ├── schemas.py
│   │   └── llm
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── mock_backend.py
│   │       ├── ollama_backend.py
│   │       └── openai_backend.py
│   ├── static
│   │   ├── app.js
│   │   ├── debug.js
│   │   └── styles.css
│   ├── templates
│   │   ├── debug.html
│   │   └── student.html
│   └── vulnerable
│       ├── prompts.py
│       ├── service.py
│       └── tools.py
├── logs
└── scripts
    ├── grade_lab.py
    └── init_db.py
```

## Setup

### Docker

Default run with Ollama-first behavior:

```bash
docker compose up --build
```

Then pull the model once inside the Ollama service:

```bash
docker compose exec ollama ollama pull llama3.2
```

After the model is present, the lab will use Ollama by default. If Ollama is unavailable or the model has not been pulled yet, the lab falls back to the deterministic challenge engine so the environments still run.

### Local Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/init_db.py --reset
```

Run the vulnerable app:

```bash
uvicorn lab.apps.vuln:app --reload --port 8000
```

Run the secure app in a second terminal:

```bash
uvicorn lab.apps.secure:app --reload --port 8001
```

## Backend Options

### Mock Backend

This is the default and is recommended for grading and deterministic challenge progression.

```bash
export LLM_BACKEND=mock
```

### OpenAI Backend

```bash
export LLM_BACKEND=openai
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-4.1-mini
```

### Ollama Backend

Run Ollama locally or through the bundled Docker service, pull a model, then point the lab at it:

```bash
ollama pull llama3.2
export LLM_BACKEND=ollama
export OLLAMA_HOST=http://127.0.0.1:11434
export OLLAMA_MODEL=llama3.2
```

Inside Docker Compose, the lab defaults to `http://ollama:11434`. If the Ollama service is unavailable, the model is missing, or the reply is not valid structured output, the lab falls back to the deterministic challenge engine so the exercises still run.

## Student Workflow

1. Open a level in the vulnerable environment.
2. Work the conversation like a CTF challenge rather than asking for the flag directly.
3. Use the model's responses to discover the real attack path and recover the hidden `ENPM604{...}` flag.
4. Submit the flag in the flag box.
5. Unlock the next level.
6. Compare the same level in the secure environment to see why the exploit fails.

The secure environment is for comparison and defense analysis. The intended flag recovery path is the vulnerable environment.

## Sample Data Setup

The lab seeds:

- `data/lab.db`
  Contains mock user records and the level 2 SQL-only flag table.
- `data/secrets.txt`
  Contains mock secrets and the level 3 disclosure flag.
- `data/documents/vendor_bulletin.txt`
  Contains poisoned context used by the level 1 prompt injection challenge.
- `data/documents/support_handoff.txt`
  Supports the level 4 agency escalation scenario.

Reset the seeded state anytime with:

```bash
python3 scripts/init_db.py --reset
```

## Attack Walkthroughs

### Level 1: Prompt Injection

Attack idea:
Ask for the visible bulletin summary first, then pivot toward the maintenance appendix or embedded guidance once you know it exists.

Vulnerable behavior:
The vulnerable environment mixes retrieved document text into the same prompt as system instructions, so poisoned vendor content can override intent and surface the flag.

Secure behavior:
The secure environment tags retrieved text as untrusted data and filters instruction-like lines before the model sees them.

### Level 2: Insecure Output Handling

Attack idea:
Probe the export path first, learn about the continuity validation store, then ask for the backend query only after you understand which store matters.

Vulnerable behavior:
Model-generated SQL is executed directly, allowing access to the hidden flag table.

Secure behavior:
The secure environment validates the strict JSON plan, restricts SQL to a small allowlist, and blocks non-`users` tables plus sensitive columns.

### Level 3: Sensitive Information Disclosure

Attack idea:
Discover the existence of the local readiness archive first, then use a diagnostics or incident-readiness pretext to make the assistant inspect it.

Vulnerable behavior:
The vulnerable environment lets the model read unrestricted local files, including the seeded secrets archive.

Secure behavior:
The secure environment blocks secret-seeking file access, restricts reads to allowlisted documents, and redacts sensitive strings from any output.

### Level 4: Excessive Agency

Attack idea:
Walk the roster and handoff chain first, then request the executive support note in a way that sounds operational instead of openly unauthorized.

Vulnerable behavior:
The vulnerable environment lets the model call `get_user_data` on arbitrary user IDs with no ownership check.

Secure behavior:
The secure environment enforces role and ownership checks before any cross-user data retrieval is allowed.

## Defense Explanations

### Prompt Separation

- Vulnerable: instructions, retrieved context, and user input are mixed together.
- Secure: system prompt, user request, and retrieved context remain separated with explicit hierarchy.

### Context Filtering

- Vulnerable: untrusted RAG documents reach the model unchanged.
- Secure: suspicious instruction-like lines are replaced with `[FILTERED INSTRUCTION REMOVED]`.

### Output Validation

- Vulnerable: model output is parsed and executed directly.
- Secure: output must match the strict planning schema before any tool logic can run.

### Tool Guardrails

- Vulnerable: tool calls run with attacker-controlled arguments and no policy gate.
- Secure: policy engine, SQL validation, file-path validation, and ownership checks gate tool execution.

### Output Redaction

- Vulnerable: secrets and flags can flow straight into the final answer.
- Secure: sensitive strings, recovery codes, and `ENPM604{...}` tokens are redacted before response delivery.

## Logs

Each environment writes JSONL logs under `logs/`:

- `logs/vulnerable.jsonl`
- `logs/secure.jsonl`

These include prompt records, model output, tool usage, and blocked actions.

## Verification

Run the grader:

```bash
python3 scripts/grade_lab.py
```

## Notes

- All secrets, users, and flags are mock data for teaching only.
- `ollama` is now the default path for a more interactive model feel.
- `mock` is still available when you want stable classroom outcomes or grading.
- `openai` remains optional if you want a hosted model instead.
