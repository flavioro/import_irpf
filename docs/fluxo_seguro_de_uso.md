# Fluxo seguro de uso

1. Trabalhe primeiro com uma declaração fake ou cópia de teste.
2. Rode sempre `--mode dry-run` antes de alterar qualquer arquivo.
3. Use `--backup-dir` para manter histórico de backups com timestamp.
4. Evite versionar `.xml`, `.conf`, `.bak` ou `.zip` com dados de declaração.
5. Após importar, abra o programa oficial IRPF e use a validação da Receita.
6. Recalcule o `.conf` com o Java do IRPF, exceto em testes internos controlados.

O backup atual cria uma pasta por operação, por exemplo:

```text
backup/import_bens_20260528_154233/
├── 00000000000-0000000000.xml
├── 00000000000-0000000000.conf
└── manifest.json
```
