import { useEffect, useState, type FormEvent } from 'react'
import type { User } from '@supabase/supabase-js'
import { getSupabase } from '../auth/supabase'
import { passwordError } from '../auth/password'
import './ProfilePage.css'

export function ProfilePage() {
  const [user, setUser] = useState<User | null>(null)
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { void getSupabase().then(async (client) => setUser((await client?.auth.getUser())?.data.user ?? null)) }, [])
  async function savePassword(event: FormEvent) {
    event.preventDefault(); setError(null); setMessage(null)
    const validation = passwordError(password, confirmation)
    if (validation) { setError(validation); return }
    setBusy(true)
    const client = await getSupabase()
    const { error: authError } = client ? await client.auth.updateUser({ password }) : { error: new Error('Autenticação indisponível.') }
    if (authError) setError(authError.message)
    else { setPassword(''); setConfirmation(''); setMessage('Senha atualizada com segurança.') }
    setBusy(false)
  }
  const providers = [...new Set(user?.identities?.map((identity) => identity.provider) ?? [])]
  return <><header className="topbar"><div><p className="eyebrow">SUA CONTA</p><h1>Perfil e segurança</h1><p className="subtitle">Gerencie suas formas de acesso à GiControl.</p></div></header><div className="profile-grid">
    <section className="panel profile-summary"><h2>Conta</h2><dl><div><dt>E-mail</dt><dd>{user?.email ?? 'Carregando…'}</dd></div><div><dt>Acessos conectados</dt><dd>{providers.length ? providers.map((provider) => provider === 'google' ? 'Google' : 'E-mail e senha').join(' · ') : 'E-mail'}</dd></div></dl></section>
    <section className="panel profile-password"><h2>Criar ou alterar senha</h2><p>Você poderá entrar com esta senha e continuar usando o Google normalmente.</p><form onSubmit={(event) => void savePassword(event)}><label>Nova senha<input required minLength={10} type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)}/></label><label>Confirme a senha<input required minLength={10} type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)}/></label><button className="primary-button" disabled={busy} type="submit">{busy ? 'Salvando…' : 'Salvar senha'}</button></form>{message && <p className="profile-success" role="status">{message}</p>}{error && <p className="profile-error" role="alert">{error}</p>}</section>
  </div></>
}
