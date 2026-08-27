import type { ReactNode } from 'react'
import './ConfirmDialog.css'

type ConfirmDialogProps = {
  title: string
  message: ReactNode
  confirmLabel: string
  tone?: 'primary' | 'danger'
  busy?: boolean
  onCancel: () => void
  onConfirm: () => void
  alternateLabel?: string
  onAlternate?: () => void
}

export function ConfirmDialog({ title, message, confirmLabel, tone = 'primary', busy = false, onCancel, onConfirm, alternateLabel, onAlternate }: ConfirmDialogProps) {
  return <div className="dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onCancel()}>
    <div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
      <span className={`dialog-icon ${tone}`} aria-hidden="true">{tone === 'danger' ? '×' : '!'}</span>
      <h2 id="confirm-dialog-title">{title}</h2>
      <div className="dialog-message">{message}</div>
      <div className="dialog-actions">
        <button className="secondary-button" type="button" onClick={onCancel}>Cancelar</button>
        {alternateLabel && onAlternate && <button className="secondary-button dialog-alternate" disabled={busy} type="button" onClick={onAlternate}>{alternateLabel}</button>}
        <button className={tone === 'danger' ? 'danger-button' : 'primary-button'} disabled={busy} type="button" onClick={onConfirm}>{confirmLabel}</button>
      </div>
    </div>
  </div>
}
