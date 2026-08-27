import unittest
from datetime import date

from backend.application.services import CreditCardCycleService
from backend.domain import CardPurchase, CreditCard, Money


class CreditCardCycleServiceTests(unittest.TestCase):
    def setUp(self):
        self.card = CreditCard("card", "Roxo", Money.from_value("5000"), 20, 28, "account")

    def test_purchase_after_closing_moves_to_next_invoice(self):
        before = CreditCardCycleService.cycle_for_purchase(self.card, date(2026, 8, 20))
        after = CreditCardCycleService.cycle_for_purchase(self.card, date(2026, 8, 21))
        self.assertEqual(date(2026, 8, 1), before.reference_month)
        self.assertEqual(date(2026, 9, 1), after.reference_month)

    def test_due_day_before_closing_belongs_to_following_month(self):
        card = CreditCard("card", "Roxo", Money.from_value("5000"), 28, 5, "account")
        cycle = CreditCardCycleService.cycle_for_purchase(card, date(2026, 8, 10))
        self.assertEqual(date(2026, 8, 28), cycle.closing_date)
        self.assertEqual(date(2026, 9, 5), cycle.due_date)
        self.assertEqual(date(2026, 9, 1), cycle.reference_month)

    def test_installments_cross_year_and_preserve_every_cent(self):
        purchase = CardPurchase("purchase", "card", "category", "Notebook", date(2026, 12, 21),
                                Money.from_value("100.00"), 3)
        installments = CreditCardCycleService.installments_for(self.card, purchase)
        self.assertEqual([date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1)],
                         [item.invoice_month for item in installments])
        self.assertEqual(Money.from_value("100"), sum((item.amount for item in installments), Money.zero()))
        self.assertEqual([Money.from_value("33.34"), Money.from_value("33.33"), Money.from_value("33.33")],
                         [item.amount for item in installments])


if __name__ == "__main__":
    unittest.main()
