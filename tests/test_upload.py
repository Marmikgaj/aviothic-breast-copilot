"""Tests for the upload and status polling endpoints."""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient


class TestUploadEndpoint:
    """Upload endpoint test suite."""

    @pytest.mark.asyncio
    async def test_upload_valid_pdf_returns_202(
        self, client: AsyncClient, auth_headers: dict[str, str], sample_mammography_pdf: bytes
    ) -> None:
        """A valid PDF upload should return 202 with a report ID."""
        response = await client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("report.pdf", sample_mammography_pdf, "application/pdf")},
        )

        assert response.status_code == 202

        body = response.json()
        assert "report_id" in body
        assert body["status"] == "processing"
        assert "message" in body

    @pytest.mark.asyncio
    async def test_upload_without_auth_returns_401(self, client: AsyncClient, sample_mammography_pdf: bytes) -> None:
        """Upload without API key should be rejected with 401."""
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("report.pdf", sample_mammography_pdf, "application/pdf")},
        )

        assert response.status_code == 401

        body = response.json()
        assert body["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_upload_with_wrong_key_returns_401(self, client: AsyncClient, sample_mammography_pdf: bytes) -> None:
        """Upload with wrong API key should be rejected with 401."""
        response = await client.post(
            "/api/v1/upload",
            headers={"X-API-Key": "wrong-key"},
            files={"file": ("report.pdf", sample_mammography_pdf, "application/pdf")},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_wrong_mime_returns_415(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """Uploading a non-PDF file should return 415."""
        response = await client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("report.txt", b"This is not a PDF", "text/plain")},
        )

        assert response.status_code == 415

        body = response.json()
        assert body["error"]["code"] == "UNSUPPORTED_MIME_TYPE"

    @pytest.mark.asyncio
    async def test_upload_empty_file_returns_422(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """Uploading an empty file should return a validation error."""
        response = await client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )

        assert response.status_code == 422

        body = response.json()
        assert body["error"]["code"] == "FILE_VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_upload_spoofed_mime_returns_422(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        """A file claiming to be PDF but with wrong magic bytes should be rejected."""
        fake_pdf = b"This is not a PDF but claims to be one"
        response = await client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
        )

        assert response.status_code == 422

        body = response.json()
        assert body["error"]["code"] == "FILE_VALIDATION_ERROR"


class TestStatusEndpoint:
    """Status polling endpoint test suite."""

    @pytest.mark.asyncio
    async def test_status_nonexistent_report_returns_404(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Polling a non-existent report ID should return 404."""
        response = await client.get(
            "/api/v1/reports/nonexistent-id/status",
            headers=auth_headers,
        )

        assert response.status_code == 404

        body = response.json()
        assert body["error"]["code"] == "REPORT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_upload_then_poll_returns_completed(
        self, client: AsyncClient, auth_headers: dict[str, str], sample_mammography_pdf: bytes
    ) -> None:
        """Upload a valid PDF, wait briefly, then poll — should be completed."""
        # Upload.
        upload_response = await client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("mammogram.pdf", sample_mammography_pdf, "application/pdf")},
        )
        assert upload_response.status_code == 202
        report_id = upload_response.json()["report_id"]

        # Wait for async processing to complete.
        await asyncio.sleep(2)

        # Poll status.
        status_response = await client.get(
            f"/api/v1/reports/{report_id}/status",
            headers=auth_headers,
        )
        assert status_response.status_code == 200

        body = status_response.json()
        assert body["status"] == "completed"
        assert body["result"] is not None
        assert body["result"]["report_id"] == report_id
        assert body["result"]["raw_text"]  # Should have extracted text.
        assert body["result"]["page_count"] >= 1
        assert body["result"]["confidence"] is not None

    @pytest.mark.asyncio
    async def test_completed_report_has_mammography_type(
        self, client: AsyncClient, auth_headers: dict[str, str], sample_mammography_pdf: bytes
    ) -> None:
        """A mammography report should be classified as 'mammography'."""
        upload_response = await client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("mammogram.pdf", sample_mammography_pdf, "application/pdf")},
        )
        report_id = upload_response.json()["report_id"]

        await asyncio.sleep(2)

        status_response = await client.get(
            f"/api/v1/reports/{report_id}/status",
            headers=auth_headers,
        )
        body = status_response.json()
        assert body["result"]["report_type"] == "mammography"

    @pytest.mark.asyncio
    async def test_completed_report_has_date(
        self, client: AsyncClient, auth_headers: dict[str, str], sample_mammography_pdf: bytes
    ) -> None:
        """A mammography report with a clear date should have report_date set."""
        upload_response = await client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("mammogram.pdf", sample_mammography_pdf, "application/pdf")},
        )
        report_id = upload_response.json()["report_id"]

        await asyncio.sleep(2)

        status_response = await client.get(
            f"/api/v1/reports/{report_id}/status",
            headers=auth_headers,
        )
        body = status_response.json()
        assert body["result"]["report_date"] is not None
        # The synthetic mammography report has "Date of Exam: 01/15/2026"
        assert body["result"]["report_date"] == "2026-01-15"

    @pytest.mark.asyncio
    async def test_status_without_auth_returns_401(self, client: AsyncClient) -> None:
        """Polling without API key should be rejected."""
        response = await client.get("/api/v1/reports/any-id/status")
        assert response.status_code == 401
