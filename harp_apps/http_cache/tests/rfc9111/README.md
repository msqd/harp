# RFC 9111 HTTP Caching Compliance Tests

This directory contains tests that verify HARP's HTTP caching implementation complies with [RFC 9111 (HTTP Caching)](https://www.rfc-editor.org/rfc/rfc9111.html).

## Overview

RFC 9111 defines how HTTP caches should behave, including:
- Which responses can be stored
- How long cached responses remain fresh
- When cached responses must be validated
- How cache directives control behavior

These tests ensure HARP's cache implementation correctly follows the standard.

## Test Organization

| File | RFC Section | Coverage |
|------|-------------|----------|
| `test_freshness.py` | §4.2 | Freshness lifetime: max-age, Expires, Age calculations, heuristic freshness |
| `test_validation.py` | §4.3 | Conditional requests: ETags, Last-Modified, 304 responses |
| `test_cache_control_response.py` | §5.2.2 | Response directives: no-store, no-cache, private, public, must-revalidate |
| `test_cache_control_request.py` | §5.2.1 | Request directives: no-cache, no-store, max-age, min-fresh |
| `test_vary.py` | §4.1 | Vary header and content negotiation |
| `test_methods.py` | §3 | HTTP method cacheability (GET, HEAD, POST, etc.) |
| `test_status_codes.py` | §3 | Status code cacheability rules |
| `test_invalidation.py` | §7 | Cache invalidation by unsafe methods |

## Running Tests

```bash
# Run all RFC 9111 compliance tests
uv run pytest harp_apps/http_cache/tests/rfc9111/

# Run specific compliance area
uv run pytest harp_apps/http_cache/tests/rfc9111/test_freshness.py

# Run single test with RFC section reference
uv run pytest harp_apps/http_cache/tests/rfc9111/ -k "rfc9111_4_2"

# Run with verbose output showing test descriptions
uv run pytest harp_apps/http_cache/tests/rfc9111/ -v
```

## Test Naming Convention

Tests follow the pattern: `test_{behavior}_rfc9111_{section}`

Examples:
- `test_max_age_takes_precedence_rfc9111_4_2_1` - Tests §4.2.1 behavior
- `test_no_store_prevents_caching_rfc9111_5_2_2_5` - Tests §5.2.2.5 behavior
- `test_etag_validation_rfc9111_4_3_2` - Tests §4.3.2 behavior

The RFC section suffix makes it easy to:
- Find tests for specific RFC requirements
- Cross-reference tests with the specification
- Filter tests by section using pytest's `-k` flag

## Test Structure

Each test file contains:
1. **Module docstring**: Overview of what RFC section is being tested
2. **Test classes**: Group related test scenarios
3. **Test methods**: Individual RFC requirement validations

Each test method includes:
- **Docstring**: Quotes the relevant RFC requirement
- **Arrange**: Setup mock backend and cache state
- **Act**: Execute HTTP request(s)
- **Assert**: Verify RFC-compliant behavior

Example:

```python
async def test_max_age_overrides_expires_rfc9111_4_2_1(self, cached_client):
    """RFC 9111 §4.2.1: max-age directive takes precedence over Expires.

    Quote from RFC:
    > If a response includes a Cache-Control field with the max-age
    > directive, a recipient MUST ignore the Expires field.
    """
    # Test implementation...
```

## Shared Test Infrastructure

All tests use shared fixtures and helpers from `conftest.py`:

### Fixtures
- `rfc_compliant_policy` - Standard RFC 9111-compliant cache policy
- `cached_client` - HTTP client with caching enabled
- `mock_storage` - Mock storage to verify cache operations

### Response Builders
- `make_cacheable_response()` - Build responses with cache headers
- `http_date()` - Format datetime as HTTP date string

### Assertion Helpers
- `assert_cache_hit()` - Verify response was served from cache
- `assert_cache_miss()` - Verify new cache entry was created
- `assert_not_cached()` - Verify response was not cached
- `assert_response_fresh()` - Verify response is within freshness lifetime
- `assert_response_stale()` - Verify response exceeded freshness lifetime

## RFC 9111 Quick Reference

### Key Concepts

**Freshness (§4.2)**
- Fresh response: Can be served from cache without validation
- Stale response: Should be validated before serving
- Freshness lifetime: Determined by max-age, s-maxage, or Expires

**Validation (§4.3)**
- Conditional request: Uses If-None-Match or If-Modified-Since
- 304 Not Modified: Indicates cached response is still valid
- Strong vs weak validators: ETags can be weak ("W/") or strong

**Cache Directives (§5.2)**
- Request directives: Control cache behavior for this request
- Response directives: Control how response may be cached

### Common Cache-Control Directives

**Response Directives:**
- `max-age=<seconds>` - How long response is fresh
- `s-maxage=<seconds>` - Like max-age but only for shared caches
- `no-cache` - Must validate before using cached response
- `no-store` - Must not store response in cache
- `private` - Only private caches may store
- `public` - Any cache may store
- `must-revalidate` - Cannot serve stale without validation

**Request Directives:**
- `max-age=<seconds>` - Only accept responses fresher than this
- `min-fresh=<seconds>` - Only accept responses that will be fresh for this long
- `no-cache` - Do not use cached response without validation
- `no-store` - Do not store this request/response
- `only-if-cached` - Only return cached response, don't contact origin

## Adding New Tests

When adding tests for new RFC requirements:

1. **Identify the RFC section** - Note the specific section number
2. **Choose the appropriate file** - Based on the test organization above
3. **Write descriptive test name** - Include RFC section in name
4. **Quote the RFC** - Include relevant quote in docstring
5. **Use shared helpers** - Leverage conftest.py fixtures and builders
6. **Keep tests focused** - One test per RFC requirement

## Contributing

When contributing RFC compliance tests:
- Keep tests simple and focused on one behavior
- Quote the relevant RFC text in docstrings
- Use shared fixtures to avoid duplication
- Verify tests fail when caching is disabled
- Update this README if adding new test files
