import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import type { Session, SupabaseClient } from '@supabase/supabase-js'
import { getSupabase, supabaseSetupIssue } from './supabase'
import { passwordError } from './password'
import { authErrorMessage, signupMayBePending } from './authMessages'
import './AuthGate.css'
import './AuthEnhancements.css'

type AuthMode = 'login' | 'signup' | 'confirmation' | 'forgot' | 'recovery'

export function AuthGate({ children }: { children: ReactNode }) {
  const [supabase, setSupabase] = useState<SupabaseClient | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [configured, setConfigured] = useState(true)
  const [configurationIssue, setConfigurationIssue] = useState<'api' | 'config' | 'disabled' | null>(null)
  const [mode, setMode] = useState<AuthMode>(() => new URLSearchParams(window.location.search).has('recovery') ? 'recovery' : 'login')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let unsubscribe = () => {}
    void getSupabase().then(async (client) => {
      if (!client) { const issue = supabaseSetupIssue(); setConfigurationIssue(issue); setConfigured(issue === 'disabled'); setLoading(false); return }
      setSupabase(client)
      const { data } = await client.auth.getSession()
      setSession(data.session)
      setLoading(false)
      const listener = client.auth.onAuthStateChange((event, next) => {
        setSession(next)
        if (event === 'PASSWORD_RECOVERY') setMode('recovery')
      })
      unsubscribe = () => listener.data.subscription.unsubscribe()
    })
    return () => unsubscribe()
  }, [])

  function changeMode(next: AuthMode) {
    setMode(next); setError(null); setMessage(null); setPassword(''); setConfirmation('')
  }

  function cancelRecovery() {
    window.history.replaceState({}, '', window.location.pathname)
    changeMode('login')
  }

  async function google() {
    if (!supabase) return
    setError(null)
    try {
      const { error: authError } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: window.location.origin } })
      if (authError) setError(authErrorMessage(authError, 'Não foi possível entrar com o Google.'))
    } catch (reason) { setError(authErrorMessage(reason, 'Não foi possível entrar com o Google.')) }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!supabase) return
    setError(null); setMessage(null); setBusy(true)
    try {
      if (mode === 'login') {
        const { error: authError } = await supabase.auth.signInWithPassword({ email, password })
        if (authError) setError('E-mail ou senha inválidos.')
      } else if (mode === 'signup') {
        const validation = passwordError(password, confirmation)
        if (validation) { setError(validation); return }
        const { data, error: authError } = await supabase.auth.signUp({ email, password, options: { data: { name }, emailRedirectTo: window.location.origin } })
        if (authError && signupMayBePending(authError)) setMode('confirmation')
        else if (authError) setError(authErrorMessage(authError, 'Não foi possível criar a conta.'))
        else if (data.session) setSession(data.session)
        else setMode('confirmation')
      } else if (mode === 'forgot') {
        const { error: authError } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/?recovery=1` })
        if (authError) setError(authErrorMessage(authError, 'Não foi possível enviar a recuperação.'))
        else setMessage('Enviamos as instruções de recuperação para seu e-mail.')
      } else {
        const validation = passwordError(password, confirmation)
        if (validation) { setError(validation); return }
        const { error: authError } = await supabase.auth.updateUser({ password })
        if (authError) setError(authErrorMessage(authError, 'Não foi possível alterar a senha.'))
        else { window.history.replaceState({}, '', window.location.pathname); setMode('login'); setMessage(null) }
      }
    } catch (reason) { setError(authErrorMessage(reason)) } finally { setBusy(false) }
  }

  async function magicLink() {
    if (!supabase || !email) { setError('Informe seu e-mail primeiro.'); return }
    setBusy(true); setError(null); setMessage(null)
    try {
      const { error: authError } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.origin } })
      if (authError) setError(authErrorMessage(authError, 'Não foi possível enviar o link de acesso.'))
      else setMessage('Link enviado. Confira sua caixa de entrada.')
    } catch (reason) { setError(authErrorMessage(reason)) } finally { setBusy(false) }
  }

  if (loading) return <div className="auth-loading">Carregando GiControl…</div>
  if (!configured) return <div className="auth-page"><section className="auth-card"><img src="/gicontrol-logo.png" alt="GiControl"/><h1>{configurationIssue === 'api' ? 'API indisponível' : 'Configure a autenticação'}</h1><p>{configurationIssue === 'api' ? 'O frontend não conseguiu consultar a configuração. Reinicie o backend e atualize esta página.' : 'O backend iniciou, mas não encontrou SUPABASE_URL e SUPABASE_ANON_KEY no arquivo .env.'}</p></section></div>
  if ((session || configurationIssue === 'disabled') && mode !== 'recovery') return <>{children}</>

  const headings = {
    login: ['Suas finanças, no seu controle', 'Entre para acessar seus dados financeiros com segurança.'],
    signup: ['Crie sua conta', 'Comece a organizar sua vida financeira.'],
    confirmation: ['Confira seu e-mail', 'Use o link recebido para confirmar a conta e depois entre normalmente.'],
    forgot: ['Recupere sua senha', 'Enviaremos um link seguro para seu e-mail.'],
    recovery: ['Defina uma nova senha', 'Use pelo menos 10 caracteres.'],
  }

  return <div className="auth-page"><section className="auth-card">
    <img src="/gicontrol-logo.png" alt="GiControl"/>
    <p className="eyebrow">BEM-VINDA À GICONTROL</p>
    <h1>{headings[mode][0]}</h1><p>{headings[mode][1]}</p>
    {mode === 'login' && <><button className="google-button" type="button" disabled={busy} onClick={() => void google()}><b>G</b> Continuar com Google</button><div className="auth-divider"><span>ou</span></div></>}
    {mode !== 'confirmation' && <form onSubmit={(event) => void submit(event)}>
      {mode === 'signup' && <label>Nome<input required autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Seu nome"/></label>}
      {mode !== 'recovery' && <label>E-mail<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="voce@gmail.com"/></label>}
      {(mode === 'login' || mode === 'signup' || mode === 'recovery') && <label>Senha<input required minLength={mode === 'login' ? undefined : 10} type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={(event) => setPassword(event.target.value)}/></label>}
      {(mode === 'signup' || mode === 'recovery') && <label>Confirme a senha<input required minLength={10} type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)}/></label>}
      <button className="primary-button" disabled={busy} type="submit">{busy ? 'Aguarde…' : mode === 'login' ? 'Entrar' : mode === 'signup' ? 'Criar conta' : mode === 'forgot' ? 'Enviar recuperação' : 'Salvar nova senha'}</button>
    </form>}
    {mode === 'confirmation' && <p className="auth-confirmation">Se a mensagem chegou, sua solicitação foi processada. Não é necessário criar a conta novamente. Caso o link tenha expirado, use “Esqueci minha senha”.</p>}
    {mode === 'login' && <div className="auth-links"><button type="button" onClick={() => changeMode('forgot')}>Esqueci minha senha</button><button type="button" onClick={() => changeMode('signup')}>Criar uma conta</button><button type="button" disabled={busy} onClick={() => void magicLink()}>Entrar por link</button></div>}
    {mode !== 'login' && <button className="auth-back" type="button" onClick={mode === 'recovery' ? cancelRecovery : () => changeMode('login')}>← {mode === 'recovery' && session ? 'Cancelar e continuar' : 'Voltar para entrar'}</button>}
    {message && <p className="auth-success" role="status">{message}</p>}{error && <p className="auth-error" role="alert">{error}</p>}
  </section></div>
}
