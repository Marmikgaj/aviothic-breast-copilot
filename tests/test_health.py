"""Tests for the health check endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Health endpoint test suite."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        """Health check should return 200 with correct schema."""
        response = await client.get("/health")

        assert response.status_code == 200

        body = response.json()
        assert body["status"] == "healthy"
        assert "version" in body
        assert "timestamp" in body
        assert "environment" in body

    @pytest.mark.asyncio
    async def test_health_requires_no_auth(self, client: AsyncClient) -> None:
        """Health check should not require authentication."""
        # Intentionally omit the X-API-Key header.
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_correct_version(self, client: AsyncClient) -> None:
        """Health check should report the configured version."""
        response = await client.get("/health")
        body = response.json()
        assert body["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_health_returns_correlation_id(self, client: AsyncClient) -> None:
        """Every response should include an X-Correlation-ID header."""
        response = await client.get("/health")
        assert "x-correlation-id" in response.headers
