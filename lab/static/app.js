const config = window.labConfig;

const STORAGE_KEY = "enpm604-lab-state-v2";
const MAX_TRANSCRIPT_TURNS = 18;

const challenges = [...config.challenges].sort((left, right) => left.level - right.level);
const challengeMap = new Map(challenges.map((challenge) => [challenge.id, challenge]));

const elements = {
  levelTrack: document.getElementById("level-track"),
  challengeMeta: document.getElementById("challenge-meta"),
  challengeTitle: document.getElementById("challenge-title"),
  challengeBrief: document.getElementById("challenge-brief"),
  challengeObjective: document.getElementById("challenge-objective"),
  challengeSuccess: document.getElementById("challenge-success"),
  hintList: document.getElementById("hint-list"),
  revealHint: document.getElementById("reveal-hint"),
  progressText: document.getElementById("progress-text"),
  progressFill: document.getElementById("progress-fill"),
  flagForm: document.getElementById("flag-form"),
  flagInput: document.getElementById("flag-input"),
  flagFeedback: document.getElementById("flag-feedback"),
  transcript: document.getElementById("transcript"),
  chatForm: document.getElementById("chat-form"),
  message: document.getElementById("message"),
  sendButton: document.getElementById("send-button"),
  resetContext: document.getElementById("reset-context"),
};

function buildDefaultState() {
  return {
    solvedIds: [],
    selectedChallengeId: config.defaultChallengeId,
    hintCounts: {},
    transcripts: {
      vulnerable: {},
      secure: {},
    },
  };
}

function loadState() {
  const defaults = buildDefaultState();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaults;
    }
    const parsed = JSON.parse(raw);
    return {
      solvedIds: Array.isArray(parsed.solvedIds) ? parsed.solvedIds.filter((id) => challengeMap.has(id)) : [],
      selectedChallengeId: typeof parsed.selectedChallengeId === "string" ? parsed.selectedChallengeId : defaults.selectedChallengeId,
      hintCounts: parsed && typeof parsed.hintCounts === "object" && parsed.hintCounts ? parsed.hintCounts : {},
      transcripts: {
        vulnerable:
          parsed &&
          parsed.transcripts &&
          typeof parsed.transcripts.vulnerable === "object" &&
          parsed.transcripts.vulnerable
            ? parsed.transcripts.vulnerable
            : {},
        secure:
          parsed &&
          parsed.transcripts &&
          typeof parsed.transcripts.secure === "object" &&
          parsed.transcripts.secure
            ? parsed.transcripts.secure
            : {},
      },
    };
  } catch {
    return defaults;
  }
}

let state = loadState();
let pending = false;

function saveState() {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function unlocked(challenge) {
  if (challenge.level === 1) {
    return true;
  }
  return challenges
    .filter((candidate) => candidate.level < challenge.level)
    .every((candidate) => state.solvedIds.includes(candidate.id));
}

function currentChallenge() {
  const selected = challengeMap.get(state.selectedChallengeId);
  if (selected && unlocked(selected)) {
    return selected;
  }
  const fallback = challenges.find((challenge) => unlocked(challenge)) || challenges[0];
  state.selectedChallengeId = fallback.id;
  saveState();
  return fallback;
}

function transcriptStore() {
  if (!state.transcripts[config.mode]) {
    state.transcripts[config.mode] = {};
  }
  return state.transcripts[config.mode];
}

function getTranscript(challengeId) {
  const transcript = transcriptStore()[challengeId];
  return Array.isArray(transcript) ? transcript : [];
}

function setTranscript(challengeId, turns) {
  transcriptStore()[challengeId] = turns.slice(-MAX_TRANSCRIPT_TURNS);
  saveState();
}

function appendTranscriptTurn(challengeId, turn) {
  const transcript = [...getTranscript(challengeId), turn];
  setTranscript(challengeId, transcript);
}

function setFeedback(message, tone = "muted") {
  elements.flagFeedback.textContent = message;
  elements.flagFeedback.className = `feedback ${tone}`;
}

function challengeShortTitle(challenge) {
  return challenge.title.replace(/^Level \d+:\s*/, "");
}

function renderLevelTrack() {
  elements.levelTrack.replaceChildren();
  const activeChallenge = currentChallenge();

  for (const challenge of challenges) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "level-button";

    const solved = state.solvedIds.includes(challenge.id);
    const isUnlocked = unlocked(challenge);
    const active = activeChallenge.id === challenge.id;

    if (solved) {
      button.classList.add("solved");
    }
    if (active) {
      button.classList.add("active");
    }
    if (!isUnlocked) {
      button.classList.add("locked");
      button.disabled = true;
    }

    const level = document.createElement("span");
    level.className = "level-chip";
    level.textContent = `L${challenge.level}`;

    const title = document.createElement("span");
    title.className = "level-name";
    title.textContent = challengeShortTitle(challenge);

    const status = document.createElement("span");
    status.className = "level-status";
    status.textContent = solved ? "Solved" : isUnlocked ? "Open" : "Locked";

    button.append(level, title, status);
    if (isUnlocked) {
      button.addEventListener("click", () => {
        state.selectedChallengeId = challenge.id;
        saveState();
        renderAll();
      });
    }
    elements.levelTrack.appendChild(button);
  }
}

