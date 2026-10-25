import pytest

from harp.utils.testing.communicators import ASGICommunicator
from harp_apps.dashboard.tests._mixins import AdminThroughASGIFixtureMixin
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

    @pytest.mark.parametrize(
        "content_type, data",
        [
            ("text/html", b"<script>alert(document.domain)</script>"),
            ("image/svg+xml", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
            ("application/json", b'{"a": 1}'),
            (None, b"\x00\x01"),
        ],
    )
    async def test_get_is_never_rendered_as_a_document(
        self, controller, blob_storage: IBlobStorage, content_type, data
    ):
        await blob_storage.put(Blob(id="blob-1", data=data, content_type=content_type))

        response = await controller.get("blob-1")

        assert response.status == 200
        assert response.headers["content-disposition"] == "attachment"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-security-policy"] == "sandbox; default-src 'none'"


class TestBlobsControllerThroughASGI(
    BlobsControllerTestFixtureMixin,
    StorageTestFixtureMixin,
    AdminThroughASGIFixtureMixin,
):
    async def test_get_not_found(self, client: ASGICommunicator):
        response = await client.http_get("/api/blobs/not-a-blob")

        assert response["status"] == 404
        assert response["headers"] == ((b"content-type", b"text/plain"),)
