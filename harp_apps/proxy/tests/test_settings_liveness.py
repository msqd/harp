import datetime

import pytest
from freezegun import freeze_time

from harp.config import Configurable
from harp.utils.testing.config import BaseConfigurableTest
from harp_apps.proxy.constants import CHECKING, DOWN, UP
from harp_apps.proxy.settings import Remote, RemoteEndpoint
from harp_apps.proxy.settings.liveness import (
    IgnoreLiveness,
    IgnoreLivenessSettings,
    InheritLivenessSettings,
    LeakyBucketLiveness,
    LeakyBucketLivenessSettings,
    LivenessSettings,
    NaiveLiveness,
    NaiveLivenessSettings,
)


class StubSettingsWithLiveness(Configurable):
    liveness: LivenessSettings = InheritLivenessSettings()


class BaseLivenessSettingsTest(BaseConfigurableTest):
    impl_type = None

    def test_build_impl(self):
        settings = self.create()
        impl = settings.liveness.build_impl()
        assert isinstance(impl, self.impl_type)


class TestDefaultLivenessSettings(BaseLivenessSettingsTest):
    type = StubSettingsWithLiveness
    initial = {}
    expected = {}
    expected_verbose = {"liveness": {"type": "inherit"}}

    def test_build_impl(self):
        assert True, "The «inherit» liveness is a placeholder, no implementation provided."


class TestNaiveLivenessSettings(BaseLivenessSettingsTest):
    type = StubSettingsWithLiveness
    impl_type = NaiveLiveness
    initial = {"liveness": {"type": "naive"}}
    expected = {"liveness": {"type": "naive"}}
    expected_verbose = {"liveness": {"failure_threshold": 1, "success_threshold": 1, "type": "naive"}}


class TestIgnoreLivenessSettings(BaseConfigurableTest):
    type = StubSettingsWithLiveness
    impl_type = IgnoreLiveness
    initial = {"liveness": {"type": "ignore"}}
    expected = {"liveness": {"type": "ignore"}}
    expected_verbose = {"liveness": {"type": "ignore"}}


class TestLeakyBucketLivenessSettings(BaseConfigurableTest):
    type = StubSettingsWithLiveness
    impl_type = LeakyBucketLiveness
    initial = {"liveness": {"type": "leaky"}}
    expected = {"liveness": {"type": "leaky"}}
    expected_verbose = {"liveness": {"capacity": 60, "rate": 1.0, "threshold": 10, "type": "leaky"}}


class MockSubject:
    status = UP
    failure_reasons = None


class TestNaiveLiveness:
    def create_liveness(self):
        return NaiveLiveness(settings=NaiveLivenessSettings())

    def test_with_mock_subject(self):
        liveness = self.create_liveness()
        subject = MockSubject()

        state_changed = liveness.success(subject)
        assert state_changed is False

        state_changed = liveness.failure(subject, "WOOPS")
        assert state_changed is True
        assert subject.status == DOWN

        state_changed = liveness.success(subject)
        assert state_changed is True
        assert subject.status == UP

    def do_test_endpoint_naive_state_changes(self, endpoint: RemoteEndpoint):
        state_changed = endpoint.success()
        assert state_changed is True

        state_changed = endpoint.success()
        assert state_changed is False

        state_changed = endpoint.failure("WOOPS")
        assert state_changed is True
        assert endpoint.status == DOWN

        state_changed = endpoint.success()
        assert state_changed is True
        assert endpoint.status == UP

    def test_with_remote_endpoint(self):
        liveness = self.create_liveness()
        endpoint = RemoteEndpoint.from_kwargs(liveness=liveness, settings={"url": "http://example.com/"})
        self.do_test_endpoint_naive_state_changes(endpoint)

    def test_with_remote_endpoint_from_settings(self):
        endpoint = RemoteEndpoint.from_kwargs(settings={"url": "http://example.com/", "liveness": {"type": "naive"}})
        self.do_test_endpoint_naive_state_changes(endpoint)

    @pytest.mark.parametrize(
        ["remote_liveness_type", "endpoint_liveness_type"],
        [
            ("naive", "naive"),
            ("naive", "inherit"),
            ("inherit", "naive"),
            ("inherit", "inherit"),  # global default is "naive" too.
        ],
    )
    def test_with_remote(self, remote_liveness_type, endpoint_liveness_type):
        remote = Remote.from_settings_dict(
            {
                "endpoints": [{"url": "http://example.com/", "liveness": {"type": endpoint_liveness_type}}],
                "liveness": {"type": remote_liveness_type},
            }
        )

        self.do_test_endpoint_naive_state_changes(remote["http://example.com/"])


