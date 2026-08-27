from copy import deepcopy
from types import TracebackType
from typing import Self

from backend.infrastructure.repositories import (
    JsonAccountRepository,
    JsonCategoryRepository,
    JsonTransactionRepository,
)


class JsonUnitOfWork:
    """Agrupa alterações no estado JSON e persiste apenas no commit."""

    def __init__(self, data: dict, persist):
        self._data = data
        self._persist = persist
        self._active = False
        self._dirty = False
        self._snapshot = None
        self.accounts = JsonAccountRepository(data["accounts"], self._changed)
        self.categories = JsonCategoryRepository(data["categories"], self._changed)
        self.transactions = JsonTransactionRepository(data["transactions"], self._changed)

    def __enter__(self) -> Self:
        if self._active:
            raise RuntimeError("Unidades de trabalho aninhadas não são suportadas")
        self._active = True
        self._dirty = False
        self._snapshot = deepcopy(self._data)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            if exc_type is not None:
                self._restore_snapshot()
            elif self._dirty:
                try:
                    self._persist()
                except Exception:
                    self._restore_snapshot()
                    raise
        finally:
            self._active = False
            self._dirty = False
            self._snapshot = None
        return False

    def _changed(self) -> None:
        if self._active:
            self._dirty = True
        else:
            self._persist()

    def _restore_snapshot(self) -> None:
        if self._snapshot is None:
            return
        for key in list(self._data):
            if key not in self._snapshot:
                del self._data[key]
        for key, original in self._snapshot.items():
            current = self._data.get(key)
            if isinstance(current, list) and isinstance(original, list):
                current[:] = deepcopy(original)
            else:
                self._data[key] = deepcopy(original)
