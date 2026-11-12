import React, { useEffect } from "react"
import { CheckCircle2, AlertTriangle, ArrowRight, X } from "lucide-react"

export default function NotificationToast({ notifications, onDismiss, onViewResults }) {
  if (!notifications || notifications.length === 0) return null

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {notifications.map((item) => (
        <div
          key={item.id}
          className="pointer-events-auto bg-white rounded-xl shadow-xl border border-slate-200 p-4 flex items-start gap-3 transition-all transform translate-y-0 opacity-100 hover:shadow-2xl"
        >
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
              item.status === "failed"
                ? "bg-rose-100 text-rose-600"
                : "bg-emerald-100 text-emerald-600"
            }`}
          >
            {item.status === "failed" ? (
              <AlertTriangle className="w-5 h-5" />
            ) : (
              <CheckCircle2 className="w-5 h-5" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-1">
              <h4 className="text-sm font-semibold text-slate-900 truncate">
                {item.supplier} search {item.status === "failed" ? "failed" : "completed"}
              </h4>
              <button
                onClick={() => onDismiss(item.id)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <p className="text-xs text-slate-600 mt-0.5">
              {item.status === "failed"
                ? item.error || "Supplier extraction failed"
                : `${item.products_found} product${item.products_found === 1 ? "" : "s"} extracted in ${item.elapsed_seconds || 0}s`}
            </p>

            {item.status !== "failed" && item.products_found > 0 && (
              <div className="mt-2.5 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onViewResults(item.vendor)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
                >
                  <span>View Results</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
