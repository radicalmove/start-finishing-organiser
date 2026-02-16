import io
import json
import zipfile


def test_export_includes_backup_manifest_and_db_snapshot(client, api_headers):
    res = client.post(
        "/export",
        data={
            "range_choice": "all",
            "include_profile": "on",
        },
        headers=api_headers,
    )
    assert res.status_code == 200

    archive = zipfile.ZipFile(io.BytesIO(res.content))
    names = set(archive.namelist())
    assert "export.json" in names
    assert "backup_manifest.json" in names
    assert "restore_notes.txt" in names
    assert "database.sqlite3" in names

    manifest = json.loads(archive.read("backup_manifest.json").decode("utf-8"))
    file_names = {row["name"] for row in manifest["files"]}
    assert "export.json" in file_names
    assert "database.sqlite3" in file_names


def test_export_health_endpoint_reports_ready(client, api_headers):
    res = client.get("/export/health", headers=api_headers)
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["database"]["readable"] is True
