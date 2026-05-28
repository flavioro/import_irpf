# Estrutura observada do XML do IRPF 2026

Este projeto trabalha com uma declaração de teste/fake gerada no PGD IRPF 2026.

## Caminho local observado

```text
C:\Arquivos de Programas RFB\IRPF2026\aplicacao\dados\<CPF>\<CPF>-0000000000.xml
C:\Arquivos de Programas RFB\IRPF2026\aplicacao\dados\<CPF>\<CPF>-0000000000.conf
```

## Papel dos arquivos

- `.xml`: contém a declaração em estrutura XML.
- `.conf`: contém hash/controle de integridade. Deve ser recalculado sempre que o XML mudar.

## Ficha Bens e Direitos

A ficha fica na tag `<bens>`. Cada bem é um `<item>` com atributos como:

- `indice`
- `grupo`
- `codigo`
- `discriminacao`
- `pais`
- `nomePais`
- `valorExercicioAnterior`
- `valorExercicioAtual`
- `registroBem`

Ao inserir, substituir ou simular itens, o script recalcula:

- `bens/@totalItens`
- `bens/@ultimoIndiceGerado`
- `bens/@totalExercicioAnterior`
- `bens/@totalExercicioAtual`
- `resumo/outrasInformacoes/@bensDireitosExercicioAnterior`
- `resumo/outrasInformacoes/@bensDireitosExercicioAtual`

## Modos implementados

### `add`

Mantém os bens existentes e adiciona os itens do CSV ao final. O próximo `indice` é calculado a partir do maior índice já existente.

### `replace`

Remove todos os `<item>` atuais de `<bens>` e insere somente os itens do CSV. Os índices recomeçam em `00001`.

Este é o modo mais indicado para testes repetidos, porque evita duplicidade.

### `dry-run`

Carrega o XML, simula a importação e recalcula os totais em memória, mas não grava o XML e não recalcula o `.conf`.

Use antes de uma importação grande para conferir quantidade de itens e totais esperados.

## Cuidados

Use primeiro apenas CPF/declaração fake. Para dados reais, faça backup completo antes de qualquer teste e valide tudo pelo próprio programa da Receita.

## Estrutura XML de Proventos

A partir de um lançamento manual fake no IRPF, a ficha de dividendos/rendimentos isentos aparece em:

```text
rendIsentos/lucroRecebidoQuadroAuxiliar/item
```

Campos principais do item:

```text
cnpjEmpresa, codBem, cpfAlimentante, cpfBeneficiario, nomeFonte,
tipoBeneficiario, valor, valor13Salario
```

O total da ficha é refletido em:

```text
rendIsentos/@lucroRecebido
rendIsentos/@total
rendIsentos/lucroRecebidoQuadroAuxiliar/@totais
resumo/outrasInformacoes/@rendIsentosNaoTributaveis
```

Juros sobre Capital Próprio aparece em:

```text
rendTributacaoExclusiva/jurosCapitalProprioQuadroAuxiliar/item
```

E os totais são refletidos em:

```text
rendTributacaoExclusiva/@jurosCapitalProprio
rendTributacaoExclusiva/@total
rendTributacaoExclusiva/jurosCapitalProprioQuadroAuxiliar/@totais
resumo/outrasInformacoes/@rendIsentosTributacaoExclusiva
```

O importador `importar_proventos_irpf2026.py` usa esse mapeamento para importar CSVs de proventos.

## Relatório de conferência de Proventos

O importador de proventos diferencia três grupos de totais:

1. **Total existente no XML**: valores que já estavam na declaração antes da simulação/importação.
2. **Total vindo do CSV**: valores que vieram da planilha e foram classificados como importáveis.
3. **Total final no XML**: resultado final após `add`, `replace` ou simulação `dry-run`.

Essa separação evita confundir valores manuais já existentes no XML com valores importados da planilha.

Eventos atualmente suportados:

- `Dividendo` e `Rendimento`: importados em `rendIsentos/lucroRecebidoQuadroAuxiliar`.
- `Juros sobre Capital Próprio` e `JCP`: importados em `rendTributacaoExclusiva/jurosCapitalProprioQuadroAuxiliar`.

Eventos não suportados, como `Reembolso`, são contabilizados como ignorados e têm o valor somado em `Total ignorado/não suportado vindo do CSV`.

## Clonagem e sanitização de declaração

O script `clonar_declaracao_irpf2026.py` atua sobre um XML existente do IRPF e gera uma nova declaração local em `aplicacao\dados\CPF_DESTINO`.

### Campos alterados

O script atualiza os identificadores principais:

- `resumo/identificadorDeclaracao/@cpf`
- `resumo/calculoImposto/identificadorDec/@cpf`
- `nome`, `transmitida`, `numReciboTransmitido`, `numeroReciboDecAnterior`, `numReciboDecRetif`
- `contribuinte` para dados cadastrais informados na linha de comando
- atributos `cpfBeneficiario` para o CPF destino

Também limpa CPFs relacionados como `cpfAlimentante`, `cpfProcurador` e `cpfInventariante` para evitar carregar dados de terceiros.

### `template-limpo`

No modo `template-limpo`, o script remove itens de coleções financeiras e zera totais monetários de fichas como:

- Rendimentos PJ
- Rendimentos Isentos
- Tributação Exclusiva
- Pagamentos
- Bens e Direitos
- Dívidas
- Renda Variável
- Fundos
- Atividade Rural
- Resumo financeiro

Esse modo é recomendado para usar um XML apenas como estrutura técnica, sem carregar dados financeiros de outra pessoa.

### `.conf`

Após salvar o XML destino, o script chama a rotina Java do próprio IRPF para recalcular o `.conf`, usando `RepositorioXMLDefault.salvarHash(xml)`. Se `--dry-run` for usado, nada é escrito e o `.conf` não é recalculado.
