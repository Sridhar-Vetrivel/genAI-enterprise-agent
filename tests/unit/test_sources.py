"""The three source clients: mock path, live REST path, and failure handling."""

from __future__ import annotations

import httpx
import pytest
import respx

from psiog_kendra.config import reset_settings, settings
from psiog_kendra.sources.base import SourceError, get_json, load_mock
from psiog_kendra.sources.crm import CRMClient
from psiog_kendra.sources.databricks import DatabricksClient
from psiog_kendra.sources.devops import DevOpsClient


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    """Switch every client off mocks and onto the live REST path."""
    monkeypatch.setenv("USE_MOCK_SOURCES", "false")
    monkeypatch.setenv("DATABRICKS_HOST", "https://dbx.example.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dbx-token")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-token")
    monkeypatch.setenv("CRM_API_BASE", "https://crm.example.com")
    monkeypatch.setenv("CRM_API_KEY", "crm-key")
    reset_settings()


class TestLoadMock:
    def test_loads_a_fixture(self) -> None:
        assert "runs" in load_mock("databricks")

    def test_missing_fixture_raises(self) -> None:
        with pytest.raises(SourceError, match="not found"):
            load_mock("no-such-source")


class TestDatabricksMocked:
    async def test_lists_runs_newest_first(self) -> None:
        runs = await DatabricksClient().list_runs()
        starts = [r["start_time"] for r in runs]
        assert starts == sorted(starts, reverse=True)

    async def test_filters_by_job_name(self) -> None:
        runs = await DatabricksClient().list_runs("sales_etl")
        assert runs and all(r["job_name"] == "sales_etl" for r in runs)

    async def test_unknown_job_yields_nothing(self) -> None:
        assert await DatabricksClient().list_runs("no_such_job") == []

    async def test_latest_run_is_the_newest(self) -> None:
        run = await DatabricksClient().latest_run("sales_etl")
        assert run is not None and run["run_id"] == 99141

    async def test_latest_run_of_unknown_job_is_none(self) -> None:
        assert await DatabricksClient().latest_run("nope") is None

    async def test_last_failed_run_skips_successes(self) -> None:
        run = await DatabricksClient().last_failed_run()
        assert run is not None and run["result_state"] == "FAILED"

    async def test_last_failed_run_is_none_when_all_succeeded(self) -> None:
        assert await DatabricksClient().last_failed_run("sales_etl") is None

    async def test_fetch_pairs_every_run_with_a_citation(self) -> None:
        runs, citations = await DatabricksClient().fetch()
        assert len(runs) == len(citations)
        assert all(c.startswith("Databricks Job #") for c in citations)


class TestDatabricksLive:
    @respx.mock
    async def test_calls_the_jobs_api_with_the_token(self, live: None) -> None:
        route = respx.get("https://dbx.example.com/api/2.1/jobs/runs/list").mock(
            return_value=httpx.Response(
                200, json={"runs": [{"run_id": 1, "job_id": 9, "job_name": "j", "start_time": "t"}]}
            )
        )
        runs = await DatabricksClient().list_runs()
        assert len(runs) == 1
        assert route.calls.last.request.headers["Authorization"] == "Bearer dbx-token"

    @respx.mock
    async def test_http_error_becomes_source_error(self, live: None) -> None:
        respx.get("https://dbx.example.com/api/2.1/jobs/runs/list").mock(
            return_value=httpx.Response(401)
        )
        with pytest.raises(SourceError, match="401"):
            await DatabricksClient().list_runs()

    @respx.mock
    async def test_network_failure_becomes_source_error(self, live: None) -> None:
        respx.get("https://dbx.example.com/api/2.1/jobs/runs/list").mock(
            side_effect=httpx.ConnectError("refused")
        )
        with pytest.raises(SourceError, match="unreachable"):
            await DatabricksClient().list_runs()

    async def test_missing_credentials_is_an_error_not_a_silent_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("USE_MOCK_SOURCES", "false")
        reset_settings()
        with pytest.raises(SourceError, match="not set"):
            await DatabricksClient().list_runs()


