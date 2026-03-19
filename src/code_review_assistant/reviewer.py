from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from src.code_review_assistant.config import settings
from src.code_review_assistant.fallback_reviewer import fallback_review
from src.code_review_assistant.models import ReviewResult
from src.code_review_assistant.parser import normalize_diff, normalize_list


SYSTEM_PROMPT = """
You are an expert senior engineer performing code review.

Prioritize:
- correctness bugs
- regressions
- security issues
- performance problems
- missing validation
- concurrency and state issues
- test coverage gaps

Do not praise the code. Focus on actionable issues and realistic testing gaps.
Prefer concrete, evidence-based findings tied to the submitted diff or code.
If there is not enough evidence for a finding, do not invent one.
When possible, include the exact file_path and the exact new-file line number in line_reference.
Only use a line number when the issue can be tied to a specific changed line.
""".strip()


USER_PROMPT = """
Review the following code change.

Primary language: {language}
Review focus areas: {focus_areas}
Include fix suggestions: {include_suggestions}

Repository context:
{repo_context}

Retrieved local repository files:
{retrieved_context}

Changed files summary:
{changed_files}

Submitted diff or code:
{diff_text}

Return a structured review result with:
- a short summary
- overall risk
- prioritized findings
- missing tests
""".strip()


class CodeReviewAssistant:
    def __init__(self) -> None:
        self.llm = None
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("user", USER_PROMPT),
            ]
        )
        self.chain = None
        self.initialization_error: str | None = None
        try:
            self.llm = self._build_llm()
            self.chain = self.prompt | self.llm.with_structured_output(ReviewResult)
        except Exception as exc:
            self.initialization_error = str(exc)

    def _build_llm(self):
        provider = settings.llm_provider.lower()
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is missing. Either set it or switch LLM_PROVIDER to ollama."
                )
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.openai_model,
                temperature=settings.temperature,
                api_key=settings.openai_api_key,
            )

        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.temperature,
            )

        if provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY is missing. Either set it or switch LLM_PROVIDER."
                )
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=settings.temperature,
            )

        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    def review(
        self,
        *,
        repo_context: str,
        retrieved_context: str,
        changed_files: str,
        diff_text: str,
        language: str,
        focus_areas: list[str],
        include_suggestions: bool,
    ) -> ReviewResult:
        payload = {
            "repo_context": repo_context.strip() or "No repository context provided.",
            "retrieved_context": retrieved_context.strip() or "No additional repository files retrieved.",
            "changed_files": changed_files.strip() or "No changed file summary provided.",
            "diff_text": normalize_diff(diff_text),
            "language": language.strip() or "Unknown",
            "focus_areas": normalize_list(focus_areas),
            "include_suggestions": "yes" if include_suggestions else "no",
        }
        if self.chain is None:
            return fallback_review(
                diff_text=payload["diff_text"],
                changed_files=payload["changed_files"],
                repo_context=payload["repo_context"],
                language=payload["language"],
                include_suggestions=include_suggestions,
                failure_reason=self.initialization_error,
            )

        try:
            return self.chain.invoke(payload)
        except Exception as exc:
            return fallback_review(
                diff_text=payload["diff_text"],
                changed_files=payload["changed_files"],
                repo_context=payload["repo_context"],
                language=payload["language"],
                include_suggestions=include_suggestions,
                failure_reason=str(exc),
            )
