# Arquitetura

O projeto foi reorganizado para separar responsabilidades reutilizáveis:

- `money.py`: conversão monetária no formato brasileiro.
- `xml_utils.py`: namespace, busca de tags obrigatórias e utilidades de XML.
- `io_tables.py`: leitura de arquivos `.csv`, `.xlsx` e `.xlsm`.
- `backup.py`: backup com timestamp e `manifest.json`.
- `conf.py`: recálculo do arquivo `.conf` usando o Java do IRPF.
- `importar_bens.py`: regras de Bens e Direitos.
- `importar_proventos.py`: regras de proventos isentos e JCP.
- `clonar_declaracao.py`: clonagem/sanitização de declaração.
- `cli.py`: CLI unificado `irpf-importer`.

Os scripts na raiz continuam existindo como compatibilidade, mas o uso recomendado é instalar com `pip install -e .` e chamar o CLI.
