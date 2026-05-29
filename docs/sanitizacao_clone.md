# Sanitização de declaração/clonagem

O comando `irpf-importer clone` permite gerar uma cópia sanitizada de uma declaração XML do IRPF 2026 sem precisar informar os valores reais antigos.

A ferramenta lê o XML de origem, localiza os elementos/atributos conhecidos e sobrescreve os valores com dados fake ou dados informados no comando.

## Campos cadastrais tratados

| Dado | Onde aparece no XML | Atributo |
|---|---|---|
| Nome do contribuinte | `identificadorDec` | `nome` |
| Nome do contribuinte | `identificadorDeclaracao` | `nome` |
| Nome do contribuinte | `copiaIdentificador` | `nome` |
| CPF principal | `identificadorDec` | `cpf` |
| CPF principal | `identificadorDeclaracao` | `cpf` |
| CPF principal | `copiaIdentificador` | `cpf` |
| CPF repetido em rendimentos | vários `item` | `cpfBeneficiario` |
| Endereço - logradouro | `contribuinte` | `logradouro` |
| Endereço - bairro | `contribuinte` | `bairro` |
| Endereço - CEP | `contribuinte` | `cep` |
| Endereço - município | `contribuinte` | `municipio` |
| E-mail | `contribuinte` | `email` |
| Telefone | `contribuinte` | `telefone` |
| Celular | `contribuinte` | `celular` |
| Título de eleitor | `contribuinte` | `tituloEleitor` |
| Data de nascimento | `contribuinte` | `dataNascimento` |
| Recibo da declaração anterior | `identificadorDec` | `numeroReciboDecAnterior` |
| Recibo da declaração anterior | `identificadorDeclaracao` | `numeroReciboDecAnterior` |
| Recibo da declaração anterior | `copiaIdentificador` | `numeroReciboDecAnterior` |
| Recibo de declaração retificadora | `identificadorDec` | `numReciboDecRetif` |
| Recibo transmitido | `identificadorDec` | `numReciboTransmitido` |

Os atributos de recibo também são limpos nos blocos `identificadorDeclaracao` e `copiaIdentificador` quando existirem, para evitar reaproveitar identificadores da declaração original.

## Exemplo de comando

```bat
irpf-importer clone ^
  --mode identidade ^
  --source-xml "data\work\declaracoes\86320947187\86320947187-0000000000.xml" ^
  --target-dir "data\work\clone" ^
  --target-cpf "00000000000" ^
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
  --irpf-dir "%IRPF_DIR%" ^
  --backup-dir "data\backup"
```

## Modos disponíveis

- `identidade`: troca/sanitiza identidade e contato, mantém fichas financeiras, remove relações pessoais como dependentes/alimentandos/herdeiros.
- `template-limpo`: troca/sanitiza identidade e limpa fichas financeiras para gerar uma base vazia de teste.
- `anonimo`: equivalente ao fluxo de template sanitizado, indicado para criar amostras sem dados pessoais.

## Segurança

Sempre rode primeiro com `--dry-run` e depois valide o XML gerado no programa oficial do IRPF antes de usar qualquer dado real.
