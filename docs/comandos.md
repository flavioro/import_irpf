# Comandos

Instalar em modo desenvolvimento:

```bat
pip install -e .[dev]
```

Rodar testes:

```bat
pytest -q
```

## Gerar/atualizar somente o `.conf`

Use este comando quando você já tem um XML pronto/corrigido e precisa apenas gerar a chave/hash `.conf` correspondente, sem importar bens/proventos novamente:

```bat
irpf-importer conf ^
  --xml "data\work\declaracoes\00000000000 \00000000000 -0000000000.xml" ^
  --irpf-dir "%IRPF_DIR%"
```

O arquivo `.conf` é criado/atualizado ao lado do XML:

```text
data\work\declaracoes\00000000000 \00000000000 -0000000000.conf
```

O comando usa a mesma rotina Java do programa IRPF usada pelas importações. Se o Java/Groovy retornar erro ou stacktrace, o comando falha em vez de mascarar a falha.

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

Clonar declaração sanitizada, sem informar os valores reais antigos. O comando localiza os atributos no XML e sobrescreve com valores fake:

```bat
irpf-importer clone ^
  --mode identidade ^
  --source-xml "data\work\declaracoes\86320947187\86320947187-0000000000.xml" ^
  --target-dir "data\work\clone" ^
  --target-cpf 00000000000 ^
  --target-name "CONTRIBUINTE TESTE" ^
  --email "fake@example.com" ^
  --ddd "19" ^
  --telefone "11112222" ^
  --ddd-celular "19" ^
  --celular "999998888" ^
  --titulo-eleitor "0000000000000" ^
  --data-nascimento "01/01/1980" ^
  --logradouro "RUA TESTE" ^
  --bairro "BAIRRO TESTE" ^
  --cep "13000000" ^
  --municipio "6291" ^
  --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" ^
  --backup-dir backup
```

Para gerar um template financeiro limpo, troque `--mode identidade` por `--mode template-limpo`.


## Conferir chaves de Bens

Para comparar os códigos da planilha com os códigos existentes no XML:

```bat
python -c "import csv, xml.etree.ElementTree as ET; csvp='data/input/bens/bens_2025.csv'; xmlp='data/work/declaracoes/86320947187/86320947187-0000000000.xml'; rows=list(csv.DictReader(open(csvp, encoding='utf-8-sig'))); plan={str(r.get('codigoNegociacao') or r.get('registroBem') or '').strip().upper() for r in rows if str(r.get('codigoNegociacao') or r.get('registroBem') or '').strip()}; root=ET.parse(xmlp).getroot(); xml={str(i.attrib.get('codigoNegociacao','')).strip().upper() for i in root.iter() if i.tag.endswith('item') and str(i.attrib.get('codigoNegociacao','')).strip()}; print('planilha codigos:', len(plan)); print('xml codigos:', len(xml)); print('intersecao:', len(plan & xml)); print('exemplos em ambos:', sorted(plan & xml)[:30])"
```


## Validar idempotência após upsert

Depois de rodar `upsert` na cópia de trabalho, rode novamente o `dry-run`:

```bat
irpf-importer bens ^
  --mode dry-run ^
  --irpf-dir "%IRPF_DIR%" ^
  --xml "data\work\declaracoes\%CPF%\%XML_FILE%" ^
  --arquivo "data\input\bens\bens_2025.xlsx" ^
  --backup-dir "data\backup" ^
  --sem-recalcular-conf
```

O resultado esperado deve ter `Adicionados: 0` ou somente itens que você decidiu tratar manualmente. Se aparecer `Ignorados por chave ambígua`, revise esses ativos antes de copiar para a pasta oficial da Receita.


## Migrar/atualizar declaração IRPF 2026

Use como base o XML 2026 que já aparece/abre no programa da Receita. O XML 2025 entra somente como referência opcional.

Simular sem gravar saída final:

```bat
irpf-importer migrar ^
  --base-xml-2026 "data\work\declaracoes\SEU_CPF\SEU_CPF-0000000000.xml" ^
  --referencia-xml-2025 "data\input\xml_2025\SEU_CPF-1839317427.xml" ^
  --target-dir "data\work\migracao_2026" ^
  --bens "data\input\bens\bens_2025_preparado_importacao.xlsx" ^
  --proventos "data\input\proventos\proventos_2025_preparado_importacao.xlsx" ^
  --dry-run ^
  --sem-recalcular-conf
```

Gerar a declaração de trabalho e recalcular `.conf`:

```bat
irpf-importer migrar ^
  --base-xml-2026 "data\work\declaracoes\SEU_CPF\SEU_CPF-0000000000.xml" ^
  --referencia-xml-2025 "data\input\xml_2025\SEU_CPF-1839317427.xml" ^
  --target-dir "data\work\migracao_2026" ^
  --bens "data\input\bens\bens_2025_preparado_importacao.xlsx" ^
  --proventos "data\input\proventos\proventos_2025_preparado_importacao.xlsx" ^
  --irpf-dir "%IRPF_DIR%" ^
  --report "data\reports\migracao_2025_2026.json"
```

O comando mantém CPF/nome do XML base 2026, exceto se você informar `--target-cpf` e `--target-name`.

Veja o fluxo completo em `docs/migracao_2025_2026.md`.
