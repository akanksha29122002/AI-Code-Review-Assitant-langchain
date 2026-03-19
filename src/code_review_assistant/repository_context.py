from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.code_review_assistant.config import settings


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "data",
}

IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".db",
}


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pass

    def embed_query(self, text: str) -> list[float]:
        pass


@dataclass
class RetrievedFile:
    path: str
    score: float
    snippet: str


class RepositoryContextRetriever:
    def __init__(
        self,
        repo_root: str = ".",
        *,
        index_path: str | None = None,
        max_files: int = 4,
        max_file_chars: int = 2500,
        max_file_bytes: int = 200000,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.index_path = Path(index_path or settings.repository_index_path)
        self.max_files = max_files
        self.max_file_chars = max_file_chars
        self.max_file_bytes = max_file_bytes
        self.embedding_provider = embedding_provider

    def retrieve(self, *, diff_text: str, changed_files: str, repo_context: str) -> str:
        indexed = self._retrieve_from_index(
            diff_text=diff_text,
            changed_files=changed_files,
            repo_context=repo_context,
        )
        if indexed is not None:
            return indexed
        return self._retrieve_heuristic(
            diff_text=diff_text,
            changed_files=changed_files,
            repo_context=repo_context,
        )

    def build_index(self) -> int:
        documents = self._collect_documents()
        if not documents:
            self._write_index({"documents": []})
            return 0

        embedder = self._get_embedding_provider()
        texts = [document["content"] for document in documents]
        vectors = embedder.embed_documents(texts)
        payload = {"documents": []}
        for document, vector in zip(documents, vectors):
            payload["documents"].append(
                {
                    "path": document["path"],
                    "content": document["content"],
                    "embedding": vector,
                }
            )
        self._write_index(payload)
        return len(payload["documents"])

    def _retrieve_from_index(self, *, diff_text: str, changed_files: str, repo_context: str) -> str | None:
        if not self.index_path.exists():
            return None

        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        documents = payload.get("documents") or []
        if not documents:
            return None

        try:
            embedder = self._get_embedding_provider()
            query_vector = embedder.embed_query("\n".join([diff_text, changed_files, repo_context]))
        except Exception:
            return None

        matches: list[RetrievedFile] = []
        for document in documents:
            embedding = document.get("embedding")
            content = document.get("content", "")
            path = document.get("path", "")
            if not path or not content or not embedding:
                continue
            score = cosine_similarity(query_vector, embedding)
            if score <= 0:
                continue
            matches.append(
                RetrievedFile(
                    path=path,
                    score=score,
                    snippet=content[: self.max_file_chars].strip(),
                )
            )

        matches.sort(key=lambda item: (-item.score, item.path))
        selected = matches[: self.max_files]
        if not selected:
            return None
        return self._format_matches(selected, score_label="Similarity")

    def _retrieve_heuristic(self, *, diff_text: str, changed_files: str, repo_context: str) -> str:
        query_tokens = self._tokenize("\n".join([diff_text, changed_files, repo_context]))
        hinted_paths = self._extract_paths("\n".join([diff_text, changed_files]))

        matches: list[RetrievedFile] = []
        for file_path in self._iter_candidate_files():
            relative_path = file_path.relative_to(self.repo_root).as_posix()
            content = self._safe_read_text(file_path)
            if content is None:
                continue
            score = self._score_file(relative_path, content, query_tokens, hinted_paths)
            if score <= 0:
                continue
            matches.append(
                RetrievedFile(
                    path=relative_path,
                    score=float(score),
                    snippet=content[: self.max_file_chars].strip(),
                )
            )

        matches.sort(key=lambda item: (-item.score, item.path))
        selected = matches[: self.max_files]
        if not selected:
            return "No relevant local repository files were retrieved."
        return self._format_matches(selected, score_label="Heuristic score")

    def _format_matches(self, matches: list[RetrievedFile], *, score_label: str) -> str:
        blocks: list[str] = []
        for item in matches:
            blocks.append(f"File: {item.path}\n{score_label}: {item.score:.4f}\n{item.snippet}")
        return "\n\n".join(blocks)

    def _collect_documents(self) -> list[dict[str, str]]:
        documents: list[dict[str, str]] = []
        for file_path in self._iter_candidate_files():
            relative_path = file_path.relative_to(self.repo_root).as_posix()
            content = self._safe_read_text(file_path)
            if not content:
                continue
            chunks = chunk_text(content)
            for index, chunk in enumerate(chunks, start=1):
                documents.append(
                    {
                        "path": f"{relative_path}#chunk-{index}",
                        "content": f"Path: {relative_path}\n{chunk}",
                    }
                )
        return documents

    def _iter_candidate_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.repo_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in IGNORED_SUFFIXES:
                continue
            try:
                if path.stat().st_size > self.max_file_bytes:
                    continue
            except OSError:
                continue
            files.append(path)
        return files

    def _safe_read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None

    def _extract_paths(self, text: str) -> set[str]:
        candidates = set(re.findall(r"[\w./-]+\.[A-Za-z0-9]+", text))
        return {candidate.strip("./") for candidate in candidates}

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text.lower())}

    def _score_file(
        self,
        relative_path: str,
        content: str,
        query_tokens: set[str],
        hinted_paths: set[str],
    ) -> int:
        score = 0
        normalized_path = relative_path.lower()
        normalized_hinted_paths = {item.lower() for item in hinted_paths}
        if relative_path in hinted_paths or normalized_path in normalized_hinted_paths:
            score += 20

        path_tokens = self._tokenize(relative_path)
        score += 3 * len(path_tokens & query_tokens)

        content_tokens = self._tokenize(content[:8000])
        score += len(content_tokens & query_tokens)
        return score

    def _get_embedding_provider(self) -> EmbeddingProvider:
        if self.embedding_provider is not None:
            return self.embedding_provider
        provider = settings.llm_provider.lower()
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI embedding retrieval.")
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
            )
        if provider == "ollama":
            from langchain_ollama import OllamaEmbeddings

            return OllamaEmbeddings(
                model=settings.ollama_embedding_model,
                base_url=settings.ollama_base_url,
            )
        if provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is required for Gemini embedding retrieval.")
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            return GoogleGenerativeAIEmbeddings(
                model=settings.gemini_embedding_model,
                google_api_key=settings.gemini_api_key,
            )
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    def _write_index(self, payload: dict) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def chunk_text(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start = max(start + 1, end - overlap)
    return chunks


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)
