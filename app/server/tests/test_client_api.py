import io
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client_api.main import create_app
from client_api.store import Store
from client_api.pipeline import SENSOR_COLUMNS, validate_csv


def csv_bytes(times=(0, 20, 40, 60)):
    return (
        ",".join(SENSOR_COLUMNS)
        + "\n"
        + "\n".join(",".join(map(str, [t] + [0.25] * 22)) for t in times)
    ).encode()


class FakePipeline:
    def run(self, path, update, output):
        assert path.read_bytes().startswith(b"timestamp_ms")
        update(
            stage="sentence",
            words=["I", "NEED", "WATER"],
            expression={"label": None},
            model={"id": 9, "version": "7"},
        )
        update(
            stage="translation",
            sentence={"text": "I need water.", "status": "suggested"},
        )
        update(stage="voice", sinhala="මට වතුර අවශ්‍යයි.")
        output.write_bytes(b"RIFF" + b"\0" * 4 + b"WAVE" + b"\0" * 40)
        update(stage="done", audio_ready=True)


@pytest.fixture
def client(tmp_path):
    app = create_app(
        store=Store(tmp_path / "users.sqlite3", mongo_uri=""),
        pipeline=FakePipeline(),
        data_dir=tmp_path / "data",
    )
    with TestClient(app) as client:
        yield client


def account(client, name="First User", email="first@example.com"):
    r = client.post(
        "/auth/signup", json=dict(username=name, email=email, password="Maple!River729")
    )
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_accounts_password_policy_login_and_revocation(client):
    assert (
        client.post(
            "/auth/signup",
            json=dict(username="One", email="a@b.com", password="password"),
        ).status_code
        == 422
    )
    headers = account(client)
    assert client.get("/auth/me", headers=headers).json()["username"] == "First User"
    assert (
        client.post(
            "/auth/signup",
            json=dict(
                username="Other", email="FIRST@example.com", password="Maple!River729"
            ),
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/auth/login",
            json=dict(email="first@example.com", password="Wrong!Password123"),
        ).status_code
        == 401
    )
    login = client.post(
        "/auth/login", json=dict(email="FIRST@example.com", password="Maple!River729")
    )
    assert login.status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_pipeline_is_owned_and_history_can_be_deleted(client):
    first = account(client)
    second = account(client, "Second User", "second@example.com")
    assert (
        client.post("/recognitions", files={"file": ("x.csv", csv_bytes())}).status_code
        == 401
    )
    row = client.post(
        "/recognitions", headers=first, files={"file": ("x.csv", csv_bytes())}
    )
    assert row.status_code == 202, row.text
    id = row.json()["id"]
    for _ in range(100):
        result = client.get("/recognitions/" + id, headers=first).json()
        if result["stage"] == "done":
            break
        time.sleep(0.01)
    assert result["words"] == ["I", "NEED", "WATER"]
    assert result["sinhala"] == "මට වතුර අවශ්‍යයි."
    assert client.get("/recognitions/" + id, headers=second).status_code == 404
    assert (
        client.get("/recognitions/" + id + "/audio", headers=second).status_code == 404
    )
    assert client.delete("/recognitions/" + id, headers=second).status_code == 404
    assert client.get("/recognitions", headers=second).json() == []
    assert client.get(
        "/recognitions/" + id + "/audio", headers=first
    ).content.startswith(b"RIFF")
    assert client.delete("/recognitions/" + id, headers=first).status_code == 204
    assert (
        client.get("/recognitions/" + id + "/audio", headers=first).status_code == 404
    )


@pytest.mark.parametrize(
    "times",
    [
        (0, 20, 20, 40),
        (0, 40, 20, 60),
        (0, 20, 40),
        (-1, 20, 40, 60),
        (0, 20, 40, 300001),
        (0, 1, 2, 3),
    ],
)
def test_rejects_invalid_time_sequences(times):
    with pytest.raises(ValueError):
        validate_csv(csv_bytes(times))


