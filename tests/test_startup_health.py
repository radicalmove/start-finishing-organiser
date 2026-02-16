import importlib
import sys
import types

from fastapi.testclient import TestClient


def test_healthz_ok_in_normal_app():
    sys.modules.pop("main", None)
    main_mod = importlib.import_module("main")
    test_client = TestClient(main_mod.app)

    res = test_client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    sys.modules.pop("main", None)


def test_main_healthz_reports_startup_failure(monkeypatch):
    fake_app = types.ModuleType("app")

    def _fail_create_app():
        raise RuntimeError("startup exploded")

    fake_app.create_app = _fail_create_app
    monkeypatch.setitem(sys.modules, "app", fake_app)
    sys.modules.pop("main", None)

    main_mod = importlib.import_module("main")
    test_client = TestClient(main_mod.app)

    health = test_client.get("/healthz")
    assert health.status_code == 503
    payload = health.json()
    assert payload["status"] == "error"
    assert "startup exploded" in payload["detail"]

    root = test_client.get("/")
    assert root.status_code == 503
    assert "Fix startup configuration" in root.json()["hint"]

    sys.modules.pop("main", None)
