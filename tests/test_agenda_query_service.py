import unittest
from datetime import date

from backend.application.services import (
    AgendaQueryService,
    RecurringExpenseService,
    SaveRecurringExpenseRequest,
    ScheduledIncomeService,
)
from backend.domain import Account, AccountType, CardInvoice, CreditCard, Money
from backend.infrastructure import JsonUnitOfWork


class AgendaQueryServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [], "categories": [], "transactions": [], "scheduled_expenses": []}
        self.uow = JsonUnitOfWork(self.data, lambda: None)
        self.uow.accounts.save(Account("account", "Principal", AccountType.CHECKING,
            Money.from_value("500"), Money.from_value("2000"), 5, "salary", date(2026, 1, 1)))
        self.incomes = ScheduledIncomeService(self.uow)
        self.expenses = RecurringExpenseService(self.uow)
        self.expense = self.expenses.save(SaveRecurringExpenseRequest("Aluguel", Money.from_value("800"),
            "account", "housing", 10, date(2026, 1, 1)))
        self.service = AgendaQueryService(self.uow, self.incomes, self.expenses)

    def test_summary_projects_only_pending_occurrences(self):
        summary = self.service.get_summary(date(2026, 8, 1), date(2026, 8, 20))
        self.assertEqual(Money.from_value("500"), summary.current_balance)
        self.assertEqual(Money.from_value("2000"), summary.pending_income)
        self.assertEqual(Money.from_value("800"), summary.pending_expense)
        self.assertEqual(Money.from_value("1700"), summary.projected_balance)
        self.assertEqual(1, summary.overdue_count)

    def test_confirmed_occurrences_leave_projection(self):
        self.incomes.confirm("account", date(2026, 8, 1), date(2026, 8, 20))
        self.expenses.confirm(self.expense.id, date(2026, 8, 1), date(2026, 8, 20))
        summary = self.service.get_summary(date(2026, 8, 1), date(2026, 8, 20))
        self.assertEqual(Money.from_value("1700"), summary.current_balance)
        self.assertEqual(Money.zero(), summary.pending_income)
        self.assertEqual(Money.zero(), summary.pending_expense)
        self.assertEqual(Money.from_value("1700"), summary.projected_balance)
        self.assertEqual(0, summary.overdue_count)

    def test_unpaid_card_invoice_enters_projection_and_overdue_count(self):
        self.uow.credit_cards.save(CreditCard("card", "Roxo", Money.from_value("1000"), 5, 12, "account"))
        self.uow.card_invoices.save(CardInvoice("invoice", "card", date(2026, 8, 1), date(2026, 8, 5), date(2026, 8, 12), Money.from_value("250")))
        summary = self.service.get_summary(date(2026, 8, 1), date(2026, 8, 20))
        self.assertEqual(Money.from_value("1050"), summary.pending_expense)
        self.assertEqual(Money.from_value("1450"), summary.projected_balance)
        self.assertEqual(2, summary.overdue_count)


if __name__ == "__main__":
    unittest.main()
