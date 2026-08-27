from datetime import date

from backend.domain import CardInstallment, CardInvoice, CardPurchase, CreditCard, InvoiceStatus, Money


class _JsonRepository:
    def __init__(self, records, persist): self.records=records; self.persist=persist
    def _save_record(self, record):
        current=next((x for x in self.records if x["id"]==record["id"]),None)
        if current is None: self.records.append(record)
        else: current.clear(); current.update(record)
        self.persist()


class JsonCreditCardRepository(_JsonRepository):
    def list_all(self): return [self._domain(x) for x in self.records]
    def get(self,item_id):
        x=next((x for x in self.records if x["id"]==item_id),None); return self._domain(x) if x else None
    def save(self,i): self._save_record({"id":i.id,"name":i.name,"credit_limit":float(i.credit_limit.amount),"closing_day":i.closing_day,"due_day":i.due_day,"payment_account_id":i.payment_account_id,"active":i.active}); return i
    def delete(self,item_id):
        before=len(self.records); self.records[:]=[x for x in self.records if x["id"]!=item_id]
        if len(self.records)!=before: self.persist(); return True
        return False
    @staticmethod
    def _domain(x): return CreditCard(x["id"],x["name"],Money.from_value(x["credit_limit"]),x["closing_day"],x["due_day"],x["payment_account_id"],x.get("active",True))


class JsonCardPurchaseRepository(_JsonRepository):
    def list_all(self): return [self._domain(x) for x in self.records]
    def get(self,item_id):
        x=next((x for x in self.records if x["id"]==item_id),None); return self._domain(x) if x else None
    def save(self,i): self._save_record({"id":i.id,"card_id":i.card_id,"category_id":i.category_id,"description":i.description,"purchase_date":i.purchase_date.isoformat(),"total_amount":float(i.total_amount.amount),"installments":i.installments}); return i
    def delete(self,item_id):
        before=len(self.records); self.records[:]=[x for x in self.records if x["id"]!=item_id]
        if len(self.records)!=before: self.persist(); return True
        return False
    @staticmethod
    def _domain(x): return CardPurchase(x["id"],x["card_id"],x["category_id"],x["description"],date.fromisoformat(x["purchase_date"]),Money.from_value(x["total_amount"]),x["installments"])


class JsonCardInstallmentRepository(_JsonRepository):
    def list_by_card(self,card_id): return [self._domain(x) for x in self.records if x["card_id"]==card_id]
    def list_by_invoice(self,card_id,reference_month): return [self._domain(x) for x in self.records if x["card_id"]==card_id and x["invoice_month"]==reference_month]
    def save_all(self,items):
        if not items:return []
        for i in items:self._save_record({"id":i.id,"purchase_id":i.purchase_id,"card_id":i.card_id,"category_id":i.category_id,"description":i.description,"amount":float(i.amount.amount),"number":i.number,"total":i.total,"invoice_month":i.invoice_month.isoformat()})
        return items
    def delete_by_purchase(self,purchase_id):
        before=len(self.records); self.records[:]=[x for x in self.records if x["purchase_id"]!=purchase_id]; count=before-len(self.records)
        if count:self.persist()
        return count
    @staticmethod
    def _domain(x): return CardInstallment(x["id"],x["purchase_id"],x["card_id"],x["category_id"],x["description"],Money.from_value(x["amount"]),x["number"],x["total"],date.fromisoformat(x["invoice_month"]))


class JsonCardInvoiceRepository(_JsonRepository):
    def list_by_card(self,card_id): return [self._domain(x) for x in self.records if x["card_id"]==card_id]
    def get(self,card_id,reference_month):
        x=next((x for x in self.records if x["card_id"]==card_id and x["reference_month"]==reference_month),None); return self._domain(x) if x else None
    def save(self,i): self._save_record({"id":i.id,"card_id":i.card_id,"reference_month":i.reference_month.isoformat(),"closing_date":i.closing_date.isoformat(),"due_date":i.due_date.isoformat(),"total":float(i.total.amount),"status":i.status.value,"paid_at":i.paid_at.isoformat() if i.paid_at else None,"payment_transaction_id":i.payment_transaction_id}); return i
    @staticmethod
    def _domain(x): return CardInvoice(x["id"],x["card_id"],date.fromisoformat(x["reference_month"]),date.fromisoformat(x["closing_date"]),date.fromisoformat(x["due_date"]),Money.from_value(x["total"]),InvoiceStatus(x["status"]),date.fromisoformat(x["paid_at"]) if x.get("paid_at") else None,x.get("payment_transaction_id"))
