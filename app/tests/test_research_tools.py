# app/tests/test_research_tools.py

import sys
from unittest.mock import MagicMock, patch

mock_settings = MagicMock()
mock_settings.litellm_api_key = "test"
mock_settings.jina_api_key = "test"
mock_settings.model_name = "test"
mock_settings.redis_password = "test"
patch("app.src.utils.settings.get_settings", return_value=mock_settings).start()
patch("app.src.utils.logger.get_settings", return_value=mock_settings).start()

import json
import pytest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

from app.src.core.tools.phases.research_tools.clinical_trials import (
    search_clinical_trials,
    get_trial_details,
    _format_trial,
)
from app.src.core.tools.phases.research_tools.pubmed import (
    search_pubmed,
    get_pubmed_abstract,
    _parse_article,
    _search_pmids,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_STUDIES_RESPONSE = {
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT12345678",
                    "briefTitle": "Test Alzheimer Trial",
                },
                "statusModule": {"overallStatus": "RECRUITING"},
                "designModule": {"phases": ["PHASE2"]},
                "armsInterventionsModule": {
                    "interventions": [{"name": "Drug X", "type": "DRUG"}]
                },
                "outcomesModule": {
                    "primaryOutcomes": [{"measure": "Cognitive score at 12 months"}]
                },
                "contactsLocationsModule": {
                    "locations": [{"facility": "MGH", "city": "Boston", "country": "USA"}]
                },
            }
        }
    ]
}

MOCK_SINGLE_STUDY_RESPONSE = MOCK_STUDIES_RESPONSE["studies"][0]

MOCK_ESEARCH_RESPONSE = {
    "esearchresult": {"idlist": ["12345678", "87654321"]}
}

MOCK_EFETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Effects of amyloid inhibition in Alzheimer disease</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
          <Author>
            <LastName>Doe</LastName>
            <ForeName>Alice</ForeName>
          </Author>
        </AuthorList>
        <Journal>
          <Title>Nature Medicine</Title>
          <JournalIssue>
            <PubDate><Year>2024</Year></PubDate>
          </JournalIssue>
        </Journal>
        <Abstract>
          <AbstractText>This is a test abstract about amyloid inhibition.</AbstractText>
        </Abstract>
        <KeywordList>
          <Keyword>amyloid</Keyword>
          <Keyword>Alzheimer</Keyword>
        </KeywordList>
      </Article>
      <MeshHeadingList>
        <MeshHeading>
          <DescriptorName>Alzheimer Disease</DescriptorName>
        </MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


# ── ClinicalTrials Tests ──────────────────────────────────────────────────────

