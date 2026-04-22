const config = window.labConfig;

const challenges = [...config.challenges].sort((left, right) => left.level - right.level);
const challengeMap = new Map(challenges.map((challenge) => [challenge.id, challenge]));

const elements = {
  form: document.getElementById("debug-form"),
  challenge: document.getElementById("debug-challenge"),
  message: document.getElementById("debug-message"),
  answer: document.getElementById("debug-answer"),
  llmInput: document.getElementById("debug-llm-input"),
  llmOutput: document.getElementById("debug-llm-output"),
  toolCalls: document.getElementById("debug-tool-calls"),
  policy: document.getElementById("debug-policy-decisions"),
};

function renderJson(target, value) {
  target.textContent = JSON.stringify(value, null, 2);
}

function populateChallenges() {
  for (const challenge of challenges) {
    const option = document.createElement("option");
    option.value = challenge.id;
    option.textContent = `${challenge.level}. ${challenge.title} (${challenge.owasp_id})`;
    if (challenge.id === config.defaultChallengeId) {
      option.selected = true;
    }
    elements.challenge.appendChild(option);
  }
  updatePlaceholder();
}

function updatePlaceholder() {
  const challenge = challengeMap.get(elements.challenge.value) || challenges[0];
  const placeholder = challenge.prompt_placeholder || "";
  elements.message.placeholder = placeholder;
  if (!elements.message.value.trim()) {
    elements.message.value = placeholder;
  }
}

async function submitDebug(event) {
  event.preventDefault();
  const challenge = challengeMap.get(elements.challenge.value) || challenges[0];
  const message = elements.message.value.trim();
  if (!message) {
    return;
  }

  elements.answer.textContent = "Running...";
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      challenge_id: challenge.id,
      user_id: challenge.default_user_id,
      role: challenge.default_role,
      difficulty: challenge.difficulty,
      history: [],
    }),
  });

  if (!response.ok) {
    elements.answer.textContent = `Request failed with status ${response.status}`;
    return;
  }

  const data = await response.json();
  elements.answer.textContent = data.answer;
  renderJson(elements.llmInput, data.llm_input);
  renderJson(elements.llmOutput, data.llm_output);
  renderJson(elements.toolCalls, data.tool_calls);
  renderJson(elements.policy, data.policy_decisions);
}

elements.challenge.addEventListener("change", updatePlaceholder);
elements.form.addEventListener("submit", submitDebug);

populateChallenges();
