import { useCallback, useEffect, useState } from 'react'
import { api, downloadMonthlyReport } from '../api/client'
import type { MonthlyReport } from '../api/types'
import './ReportsPage.css'

const currency = new Intl.NumberFormat('pt-BR', { style:'currency', currency:'BRL' })
const currentMonth = () => { const value=new Date(); return `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,'0')}` }

export function ReportsPage() {
  const [month,setMonth]=useState(currentMonth), [report,setReport]=useState<MonthlyReport|null>(null), [loading,setLoading]=useState(true), [error,setError]=useState<string|null>(null)
  const load=useCallback(async()=>{setLoading(true);setError(null);try{setReport(await api.monthlyReport(month))}catch(requestError){setError(requestError instanceof Error?requestError.message:'Não foi possível gerar o relatório.')}finally{setLoading(false)}},[month])
  async function exportCsv(){try{const blob=await downloadMonthlyReport(month),url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;anchor.download=`gicontrol-${month}.csv`;anchor.click();URL.revokeObjectURL(url)}catch(requestError){setError(requestError instanceof Error?requestError.message:'Não foi possível exportar o relatório.')}}
  // oxlint-disable-next-line react/set-state-in-effect -- atualiza o fechamento ao trocar o mês.
  useEffect(()=>{void load()},[load])
  return <>
    <header className="topbar dashboard-header"><div><p className="eyebrow">FECHAMENTO FINANCEIRO</p><h1>Relatório mensal</h1><p className="subtitle">Receitas e despesas por competência, incluindo parcelas de cartões.</p></div><div className="dashboard-actions"><label>Mês<input type="month" value={month} onChange={(event)=>setMonth(event.target.value||currentMonth())}/></label><button className="primary-button report-download" type="button" onClick={()=>void exportCsv()}>Exportar CSV</button></div></header>
    {error&&<section className="error-state" role="alert"><div><strong>Não foi possível gerar o relatório</strong><p>{error}</p></div><button type="button" onClick={()=>void load()}>Tentar novamente</button></section>}
    <section className="report-metrics"><ReportMetric label="Receitas realizadas" value={report?.income} loading={loading}/><ReportMetric label="Despesas em contas" value={report?.bank_expenses} loading={loading}/><ReportMetric label="Despesas em cartões" value={report?.card_expenses} loading={loading}/><ReportMetric label="Resultado do mês" value={report?.result} loading={loading} result/></section>
    <section className="panel report-categories"><div className="panel-heading"><div><p className="eyebrow">COMPOSIÇÃO</p><h2>Despesas por categoria</h2></div><span className="count-badge">{report?.categories.length??0}</span></div>{report?.categories.length?<div className="report-category-list">{report.categories.map((item)=><div key={item.category_id}><span><strong>{item.category_name}</strong><small>{report.total_expenses>0?Math.round(item.total/report.total_expenses*100):0}% das despesas</small></span><b>{currency.format(item.total)}</b></div>)}</div>:<div className="invoice-empty"><strong>Nenhuma despesa no mês</strong><p>Os lançamentos e parcelas aparecerão aqui automaticamente.</p></div>}</section>
  </>
}
function ReportMetric({label,value,loading,result}:{label:string;value?:number;loading:boolean;result?:boolean}){return <article className={`report-metric ${result?(value??0)>=0?'positive-result':'negative-result':''}`}><span>{label}</span>{loading?<i/>:<strong>{currency.format(value??0)}</strong>}</article>}
