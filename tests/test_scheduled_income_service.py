import unittest
from datetime import date

from backend.application.services import ScheduledIncomeService
from backend.domain import Account, AccountType, Money
from backend.infrastructure import JsonUnitOfWork


class ScheduledIncomeServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [], "categories": [], "transactions": []}
        self.persist_calls = 0
        self.uow = JsonUnitOfWork(self.data, self._persist)
        self.service = ScheduledIncomeService(self.uow)
        self.uow.accounts.save(Account(id="account", name="Principal",
            account_type=AccountType.CHECKING, balance=Money.from_value("100"),
            monthly_income=Money.from_value("2000"), income_day=31,
            income_category_id="salary", income_start_date=date(2026, 2, 1)))
        self.persist_calls = 0

    def _persist(self):
        self.persist_calls += 1

    def test_month_preview_clamps_to_last_day(self):
        preview = self.service.list_month(date(2026, 2, 1))[0]
        self.assertEqual(date(2026, 2, 28), preview.due_date)
        self.assertFalse(preview.confirmed)

    def test_confirmation_is_idempotent_and_updates_balance_once(self):
        first = self.service.confirm("account", date(2026, 2, 1), date(2026, 2, 28))
        second = self.service.confirm("account", date(2026, 2, 1), date(2026, 3, 1))
        self.assertEqual(first.id, second.id)
        self.assertEqual(2100.0, self.data["accounts"][0]["balance"])
        self.assertEqual(1, len(self.data["transactions"]))
        self.assertEqual(1, self.persist_calls)
        self.assertTrue(self.service.list_month(date(2026, 2, 1))[0].confirmed)

    def test_future_income_cannot_be_confirmed(self):
        with self.assertRaisesRegex(ValueError, "data prevista"):
            self.service.confirm("account", date(2026, 3, 1), date(2026, 2, 28))
        self.assertEqual(0, self.persist_calls)
