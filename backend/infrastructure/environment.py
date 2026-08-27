import os
from pathlib import Path
from urllib.parse import quote, urlsplit


def load_project_environment(project_dir: str | Path) -> None:
    """Carrega `.env` local sem substituir variáveis já definidas pelo ambiente."""
    env_path = Path(project_dir).resolve() / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError as error:
        raise RuntimeError("Instale as dependências com 'pip install -r requirements.txt'") from error
    load_dotenv(env_path, override=False)


def database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value.startswith(("postgres://", "postgresql://")) or "@" not in value:
        return value
    scheme, address = value.split("://", 1)
    credentials, host = address.rsplit("@", 1)
    if ":" not in credentials:
        return value
    username, password = credentials.split(":", 1)
    if username == "postgres" and ".pooler.supabase.com" in host:
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        project_ref = urlsplit(supabase_url).hostname.split(".")[0] if urlsplit(supabase_url).hostname else ""
        if project_ref and "[" not in project_ref:
            username = f"postgres.{project_ref}"
    # Preserva escapes existentes e codifica caracteres reservados de senhas copiadas em texto puro.
    return f"{scheme}://{quote(username, safe='.%')}:{quote(password, safe='%')}@{host}"
