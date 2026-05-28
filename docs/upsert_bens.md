# Upsert de Bens e Direitos

O modo `upsert` atualiza itens existentes em **Bens e Direitos** sem duplicar quando encontra uma chave compatível entre a planilha e o XML da declaração.

## Estrutura real do XML da Receita

No XML local do IRPF 2026, os dados de cada bem ficam como **atributos** do elemento `<item>`, por exemplo:

```xml
<item
  grupo="03"
  codigo="01"
  codigoNegociacao="CMIG4"
  discriminacao="CMIG4; CIA ENERGETICA DE MINAS GERAIS"
  niEmpresa="17.155.730/0001-64"
  registroBem=""
  valorExercicioAnterior="3.100,39"
  valorExercicioAtual="4.200,00"
/>
```

Isso significa que `registroBem`, `codigoNegociacao`, `grupo`, `codigo`, `niEmpresa` e valores não aparecem como tags-filhas. Eles aparecem dentro de `item.attrib`.

## Ordem de chaves usada pelo upsert

Para cada linha da planilha, o importador monta uma chave de comparação nesta ordem:

1. `grupo + codigo + codigoNegociacao`, quando `codigoNegociacao` está preenchido.
2. `grupo + codigo + registroBem`, apenas quando `registroBem` parece um registro real, como RENAVAM, matrícula ou número longo.
3. `grupo + codigo + niEmpresa`, quando `niEmpresa` está preenchido e não há código de negociação.
4. `grupo + codigo + discriminacao normalizada`, como fallback.

Essa regra existe porque, em planilhas de investimentos, muitas vezes `registroBem` é usado como ticker. No XML real da Receita, porém, ações, FIIs, BDRs e ETFs costumam usar `codigoNegociacao`, enquanto `registroBem` fica vazio.

## Comportamento do dry-run

`--mode dry-run` simula o fluxo de `upsert` sem alterar o XML e sem recalcular o `.conf`.

Ele mostra:

- quantos itens seriam adicionados;
- quantos itens seriam atualizados;
- quantos itens seriam removidos;
- quantas linhas duplicadas da planilha foram consolidadas;
- quantas chaves ambíguas foram encontradas no XML.

Exemplo:

```text
Modo: dry-run
Adicionados: 61 | Atualizados: 73 | Removidos: 0
Duplicados consolidados: 20 | Chaves ambíguas no XML: 5
Total itens: 197
```

## Consolidação de duplicados

Antes de atualizar o XML, o importador consolida linhas repetidas da planilha com a mesma chave de upsert.

Exemplo: duas linhas de `CMIG4`, cada uma de uma corretora diferente, são agrupadas em uma única linha antes da atualização.

Campos monetários consolidados:

- `valorExercicioAnterior`
- `valorExercicioAtual`
- `valorRecebido`

Campos textuais preservados quando possível:

- `discriminacao`
- `observacao`
- `instituicao`
- `conta`

## Quando não rodar upsert

Não rode `upsert` quando o `dry-run` mostrar algo suspeito, por exemplo:

```text
Adicionados: 154 | Atualizados: 0
```

Esse resultado indica que nenhuma chave da planilha bateu com o XML e pode haver duplicação.

## Fluxo seguro recomendado

1. Feche o programa IRPF 2026.
2. Copie a pasta da declaração para `data/work/declaracoes/<CPF>`.
3. Rode `dry-run` na cópia.
4. Confira os números de adicionados, atualizados e duplicados consolidados.
5. Rode `upsert` somente na cópia de trabalho.
6. Abra a declaração no programa oficial e valide as pendências.
7. Só depois substitua os arquivos na pasta da Receita, mantendo backup.
