"""
Tests for proxy controller event ordering and transaction lifecycle.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from harp.http import HttpRequest
from harp_apps.proxy.controllers import HttpProxyController
from harp_apps.proxy.events import EVENT_FILTER_PROXY_REQUEST, EVENT_TRANSACTION_MESSAGE, EVENT_TRANSACTION_STARTED
from harp_apps.proxy.settings import Endpoint


class TestEventOrder:
    """
    Test that events are dispatched in the correct order, allowing transaction
    modifications before storage is scheduled.
    """

    @pytest.mark.asyncio
    async def test_filter_request_called_before_transaction_message_event(self):
        """
        Test that filter_request is called before EVENT_TRANSACTION_MESSAGE is dispatched.
        This allows modifying transaction markers before the transaction is scheduled for storage.
        """
        event_order = []

        # Create a mock dispatcher that tracks event order
        mock_dispatcher = AsyncMock()

        async def track_dispatch(event_id, event=None):
            event_order.append(event_id)
            return event

        mock_dispatcher.adispatch = track_dispatch

        # Create controller with the mock dispatcher
        endpoint = Endpoint.from_kwargs(
            settings={
                "name": "test",
                "port": 80,
                "url": "http://example.com",
            }
        )
        http_client = AsyncClient()
        controller = HttpProxyController(
            http_client=http_client,
            remote=endpoint.remote,
            name=endpoint.settings.name,
            dispatcher=mock_dispatcher,
        )

        # Create a simple request
        request = HttpRequest(method="GET", path="/echo")

        # Call start_transaction
        context = await controller.start_transaction(request)

        # Verify the event order
        assert len(event_order) >= 3
        assert event_order[0] == EVENT_TRANSACTION_STARTED
        assert event_order[1] == EVENT_FILTER_PROXY_REQUEST
        assert event_order[2] == EVENT_TRANSACTION_MESSAGE

        # Verify the context was returned with a transaction
        assert context.transaction is not None
        assert context.request == request

    @pytest.mark.asyncio
    async def test_transaction_can_be_modified_by_filter_before_storage(self):
        """
        Test that the transaction can be modified via filter_request before
        EVENT_TRANSACTION_MESSAGE is dispatched (which triggers storage).
        """
        modified_tag = None

        # Create a mock dispatcher that modifies the transaction in filter_request
        mock_dispatcher = AsyncMock()

        async def modify_transaction(event_id, event=None):
            nonlocal modified_tag
            if event_id == EVENT_FILTER_PROXY_REQUEST:
                # Modify the transaction before it's sent to storage
                event.transaction.tags = ["modified-by-filter"]
                modified_tag = event.transaction.tags[0]
            return event

        mock_dispatcher.adispatch = modify_transaction

        # Create controller with the mock dispatcher
        endpoint = Endpoint.from_kwargs(
            settings={
                "name": "test",
                "port": 80,
                "url": "http://example.com",
            }
        )
        http_client = AsyncClient()
        controller = HttpProxyController(
            http_client=http_client,
            remote=endpoint.remote,
            name=endpoint.settings.name,
            dispatcher=mock_dispatcher,
        )

        # Create a simple request with initial tags
        request = HttpRequest(method="GET", path="/echo")

        # Call start_transaction with initial tags
        context = await controller.start_transaction(request, tags=["initial-tag"])

        # Verify the transaction was modified by the filter
        assert modified_tag == "modified-by-filter"
        assert context.transaction.tags == ["modified-by-filter"]
