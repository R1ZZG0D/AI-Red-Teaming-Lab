from __future__ import annotations

import re
from pathlib import Path

from lab.shared.schemas import RetrievedDocument


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")
DOCUMENT_REQUEST_TERMS = {
    "document",
    "documents",
    "vendor",
    "bulletin",
    "summary",
    "summarize",
    "brief",
    "briefing",
    "audit",
    "memo",
    "guidance",
    "digest",
    "report",
    "notes",
    "appendix",
    "maintenance",
    "embedded",
    "operational",
}


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def load_documents(documents_dir: Path) -> list[RetrievedDocument]:
    documents: list[RetrievedDocument] = []
    for path in sorted(documents_dir.glob("*.txt")):
        documents.append(
            RetrievedDocument(
                title=path.stem.replace("_", " ").title(),
                content=path.read_text(encoding="utf-8"),
                score=0,
            )
        )
    return documents


def should_retrieve_documents(question: str) -> bool:
    question_tokens = tokenize(question)
    return bool(question_tokens & DOCUMENT_REQUEST_TERMS)


def retrieve_documents(documents_dir: Path, question: str, limit: int = 2) -> list[RetrievedDocument]:
    question_tokens = tokenize(question)
    vendor_bias_active = any(
        token in question_tokens
        for token in {
            "vendor",
            "bulletin",
            "document",
            "documents",
            "summary",
            "summarize",
            "appendix",
            "maintenance",
            "embedded",
            "operational",
        }
    )
    ranked: list[RetrievedDocument] = []
    for document in load_documents(documents_dir):
        score = len(question_tokens & tokenize(document.content))
        if vendor_bias_active and "vendor" in document.title.lower():
            score += 2
        ranked.append(document.model_copy(update={"score": score}))
    ranked.sort(key=lambda doc: (doc.score, doc.title), reverse=True)
    if vendor_bias_active:
        vendor_docs = [doc for doc in ranked if "vendor" in doc.title.lower() and doc.score > 0]
        if vendor_docs:
            return vendor_docs[:1]
    top_docs = [doc for doc in ranked[:limit] if doc.score > 0]
    if top_docs:
        return top_docs
    return [doc for doc in ranked if "vendor" not in doc.title.lower()][:limit]


def summarize_documents(documents: list[RetrievedDocument]) -> str:
    snippets = []
    for document in documents:
        first_line = next((line.strip() for line in document.content.splitlines() if line.strip()), document.title)
        snippets.append(f"{document.title}: {first_line}")
    return "\n".join(snippets)
