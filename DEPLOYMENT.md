# Publicação gratuita da GiControl

A aplicação é empacotada como um único serviço Docker: o FastAPI atende a API em `/api` e entrega o frontend compilado no mesmo domínio. O banco e a autenticação permanecem no Supabase.

## Render

1. Envie o repositório ao GitHub.
2. No Render, escolha **New > Blueprint** e conecte o repositório. O arquivo `render.yaml` seleciona o plano gratuito.
3. Preencha `DATABASE_URL`, `SUPABASE_URL` e `SUPABASE_ANON_KEY` quando solicitado. Nunca cadastre `SUPABASE_SERVICE_ROLE_KEY` no frontend.
4. Aguarde o health check `/api/health` ficar saudável.
5. Copie o domínio `https://...onrender.com` criado pelo Render.

## OAuth e links por e-mail

No Supabase, abra **Authentication > URL Configuration**:

- use o domínio do Render como **Site URL**;
- inclua o mesmo domínio em **Redirect URLs**;
- durante o desenvolvimento, mantenha `http://localhost:5173` e `http://localhost:5174` permitidos.

Para Google, habilite o provider no Supabase e configure no Google Cloud a callback URL mostrada pelo próprio Supabase. O Client Secret do Google fica somente no Supabase.

## Vincular os dados anteriores ao primeiro usuário

Depois que o primeiro login existir, execute uma única vez:

```powershell
python -m backend.infrastructure.migrate_legacy_to_user --email seu-email@gmail.com
```

A ferramenta preserva a origem, recusa um destino que já possua dados e compara as contagens de todas as tabelas. `--overwrite` só deve ser usado deliberadamente para substituir um destino já utilizado.

## Limitações do plano gratuito

O serviço gratuito do Render pode hibernar após um período sem acessos. O primeiro carregamento seguinte pode demorar enquanto a instância desperta. Os dados não dependem do disco do Render: continuam persistidos no Supabase.
