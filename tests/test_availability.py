from cloudlab_cli.availability import parse_cluster_status


def test_parse_cluster_status_table() -> None:
    html = """
    <table><tr><th>Other</th></tr></table>
    <table>
      <thead><tr><th colspan="3">Cluster Status</th></tr></thead>
      <tbody>
        <tr><td colspan="3">Active Experiments: 4</td></tr>
        <tr><th>Type</th><th>Free</th><th>% Inuse</th></tr>
        <tr><td>c6525-100g</td><td><span>8</span></td><td>78% inuse</td></tr>
        <tr><td>m400</td><td><span>31</span></td><td>31% inuse</td></tr>
      </tbody>
    </table>
    """
    assert parse_cluster_status(html, "Utah") == [
        {"cluster": "Utah", "type": "c6525-100g", "available": 8},
        {"cluster": "Utah", "type": "m400", "available": 31},
    ]
