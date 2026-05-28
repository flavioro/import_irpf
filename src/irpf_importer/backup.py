from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


def backup_files(xml_path: Path, backup_dir: Path | None = None, *, operation: str = "backup") -> tuple[Path, Path | None]:
    xml_path = Path(xml_path)
    base_dir = Path(backup_dir) if backup_dir else xml_path.parent / "backups"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_dir = base_dir / f"{operation}_{stamp}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    xml_backup = dest_dir / xml_path.name
    shutil.copy2(xml_path, xml_backup)

    conf_path = xml_path.with_suffix(".conf")
    conf_backup = None
    if conf_path.exists():
        conf_backup = dest_dir / conf_path.name
        shutil.copy2(conf_path, conf_backup)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "operation": operation,
        "source_xml": str(xml_path),
        "xml_backup": str(xml_backup),
        "source_conf": str(conf_path) if conf_path.exists() else None,
        "conf_backup": str(conf_backup) if conf_backup else None,
    }
    (dest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return xml_backup, conf_backup
