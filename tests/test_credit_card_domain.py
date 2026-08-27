import unittest
from datetime import date

from backend.domain import CardInstallment, CardInvoice, CardPurchase, CreditCard, InvoiceStatus, Money


class CreditCardDomainTests(unittest.TestCase):
    def test_card_requires_positive_limit_and_valid_cycle_days(self):
        card = CreditCard("card", " Roxo ", Money.from_value("5000"), 20, 28, "account")
        self.assertEqual("Roxo", card.name)
        with self.assertRaisesRegex(ValueError, "Limite"):
            CreditCard("card", "Roxo", Money.zero(), 20, 28, "account")
        with self.assertRaisesRegex(ValueError, "dias 1 e 31"):
            CreditCard("card", "Roxo", Money.from_value("100"), 0, 28, "account")

    def test_purchase_does_not_reference_bank_balance(self):
        purchase = CardPurchase("purchase", "card", "category", " Mercado ", date(2026, 8, 27),
                                Money.from_value("300"), 3)
        self.assertEqual("Mercado", purchase.description)
        self.assertFalse(hasattr(purchase, "account_id"))

    def test_installment_requires_first_day_invoice_reference(self):
        with self.assertRaisesRegex(ValueError, "primeiro dia"):
            CardInstallment("part", "purchase", "card", "category", "Compra", Money.from_value("100"),
                            1, 3, date(2026, 9, 2))

    def test_paid_invoice_requires_payment_audit_fields(self):
        with self.assertRaisesRegex(ValueError, "data e transação"):
            CardInvoice("invoice", "card", date(2026, 9, 1), date(2026, 8, 20), date(2026, 9, 28),
                        Money.from_value("100"), InvoiceStatus.PAID)
        invoice = CardInvoice("invoice", "card", date(2026, 9, 1), date(2026, 8, 20), date(2026, 9, 28),
                              Money.from_value("100"), InvoiceStatus.PAID, date(2026, 9, 28), "transaction")
        self.assertEqual(InvoiceStatus.PAID, invoice.status)


if __name__ == "__main__":
    unittest.main()
