# Comandos

Instalar em modo desenvolvimento:

```bat
pip install -e .[dev]
```

Rodar testes:

```bat
pytest -q
```

Importar bens em simulação segura. O `dry-run` simula `upsert`, não altera o XML e não recalcula o `.conf`:

```bat
irpf-importer bens --mode dry-run --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "data\work\declaracoes\86320947187\86320947187-0000000000.xml" --arquivo data\input\bens\bens_2025.xlsx --backup-dir data\backup --sem-recalcular-conf
```

Importar bens atualizando sem duplicar, depois de validar o `dry-run`:

```bat
irpf-importer bens --mode upsert --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "data\work\declaracoes\86320947187\86320947187-0000000000.xml" --arquivo data\input\bens\bens_2025.xlsx --backup-dir data\backup
```

Importar proventos:

```bat
irpf-importer proventos --mode replace --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\...\00000000000-0000000000.xml" --arquivo dados\proventos.xlsx --backup-dir backup
```

Clonar declaração sanitizada:

```bat
irpf-importer clone --mode template-limpo --source-xml origem.xml --target-dir "C:\Arquivos de Programas RFB\IRPF2026\aplicacao\dados" --target-cpf 00000000000 --target-name "PESSOA TESTE" --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --backup-dir backup
```


## Conferir chaves de Bens

Para comparar os códigos da planilha com os códigos existentes no XML:

```bat
python -c "import csv, xml.etree.ElementTree as ET; csvp='data/input/bens/bens_2025.csv'; xmlp='data/work/declaracoes/86320947187/86320947187-0000000000.xml'; rows=list(csv.DictReader(open(csvp, encoding='utf-8-sig'))); plan={str(r.get('codigoNegociacao') or r.get('registroBem') or '').strip().upper() for r in rows if str(r.get('codigoNegociacao') or r.get('registroBem') or '').strip()}; root=ET.parse(xmlp).getroot(); xml={str(i.attrib.get('codigoNegociacao','')).strip().upper() for i in root.iter() if i.tag.endswith('item') and str(i.attrib.get('codigoNegociacao','')).strip()}; print('planilha codigos:', len(plan)); print('xml codigos:', len(xml)); print('intersecao:', len(plan & xml)); print('exemplos em ambos:', sorted(plan & xml)[:30])"
```
