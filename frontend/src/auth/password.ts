export function passwordError(password: string, confirmation: string) {
  if (password.length < 10) return 'A senha deve ter pelo menos 10 caracteres.'
  if (password !== confirmation) return 'As senhas não coincidem.'
  return null
}
