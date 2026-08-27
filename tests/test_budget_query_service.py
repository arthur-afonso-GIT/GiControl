import unittest
from datetime import date

from backend.application.services import BudgetQueryService
from backend.domain import CardInstallment, Category, CreditCard, Money, Transaction, TransactionType
from backend.infrastructure import JsonUnitOfWork


class BudgetQueryServiceTests(unittest.TestCase):
    def setUp(self):
        self.data = {"accounts": [], "categories": [], "transactions": []}
        self.uow = JsonUnitOfWork(self.data, lambda: None)
        self.service = BudgetQueryService(self.uow)

    def test_groups_only_reference_month_and_limited_expense_categories(self):
        self.uow.categories.save(Category("food", "Alimentação", TransactionType.EXPENSE, Money.from_value("500")))
        self.uow.categories.save(Category("free", "Lazer", TransactionType.EXPENSE, Money.zero()))
        self.uow.categories.save(Category("income", "Salário", TransactionType.INCOME, Money.zero()))
        self._transaction("current", "125", date(2026, 8, 5), "food")
        self._transaction("old", "200", date(2026, 7, 5), "food")
        self._transaction("unlimited", "50", date(2026, 8, 6), "free")

        budgets = self.service.get_month(date(2026, 8, 27))

        self.assertEqual(1, len(budgets))
        self.assertEqual(Money.from_value("125"), budgets[0].spent)
        self.assertEqual(Money.from_value("375"), budgets[0].remaining)
        self.assertEqual("25.00", str(budgets[0].usage_percentage))

    def test_keeps_overspent_amount_visible(self):
        self.uow.categories.save(Category("food", "Alimentação", TransactionType.EXPENSE, Money.from_value("100")))
        self._transaction("current", "130", date(2026, 8, 5), "food")

        budget = self.service.get_month(date(2026, 8, 27))[0]

        self.assertEqual(Money.from_value("-30"), budget.remaining)
        self.assertEqual("130.00", str(budget.usage_percentage))

    def test_card_installment_consumes_its_category_budget(self):
        self.uow.categories.save(Category("food", "Alimentação", TransactionType.EXPENSE, Money.from_value("500")))
        self.uow.credit_cards.save(CreditCard("card", "Roxo", Money.from_value("1000"), 20, 28, "account"))
        self.uow.card_installments.save_all([CardInstallment("part", "purchase", "card", "food", "Mercado", Money.from_value("140"), 1, 1, date(2026, 8, 1))])
        budget = self.service.get_month(date(2026, 8, 27))[0]
        self.assertEqual(Money.from_value("140"), budget.spent)
        self.assertEqual("28.00", str(budget.usage_percentage))

    def _transaction(self, identifier, amount, when, category_id):
        self.uow.transactions.save(Transaction(
            id=identifier, amount=Money.from_value(amount), date=when,
            category_id=category_id, account_id="account", description=identifier,
            transaction_type=TransactionType.EXPENSE,
        ))
