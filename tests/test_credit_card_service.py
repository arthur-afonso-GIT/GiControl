import unittest
from datetime import date

from backend.application.services import CreateCardPurchaseRequest, CreditCardService, SaveCreditCardRequest
from backend.domain import Account, AccountType, Category, InvoiceStatus, Money, TransactionType
from backend.infrastructure import JsonUnitOfWork


class CreditCardServiceTests(unittest.TestCase):
    def setUp(self):
        self.data={"accounts":[],"categories":[],"transactions":[]}
        self.uow=JsonUnitOfWork(self.data,lambda:None)
        self.uow.accounts.save(Account("account","Principal",AccountType.CHECKING))
        self.uow.categories.save(Category("category","Compras",TransactionType.EXPENSE))
        self.service=CreditCardService(self.uow)
        self.card=self.service.save_card(SaveCreditCardRequest("Roxo",Money.from_value("1000"),20,28,"account"))

    def test_purchase_creates_installments_and_invoices_without_debiting_account(self):
        purchase, installments=self.service.create_purchase(CreateCardPurchaseRequest(self.card.id,"category","Celular",date(2026,8,21),Money.from_value("300"),3))
        self.assertEqual(3,len(installments)); self.assertEqual(Money.from_value("700"),self.service.available_limit(self.card.id))
        self.assertEqual(Money.zero(),self.uow.accounts.get("account").balance)
        invoices=self.service.list_invoices(self.card.id)
        self.assertEqual(3,len(invoices)); self.assertEqual(Money.from_value("100"),invoices[0].total)
        self.assertEqual(purchase.id,installments[0].purchase_id)

    def test_purchase_above_available_limit_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"Limite insuficiente"):
            self.service.create_purchase(CreateCardPurchaseRequest(self.card.id,"category","Compra",date(2026,8,1),Money.from_value("1000.01")))

    def test_close_and_payment_debit_once_and_restore_limit(self):
        self.uow.accounts.save(Account("account", "Principal", AccountType.CHECKING, Money.from_value("500")))
        self.service.create_purchase(CreateCardPurchaseRequest(self.card.id,"category","Compra",date(2026,8,1),Money.from_value("200")))
        closed = self.service.close_invoice(self.card.id, "2026-08", date(2026,8,20))
        self.assertEqual(InvoiceStatus.CLOSED, closed.status)
        paid = self.service.pay_invoice(self.card.id, "2026-08", date(2026,8,28))
        paid_again = self.service.pay_invoice(self.card.id, "2026-08", date(2026,8,29))
        self.assertEqual(InvoiceStatus.PAID, paid.status)
        self.assertEqual(paid.payment_transaction_id, paid_again.payment_transaction_id)
        self.assertEqual(Money.from_value("300"), self.uow.accounts.get("account").balance)
        self.assertEqual(Money.from_value("1000"), self.service.available_limit(self.card.id))
        self.assertEqual(1, len(self.uow.transactions.list_all()))

    def test_invoice_cannot_close_before_closing_date(self):
        self.service.create_purchase(CreateCardPurchaseRequest(self.card.id,"category","Compra",date(2026,8,1),Money.from_value("50")))
        with self.assertRaisesRegex(ValueError, "só pode ser fechada"):
            self.service.close_invoice(self.card.id, "2026-08", date(2026,8,19))


if __name__=="__main__":unittest.main()