def test_rejects_answer_labels_and_nonfinite_channels():
    raw = csv_bytes().decode().splitlines()
    with pytest.raises(ValueError):
        validate_csv(
            (
                "\n".join([raw[0] + ",label"] + [line + ",WATER" for line in raw[1:]])
            ).encode()
        )
    with pytest.raises(ValueError):
        validate_csv(csv_bytes().replace(b"0.25", b"inf", 1))
    assert validate_csv(csv_bytes()).startswith(b"timestamp_ms")


def test_no_admin_routes(client):
    assert client.get("/api/studio/overview").status_code == 404
    assert client.post("/training").status_code == 404


def test_sinhala_correction_regenerates_owner_audio(client, monkeypatch):
    import app.ml.sinhala_speech

    monkeypatch.setattr(
        app.ml.sinhala_speech,
        "synthesize_sinhala",
        lambda text, emotion: b"RIFF" + b"0" * 4 + b"WAVE" + text.encode(),
    )
    first = account(client, "Third User", "third@example.com")
    second = account(client, "Fourth User", "fourth@example.com")
    id = client.post(
        "/recognitions", headers=first, files={"file": ("x.csv", csv_bytes())}
    ).json()["id"]
    for _ in range(100):
        if client.get("/recognitions/" + id, headers=first).json()["stage"] == "done":
            break
        time.sleep(0.01)
    assert (
        client.patch(
            "/recognitions/" + id + "/sinhala",
            headers=second,
            json={"text": "මට වතුර ඕනේ."},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            "/recognitions/" + id + "/sinhala",
            headers=first,
            json={"text": "English only"},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/recognitions/" + id + "/sinhala",
            headers=first,
            json={"text": "මට වතුර ඕනේ."},
        ).status_code
        == 202
    )
    for _ in range(100):
        row = client.get("/recognitions/" + id, headers=first).json()
        if row["stage"] == "done":
            break
        time.sleep(0.01)
    assert row["edited"] and row["machine_sinhala"] == "මට වතුර අවශ්‍යයි."
    assert row["sinhala"] == "මට වතුර ඕනේ."
    assert client.get("/recognitions/" + id + "/audio", headers=first).content.endswith(
        "මට වතුර ඕනේ.".encode()
    )


def test_failed_translation_can_resume_without_csv_or_cross_account_access(tmp_path):
    class InterruptedPipeline:
        calls = 0

        def run(self, path, update, output):
            self.calls += 1
            update(
                words=["I", "NEED", "WATER"],
                sentence={"text": "I need water.", "status": "suggested"},
                expression={"label": None},
            )
            raise RuntimeError("Simulated translator timeout")

        def resume(self, row, update, output):
            assert row["words"] == ["I", "NEED", "WATER"]
            assert row["sentence"]["text"] == "I need water."
            output.write_bytes(b"RIFF" + b"0" * 4 + b"WAVE" + b"0" * 44)
            update(stage="done", sinhala="මට වතුර ඕනේ.", audio_ready=True, error=None)

    engine = InterruptedPipeline()
    storage = tmp_path / "recordings"
    with TestClient(
        create_app(
            store=Store(tmp_path / "retry.sqlite3", mongo_uri=""),
            pipeline=engine,
            data_dir=storage,
        )
    ) as client:
        owner = account(client, "Retry User", "retry@example.com")
        other = account(client, "Private User", "private@example.com")
        id = client.post(
            "/recognitions", headers=owner, files={"file": ("motion.csv", csv_bytes())}
        ).json()["id"]
        for _ in range(100):
            if (
                client.get("/recognitions/" + id, headers=owner).json()["stage"]
                == "error"
            ):
                break
            time.sleep(0.01)
        assert not (storage / (id + ".csv")).exists()
        assert (
            client.post("/recognitions/" + id + "/retry", headers=other).status_code
            == 404
        )
        assert (
            client.post("/recognitions/" + id + "/retry", headers=owner).status_code
            == 202
        )
        for _ in range(100):
            row = client.get("/recognitions/" + id, headers=owner).json()
            if row["stage"] == "done":
                break
            time.sleep(0.01)
        assert row["audio_ready"] and row["error"] is None and engine.calls == 1