class TestIgnoreLiveness:
    def create_liveness(self):
        return IgnoreLiveness(settings=IgnoreLivenessSettings())

    def test_with_mock_subject(self):
        liveness = self.create_liveness()
        subject = MockSubject()

        state_changed = liveness.success(subject)
        assert state_changed is False

        state_changed = liveness.failure(subject, "WOOPS")

        # failures are ignored with this liveness
        assert state_changed is False
        assert subject.status == UP

        # successes are also ignored with this liveness
        state_changed = liveness.success(subject)
        assert state_changed is False
        assert subject.status == UP

        # in fact, it does nothing, dot.
        subject.status = DOWN
        state_changed = liveness.success(subject)
        assert state_changed is False
        assert subject.status == DOWN

    def do_test_endpoint_ignore_state_changes(self, endpoint: RemoteEndpoint):
        initial_status = endpoint.status

        state_changed = endpoint.success()
        assert state_changed is False
        assert endpoint.status == initial_status

        state_changed = endpoint.success()
        assert state_changed is False
        assert endpoint.status == initial_status

        state_changed = endpoint.failure("WOOPS")
        assert state_changed is False
        assert endpoint.status == initial_status

        state_changed = endpoint.success()
        assert state_changed is False
        assert endpoint.status == initial_status

    def test_with_remote_endpoint(self):
        liveness = self.create_liveness()
        endpoint = RemoteEndpoint.from_kwargs(liveness=liveness, settings={"url": "http://example.com/"})
        self.do_test_endpoint_ignore_state_changes(endpoint)

    def test_with_remote_endpoint_from_settings(self):
        endpoint = RemoteEndpoint.from_kwargs(settings={"url": "http://example.com/", "liveness": {"type": "ignore"}})
        self.do_test_endpoint_ignore_state_changes(endpoint)

    @pytest.mark.parametrize(
        ["remote_liveness_type", "endpoint_liveness_type"],
        [
            ("ignore", "ignore"),
            ("ignore", "inherit"),
            ("inherit", "ignore"),
        ],
    )
    def test_with_remote(self, remote_liveness_type, endpoint_liveness_type):
        remote = Remote.from_settings_dict(
            {
                "endpoints": [{"url": "http://example.com/", "liveness": {"type": endpoint_liveness_type}}],
                "liveness": {"type": remote_liveness_type},
            }
        )

        self.do_test_endpoint_ignore_state_changes(remote["http://example.com/"])


class TestLeakyBucketLiveness:
    leaky_bucket_settings = {"capacity": 4, "threshold": 2, "rate": 1.0}

    def create_liveness(self):
        return LeakyBucketLiveness(settings=LeakyBucketLivenessSettings(**self.leaky_bucket_settings))

    def test_with_mock_subject(self):
        liveness = self.create_liveness()
        subject = MockSubject()

        now = datetime.datetime.fromisoformat("2021-01-01T00:00:00")
        with freeze_time(now) as clock:
            state_changed = liveness.success(subject)
            assert state_changed is False

            # under threshold
            state_changed = liveness.failure(subject, "WOOPS")
            assert state_changed is False
            assert subject.status == UP

            # threshold is 2, should fail
            state_changed = liveness.failure(subject, "WOOPS")
            assert state_changed is True
            assert subject.status == DOWN

            # more failures ...
            state_changed = liveness.failure(subject, "WOOPS")
            assert state_changed is False
            assert subject.status == DOWN

            # successes does not change the status, we need to wait for the bucket to leak
            assert not liveness.success(subject)
            assert not liveness.success(subject)
            assert not liveness.success(subject)

            # tic, tac, tic, tac
            clock.tick()
            assert not liveness.success(subject)

            # tic, tac, tic, tac
            clock.tick()
            assert liveness.success(subject)
            assert subject.status == UP

    def do_test_endpoint_leaky_bucket_state_changes(self, endpoint: RemoteEndpoint):
        assert endpoint.status == CHECKING
        now = datetime.datetime.fromisoformat("2021-01-01T00:00:00")
        with freeze_time(now) as clock:
            assert endpoint.success()
            assert endpoint.status == UP

            assert not endpoint.failure("WOOPS")
            assert endpoint.failure("WOOPS")
            assert endpoint.status == DOWN

            assert not endpoint.failure("WOOPS")
            assert not endpoint.success()
            assert not endpoint.success()
            assert not endpoint.success()
            clock.tick()
            assert not endpoint.success()
            clock.tick()
            assert endpoint.success()
            assert endpoint.status == UP

    def test_with_remote_endpoint(self):
        liveness = self.create_liveness()
        endpoint = RemoteEndpoint.from_kwargs(liveness=liveness, settings={"url": "http://example.com/"})
        self.do_test_endpoint_leaky_bucket_state_changes(endpoint)

    def test_with_remote_endpoint_from_settings(self):
        endpoint = RemoteEndpoint.from_kwargs(
            settings={"url": "http://example.com/", "liveness": {"type": "leaky", **self.leaky_bucket_settings}}
        )
        self.do_test_endpoint_leaky_bucket_state_changes(endpoint)

    @pytest.mark.parametrize(
        ["remote_liveness_type", "endpoint_liveness_type"],
        [
            ("leaky", "leaky"),
            ("leaky", "inherit"),
            ("inherit", "leaky"),
        ],
    )
    def test_with_remote(self, remote_liveness_type, endpoint_liveness_type):
        remote = Remote.from_settings_dict(
            {
                "endpoints": [
                    {
                        "url": "http://example.com/",
                        "liveness": {
                            "type": endpoint_liveness_type,
                            **(self.leaky_bucket_settings if endpoint_liveness_type == "leaky" else {}),
                        },
                    },
                ],
                "liveness": {
                    "type": remote_liveness_type,
                    **(self.leaky_bucket_settings if remote_liveness_type == "leaky" else {}),
                },
            }
        )

        self.do_test_endpoint_leaky_bucket_state_changes(remote["http://example.com/"])
