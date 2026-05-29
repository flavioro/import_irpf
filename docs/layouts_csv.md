# Layouts CSV/XLSX

Os arquivos podem ser `.csv`, `.xlsx` ou `.xlsm`. A primeira linha deve conter os nomes das colunas.

## Bens e Direitos

Colunas principais:

- `acao`: `add`, `upsert`, `delete` ou `skip`.
- `grupo`: grupo do bem no IRPF.
- `codigo`: código do bem no IRPF.
- `codigoNegociacao`: ticker/código negociado, como `CMIG4`, `ITSA4`, `HGLG11`, `AAPL34`.
- `discriminacao`: descrição do bem.
- `niEmpresa`: CNPJ/NI da empresa, quando aplicável.
- `valorExercicioAnterior`: valor em 31/12 do ano anterior no formato `1.234,56`.
- `valorExercicioAtual`: valor em 31/12 do ano atual no formato `1.234,56`.
- `registroBem`: registro real do bem, como RENAVAM, matrícula ou número longo. Para investimentos, prefira `codigoNegociacao`.

Colunas opcionais aceitas quando existem no XML de Bens:

- `pais`
- `nomePais`
- `registrado`
- `unidade`
- `dataAquisicao`
- `municipio`
- `uf`
- `cep`
- `logradouro`
- `numero`
- `complemento`
- `bairro`
- `banco`
- `agencia`
- `conta`
- `dvConta`
- `tipo`
- `valorRecebido`

### Chave do upsert em Bens

O modo `upsert` usa esta ordem de comparação:

1. `grupo + codigo + codigoNegociacao`.
2. `grupo + codigo + registroBem`, apenas quando `registroBem` parece um registro real.
3. `grupo + codigo + niEmpresa`.
4. `grupo + codigo + discriminacao normalizada`.

Para ativos negociados, preencha `codigoNegociacao`. Não use ticker em `registroBem` como chave principal.

### Duplicados na planilha

Linhas repetidas com a mesma chave de upsert são consolidadas antes da alteração do XML. Os valores monetários são somados.

## Proventos

Colunas obrigatórias:

- `produto`
- `tipoEvento`
- `valorLiquido`

Colunas recomendadas:

- `nomeFonte`
- `cnpjEmpresa`
- `codBem`
- `tipoBeneficiario`

Eventos contendo `dividendo` ou `rendimento` entram como isentos. Eventos contendo `jcp` ou `juros sobre capital` entram como tributação exclusiva.

## Campo `tipo` em Bens

Na planilha de entrada, o campo `tipo` pode vir com descrições como `ON`, `PN`, `PNA`, `PNB`, `UNIT`, `BDR`, `ETF` ou `Cotas`.

Para compatibilidade com o XML do IRPF 2026, o importador grava esse atributo técnico como `T`, porque o programa aceita somente 1 caractere nesse campo. A informação textual deve continuar na coluna `discriminacao`.
