from __future__ import annotations

from pathlib import Path

import pytest

from irpf_importer import cli


def test_cli_conf_help_is_registered(capsys: pytest.CaptureFixture[str]):
    parser = cli.build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["conf", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Gera/atualiza o arquivo .conf" in out
    assert "--irpf-dir" in out
    assert "--xml" in out


def test_cli_conf_calls_recalcular_conf(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    xml = tmp_path / "00000000000 -0000000000.xml"
    xml.write_text("<classe />", encoding="utf-8")
    irpf_dir = tmp_path / "IRPF2026"
    irpf_dir.mkdir()
    calls = {}

    def fake_recalcular_conf(received_irpf_dir: Path, received_xml: Path) -> None:
        calls["irpf_dir"] = received_irpf_dir
        calls["xml"] = received_xml
        received_xml.with_suffix(".conf").write_text("HASH", encoding="utf-8")

    monkeypatch.setattr(cli, "recalcular_conf", fake_recalcular_conf)
    monkeypatch.setattr(
        "sys.argv",
        ["irpf-importer", "conf", "--irpf-dir", str(irpf_dir), "--xml", str(xml)],
    )

    cli.main()

    assert calls["irpf_dir"] == irpf_dir
    assert calls["xml"] == xml
    assert "CONF atualizado:" in capsys.readouterr().out
