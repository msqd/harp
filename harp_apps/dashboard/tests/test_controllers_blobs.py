import pytest

from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.sqlalchemy_storage.models import Blob
from harp_apps.sqlalchemy_storage.utils.testing.mixins import SqlalchemyStorageTestFixtureMixin

from ..controllers import BlobsController


class BlobsControllerTestFixtureMixin:
    @pytest.fixture
    def controller(self, storage):
        return BlobsController(storage=storage, handle_errors=False)


class TestBlobsController(
    BlobsControllerTestFixtureMixin,
    SqlalchemyStorageTestFixtureMixin,
):
    async def test_get_not_found(self, controller):
        response = await controller.get("not-a-blob")
        assert response.status == 404
        assert response.content_type == "text/plain"

    async def test_get_existing(self, controller, storage):
        async with storage.begin() as session:
            blob = Blob(
                id="blob-1",
                data=b"hello",
            )
            session.add(blob)

        response = await controller.get("blob-1")
        assert response.status == 200
        assert response.content_type == "application/octet-stream"

        response = await controller.get("blob-2")
        assert response.status == 404
        assert response.content_type == "text/plain"


class TestBlobsControllerThroughASGI(
    BlobsControllerTestFixtureMixin,
    SqlalchemyStorageTestFixtureMixin,
    ControllerThroughASGIFixtureMixin,
):
    async def test_get_not_found(self, client: ASGICommunicator):
        response = await client.http_get("/api/blobs/not-a-blob")

        assert response["status"] == 404
        assert response["headers"] == ((b"content-type", b"text/plain"),)
