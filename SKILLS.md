# AI Red Teaming Lab Builder (Advanced)

## Objective

Build TWO environments:

1. Vulnerable AI System (lab-vuln)
2. Secure AI System with Guardrails (lab-secure)

Both must have identical functionality but different security controls.

---

## Tech Stack

* Backend: FastAPI (Python)
* Frontend: Simple Chat UI (HTML/JS or Streamlit)
* DB: SQLite
* LLM: OpenAI API (pluggable)
* Deployment: Docker Compose (two services)

---

## Core Architecture

### Vulnerable Flow

User → API → LLM → Tools/DB (direct execution)

### Secure Flow

User → API → LLM Orchestrator → Policy Engine → Tools/DB

---

## Features

* Chat endpoint `/chat`

* Query endpoint `/query`

* Tool system:

  * run_sql(query)
  * read_file(path)
  * get_user_data(user_id)

* Shared dataset across both environments

---

## Vulnerabilities (Vulnerable Environment)

### V1: Indirect Prompt Injection

* Use RAG (documents as context)
* Include malicious document with hidden instructions
* No context sanitization

### V2: Insecure Output Handling

* LLM generates structured JSON with SQL
* Backend executes without validation

### V3: Sensitive Data Exposure

* Secrets stored in:

  * system prompt
  * local file (secrets.txt)
  * mock environment variables

### V4: Excessive Agency

* LLM can call tools freely
* No permission checks

---

## Secure Environment (Guardrails)

### Prompt Security

* Separate system/user/context prompts
* Enforce instruction hierarchy

### Context Filtering

* Strip executable instructions from documents
* Tag data vs instructions

### Output Validation

* Enforce strict JSON schema
* Reject unsafe SQL patterns

### Tool Security

* Role-based tool access
* Require intent validation
* Allowlist operations only

### Data Protection

* Remove secrets from prompts
* Restrict file access
* Output redaction

### Policy Engine

* Evaluate:

  * user intent
  * risk level
  * requested tool
* Block unsafe actions

---

## UI Requirements

* Two separate URLs:

  * /vuln
  * /secure

* Display:

  * LLM input
  * LLM output
  * Tool calls
  * Policy decisions (secure env)

---

## Logging

* Log all:

  * prompts
  * outputs
  * tool usage
  * blocked actions

---

## Deliverables

* Fully working dual-environment app
* Dockerized setup
* Sample dataset
* Attack walkthroughs
* Defense walkthroughs

---

## Constraints

* Educational use only
* Mock data only
* No real secrets

---

## Bonus

* Difficulty levels for attacks
* Guided hints
* Auto-grading scripts
