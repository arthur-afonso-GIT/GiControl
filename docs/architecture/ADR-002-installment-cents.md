# ADR 002: distribuição de centavos em parcelas

## Status

Aceito para a migração do repositório de transações.

## Contexto

O comportamento legado divide valores com `float`. Valores como R$ 100,00 em três parcelas produzem números com mais de duas casas decimais, inadequados para persistência financeira e incompatíveis com `Money`.

## Decisão

Converter o total para centavos inteiros, aplicar divisão inteira e distribuir os centavos restantes nas primeiras parcelas.

R$ 100,00 em três parcelas resulta em R$ 33,34, R$ 33,33 e R$ 33,33. A soma das parcelas deve ser exatamente igual ao valor original.

## Consequências

- Toda parcela possui no máximo duas casas decimais.
- O saldo recebe exatamente o valor total da operação.
- Valores antigos com frações menores que um centavo são normalizados na leitura.
- A decisão não altera quando parcelas futuras afetam o saldo; esse comportamento continua igual ao legado.
