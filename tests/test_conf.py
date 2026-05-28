from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from irpf_importer.conf import RecalculoConfError, recalcular_conf


def make_fake_irpf(tmp_path: Path) -> Path:
    irpf_dir = tmp_path / "IRPF2026"
    (irpf_dir / "jre" / "bin").mkdir(parents=True)
    (irpf_dir / "jre" / "bin" / "java.exe").write_text("fake", encoding="utf-8")
    return irpf_dir


def test_recalcular_conf_uses_absolute_xml_path_and_validates_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    irpf_dir = make_fake_irpf(tmp_path)
    xml = tmp_path / "work" / "declaracao.xml"
    xml.parent.mkdir()
    xml.write_text("<xml />", encoding="utf-8")
    xml.with_suffix(".conf").write_text("OLD", encoding="utf-8")
    calls = {}

    def fake_run(cmd, cwd, check, capture_output, text):
        calls["cmd"] = cmd
        calls["cwd"] = cwd
        xml.with_suffix(".conf").write_text("NEW", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="HASH\nCONF_ATUALIZADO\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    recalcular_conf(irpf_dir, xml)

    assert Path(calls["cmd"][-1]).is_absolute()
    assert calls["cwd"] == irpf_dir.resolve()
    assert xml.with_suffix(".conf").read_text(encoding="utf-8") == "NEW"


def test_recalcular_conf_fails_on_java_stacktrace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    irpf_dir = make_fake_irpf(tmp_path)
    xml = tmp_path / "declaracao.xml"
    xml.write_text("<xml />", encoding="utf-8")
    xml.with_suffix(".conf").write_text("OLD", encoding="utf-8")

    def fake_run(cmd, cwd, check, capture_output, text):
        return subprocess.CompletedProcess(cmd, 0, stdout="CONF_ATUALIZADO\n", stderr="java.nio.file.NoSuchFileException: arquivo.xml")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RecalculoConfError):
        recalcular_conf(irpf_dir, xml)
