# Comandos

Instalar em modo desenvolvimento:

```bat
pip install -e .
```

Rodar testes:

```bat
pytest -q
```

Importar bens em simulação:

```bat
irpf-importer bens --mode dry-run --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\...\00000000000-0000000000.xml" --arquivo examples\bens_exemplo.csv --sem-recalcular-conf
```

Importar bens atualizando sem duplicar:

```bat
irpf-importer bens --mode upsert --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\...\00000000000-0000000000.xml" --arquivo dados\bens.xlsx --backup-dir backup
```

Importar proventos:

```bat
irpf-importer proventos --mode replace --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\...\00000000000-0000000000.xml" --arquivo dados\proventos.xlsx --backup-dir backup
```

Clonar declaração sanitizada:

```bat
irpf-importer clone --mode template-limpo --source-xml origem.xml --target-dir "C:\Arquivos de Programas RFB\IRPF2026\aplicacao\dados" --target-cpf 00000000000 --target-name "PESSOA TESTE" --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --backup-dir backup
```
