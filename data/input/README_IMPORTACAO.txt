Importação IRPF 2026 - relatório-consolidado-anual-2025.xlsx
Arquivos gerados:
- bens_irpf2026_import_fake.csv: CSV compatível com o importador atual de Bens e Direitos.
- proventos_para_futura_importacao.csv: resumo de proventos/reembolsos; ainda não é importado pelo script atual.

Quantidade de linhas para Bens e Direitos:
- Posição - Ações: 41 itens, total importado para teste: 149.243,33
- Posição - BDR: 26 itens, total importado para teste: 78.474,09
- Posição - ETF: 5 itens, total importado para teste: 17.729,67
- Posição - Fundos: 32 itens, total importado para teste: 93.381,20
- Posição - Renda Fixa: 48 itens, total importado para teste: 79.657,21
- Posição - Tesouro Direto: 2 itens, total importado para teste: 4.262,20

Total geral de itens de Bens e Direitos: 154
Total geral importado para teste: 422.747,70

Observações importantes:
1. O arquivo usa os valores 'Valor Atualizado' da planilha como valorExercicioAtual, apenas para teste em declaração fake.
2. Para declaração real, ações/BDRs/ETFs/FIIs normalmente devem ser informados pelo custo de aquisição, não pelo valor de mercado.
3. O importador atual apenas adiciona itens; se rodar o mesmo CSV duas vezes, vai duplicar os bens.
4. Proventos e reembolsos foram separados, porque exigem outro módulo de importação no XML.
5. A aba Posição - Empréstimos não foi inserida no CSV de Bens para evitar possível duplicidade com ativos já listados. Pode ser tratada depois.

XML base 2025 fake:
- data/input/xml_2025/21585587400-0000000000.xml

Uso sugerido para migração:
irpf-importer migrar --source-xml "data\input\xml_2025\21585587400-0000000000.xml" --target-dir "data\work\migracao_2026" --bens "data\input\bens\bens_2025.xlsx" --dry-run --sem-recalcular-conf
