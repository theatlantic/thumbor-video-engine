import pytest
import pytest_asyncio
import aiobotocore.session
from aiobotocore.config import AioConfig

from tests.moto_server import MotoService


@pytest_asyncio.fixture
async def s3_server(monkeypatch, event_loop):
    monkeypatch.setenv("TEST_SERVER_MODE", "true")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test-session-token")
    async with MotoService("s3", ssl=False) as svc:
        yield svc.endpoint_url


@pytest.fixture
def session(event_loop):
    return aiobotocore.session.AioSession()


@pytest_asyncio.fixture
async def s3_client(
    session,
    s3_server,
):
    # This depends on mock_attributes because we may want to test event listeners.
    # See the documentation of `mock_attributes` for details.
    read_timeout = connect_timeout = 5
    region = "us-east-1"

    async with session.create_client(
        "s3",
        region_name=region,
        config=AioConfig(
            region_name=region,
            signature_version="s3",
            read_timeout=read_timeout,
            connect_timeout=connect_timeout,
        ),
        verify=False,
        endpoint_url=s3_server,
        aws_secret_access_key="xxx",
        aws_access_key_id="xxx",
    ) as client:
        yield client
