# app/src/core/tools/phases/research_tools/pubmed.py

import time
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from langchain_core.tools import tool

from app.src.utils.logger import get_logger

logger = get_logger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
TIMEOUT = 30


def _get(url: str, params: dict, retries: int = 1) -> requests.Response:
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            raise


def _search_pmids(query: str, max_results: int, date_filter: Optional[str] = None) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    if date_filter:
        params["datetype"] = "pdat"
        params["reldate"] = date_filter

    resp = _get(ESEARCH_URL, params)
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def _fetch_articles(pmids: list[str]) -> ET.Element:
    resp = _get(EFETCH_URL, {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    })
    return ET.fromstring(resp.content)


def _extract_text(element, tag: str, default: str = "N/A") -> str:
    node = element.find(f".//{tag}")
    return node.text.strip() if node is not None and node.text else default


def _parse_article(article: ET.Element) -> dict:
    pmid = _extract_text(article, "PMID")
    title = _extract_text(article, "ArticleTitle")

    authors = []
    for author in article.findall(".//Author"):
        last = _extract_text(author, "LastName", "")
        fore = _extract_text(author, "ForeName", "")
        if last:
            authors.append(f"{last} {fore}".strip())

    journal = _extract_text(article, "Title")  # Journal title
    year = _extract_text(article, "Year", "")
    month = _extract_text(article, "Month", "")
    pub_date = f"{journal}, {year}" if year else journal

    abstract_texts = article.findall(".//AbstractText")
    if abstract_texts:
        abstract = " ".join(
            (f"[{a.get('Label', '')}] " if a.get('Label') else "") + (a.text or "")
            for a in abstract_texts
        ).strip()
    else:
        abstract = "No abstract available."

    keywords = [
        kw.text.strip() for kw in article.findall(".//Keyword") if kw.text
    ]
    mesh_terms = [
        mh.findtext("DescriptorName", "").strip()
        for mh in article.findall(".//MeshHeading")
    ]

    return {
        "pmid": pmid,
        "title": title,
        "authors": ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
        "journal": pub_date,
        "abstract": abstract,
        "keywords": keywords,
        "mesh_terms": mesh_terms,
    }


def _format_article_summary(a: dict, index: int) -> str:
    kw_str = ", ".join(a["keywords"][:8]) if a["keywords"] else "N/A"
    abstract_preview = a["abstract"][:400] + "..." if len(a["abstract"]) > 400 else a["abstract"]
    return (
        f"### {index}. PMID: {a['pmid']} — {a['title']}\n"
        f"- **Authors**: {a['authors']}\n"
        f"- **Journal**: {a['journal']}\n"
        f"- **Keywords**: {kw_str}\n"
        f"- **Abstract**: {abstract_preview}\n"
    )


@tool
def search_pubmed(
    query: str,
    max_results: int = 10,
    publication_years: Optional[int] = None,
) -> str:
    """Search PubMed for biomedical literature.

    Args:
        query: Search query e.g. 'Alzheimer amyloid beta treatment'.
        max_results: Maximum number of results to return (default 10).
        publication_years: Optional. Only return papers from the last N years.

    Returns:
        Markdown formatted list of papers with titles, authors, and abstracts.
    """
    try:
        date_filter = str(publication_years * 365) if publication_years else None
        pmids = _search_pmids(query, max_results, date_filter)

        if not pmids:
            return f"## PubMed Results\n\nNo papers found for query: **{query}**."

        root = _fetch_articles(pmids)
        articles = [_parse_article(a) for a in root.findall(".//PubmedArticle")]

        if not articles:
            return f"## PubMed Results\n\nCould not parse results for query: **{query}**."

        lines = [f"## PubMed Results for: {query}\n"]
        lines.append(f"*Found {len(articles)} result(s)*\n\n---\n")
        for i, article in enumerate(articles, 1):
            lines.append(_format_article_summary(article, i))
            lines.append("\n---\n")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"[PubMed] search failed: {e}")
        return f"## PubMed Results\n\nError searching PubMed: {e}"


@tool
def get_pubmed_abstract(pmid: str) -> str:
    """Retrieve the full abstract and metadata for a PubMed paper by PMID.

    Args:
        pmid: PubMed ID e.g. '12345678'.

    Returns:
        Full abstract and metadata formatted as markdown.
    """
    try:
        root = _fetch_articles([pmid])
        articles = root.findall(".//PubmedArticle")

        if not articles:
            return f"## PubMed Abstract\n\nNo article found for PMID: {pmid}."

        a = _parse_article(articles[0])
        mesh_str = "\n".join(f"  - {m}" for m in a["mesh_terms"][:15]) or "  - N/A"
        kw_str = "\n".join(f"  - {k}" for k in a["keywords"][:15]) or "  - N/A"

        return (
            f"## PMID: {a['pmid']} — {a['title']}\n\n"
            f"**Authors**: {a['authors']}\n"
            f"**Journal**: {a['journal']}\n\n"
            f"### Abstract\n{a['abstract']}\n\n"
            f"### Keywords\n{kw_str}\n\n"
            f"### MeSH Terms\n{mesh_str}\n"
        )

    except Exception as e:
        logger.error(f"[PubMed] get_pubmed_abstract failed for {pmid}: {e}")
        return f"## PubMed Abstract\n\nError retrieving PMID {pmid}: {e}"