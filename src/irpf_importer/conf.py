from __future__ import annotations

import subprocess
from pathlib import Path


def recalcular_conf(irpf_dir: Path, xml_path: Path) -> None:
    java = irpf_dir / "jre" / "bin" / "java.exe"
    if not java.exists():
        raise FileNotFoundError(f"java.exe não encontrado: {java}")
    cmd = [
        str(java),
        "-cp",
        str(irpf_dir / "irpf.jar") + ";" + str(irpf_dir / "lib" / "*") + ";" + str(irpf_dir / "lib-modulos" / "*"),
        "groovy.ui.GroovyMain",
        "-e",
        (
            "def xml=args[0]; "
            "def repo=serpro.ppgd.persistenciagenerica.RepositorioXMLDefault.getInstancia(); "
            "println repo.gerarHash(xml); "
            "repo.salvarHash(xml); "
            "println 'CONF_ATUALIZADO'"
        ),
        str(xml_path),
    ]
    subprocess.run(cmd, cwd=irpf_dir, check=True)
