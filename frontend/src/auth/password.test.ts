import { describe, expect, it } from 'vitest'
import { passwordError } from './password'

describe('passwordError', () => {
  it('exige pelo menos dez caracteres', () => expect(passwordError('curta', 'curta')).toContain('10'))
  it('exige confirmação idêntica', () => expect(passwordError('senha-segura', 'outra-senha')).toContain('coincidem'))
  it('aceita senha válida', () => expect(passwordError('senha-segura', 'senha-segura')).toBeNull())
})
