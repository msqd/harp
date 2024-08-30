import pytest

from harp.utils.testing.communicators import ASGICommunicator
from harp.utils.testing.mixins import ControllerThroughASGIFixtureMixin
from harp_apps.dashboard.controllers.blobs import BlobsController
from harp_apps.storage.models import Blob
from harp_apps.storage.types import IBlobStorage
from harp_apps.storage.utils.testing.mixins import StorageTestFixtureMixin


class BlobsControllerTestFixtureMixin:
    @pytest.fixture
    async def controller(self, blob_storage):
        return BlobsController(storage=blob_storage, handle_errors=False)


class TestBlobsController(
    BlobsControllerTestFixtureMixin,
    StorageTestFixtureMixin,
):
    async def test_get_not_found(self, controller):
        response = await controller.get("not-a-blob")
        assert response.status == 404
        assert response.content_type == "text/plain"

    async def test_get_existing(self, controller, blob_storage: IBlobStorage):
        await blob_storage.put(Blob(id="blob-1", data=b"hello"))

        response = await controller.get("blob-1")
        assert response.status == 200
        assert response.content_type == "application/octet-stream"

        response = await controller.get("blob-2")
        assert response.status == 404
        assert response.content_type == "text/plain"


class TestBlobsControllerThroughASGI(
    BlobsControllerTestFixtureMixin,
    StorageTestFixtureMixin,
    ControllerThroughASGIFixtureMixin,
):
    async def test_get_not_found(self, client: ASGICommunicator):
        response = await client.http_get("/api/blobs/not-a-blob")

        assert response["status"] == 404
        assert response["headers"] == ((b"content-type", b"text/plain"),)
