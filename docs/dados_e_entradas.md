# Dados de entrada e pastas de trabalho

Esta pasta separa arquivos de entrada, cópias de trabalho da declaração, backups e snapshots.

## Estrutura

```text
data/
├── input/
│   ├── bens/
│   │   ├── bens_2025.xlsx
│   │   ├── bens_2025.csv
│   │   ├── bens_irpf2026_import_fake.xlsx
│   │   ├── bens_irpf2026_import_fake.csv
│   │   └── bens_irpf_teste.csv
│   └── proventos/
│       ├── proventos_2025.csv
│       └── proventos_para_futura_importacao.csv
├── work/
│   └── declaracoes/
├── backup/
├── reports/
└── snapshots/
```

## Arquivo principal de teste

O comando abaixo usa o alias `data/input/bens/bens_2025.xlsx`, que aponta para a planilha fake de Bens e Direitos colocada neste projeto:

```bat
irpf-importer bens ^
  --mode dry-run ^
  --irpf-dir "%IRPF_DIR%" ^
  --xml "data\work\declaracoes\%CPF%\%XML_FILE%" ^
  --arquivo "data\input\bens\bens_2025.xlsx" ^
  --backup-dir "data\backup" ^
  --sem-recalcular-conf
```

## Atenção

Os arquivos `data/work`, `data/backup`, `data/reports`, `data/snapshots` e `tmp` são para uso local e não devem guardar dados reais versionados.
