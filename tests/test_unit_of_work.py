import unittest

from backend.domain import Account, AccountType, Money
from backend.infrastructure import JsonUnitOfWork


class JsonUnitOfWorkTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "accounts": [],
            "categories": [],
            "transactions": [],
        }
        self.persist_calls = 0
        self.unit_of_work = JsonUnitOfWork(self.data, self._persist)

    def _persist(self):
        self.persist_calls += 1

    def test_multiple_repository_changes_commit_once(self):
        with self.unit_of_work as uow:
            uow.accounts.save(
                Account(
                    id="account",
                    name="Conta",
                    account_type=AccountType.CHECKING,
                    balance=Money.from_value("100"),
                )
            )
            uow.accounts.save(
                Account(
                    id="account",
                    name="Conta",
                    account_type=AccountType.CHECKING,
                    balance=Money.from_value("90"),
                )
            )

        self.assertEqual(1, self.persist_calls)
        self.assertEqual(90.0, self.data["accounts"][0]["balance"])

    def test_exception_rolls_back_memory_without_persisting(self):
        with self.assertRaises(RuntimeError):
            with self.unit_of_work as uow:
                uow.accounts.save(
                    Account(
                        id="account",
                        name="Conta",
                        account_type=AccountType.CHECKING,
                    )
                )
                raise RuntimeError("falha simulada")

        self.assertEqual([], self.data["accounts"])
        self.assertEqual(0, self.persist_calls)

    def test_persistence_failure_rolls_back_memory(self):
        failing = JsonUnitOfWork(self.data, lambda: (_ for _ in ()).throw(OSError("disco")))

        with self.assertRaises(OSError):
            with failing as uow:
                uow.accounts.save(
                    Account(
                        id="account",
                        name="Conta",
                        account_type=AccountType.CHECKING,
                    )
                )

        self.assertEqual([], self.data["accounts"])


if __name__ == "__main__":
    unittest.main()
