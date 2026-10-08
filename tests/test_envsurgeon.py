import json
from pathlib import Path

import pytest

from envsurgeon.cli import main


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "import os\n"
        "DB_URL = os.environ['DATABASE_URL']\n"
        "PORT = os.getenv('PORT', '8080')\n"
        "print(DB_URL, PORT)\n"
    )
    (tmp_path / "web.js").write_text(
        "const key = process.env.STRIPE_KEY;\n"
        "const api = process.env.API_URL;\n"
    )
    (tmp_path / ".env.example").write_text(
        "DATABASE_URL=postgres://localhost/app\n"
        "PORT=8080\n"
        "LEGACY_FLAG=unused\n"
    )
    (tmp_path / ".gitignore").write_text("node_modules/\n.env\n")
    return tmp_path


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "envsurgeon" in capsys.readouterr().out


def test_doctor_detects_missing_and_unused(project: Path, capsys):
    code = main(["doctor", str(project)])
    out = capsys.readouterr().out
    assert code == 1
    assert "STRIPE_KEY" in out and "API_URL" in out
    assert "LEGACY_FLAG" in out
    assert "never declared" in out


def test_doctor_json_shape(project: Path, capsys):
    code = main(["doctor", str(project), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 1
    assert set(data["missing"]) == {"API_URL", "STRIPE_KEY"}
    assert data["unused"] == ["LEGACY_FLAG"]
    assert data["env_gitignored"] is True
    assert data["ok"] is False


def test_doctor_healthy_project(tmp_path: Path, capsys):
    (tmp_path / "main.go").write_text('os.Getenv("API_URL")\n')
    (tmp_path / ".env.example").write_text("API_URL=https://example.com\n")
    code = main(["doctor", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "healthy" in out


def test_scan_detects_aws_key_and_masks(tmp_path: Path, capsys):
    (tmp_path / "conf.py").write_text('AWS = "AKIAIOSFODNN7EXAMPLE"\n')
    code = main(["scan", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 1
    assert "AWS Access Key" in out
    assert "AKIAIOSFODNN7EXAMPLE" not in out  # masked


def test_scan_ignores_placeholders(tmp_path: Path, capsys):
    (tmp_path / "conf.py").write_text('API_KEY = "your-api-key-here-changeme"\n')
    code = main(["scan", str(tmp_path)])
    assert code == 0


def test_usage_lists_vars(project: Path, capsys):
    code = main(["usage", str(project)])
    out = capsys.readouterr().out
    assert code == 0
    assert "DATABASE_URL" in out and "PORT" in out


def test_missing_path_errors(capsys):
    code = main(["doctor", "/definitely/not/here"])
    assert code == 2
    assert "path not found" in capsys.readouterr().err
