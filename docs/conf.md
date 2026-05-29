# Geração do arquivo .conf

O arquivo `.conf` é a chave/hash usada pelo PGD IRPF para validar o XML local da declaração.

O projeto já recalcula esse arquivo automaticamente após importações reais de bens, proventos, clone e migração. Quando você tiver um XML já corrigido manualmente ou por outro fluxo, use o comando dedicado:

```bat
irpf-importer conf ^
  --xml "data\work\declaracoes\00000000000 \00000000000 -0000000000.xml" ^
  --irpf-dir "%IRPF_DIR%"
```

O `.conf` será salvo ao lado do XML:

```text
00000000000 -0000000000.xml
00000000000 -0000000000.conf
```

A implementação fica em `src/irpf_importer/conf.py`, na função `recalcular_conf`. Ela chama o `java.exe` do próprio IRPF 2026 e a classe `serpro.ppgd.persistenciagenerica.RepositorioXMLDefault`.

## Cuidados

- Feche o programa IRPF antes de substituir XML/CONF na pasta oficial.
- Sempre trabalhe primeiro em `data\work`.
- Se o comando mostrar erro Java/Groovy ou `NoSuchFileException`, o `.conf` não deve ser usado.
- O comando usa caminho absoluto do XML para evitar falha de localização no Java da Receita.
