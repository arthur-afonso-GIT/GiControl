# ADR 001: núcleo de domínio independente

## Status

Aceito para a Fase 1.

## Contexto

O grafo inicial identificou `FinanceManager` como o principal nó de acoplamento. Ele reúne regras financeiras, estado mutável, consultas e gravação em JSON. As views PySide6 dependem dos dicionários retornados por esse objeto.

## Decisão

Criar um núcleo em `backend/domain` sem dependências de PySide6, FastAPI, SQLAlchemy ou JSON. O código legado permanece funcional e será adaptado aos novos tipos somente depois da introdução das interfaces de repositório.

As entidades iniciais são `Account`, `Category` e `Transaction`. Dinheiro passa a ser representado por `Money`, baseado em `Decimal` e limitado a centavos de BRL.

## Compatibilidade durante a transição

- IDs continuam sendo strings para preservar os UUIDs existentes.
- Os valores textuais `Receita`, `Despesa` e os tipos de conta são preservados.
- Saldos podem ser negativos, como permitido pela interface atual.
- Renda mensal e limites de categoria não podem ser negativos.
- Categorias de receita não possuem limite mensal.
- Transações precisam ter valor positivo.
- Parcelamento, recorrência, estorno e cálculo de saldo continuam no legado nesta fase.
- Nenhuma migração de `data/data.json` ocorre nesta decisão.

## Decisões postergadas

- Saldo armazenado versus saldo calculado.
- Efeito de transações futuras no saldo atual.
- Política de exclusão de contas e histórico.
- Representação de parcelas e recorrências.
- Distribuição de diferenças de centavos entre parcelas.

Essas decisões serão tratadas em ADRs próprios antes da migração dos respectivos casos de uso.
