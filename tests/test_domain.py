import unittest
from datetime import date
from decimal import Decimal

from backend.domain import (
    Account,
    AccountType,
    Category,
    Money,
    Transaction,
    TransactionType,
)


class MoneyTests(unittest.TestCase):
    def test_money_uses_decimal_and_cent_precision(self):
        value = Money.from_value("10.125")

        self.assertEqual(Decimal("10.12"), value.amount)
        self.assertEqual("BRL", value.currency)

    def test_money_arithmetic_preserves_precision(self):
        result = Money.from_value("0.10") + Money.from_value("0.20")

        self.assertEqual(Decimal("0.30"), result.amount)

    def test_unsupported_currency_is_rejected(self):
        with self.assertRaises(ValueError):
            Money(Decimal("10.00"), "USD")


class EntityTests(unittest.TestCase):
    def test_account_normalizes_text_and_allows_negative_balance(self):
        account = Account(
            id=" account-id ",
            name=" Conta principal ",
            account_type=AccountType.CHECKING,
            balance=Money.from_value("-25.50"),
        )

        self.assertEqual("account-id", account.id)
        self.assertEqual("Conta principal", account.name)
        self.assertEqual(Decimal("-25.50"), account.balance.amount)

    def test_account_rejects_negative_monthly_income(self):
        with self.assertRaises(ValueError):
            Account(
                id="account-id",
                name="Conta",
                account_type=AccountType.WALLET,
                monthly_income=Money.from_value("-1"),
            )

    def test_expense_category_accepts_monthly_limit(self):
        category = Category(
            id="category-id",
            name=" Mercado ",
            category_type=TransactionType.EXPENSE,
            monthly_limit=Money.from_value("500"),
        )

        self.assertEqual("Mercado", category.name)
        self.assertEqual(Decimal("500.00"), category.monthly_limit.amount)

    def test_income_category_rejects_monthly_limit(self):
        with self.assertRaises(ValueError):
            Category(
                id="category-id",
                name="Salário",
                category_type=TransactionType.INCOME,
                monthly_limit=Money.from_value("100"),
            )

    def test_transaction_preserves_current_fields(self):
        transaction = Transaction(
            id="transaction-id",
            amount=Money.from_value("29.90"),
            date=date(2026, 8, 26),
            category_id="category-id",
            account_id="account-id",
            description=" Mercado ",
            transaction_type=TransactionType.EXPENSE,
            is_fixed=True,
        )

        self.assertEqual("Mercado", transaction.description)
        self.assertTrue(transaction.is_fixed)

    def test_transaction_rejects_non_positive_amount(self):
        with self.assertRaises(ValueError):
            Transaction(
                id="transaction-id",
                amount=Money.zero(),
                date=date(2026, 8, 26),
                category_id="category-id",
                account_id="account-id",
                description="Teste",
                transaction_type=TransactionType.EXPENSE,
            )

    def test_entities_reject_blank_required_text(self):
        with self.assertRaises(ValueError):
            Category(
                id="category-id",
                name="   ",
                category_type=TransactionType.EXPENSE,
            )


if __name__ == "__main__":
    unittest.main()
