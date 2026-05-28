# Layouts CSV/XLSX

## Bens e Direitos

Colunas principais:

- `acao`: `add`, `upsert`, `delete` ou `skip`.
- `grupo`: grupo do bem no IRPF.
- `codigo`: código do bem no IRPF.
- `discriminacao`: descrição do bem.
- `valorExercicioAnterior`: valor em 31/12 do ano anterior no formato `1.234,56`.
- `valorExercicioAtual`: valor em 31/12 do ano atual no formato `1.234,56`.
- `registroBem`: chave recomendada para atualizar o mesmo item sem duplicar.

O modo `upsert` procura primeiro por `registroBem`. Se estiver vazio, usa a chave natural `grupo + codigo + discriminacao normalizada`.

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
