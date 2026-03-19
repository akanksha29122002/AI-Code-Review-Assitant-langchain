from __future__ import annotations

import streamlit as st

from src.code_review_assistant.config import settings
from src.code_review_assistant.github_review import GitHubReviewService
from src.code_review_assistant.history_store import ReviewHistoryStore
from src.code_review_assistant.repository_context import RepositoryContextRetriever
from src.code_review_assistant.reviewer import CodeReviewAssistant


st.set_page_config(
    page_title="AI Code Review Assistant",
    page_icon="CR",
    layout="wide",
)

st.title("AI-Powered Code Review Assistant")
st.caption("One app for manual diffs and GitHub pull request reviews.")

history_store = ReviewHistoryStore()


def format_error_message(exc: Exception) -> str:
    message = str(exc)
    normalized = message.lower()

    if "resource_exhausted" in normalized or "quota exceeded" in normalized:
        return (
            "Gemini quota is exhausted for the configured API key. "
            "Wait for quota reset, enable Gemini billing, or switch `.env` to another provider such as OpenAI or Ollama."
        )

    if "modulenotfounderror" in normalized or "no module named" in normalized:
        return (
            "A required provider package is missing in this Python environment. "
            "Install dependencies from `requirements.txt` and restart Streamlit."
        )

    if "resource not accessible by personal access token" in normalized:
        return (
            "GitHub blocked posting the review with the current token. "
            "Use preview mode by turning off `Publish review back to GitHub`, or create a token/GitHub App with "
            "`Pull requests: Read and write` and `Issues: Read and write` access for this repository."
        )

    return message


def is_fallback_result(result) -> bool:
    return "fallback" in result.summary.lower()


def render_review_result(result, *, retrieved_context: str | None = None) -> None:
    fallback_mode = is_fallback_result(result)
    if fallback_mode:
        st.info("External model review was unavailable. Showing local fallback analysis.")
        if not result.findings:
            st.warning(
                "Fallback mode did not find an obvious issue, but this is not the same as a full model-based review."
            )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.subheader("Summary")
        st.write(result.summary)
    with c2:
        st.subheader("Risk")
        st.metric("Overall risk", result.overall_risk)
    with c3:
        st.subheader("Engine")
        st.metric("Review engine", "Fallback" if fallback_mode else settings.llm_provider.title())

    st.subheader("Findings")
    if not result.findings:
        st.success("No significant findings were reported.")
    else:
        for idx, finding in enumerate(result.findings, start=1):
            with st.container(border=True):
                st.markdown(f"**{idx}. {finding.title}**")
                st.write(f"Severity: {finding.severity}")
                if finding.file_path:
                    st.write(f"File: `{finding.file_path}`")
                if finding.line_reference:
                    st.write(f"Line: `{finding.line_reference}`")
                st.write(finding.description)
                if finding.impact:
                    st.write(f"Impact: {finding.impact}")
                if finding.recommendation:
                    st.write(f"Recommendation: {finding.recommendation}")

    st.subheader("Missing Tests")
    if result.missing_tests:
        for test_item in result.missing_tests:
            st.write(f"- {test_item}")
    else:
        st.write("No specific missing tests were identified.")

    with st.expander("Raw Structured Output"):
        st.json(result.model_dump())

    if retrieved_context is not None:
        with st.expander("Retrieved Repository Context"):
            st.code(retrieved_context)


def render_recent_reviews() -> None:
    st.divider()
    st.subheader("Recent Reviews")
    recent_reviews = history_store.list_recent_reviews(limit=10)
    if not recent_reviews:
        st.write("No reviews have been saved yet.")
        return

    for item in recent_reviews:
        with st.container(border=True):
            display_title = item.title
            if item.repository and item.pull_request_number:
                display_title = f"{item.repository}#{item.pull_request_number}"
            st.markdown(f"**{display_title}**")
            st.write(f"Source: `{item.source}`")
            st.write(f"Risk: `{item.overall_risk}`")
            st.write(
                f"Findings: `{item.findings_count}` | Missing tests: `{item.missing_tests_count}` | Created: `{item.created_at}`"
            )
            st.write(item.summary)