function renderChallengeSummary() {
  const challenge = currentChallenge();
  const solved = state.solvedIds.includes(challenge.id);

  elements.challengeMeta.textContent = `${challenge.owasp_id} • ${challenge.owasp_name} • ${challenge.difficulty.toUpperCase()}`;
  elements.challengeTitle.textContent = challenge.title;
  elements.challengeBrief.textContent = challenge.brief;
  elements.challengeObjective.textContent = challenge.objective;
  elements.challengeSuccess.textContent = challenge.success_condition;
  elements.message.placeholder = challenge.prompt_placeholder;

  if (solved) {
    setFeedback("Flag captured for this level. You can keep probing or move to the next unlocked level.", "success");
  } else {
    setFeedback("Solve the challenge, recover the flag, and submit it here.", "muted");
  }
}

function renderHints() {
  const challenge = currentChallenge();
  const revealedCount = Math.min(
    Number(state.hintCounts[challenge.id] || 0),
    challenge.hints.length,
  );

  elements.hintList.replaceChildren();
  for (const hint of challenge.hints.slice(0, revealedCount)) {
    const item = document.createElement("li");
    item.textContent = hint;
    elements.hintList.appendChild(item);
  }

  if (revealedCount === 0) {
    const item = document.createElement("li");
    item.className = "hint-placeholder";
    item.textContent = "Hints stay hidden until you choose to reveal them.";
    elements.hintList.appendChild(item);
  }

  elements.revealHint.disabled = revealedCount >= challenge.hints.length;
  elements.revealHint.textContent =
    revealedCount >= challenge.hints.length ? "All Hints Revealed" : `Reveal Hint ${revealedCount + 1}`;
}

function renderProgress() {
  const solvedCount = state.solvedIds.length;
  const progress = (solvedCount / config.totalChallenges) * 100;
  elements.progressText.textContent = `${solvedCount} / ${config.totalChallenges}`;
  elements.progressFill.style.width = `${progress}%`;
}

function createTurnElement(turn) {
  const wrapper = document.createElement("article");
  wrapper.className = `turn ${turn.role}`;

  const label = document.createElement("p");
  label.className = "turn-label";
  label.textContent = turn.role === "user" ? "You" : "Assistant";

  const body = document.createElement("pre");
  body.className = "turn-body";
  body.textContent = turn.content;

  wrapper.append(label, body);
  return wrapper;
}

function renderTranscript() {
  const challenge = currentChallenge();
  const transcript = getTranscript(challenge.id);
  elements.transcript.replaceChildren();

  if (transcript.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-transcript";
    empty.innerHTML =
      "<p>No conversation yet.</p><p>Use the brief on the left, probe the model here, and recover the flag.</p>";
    elements.transcript.appendChild(empty);
    return;
  }

  for (const turn of transcript) {
    elements.transcript.appendChild(createTurnElement(turn));
  }
  elements.transcript.scrollTop = elements.transcript.scrollHeight;
}

function renderAll() {
  renderLevelTrack();
  renderChallengeSummary();
  renderHints();
  renderProgress();
  renderTranscript();
}

async function submitMessage(event) {
  event.preventDefault();
  if (pending) {
    return;
  }

  const message = elements.message.value.trim();
  if (!message) {
    return;
  }

  const challenge = currentChallenge();
  const history = getTranscript(challenge.id);

  appendTranscriptTurn(challenge.id, { role: "user", content: message });
  renderTranscript();
  elements.message.value = "";

  pending = true;
  elements.sendButton.disabled = true;
  elements.sendButton.textContent = "Running...";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        challenge_id: challenge.id,
        user_id: challenge.default_user_id,
        role: challenge.default_role,
        difficulty: challenge.difficulty,
        history,
      }),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    appendTranscriptTurn(challenge.id, { role: "assistant", content: data.answer });
  } catch (error) {
    appendTranscriptTurn(challenge.id, {
      role: "assistant",
      content: `The request failed. ${error instanceof Error ? error.message : "Unexpected error."}`,
    });
  } finally {
    pending = false;
    elements.sendButton.disabled = false;
    elements.sendButton.textContent = "Send";
    renderTranscript();
  }
}

async function submitFlag(event) {
  event.preventDefault();
  const challenge = currentChallenge();
  const flag = elements.flagInput.value.trim();
  if (!flag) {
    return;
  }

  const response = await fetch("/api/submit-flag", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      challenge_id: challenge.id,
      flag,
    }),
  });

  if (!response.ok) {
    setFeedback(`Flag submission failed with status ${response.status}.`, "error");
    return;
  }

  const data = await response.json();
  if (data.correct) {
    if (!state.solvedIds.includes(challenge.id)) {
      state.solvedIds.push(challenge.id);
      state.solvedIds.sort(
        (left, right) => challengeMap.get(left).level - challengeMap.get(right).level,
      );
      saveState();
    }
    const unlockedMessage = data.next_challenge_id ? " The next level is now unlocked." : " All levels cleared.";
    setFeedback(`${data.message}${unlockedMessage}`, "success");
    renderLevelTrack();
    renderProgress();
  } else {
    setFeedback(data.message, "error");
  }

  elements.flagInput.value = "";
}

function resetContext() {
  const challenge = currentChallenge();
  setTranscript(challenge.id, []);
  renderTranscript();
}

elements.chatForm.addEventListener("submit", submitMessage);
elements.flagForm.addEventListener("submit", submitFlag);
elements.resetContext.addEventListener("click", resetContext);
elements.revealHint.addEventListener("click", () => {
  const challenge = currentChallenge();
  const currentCount = Number(state.hintCounts[challenge.id] || 0);
  state.hintCounts[challenge.id] = Math.min(currentCount + 1, challenge.hints.length);
  saveState();
  renderHints();
});

renderAll();
