from enum import StrEnum


class TransactionType(StrEnum):
    EXPENSE = "Despesa"
    INCOME = "Receita"


class AccountType(StrEnum):
    WALLET = "Carteira"
    CHECKING = "Conta Corrente"
    SAVINGS = "Poupança"
    CREDIT_CARD = "Cartão"
