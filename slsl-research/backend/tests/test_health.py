def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_system_status_empty(client):
    res = client.get("/api/system/status")
    assert res.status_code == 200
    body = res.json()
    assert body["dataset_count"] == 0
    assert body["model_count"] == 0
    assert body["setup_complete"] is False
    assert body["hardware_gloves_connected"] is False
    assert body["features"]["training"] == "planned"
