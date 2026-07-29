import httpx

from cloudlab_cli.availability import CLUSTERS, fetch_availability


def test_certificate_fallback_is_limited_to_public_status_fetches(
    monkeypatch, capsys
) -> None:
    html = """
    <table>
      <tr><th>Type</th><th>Free</th><th>% Inuse</th></tr>
      <tr><td>node-type</td><td>2</td><td>50% inuse</td></tr>
    </table>
    """

    def fake_get(url, *, verify, **kwargs):
        request = httpx.Request("GET", url)
        if verify:
            raise httpx.ConnectError("CERTIFICATE_VERIFY_FAILED", request=request)
        return httpx.Response(200, text=html, request=request)

    monkeypatch.setattr(httpx, "get", fake_get)
    result = fetch_availability()

    assert len(result) == len(CLUSTERS)
    assert all(row["available"] == 2 for row in result)
    assert "unauthenticated status pages only" in capsys.readouterr().err
