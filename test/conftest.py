import pytest


@pytest.fixture(autouse=True)
def default_tls_files(tmp_path, monkeypatch):
    """Nodes need TLS files to start; point the default directory at placeholder files."""
    tls = tmp_path / "config" / "xr_media" / "tls"
    tls.mkdir(parents=True)
    (tls / "cert.pem").write_text("cert", encoding="utf-8")
    (tls / "key.pem").write_text("key", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return tls
