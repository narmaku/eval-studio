"""Unit tests for the HTTP RAG backend adapter."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.rag_backends.http_adapter import HttpRAGAdapter


@pytest.fixture
def adapter():
    """Create an HttpRAGAdapter with default settings."""
    return HttpRAGAdapter(url="http://localhost:8080/api/rag")


@pytest.fixture
def custom_adapter():
    """Create an HttpRAGAdapter with custom field mappings."""
    return HttpRAGAdapter(
        url="http://localhost:9090/search",
        auth_header={"Authorization": "Bearer test-token"},
        query_field="input_text",
        answer_field="result",
        chunks_field="contexts",
    )


def _mock_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    response.json.return_value = json_data
    return response


@pytest.mark.asyncio
async def test_retrieve_and_generate_success(adapter: HttpRAGAdapter):
    """Successful retrieval returns answer and normalized chunks."""
    mock_response = _mock_httpx_response(
        {
            "answer": "Red Hat Enterprise Linux",
            "source_documents": [
                {"content": "RHEL is Red Hat Enterprise Linux.", "source": "docs/rhel.md"},
                {"content": "It is enterprise-grade.", "source": "docs/overview.md"},
            ],
        }
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    adapter._client = mock_client

    result = await adapter.retrieve_and_generate("What is RHEL?")

    assert result.answer == "Red Hat Enterprise Linux"
    assert len(result.chunks) == 2
    assert result.chunks[0]["content"] == "RHEL is Red Hat Enterprise Linux."
    assert result.chunks[0]["source"] == "docs/rhel.md"
    assert result.chunks[1]["content"] == "It is enterprise-grade."

    # Verify the POST was called with the right body
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"] == {"query": "What is RHEL?"}


@pytest.mark.asyncio
async def test_retrieve_and_generate_custom_fields(custom_adapter: HttpRAGAdapter):
    """Custom field mappings are used in request and response parsing."""
    mock_response = _mock_httpx_response(
        {
            "result": "systemd is an init system",
            "contexts": [
                {"content": "systemd manages services.", "page": 5},
            ],
        }
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    custom_adapter._client = mock_client

    result = await custom_adapter.retrieve_and_generate("What is systemd?")

    assert result.answer == "systemd is an init system"
    assert len(result.chunks) == 1
    assert result.chunks[0]["content"] == "systemd manages services."

    # Verify custom query field was used
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"] == {"input_text": "What is systemd?"}

    # Verify auth header was passed
    assert call_kwargs[1]["headers"]["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_retrieve_and_generate_string_chunks(adapter: HttpRAGAdapter):
    """String chunks are normalized to dicts with 'content' key."""
    mock_response = _mock_httpx_response(
        {
            "answer": "A Linux distribution",
            "source_documents": [
                "Fedora is a Linux distribution.",
                "It is community-driven.",
            ],
        }
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    adapter._client = mock_client

    result = await adapter.retrieve_and_generate("What is Fedora?")

    assert result.answer == "A Linux distribution"
    assert len(result.chunks) == 2
    assert result.chunks[0] == {"content": "Fedora is a Linux distribution."}
    assert result.chunks[1] == {"content": "It is community-driven."}


@pytest.mark.asyncio
async def test_health_check_success(adapter: HttpRAGAdapter):
    """Health check returns True when endpoint returns 200."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    adapter._client = mock_client

    result = await adapter.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(adapter: HttpRAGAdapter):
    """Health check returns False when endpoint raises an error."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.is_closed = False

    adapter._client = mock_client

    result = await adapter.health_check()
    assert result is False


@pytest.mark.asyncio
async def test_health_check_non_200(adapter: HttpRAGAdapter):
    """Health check returns False for non-2xx status codes."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 503

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False

    adapter._client = mock_client

    result = await adapter.health_check()
    assert result is False
