import { useState } from 'react'
import { inr } from '../../services/shopping'
import type { Comparison } from '../../types/shopping'
import { ChevronDown } from '../icons'

const fmt = (specs: Record<string, string | number | boolean>, key: string, suffix = '') =>
  specs[key] == null ? '—' : typeof specs[key] === 'boolean' ? (specs[key] ? 'Yes' : 'No') : `${specs[key]}${suffix}`

export default function ProductComparison({ comparison, selectedId }: { comparison: Comparison; selectedId?: string }) {
  const [open, setOpen] = useState(true)
  const rows = comparison.table ?? []
  if (rows.length === 0) return null
  const hasSpec = (k: string) => rows.some((r) => r.specs[k] != null)
  const columns = [
    { key: 'ram_gb', label: 'RAM', suffix: 'GB' },
    { key: 'storage_gb', label: 'Storage', suffix: 'GB' },
    { key: 'battery_hours', label: 'Battery', suffix: 'h' },
    { key: 'battery_mah', label: 'Battery', suffix: 'mAh' },
    { key: 'anc', label: 'ANC', suffix: '' },
    { key: 'camera_mp', label: 'Camera', suffix: 'MP' },
  ].filter((c) => hasSpec(c.key))

  return (
    <section className="rounded-xl border border-zinc-200 bg-white" aria-label="Product comparison">
      <button className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        Comparison · {rows.length} products
        <ChevronDown className={`text-zinc-400 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="border-t border-zinc-100 px-4 pb-4 pt-2">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-left text-[13px]">
              <thead className="text-[11px] uppercase text-zinc-400">
                <tr>
                  <th className="py-2 pr-3 font-medium">Product</th>
                  <th className="py-2 pr-3 text-right font-medium">Price</th>
                  {columns.map((c) => (
                    <th key={c.key} className="py-2 pr-3 font-medium">
                      {c.label}
                    </th>
                  ))}
                  <th className="py-2 pr-3 font-medium">Rating</th>
                  <th className="py-2 text-right font-medium">Match</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className={`border-t border-zinc-100 ${r.id === selectedId ? 'bg-zinc-50' : ''}`}>
                    <td className="max-w-[200px] truncate py-2 pr-3 font-medium text-zinc-900" title={r.name}>
                      {r.name} {r.id === selectedId && <span className="ml-1">★</span>}
                    </td>
                    <td className="py-2 pr-3 text-right">{inr(r.price)}</td>
                    {columns.map((c) => (
                      <td key={c.key} className="py-2 pr-3">
                        {fmt(r.specs, c.key, c.suffix)}
                      </td>
                    ))}
                    <td className="py-2 pr-3">{r.rating > 0 ? `${r.rating}★` : '—'}</td>
                    <td className="py-2 text-right font-semibold text-emerald-600">{Math.round(r.suitability)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {comparison.summary && <p className="mt-3 text-[13px] leading-relaxed text-zinc-600">{comparison.summary}</p>}
        </div>
      )}
    </section>
  )
}
