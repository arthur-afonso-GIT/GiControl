export function authErrorMessage(error: unknown, fallback = 'Não foi possível concluir. Tente novamente.') {
  const code = authErrorCode(error)
  if (code === 'email_address_not_authorized') return 'O envio de confirmação está restrito no Supabase. Configure um SMTP próprio ou use um e-mail autorizado no projeto.'
  if (code === 'email_provider_disabled' || code === 'signup_disabled') return 'O cadastro por e-mail está desativado nas configurações do Supabase.'
  if (code === 'email_address_invalid' || code === 'validation_failed') return 'O Supabase recusou este endereço de e-mail. Verifique o endereço ou tente outro.'
  if (code === 'email_exists' || code === 'user_already_exists') return 'Este e-mail já possui uma conta.'
  if (code === 'over_email_send_rate_limit' || code === 'over_request_rate_limit') return 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
  if (code === 'weak_password') return 'Escolha uma senha mais forte.'
  const message = error instanceof Error ? error.message : typeof error === 'string' ? error : ''
  const normalized = message.toLowerCase()
  if (normalized.includes('rate limit') || normalized.includes('too many')) return 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'
  if (normalized.includes('already registered') || normalized.includes('already exists')) return 'Este e-mail já possui uma conta.'
  if (normalized.includes('password') && normalized.includes('weak')) return 'Escolha uma senha mais forte.'
  if (normalized.includes('email') && normalized.includes('invalid')) return 'Informe um e-mail válido.'
  if (normalized.includes('network') || normalized.includes('fetch')) return 'Não foi possível conectar. Verifique sua internet e tente novamente.'
  return fallback
}

export function authErrorCode(error: unknown) {
  return typeof error === 'object' && error !== null && 'code' in error ? String(error.code) : ''
}

export function signupMayBePending(error: unknown) {
  return ['email_exists', 'user_already_exists', 'over_email_send_rate_limit'].includes(authErrorCode(error))
}
