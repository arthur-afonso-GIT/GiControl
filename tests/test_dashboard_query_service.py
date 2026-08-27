import unittest
from datetime import date

from backend.application.services import DashboardQueryService
from backend.domain import Account, AccountType, Money, Transaction, TransactionType
from backend.infrastructure import JsonUnitOfWork


class DashboardQueryServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [], "categories": [], "transactions": []}
        self.uow = JsonUnitOfWork(self.data, lambda: None)
        self.service = DashboardQueryService(self.uow)
        self.uow.accounts.save(Account(
            id="account-1",
            name="Principal",
            account_type=AccountType.CHECKING,
            balance=Money.from_value("1700"),
            monthly_income=Money.from_value("2000"),
        ))

    def _transaction(self, identifier, amount, when, transaction_type):
        self.uow.transactions.save(Transaction(
            id=identifier,
            amount=Money.from_value(amount),
            date=when,
            category_id="category-1",
            account_id="account-1",
            description=identifier,
            transaction_type=transaction_type,
        ))

    def test_expected_income_wins_and_only_reference_month_is_summed(self):
        self._transaction("income", "1200", date(2026, 8, 10), TransactionType.INCOME)
        self._transaction("expense", "500", date(2026, 8, 11), TransactionType.EXPENSE)
        self._transaction("old", "900", date(2026, 7, 31), TransactionType.EXPENSE)

        metrics = self.service.get_metrics(date(2026, 8, 26))

        self.assertEqual(Money.from_value("1700"), metrics.current_balance)
        self.assertEqual(Money.from_value("2000"), metrics.monthly_income)
        self.assertEqual(Money.from_value("500"), metrics.monthly_expense)
        self.assertEqual(Money.from_value("1500"), metrics.savings)

    def test_real_income_wins_and_recent_transactions_are_limited(self):
        for day in range(1, 7):
            self._transaction(
                f"income-{day}", "500", date(2026, 8, day), TransactionType.INCOME
            )

        metrics = self.service.get_metrics(date(2026, 8, 26))

        self.assertEqual(Money.from_value("3000"), metrics.monthly_income)
        self.assertEqual(5, len(metrics.recent_transactions))
        self.assertEqual("income-6", metrics.recent_transactions[0].id)
