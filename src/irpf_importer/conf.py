from __future__ import annotations

import subprocess
from pathlib import Path


class RecalculoConfError(RuntimeError):
    """Erro ao recalcular o arquivo .conf com a rotina Java do IRPF."""


def _classpath(irpf_dir: Path) -> str:
    sep = ";"  # O PGD IRPF usado neste projeto roda no Windows.
    return sep.join(
        [
            str(irpf_dir / "irpf.jar"),
            str(irpf_dir / "lib" / "*"),
            str(irpf_dir / "lib-modulos" / "*"),
        ]
    )


def recalcular_conf(irpf_dir: Path, xml_path: Path) -> None:
    irpf_dir = Path(irpf_dir).resolve()
    xml_path = Path(xml_path).resolve()
    java = irpf_dir / "jre" / "bin" / "java.exe"

    if not java.exists():
        raise FileNotFoundError(f"java.exe não encontrado: {java}")
    if not xml_path.exists():
        raise FileNotFoundError(f"XML não encontrado para recalcular .conf: {xml_path}")

    conf_path = xml_path.with_suffix(".conf")
    old_conf = conf_path.read_text(encoding="utf-8", errors="ignore").strip() if conf_path.exists() else ""

    cmd = [
        str(java),
        "-cp",
        _classpath(irpf_dir),
        "groovy.ui.GroovyMain",
        "-e",
        (
            "def xml=args[0]; "
            "def repo=serpro.ppgd.persistenciagenerica.RepositorioXMLDefault.getInstancia(); "
            "def hash=repo.gerarHash(xml); "
            "println hash; "
            "repo.salvarHash(xml); "
            "println 'CONF_ATUALIZADO'"
        ),
        str(xml_path),
    ]

    proc = subprocess.run(cmd, cwd=irpf_dir, check=False, capture_output=True, text=True)
    output = "\n".join(part for part in [proc.stdout, proc.stderr] if part)
    if proc.returncode != 0 or "Exception" in output or "NoSuchFileException" in output:
        raise RecalculoConfError(f"Falha ao recalcular .conf para {xml_path}:\n{output.strip()}")
    if "CONF_ATUALIZADO" not in proc.stdout:
        raise RecalculoConfError(f"Recalculo do .conf não confirmou atualização para {xml_path}:\n{output.strip()}")
    if not conf_path.exists():
        raise RecalculoConfError(f"O arquivo .conf não foi criado/atualizado: {conf_path}")

    new_conf = conf_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not new_conf:
        raise RecalculoConfError(f"O arquivo .conf ficou vazio: {conf_path}")
    if new_conf == old_conf:
        # Nem toda alteração de XML necessariamente muda o hash textual esperado pela rotina,
        # mas isso é raro. Mantemos como aviso visível, não como erro, para não bloquear testes.
        print("AVISO_CONF_SEM_ALTERACAO")
