import httpx


def test_get_dashboard(process):
    response = httpx.get("http://localhost:4080/")
    assert response.status_code == 200
