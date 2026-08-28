import { describe, expect, it } from 'vitest'
import { authErrorMessage, signupMayBePending } from './authMessages'

describe('authErrorMessage', () => {
  it('traduz limite de tentativas', () => expect(authErrorMessage(new Error('Email rate limit exceeded'))).toContain('Muitas tentativas'))
  it('traduz conta existente', () => expect(authErrorMessage('User already registered')).toContain('já possui'))
  it('não expõe erros internos desconhecidos', () => expect(authErrorMessage(new Error('internal detail'))).toBe('Não foi possível concluir. Tente novamente.'))
  it('explica a restrição do SMTP padrão', () => expect(authErrorMessage({ code: 'email_address_not_authorized' })).toContain('SMTP'))
  it('distingue cadastro desativado', () => expect(authErrorMessage({ code: 'email_provider_disabled' })).toContain('desativado'))
  it('reconhece cadastro possivelmente pendente', () => expect(signupMayBePending({ code: 'user_already_exists' })).toBe(true))
})
