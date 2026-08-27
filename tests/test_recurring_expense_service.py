import unittest
from datetime import date

from backend.application.services import RecurringExpenseService, SaveRecurringExpenseRequest
from backend.domain import Account, AccountType, Money
from backend.infrastructure import JsonUnitOfWork


class RecurringExpenseServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [], "categories": [], "transactions": [], "scheduled_expenses": []}
        self.persist_calls = 0
        self.uow = JsonUnitOfWork(self.data, self._persist)
        self.uow.accounts.save(Account("account", "Principal", AccountType.CHECKING, Money.from_value("500")))
        self.service = RecurringExpenseService(self.uow)
        self.expense = self.service.save(SaveRecurringExpenseRequest("Internet", Money.from_value("100"),
            "account", "category", 31, date(2026, 2, 1)))
        self.persist_calls = 0

    def _persist(self): self.persist_calls += 1

    def test_lists_occurrence_using_last_day_of_short_month(self):
        occurrence = self.service.list_month(date(2026, 2, 1))[0]
        self.assertEqual(date(2026, 2, 28), occurrence.due_date)
        self.assertFalse(occurrence.confirmed)

    def test_confirmation_is_idempotent_and_debits_once(self):
        first = self.service.confirm(self.expense.id, date(2026, 2, 1), date(2026, 2, 28))
        second = self.service.confirm(self.expense.id, date(2026, 2, 1), date(2026, 3, 1))
        self.assertEqual(first.id, second.id)
        self.assertEqual(400.0, self.data["accounts"][0]["balance"])
        self.assertEqual(1, len(self.data["transactions"]))
        self.assertEqual(1, self.persist_calls)

    def test_future_occurrence_cannot_be_confirmed(self):
        with self.assertRaisesRegex(ValueError, "data prevista"):
            self.service.confirm(self.expense.id, date(2026, 3, 1), date(2026, 2, 28))
