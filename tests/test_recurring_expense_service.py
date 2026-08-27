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

    def test_month_can_be_postponed_without_changing_next_month(self):
        expense = self.service.save(SaveRecurringExpenseRequest("Água", Money.from_value("50"),
            "account", "category", 10, date(2026, 3, 1)))
        self.service.set_month_exception(expense.id, date(2026, 3, 1), date(2026, 3, 20))
        march = next(item for item in self.service.list_month(date(2026, 3, 1)) if item.expense.id == expense.id)
        april = next(item for item in self.service.list_month(date(2026, 4, 1)) if item.expense.id == expense.id)
        self.assertEqual(date(2026, 3, 20), march.due_date)
        self.assertEqual(date(2026, 4, 10), april.due_date)

    def test_month_can_be_skipped_without_removing_schedule(self):
        self.service.set_month_exception(self.expense.id, date(2026, 2, 1), skipped=True)
        self.assertEqual([], self.service.list_month(date(2026, 2, 1)))
        self.assertEqual(1, len(self.service.list_month(date(2026, 3, 1))))
        with self.assertRaisesRegex(ValueError, "cancelada"):
            self.service.confirm(self.expense.id, date(2026, 2, 1), date(2026, 3, 1))
