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



## Dados de entrada incluídos

Esta versão já traz os arquivos fake de importação colocados nas pastas corretas:

```text
data/input/bens/bens_2025.xlsx
data/input/bens/bens_2025.csv
data/input/bens/bens_irpf2026_import_fake.xlsx
data/input/bens/bens_irpf2026_import_fake.csv
data/input/bens/bens_irpf_teste.csv
data/input/proventos/proventos_2025.csv
data/input/proventos/proventos_para_futura_importacao.csv
```

Para detalhes, veja `docs/dados_e_entradas.md`.


## Código-fonte

```text
src/irpf_importer/
├── __init__.py
├── __main__.py
├── backup.py
├── cli.py
├── clone.py
├── conf.py
├── migrar.py
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

Simular importação de bens. O `dry-run` simula o `upsert`, consolida duplicados da planilha e não altera o XML nem o `.conf`:

```bat
irpf-importer bens --mode dry-run --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "data\work\declaracoes\86320947187\86320947187-0000000000.xml" --arquivo data\input\bens\bens_2025.xlsx --backup-dir data\backup --sem-recalcular-conf
```

Importar bens com atualização por chave segura. O `upsert` usa primeiro `grupo + codigo + codigoNegociacao`, depois `registroBem` real, `niEmpresa` e, por último, a discriminação normalizada:

```bat
irpf-importer bens --mode upsert --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "data\work\declaracoes\86320947187\86320947187-0000000000.xml" --arquivo data\input\bens\bens_2025.xlsx --backup-dir data\backup
```

Importar proventos:

```bat
irpf-importer proventos --mode replace --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --xml "C:\caminho\declaracao.xml" --arquivo dados\proventos.xlsx --backup-dir backup
```

Gerar/atualizar somente o arquivo `.conf` de um XML já corrigido:

```bat
irpf-importer conf --xml "data\work\declaracoes\00000000000\00000000000-0000000000.xml" --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026"
```

Esse comando usa a mesma rotina Java do IRPF para gerar a chave/hash `.conf` ao lado do XML.

Clonar/sanitizar declaração para teste ou novo template, sem informar os valores reais antigos. O comando sobrescreve nome/CPF, contato, endereço, título, data de nascimento e limpa recibos conhecidos nos identificadores:

```bat
irpf-importer clone --mode identidade --source-xml "data\work\declaracoes\86320947187\86320947187-0000000000.xml" --target-dir "data\work\clone" --target-cpf "00000000000" --target-name "CONTRIBUINTE TESTE" --email "fake@example.com" --telefone "11112222" --celular "999998888" --titulo-eleitor "0000000000000" --data-nascimento "01/01/1980" --logradouro "RUA TESTE" --bairro "BAIRRO TESTE" --cep "13000000" --municipio "6291" --irpf-dir "C:\Arquivos de Programas RFB\IRPF2026" --backup-dir backup
```

Veja o mapa completo dos campos em `docs/sanitizacao_clone.md`.


## Migração para IRPF 2026

Para atualizar a declaração deste ano, use o XML **2026** que já aparece/abre no programa da Receita como base. O XML de 2025 deve ser usado apenas como referência, porque a estrutura interna muda entre versões (`serpro.ppgd.irpf.*` em 2025 e `serpro.ppgd.irpf.negocio.*` em 2026).

Por padrão, a migração **preserva recibos e metadados** do XML 2026. Ela só limpa recibos se você passar `--limpar-recibos`.

Primeiro simule:

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

Depois execute em uma pasta de trabalho:

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

Veja detalhes em `docs/migracao_2025_2026.md`.

## Upsert de Bens e Direitos

O importador foi ajustado para a estrutura real do XML da Receita: os campos de Bens ficam como atributos do elemento `<item>`. Em investimentos, o XML normalmente deixa `registroBem` vazio e usa `codigoNegociacao` para ações, FIIs, BDRs e ETFs.

Por isso, o `upsert` agora prioriza `codigoNegociacao` e consolida linhas duplicadas da planilha antes de atualizar o XML. A saída do comando mostra também:

```text
Duplicados consolidados: N | Chaves ambíguas no XML: N
```

Não rode `upsert` se o `dry-run` mostrar muitos adicionados e zero atualizados sem explicação. Primeiro confira `docs/upsert_bens.md`.

## Testes

```bat
pytest -q
```

Resultado validado nesta entrega:

```text
22 passed
```

## Documentação

- `docs/arquitetura.md`
- `docs/layouts_csv.md`
- `docs/fluxo_seguro_de_uso.md`
- `docs/comandos.md`
- `docs/estrutura_xml_irpf2026.md`
- `docs/upsert_bens.md`
- `docs/sanitizacao_clone.md`
- `docs/migracao_2025_2026.md`


## Melhorias do upsert de Bens

O importador de Bens e Direitos usa a estrutura real do XML local do IRPF 2026, onde os dados de cada bem ficam nos atributos do elemento `item`.

No modo `upsert`, a chave de comparação é escolhida nesta ordem:

1. `grupo + codigo + codigoNegociacao`, para ações, FIIs, ETFs, BDRs, CDBs e outros investimentos com código.
2. `grupo + codigo + registroBem`, somente quando `registroBem` parece um registro real, como RENAVAM, matrícula ou número longo.
3. `grupo + codigo + niEmpresa`, quando não existe código de negociação.
4. `grupo + codigo + discriminacao normalizada`, como último fallback.

Quando o XML tem mais de um item com a mesma chave, o importador considera a chave ambígua e não atualiza nem adiciona esse item automaticamente. A saída mostra `Ignorados por chave ambígua`, para evitar duplicidade silenciosa.

O recálculo do `.conf` usa caminho absoluto do XML e falha explicitamente se o Java/Groovy da Receita retornar stacktrace, `NoSuchFileException` ou não confirmar `CONF_ATUALIZADO`.

### Observação sobre o campo `tipo` em Bens

Se a planilha trouxer valores como `PN`, `ON`, `PNA`, `PNB`, `UNIT`, `BDR`, `ETF` ou `Cotas`, o importador normaliza automaticamente o atributo XML `tipo` para `T`. Isso evita erro no envio da declaração do IRPF 2026 por tamanho inválido do campo técnico. A descrição completa do tipo deve ficar no texto da discriminação.
