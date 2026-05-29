from __future__ import annotations

import argparse
from pathlib import Path

from .clone import clone_declaration, print_result as print_clone_result, SUPPORTED_CLONE_MODES
from .importers.bens import run_import as run_import_bens, SUPPORTED_MODES as BENS_MODES
from .importers.proventos import run_import as run_import_proventos, SUPPORTED_MODES as PROVENTOS_MODES
from .migrar import migrate_declaration, print_result as print_migration_result
from .conf import recalcular_conf


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

    conf = sub.add_parser("conf", help="Gera/atualiza o arquivo .conf correspondente a um XML do IRPF.", description="Gera/atualiza o arquivo .conf correspondente a um XML do IRPF.")
    conf.add_argument("--irpf-dir", required=True, help="Pasta de instalação do IRPF 2026.")
    conf.add_argument("--xml", required=True, help="Caminho do XML para gerar/atualizar o .conf ao lado dele.")

    migrar = sub.add_parser("migrar", help="Atualiza uma declaração IRPF 2026 usando planilhas atuais e, opcionalmente, XML 2025 como referência.")
    migrar.add_argument("--base-xml-2026", help="XML criado/reconhecido pelo programa IRPF 2026. Este é o arquivo base que será atualizado.")
    migrar.add_argument("--referencia-xml-2025", help="Opcional: XML da declaração 2025 entregue, usado apenas para comparação/referência.")
    migrar.add_argument("--source-xml", help="Compatibilidade: alias antigo para --base-xml-2026.")
    migrar.add_argument("--target-dir", required=True, help="Pasta de saída para a declaração migrada.")
    migrar.add_argument("--irpf-dir", help="Pasta de instalação do IRPF 2026. Obrigatório se recalcular .conf.")
    migrar.add_argument("--bens", help="CSV/XLSX atualizado de Bens e Direitos.")
    migrar.add_argument("--proventos", help="CSV/XLSX atualizado de proventos.")
    migrar.add_argument("--target-cpf", help="Opcional: CPF destino. Se omitido, mantém o CPF do XML/arquivo origem.")
    migrar.add_argument("--target-name", help="Opcional: nome destino. Se omitido, mantém o nome do XML origem.")
    migrar.add_argument("--bens-mode", choices=BENS_MODES, default="upsert")
    migrar.add_argument("--proventos-mode", choices=PROVENTOS_MODES, default="replace")
    migrar.add_argument("--report", help="Caminho para gravar relatório JSON da migração.")
    migrar.add_argument("--dry-run", action="store_true")
    migrar.add_argument("--limpar-recibos", action="store_true", help="Opcional: limpa recibos/metadados de transmissão. Por padrão, recibos do XML 2026 base são preservados.")
    migrar.add_argument("--sem-limpar-recibos", action="store_true", help=argparse.SUPPRESS)  # compatibilidade; agora é o padrão
    migrar.add_argument("--sem-recalcular-conf", action="store_true")

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
        ("email", ""), ("telefone", ""), ("ddd", ""), ("celular", ""), ("ddd-celular", ""),
        ("titulo-eleitor", "0000000000000"), ("data-nascimento", ""), ("cep", ""), ("tipo-logradouro", "RUA"), ("logradouro", ""), ("numero", ""),
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
        print(f"Duplicados consolidados: {s.consolidated_duplicates} | Chaves ambíguas no XML: {s.ambiguous_keys}")
        if getattr(s, "skipped_ambiguous", 0):
            print(f"Ignorados por chave ambígua: {s.skipped_ambiguous}")
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

    if args.command == "conf":
        xml_path = Path(args.xml)
        recalcular_conf(Path(args.irpf_dir), xml_path)
        conf_path = xml_path.with_suffix(".conf")
        print(f"CONF atualizado: {conf_path}")
        return

    if args.command == "migrar":
        result = migrate_declaration(
            base_xml_2026=Path(args.base_xml_2026) if args.base_xml_2026 else (Path(args.source_xml) if args.source_xml else None),
            referencia_xml_2025=Path(args.referencia_xml_2025) if args.referencia_xml_2025 else None,
            target_dir=Path(args.target_dir),
            irpf_dir=Path(args.irpf_dir) if args.irpf_dir else None,
            bens_file=Path(args.bens) if args.bens else None,
            proventos_file=Path(args.proventos) if args.proventos else None,
            target_cpf=args.target_cpf,
            target_name=args.target_name,
            clear_receipts=args.limpar_recibos,
            recalc_conf=not args.sem_recalcular_conf,
            dry_run=args.dry_run,
            bens_mode=args.bens_mode,
            proventos_mode=args.proventos_mode,
            report_path=Path(args.report) if args.report else None,
        )
        print_migration_result(result)
        return
    if args.command == "clone":
        result = clone_declaration(
            source_xml=Path(args.source_xml), target_dir=Path(args.target_dir), target_cpf=args.target_cpf,
            target_name=args.target_name, mode=args.mode, irpf_dir=Path(args.irpf_dir) if args.irpf_dir else None,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None, dry_run=args.dry_run,
            recalc_conf=not args.sem_recalcular_conf, email=args.email, telefone=args.telefone,
            ddd=args.ddd, celular=args.celular, ddd_celular=args.ddd_celular,
            titulo_eleitor=args.titulo_eleitor, data_nascimento=args.data_nascimento, cep=args.cep,
            tipo_logradouro=args.tipo_logradouro, logradouro=args.logradouro, numero=args.numero,
            complemento=args.complemento, bairro=args.bairro, municipio=args.municipio, uf=args.uf,
            natureza_ocupacao=args.natureza_ocupacao, ocupacao_principal=args.ocupacao_principal,
            cpf_conjuge=args.cpf_conjuge,
        )
        print_clone_result(result)


if __name__ == "__main__":
    main()
