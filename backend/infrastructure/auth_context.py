from contextvars import ContextVar

current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)
current_user_email: ContextVar[str | None] = ContextVar("current_user_email", default=None)

def user_id() -> str | None: return current_user_id.get()