with st.sidebar:
    st.header("Review Options")
    language = st.text_input("Primary language", value="Python")
    focus_areas = st.multiselect(
        "Focus areas",
        options=[
            "Correctness",
            "Security",
            "Performance",
            "Readability",
            "Testing",
            "Maintainability",
        ],
        default=["Correctness", "Security", "Testing"],
    )
    include_suggestions = st.toggle("Include fix suggestions", value=True)
    use_local_context = st.toggle("Use local repository context", value=True)
    st.caption("For vector retrieval, build the local index with `python scripts/build_repository_index.py`.")
    st.divider()
    st.subheader("Model Status")
    st.caption(f"Configured provider: `{settings.llm_provider}`")
    if settings.llm_provider.lower() == "gemini":
        st.caption(f"Configured model: `{settings.gemini_model}`")
    elif settings.llm_provider.lower() == "openai":
        st.caption(f"Configured model: `{settings.openai_model}`")
    elif settings.llm_provider.lower() == "ollama":
        st.caption(f"Configured model: `{settings.ollama_model}`")
    st.divider()
    st.subheader("GitHub Mode")
    github_ready = settings.uses_github_app or bool(settings.github_token)
    if github_ready:
        st.success("GitHub auth detected.")
    else:
        st.warning("GitHub auth is not configured in `.env` yet.")

manual_tab, github_tab = st.tabs(["Manual Review", "GitHub PR Review"])

with manual_tab:
    repo_context = st.text_area(
        "Repository context",
        placeholder="Describe the project, architecture, constraints, or coding standards.",
        height=120,
        key="manual_repo_context",
    )

    changed_files = st.text_area(
        "Changed files summary",
        placeholder="Example:\n- src/api/reviews.py: adds review endpoint\n- src/llm/reviewer.py: prompt and parsing logic",
        height=120,
        key="manual_changed_files",
    )

    diff_text = st.text_area(
        "Diff or changed code",
        placeholder="Paste a git diff, patch, or code snippet here.",
        height=320,
        key="manual_diff_text",
    )

    if st.button("Run Manual Review", type="primary", use_container_width=True):
        if not diff_text.strip():
            st.error("Provide a diff or changed code before running the review.")
        else:
            assistant = CodeReviewAssistant()
            retrieved_context = "No additional repository files retrieved."
            if use_local_context:
                retriever = RepositoryContextRetriever()
                retrieved_context = retriever.retrieve(
                    diff_text=diff_text,
                    changed_files=changed_files,
                    repo_context=repo_context,
                )
            with st.spinner("Reviewing code changes..."):
                try:
                    result = assistant.review(
                        repo_context=repo_context,
                        retrieved_context=retrieved_context,
                        changed_files=changed_files,
                        diff_text=diff_text,
                        language=language,
                        focus_areas=focus_areas,
                        include_suggestions=include_suggestions,
                    )
                except Exception as exc:
                    st.error(format_error_message(exc))
                else:
                    history_store.save_review(
                        source="manual",
                        title="Manual review",
                        result=result,
                        raw_input=diff_text,
                    )
                    render_review_result(
                        result,
                        retrieved_context=retrieved_context if use_local_context else None,
                    )

with github_tab:
    st.caption(
        "Review an existing GitHub pull request by entering the repository owner, repository name, and PR number."
    )
    with st.expander("How To Use GitHub PR Review"):
        st.markdown(
            """
1. Open the target repository on GitHub.
2. Create or locate a pull request in that repository.
3. Enter the repository owner, repository name, and PR number here.
4. Turn off `Publish review back to GitHub` if you only want a preview inside this app.
5. Turn it on if you want the app to post comments and status checks back to GitHub.

Example:
- Owner or org: `akanksha29122002`
- Repository: `CodeforALL`
- PR number: `1`
"""
        )

    col1, col2, col3 = st.columns([1.2, 1.2, 0.8])
    with col1:
        github_owner = st.text_input("Owner or org", placeholder="octocat")
    with col2:
        github_repo = st.text_input("Repository", placeholder="hello-world")
    with col3:
        github_pr_number = st.number_input("PR number", min_value=1, step=1, value=1)

    publish_review = st.toggle(
        "Publish review back to GitHub",
        value=True,
        help="Turn this off to preview the AI review inside the app without posting comments or statuses.",
    )

    if st.button("Run GitHub PR Review", type="primary", use_container_width=True):
        if not github_owner.strip() or not github_repo.strip():
            st.error("Provide both the GitHub owner and repository.")
        elif publish_review and not (settings.uses_github_app or settings.github_token):
            st.error("Publishing requires GitHub auth. Add GITHUB_TOKEN or GitHub App settings in `.env`.")
        else:
            service = GitHubReviewService()
            with st.spinner("Fetching pull request and running review..."):
                try:
                    result = service.review_pull_request(
                        github_owner.strip(),
                        github_repo.strip(),
                        int(github_pr_number),
                        publish_review=publish_review,
                    )
                except Exception as exc:
                    st.error(format_error_message(exc))
                else:
                    if publish_review:
                        st.success("GitHub PR reviewed and publication was attempted.")
                    else:
                        st.info("Preview review completed. Nothing was posted to GitHub.")
                    render_review_result(result)

render_recent_reviews()
