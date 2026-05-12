import json

from langchain.tools import ToolRuntime, tool

from app.src.core.state import ResearchAgentState
from app.src.core.tools.phases._shared import (
    send_results,
    get_markdown,
)
import feedparser


@tool
def research_scan_literature(
    query: str,
    max_results: int,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Search arXiv for biomedical papers. Returns JSON list of papers with title, authors, date, summary, PDF link.

    Use in research phase to gather evidence.
    Results over max_results_length saved to file; read with read_file.

    Args:
        query: Search term (lowercase single word).
        max_results: Max papers to retrieve (int).
    """
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries:
        entry_dict = {
            "title": entry.title,
            "published": entry.published,
            "updated": entry.updated,
            "summary": entry.summary,
            "authors": [a.name for a in entry.authors],
            "links": [
                {"href": link.href}
                for link in entry.links
                if link.type == "application/pdf"
            ],
        }
        results.append(entry_dict)
    results_str = json.dumps(results, indent=2)
    return send_results(str(results_str), runtime)


@tool
def fetch_paper_from_link(
    link: str,
    runtime: ToolRuntime[None, ResearchAgentState],
):
    """Fetch paper PDF content and convert to markdown. Returns text.

    Use after research_scan_literature to read specific papers.
    Multiple fetches: call tool sequentially.

    Args:
        link: PDF URL from research_scan_literature result (str).
    """
    return get_markdown(link, runtime)