class TestSearchClinicalTrials:
    def _mock_get(self, url, params, retries=1):
        mock = MagicMock()
        mock.json.return_value = MOCK_STUDIES_RESPONSE
        mock.raise_for_status = MagicMock()
        return mock

    def test_returns_markdown(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.return_value.json.return_value = MOCK_STUDIES_RESPONSE
            mock.return_value.raise_for_status = MagicMock()
            result = search_clinical_trials.invoke({"condition": "Alzheimer"})
        assert "## Clinical Trials" in result
        assert "NCT12345678" in result

    def test_includes_trial_fields(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.return_value.json.return_value = MOCK_STUDIES_RESPONSE
            mock.return_value.raise_for_status = MagicMock()
            result = search_clinical_trials.invoke({"condition": "Alzheimer"})
        assert "RECRUITING" in result
        assert "PHASE2" in result
        assert "Drug X" in result

    def test_empty_results(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.return_value.json.return_value = {"studies": []}
            mock.return_value.raise_for_status = MagicMock()
            result = search_clinical_trials.invoke({"condition": "UnknownDisease"})
        assert "No trials found" in result

    def test_api_error_handled(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.side_effect = Exception("Connection timeout")
            result = search_clinical_trials.invoke({"condition": "Alzheimer"})
        assert "Error" in result

    def test_status_filter_passed(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.return_value.json.return_value = {"studies": []}
            mock.return_value.raise_for_status = MagicMock()
            search_clinical_trials.invoke({"condition": "Alzheimer", "status": "RECRUITING"})
            call_params = mock.call_args[1]["params"]
            assert call_params.get("filter.overallStatus") == "RECRUITING"

    def test_max_results_passed(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.return_value.json.return_value = {"studies": []}
            mock.return_value.raise_for_status = MagicMock()
            search_clinical_trials.invoke({"condition": "Alzheimer", "max_results": 5})
            call_params = mock.call_args[1]["params"]
            assert call_params.get("pageSize") == 5


class TestGetTrialDetails:
    def test_returns_full_details(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.return_value.json.return_value = MOCK_SINGLE_STUDY_RESPONSE
            mock.return_value.raise_for_status = MagicMock()
            result = get_trial_details.invoke({"nct_id": "NCT12345678"})
        assert "NCT12345678" in result
        assert "Test Alzheimer Trial" in result

    def test_api_error_handled(self):
        with patch("app.src.core.tools.phases.research_tools.clinical_trials.requests.get") as mock:
            mock.side_effect = Exception("404 Not Found")
            result = get_trial_details.invoke({"nct_id": "NCT99999999"})
        assert "Error" in result


# ── PubMed Tests ──────────────────────────────────────────────────────────────

class TestSearchPubmed:
    def test_returns_markdown(self):
        with patch("app.src.core.tools.phases.research_tools.pubmed.requests.get") as mock:
            search_resp = MagicMock()
            search_resp.json.return_value = MOCK_ESEARCH_RESPONSE
            search_resp.raise_for_status = MagicMock()

            fetch_resp = MagicMock()
            fetch_resp.content = MOCK_EFETCH_XML.encode()
            fetch_resp.raise_for_status = MagicMock()

            mock.side_effect = [search_resp, fetch_resp]
            result = search_pubmed.invoke({"query": "Alzheimer amyloid"})

        assert "## PubMed Results" in result
        assert "12345678" in result

    def test_includes_paper_fields(self):
        with patch("app.src.core.tools.phases.research_tools.pubmed.requests.get") as mock:
            search_resp = MagicMock()
            search_resp.json.return_value = MOCK_ESEARCH_RESPONSE
            search_resp.raise_for_status = MagicMock()

            fetch_resp = MagicMock()
            fetch_resp.content = MOCK_EFETCH_XML.encode()
            fetch_resp.raise_for_status = MagicMock()

            mock.side_effect = [search_resp, fetch_resp]
            result = search_pubmed.invoke({"query": "Alzheimer amyloid"})

        assert "Smith" in result
        assert "Nature Medicine" in result
        assert "amyloid inhibition" in result

    def test_empty_results(self):
        with patch("app.src.core.tools.phases.research_tools.pubmed.requests.get") as mock:
            mock.return_value.json.return_value = {"esearchresult": {"idlist": []}}
            mock.return_value.raise_for_status = MagicMock()
            result = search_pubmed.invoke({"query": "xyzunknowndisease123"})
        assert "No papers found" in result

    def test_api_error_handled(self):
        with patch("app.src.core.tools.phases.research_tools.pubmed.requests.get") as mock:
            mock.side_effect = Exception("Network error")
            result = search_pubmed.invoke({"query": "Alzheimer"})
        assert "Error" in result

    def test_max_results_passed(self):
        with patch("app.src.core.tools.phases.research_tools.pubmed.requests.get") as mock:
            mock.return_value.json.return_value = {"esearchresult": {"idlist": []}}
            mock.return_value.raise_for_status = MagicMock()
            search_pubmed.invoke({"query": "Alzheimer", "max_results": 3})
            call_params = mock.call_args[1]["params"]
            assert call_params.get("retmax") == 3


class TestGetPubmedAbstract:
    def test_returns_full_abstract(self):
        with patch("app.src.core.tools.phases.research_tools.pubmed.requests.get") as mock:
            mock.return_value.content = MOCK_EFETCH_XML.encode()
            mock.return_value.raise_for_status = MagicMock()
            result = get_pubmed_abstract.invoke({"pmid": "12345678"})
        assert "12345678" in result
        assert "amyloid inhibition" in result
        assert "MeSH Terms" in result

    def test_api_error_handled(self):
        with patch("app.src.core.tools.phases.research_tools.pubmed.requests.get") as mock:
            mock.side_effect = Exception("Timeout")
            result = get_pubmed_abstract.invoke({"pmid": "99999999"})
        assert "Error" in result


class TestParsing:
    def test_parse_article_fields(self):
        root = ET.fromstring(MOCK_EFETCH_XML)
        article = root.find(".//PubmedArticle")
        parsed = _parse_article(article)
        assert parsed["pmid"] == "12345678"
        assert "Smith" in parsed["authors"]
        assert "amyloid" in parsed["keywords"]
        assert "Alzheimer Disease" in parsed["mesh_terms"]

    def test_format_trial_fields(self):
        study = MOCK_STUDIES_RESPONSE["studies"][0]
        formatted = _format_trial(study)
        assert "NCT12345678" in formatted
        assert "RECRUITING" in formatted
        assert "Drug X" in formatted