# IRPF Importer

Ferramentas experimentais para importar dados de planilhas `.csv` e `.xlsx` no XML local do IRPF 2026, com foco em testes controlados, backup e validação posterior no programa oficial da Receita Federal.

> Aviso: este projeto não substitui o programa oficial IRPF. Sempre valide a declaração no IRPF antes de transmitir. Não versionar XML/CONF reais de declaração.

## Estrutura organizada

A raiz do projeto agora fica apenas com arquivos de configuração/documentação e pastas principais:

```text
.
├── .gitignore
├── README.md
├── pyproject.toml
├── requirements.txt
├── docs/
├── examples/
├── scripts/
├── src/
└── tests/
```

Não ficam mais scripts Python soltos na raiz. Os comandos antigos `importar_bens_irpf2026.py`, `importar_proventos_irpf2026.py` e `clonar_declaracao_irpf2026.py` foram removidos da raiz; agora o ponto de entrada oficial é o CLI unificado `irpf-importer`.

## Código-fonte

```text
src/irpf_importer/
├── __init__.py
├── __main__.py
├── backup.py
├── cli.py
├── clone.py
├── conf.py
├── importers/
│   ├── __init__.py
│   ├── bens.py
│   └── proventos.py
├── io_tables.py
├── money.py
└── xml_utils.py
```

## Instalação

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

Ou, sem extras de desenvolvimento:

```bat
pip install -r requirements.txt
pip install -e .
```

## Uso rápido

Simular importação de bens:

```bat
irpf-importer bens --mode dry-run --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\caminho\declaracao.xml" --arquivo examples\bens_exemplo.csv --sem-recalcular-conf
```

Importar bens com atualização por chave:

```bat
irpf-importer bens --mode upsert --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\caminho\declaracao.xml" --arquivo dados\bens.xlsx --backup-dir backup
```

Importar proventos:

```bat
irpf-importer proventos --mode replace --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\caminho\declaracao.xml" --arquivo dados\proventos.xlsx --backup-dir backup
```

Clonar/sanitizar declaração para template de teste:

```bat
irpf-importer clone --mode template-limpo --source-xml "C:\caminho\origem.xml" --target-dir "C:\Arquivos de Programas RFB\IRPF2026\aplicacao\dados" --target-cpf "00000000000" --target-name "PESSOA TESTE" --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --backup-dir backup
```

## Testes

```bat
pytest -q
```

Resultado validado nesta entrega:

```text
12 passed
```

## Documentação

- `docs/arquitetura.md`
- `docs/layouts_csv.md`
- `docs/fluxo_seguro_de_uso.md`
- `docs/comandos.md`
- `docs/estrutura_xml_irpf2026.md`
