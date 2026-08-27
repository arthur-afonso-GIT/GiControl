import unittest
from datetime import date

from backend.application.services import AccountService, CreateAccountRequest
from backend.domain import AccountType, Money, Transaction, TransactionType
from backend.infrastructure import JsonUnitOfWork


class AccountServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [], "categories": [], "transactions": []}
        self.commits = 0
        self.uow = JsonUnitOfWork(self.data, self._persist)
        self.service = AccountService(self.uow)

    def _persist(self):
        self.commits += 1

    def _create_account(self):
        return self.service.create(CreateAccountRequest(
            name="Conta principal",
            account_type=AccountType.CHECKING,
            initial_balance=Money.from_value("1000"),
            monthly_income=Money.from_value("2000"),
        ))

    def test_create_and_updates_use_domain_values(self):
        account = self._create_account()
        self.service.update_balance(account.id, Money.from_value("850.25"))
        updated = self.service.update_monthly_income(
            account.id, Money.from_value("2200")
        )

        self.assertEqual(Money.from_value("850.25"), updated.balance)
        self.assertEqual(Money.from_value("2200"), updated.monthly_income)
        self.assertEqual(3, self.commits)

    def test_delete_account_and_its_transactions_commits_once(self):
        account = self._create_account()
        self.uow.transactions.save(Transaction(
            id="transaction-1",
            amount=Money.from_value("50"),
            date=date(2026, 8, 26),
            category_id="category-1",
            account_id=account.id,
            description="Compra",
            transaction_type=TransactionType.EXPENSE,
        ))
        commits_before_delete = self.commits

        self.assertTrue(self.service.delete(account.id))

        self.assertEqual([], self.data["accounts"])
        self.assertEqual([], self.data["transactions"])
        self.assertEqual(commits_before_delete + 1, self.commits)

    def test_delete_missing_account_does_not_remove_or_persist(self):
        self.uow.transactions.save(Transaction(
            id="transaction-1",
            amount=Money.from_value("50"),
            date=date(2026, 8, 26),
            category_id="category-1",
            account_id="orphan-account",
            description="Legado órfão",
            transaction_type=TransactionType.EXPENSE,
        ))
        commits_before_delete = self.commits

        self.assertTrue(self.service.delete("missing-account"))

        self.assertEqual(1, len(self.data["transactions"]))
        self.assertEqual(commits_before_delete, self.commits)