class TestDevOpsMocked:
    async def test_filters_by_service(self) -> None:
        runs = await DevOpsClient().list_runs("payments")
        assert runs and all("payments" in r["service"] for r in runs)

    async def test_service_suffix_is_tolerated(self) -> None:
        assert await DevOpsClient().list_runs("payments-service")

    async def test_failed_gates_returns_only_failures(self) -> None:
        run = await DevOpsClient().latest_run("ingestion")
        assert run is not None
        failing = DevOpsClient.failed_gates(run)
        assert {g["name"] for g in failing} == {"code-coverage", "integration-tests"}

    async def test_failed_gates_is_empty_for_a_clean_run(self) -> None:
        run = await DevOpsClient().latest_run("payments")
        assert run is not None
        assert DevOpsClient.failed_gates(run) == []

    async def test_failed_gates_on_a_run_with_no_gates(self) -> None:
        assert DevOpsClient.failed_gates({}) == []

    async def test_citations_name_the_commit(self) -> None:
        _, citations = await DevOpsClient().fetch("payments")
        assert any("a1f9c34" in c for c in citations)


class TestDevOpsLive:
    @respx.mock
    async def test_calls_the_actions_api(self, live: None) -> None:
        repo = settings().github_repo
        route = respx.get(f"https://api.github.com/repos/{repo}/actions/runs").mock(
            return_value=httpx.Response(
                200, json={"workflow_runs": [{"run_id": 1, "service": "a"}]}
            )
        )
        assert len(await DevOpsClient().list_runs()) == 1
        assert route.calls.last.request.headers["Authorization"] == "Bearer gh-token"


class TestCRMMocked:
    async def test_finds_deal_by_partial_account_name(self) -> None:
        deals = await CRMClient().find_deals("acme")
        assert deals and deals[0]["stage"] == "Negotiation"

    async def test_finds_account_owner(self) -> None:
        accounts = await CRMClient().find_accounts("TechStart")
        assert accounts and accounts[0]["owner"] == "Karthik Rao"

    async def test_unknown_account_yields_nothing(self) -> None:
        assert await CRMClient().find_deals("Nonexistent Ltd") == []

    async def test_no_filter_returns_everything(self) -> None:
        assert len(await CRMClient().find_deals()) == 3

    async def test_fetch_bundles_accounts_deals_and_contacts(self) -> None:
        records, citations = await CRMClient().fetch("acme")
        assert records["accounts"] and records["deals"] and records["contacts"]
        assert citations

    async def test_stale_sync_status_survives_into_the_record(self) -> None:
        records, _ = await CRMClient().fetch("acme")
        assert records["accounts"][0]["sync_status"] == "stale"


class TestCRMLive:
    @respx.mock
    async def test_calls_the_crm_api(self, live: None) -> None:
        route = respx.get("https://crm.example.com/deals").mock(
            return_value=httpx.Response(
                200, json={"deals": [{"deal_id": "D1", "account_name": "X"}]}
            )
        )
        assert len(await CRMClient().find_deals()) == 1
        assert route.calls.last.request.headers["Authorization"] == "Bearer crm-key"

    @respx.mock
    async def test_bare_list_response_is_accepted(self, live: None) -> None:
        respx.get("https://crm.example.com/deals").mock(
            return_value=httpx.Response(200, json=[{"deal_id": "D1", "account_name": "X"}])
        )
        assert len(await CRMClient().find_deals()) == 1


class TestGetJson:
    async def test_non_json_body_is_an_error(self, respx_mock: respx.Router) -> None:
        respx_mock.get("https://x.example/y").mock(return_value=httpx.Response(200, text="<html>"))
        with pytest.raises(SourceError):
            await get_json("https://x.example/y")

    async def test_timeout_becomes_source_error(self, respx_mock: respx.Router) -> None:
        respx_mock.get("https://x.example/slow").mock(side_effect=httpx.ReadTimeout("too slow"))
        with pytest.raises(SourceError, match="unreachable"):
            await get_json("https://x.example/slow")
