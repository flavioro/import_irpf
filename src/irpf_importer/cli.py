from __future__ import annotations

import argparse
from pathlib import Path

from .clone import clone_declaration, print_result as print_clone_result, SUPPORTED_CLONE_MODES
from .importers.bens import run_import as run_import_bens, SUPPORTED_MODES as BENS_MODES
from .importers.proventos import run_import as run_import_proventos, SUPPORTED_MODES as PROVENTOS_MODES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="irpf-importer", description="Ferramentas para automatizar importações controladas no XML local do IRPF 2026.")
    sub = parser.add_subparsers(dest="command", required=True)

    bens = sub.add_parser("bens", help="Importa Bens e Direitos de CSV/XLSX.")
    bens.add_argument("--irpf-dir", required=True)
    bens.add_argument("--xml", required=True)
    bens.add_argument("--arquivo", "--csv", dest="arquivo", required=True, help="CSV/XLSX com bens.")
    bens.add_argument("--backup-dir")
    bens.add_argument("--mode", choices=BENS_MODES, default="dry-run")
    bens.add_argument("--sem-recalcular-conf", action="store_true")

    prov = sub.add_parser("proventos", help="Importa proventos de CSV/XLSX.")
    prov.add_argument("--irpf-dir", required=True)
    prov.add_argument("--xml", required=True)
    prov.add_argument("--arquivo", "--csv", dest="arquivo", required=True, help="CSV/XLSX com proventos.")
    prov.add_argument("--backup-dir")
    prov.add_argument("--mode", choices=PROVENTOS_MODES, default="dry-run")
    prov.add_argument("--sem-recalcular-conf", action="store_true")

    clone = sub.add_parser("clone", help="Clona/sanitiza uma declaração para outro CPF.")
    clone.add_argument("--mode", required=True, choices=SUPPORTED_CLONE_MODES)
    clone.add_argument("--source-xml", required=True)
    clone.add_argument("--target-dir", required=True)
    clone.add_argument("--target-cpf", required=True)
    clone.add_argument("--target-name", required=True)
    clone.add_argument("--irpf-dir")
    clone.add_argument("--backup-dir")
    clone.add_argument("--dry-run", action="store_true")
    clone.add_argument("--sem-recalcular-conf", action="store_true")
    for arg, default in [
        ("email", ""), ("celular", ""), ("ddd-celular", ""), ("data-nascimento", ""),
        ("cep", ""), ("tipo-logradouro", "RUA"), ("logradouro", ""), ("numero", ""),
        ("complemento", ""), ("bairro", ""), ("municipio", "0000"), ("uf", ""),
        ("natureza-ocupacao", "01"), ("ocupacao-principal", "519"), ("cpf-conjuge", ""),
    ]:
        clone.add_argument(f"--{arg}", default=default)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "bens":
        result = run_import_bens(
            irpf_dir=Path(args.irpf_dir),
            xml_path=Path(args.xml),
            csv_path=Path(args.arquivo),
            recalc_conf=not args.sem_recalcular_conf,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None,
            mode=args.mode,
        )
        s = result.stats
        print(f"Modo: {s.mode}")
        print(f"Adicionados: {s.added} | Atualizados: {s.updated} | Removidos: {s.removed}")
        print(f"Total itens: {s.total_items}")
        print(f"Totais: anterior={s.total_exercicio_anterior} atual={s.total_exercicio_atual}")
        return
    if args.command == "proventos":
        result = run_import_proventos(
            irpf_dir=Path(args.irpf_dir),
            xml_path=Path(args.xml),
            csv_path=Path(args.arquivo),
            recalc_conf=not args.sem_recalcular_conf,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None,
            mode=args.mode,
        )
        s = result.stats
        print(f"Modo: {s.mode}")
        print(f"Isentos adicionados: {s.isentos_added} | JCP adicionados: {s.jcp_added} | Ignorados: {s.ignored}")
        print(f"Totais: isentos={s.total_isentos} jcp={s.total_jcp}")
        return
    if args.command == "clone":
        result = clone_declaration(
            source_xml=Path(args.source_xml), target_dir=Path(args.target_dir), target_cpf=args.target_cpf,
            target_name=args.target_name, mode=args.mode, irpf_dir=Path(args.irpf_dir) if args.irpf_dir else None,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None, dry_run=args.dry_run,
            recalc_conf=not args.sem_recalcular_conf, email=args.email, celular=args.celular,
            ddd_celular=args.ddd_celular, data_nascimento=args.data_nascimento, cep=args.cep,
            tipo_logradouro=args.tipo_logradouro, logradouro=args.logradouro, numero=args.numero,
            complemento=args.complemento, bairro=args.bairro, municipio=args.municipio, uf=args.uf,
            natureza_ocupacao=args.natureza_ocupacao, ocupacao_principal=args.ocupacao_principal,
            cpf_conjuge=args.cpf_conjuge,
        )
        print_clone_result(result)


if __name__ == "__main__":
    main()
