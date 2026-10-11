import { inr } from '../../services/shopping'
import type { Comparison } from '../../types/shopping'

const fmt = (specs: Record<string, string | number | boolean>, key: string, suffix = '') =>
  specs[key] == null ? '—' : typeof specs[key] === 'boolean' ? (specs[key] ? 'Yes' : 'No') : `${specs[key]}${suffix}`

export default function ProductComparison({ comparison, selectedId }: { comparison: Comparison; selectedId?: string }) {
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
    <section className="card" aria-label="Product comparison">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Comparison</h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="text-xs uppercase text-slate-500">
            <tr>
              <th className="py-2 pr-3">Product</th>
              <th className="py-2 pr-3 text-right">Price</th>
              {columns.map((c) => (
                <th key={c.key} className="py-2 pr-3">
                  {c.label}
                </th>
              ))}
              <th className="py-2 pr-3">Rating</th>
              <th className="py-2 text-right">Suitability</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className={`border-t border-white/5 ${r.id === selectedId ? 'bg-brand-500/10' : ''}`}>
                <td className="py-2 pr-3 font-medium text-white">
                  {r.name} {r.id === selectedId && <span className="ml-1 text-brand-400">★</span>}
                </td>
                <td className="py-2 pr-3 text-right">{inr(r.price)}</td>
                {columns.map((c) => (
                  <td key={c.key} className="py-2 pr-3">
                    {fmt(r.specs, c.key, c.suffix)}
                  </td>
                ))}
                <td className="py-2 pr-3">{r.rating}★</td>
                <td className="py-2 text-right font-semibold text-emerald-400">{Math.round(r.suitability)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {comparison.summary && <p className="mt-3 text-sm leading-relaxed text-slate-300">{comparison.summary}</p>}
    </section>
  )
}
