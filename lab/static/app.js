const form = document.getElementById("chat-form");
const messageField = document.getElementById("message");
const userField = document.getElementById("user_id");
const roleField = document.getElementById("role");
const difficultyField = document.getElementById("difficulty");
const answerEl = document.getElementById("answer");
const llmInputEl = document.getElementById("llm-input");
const llmOutputEl = document.getElementById("llm-output");
const toolCallsEl = document.getElementById("tool-calls");
const policyEl = document.getElementById("policy-decisions");
const hintBox = document.getElementById("hint-box");

function renderJson(target, value) {
  target.textContent = JSON.stringify(value, null, 2);
}

async function submitPrompt(event) {
  event.preventDefault();
  answerEl.textContent = "Running...";

  const payload = {
    message: messageField.value,
    user_id: userField.value,
    role: roleField.value,
    difficulty: difficultyField.value,
  };

  const response = await fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    answerEl.textContent = `Request failed with status ${response.status}`;
    return;
  }

  const data = await response.json();
  answerEl.textContent = data.answer;
  renderJson(llmInputEl, data.llm_input);
  renderJson(llmOutputEl, data.llm_output);
  renderJson(toolCallsEl, data.tool_calls);
  renderJson(policyEl, data.policy_decisions);
  hintBox.textContent = `Hint: ${data.guided_hint ?? "No hint available."}`;
}

form.addEventListener("submit", submitPrompt);

document.querySelectorAll(".preset").forEach((button) => {
  button.addEventListener("click", () => {
    messageField.value = button.dataset.prompt;
    if (button.dataset.user_id) {
      userField.value = button.dataset.user_id;
    }
    if (button.dataset.role) {
      roleField.value = button.dataset.role;
    }
    if (button.dataset.difficulty) {
      difficultyField.value = button.dataset.difficulty;
    }
  });
});
