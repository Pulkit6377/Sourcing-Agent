import React, { useEffect, useRef, useState } from "react"
import {
  Terminal,
  Activity,
  ChevronDown,
  ChevronUp,
} from "lucide-react"

export default function ActivityLog({
  logs,
  totalSuppliers = 2,
  completedSuppliers = 0,
  failedSuppliers = 0,
  totalProducts = 0,
  totalVerifiedPrices = 0,
  overallStatus = "Idle",
}) {
  const logContainerRef = useRef(null)
  const [filter, setFilter] = useState("all") // all | info | success | error
  const [isExpanded, setIsExpanded] = useState(false)

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const filteredLogs = logs.filter((log) => {
    if (filter === "all") return true
    return log.level === filter
  })

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-3.5 flex flex-col">
      {/* Sleek Summary Row */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-blue-600" />
          <span className="text-xs font-semibold text-slate-800">
            Execution Activity
          </span>
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
              overallStatus === "Completed"
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : overallStatus === "Searching" || overallStatus === "In Progress"
                ? "bg-blue-50 text-blue-700 border-blue-200 animate-pulse"
                : overallStatus === "Failed"
                ? "bg-rose-50 text-rose-700 border-rose-200"
                : "bg-slate-50 text-slate-600 border-slate-200"
            }`}
          >
            {overallStatus}
          </span>
        </div>

        {/* Compact stats */}
        <div className="flex items-center gap-3 text-xs text-slate-600">
          <span>
            <strong className="text-slate-900 font-semibold">{totalProducts}</strong> parts found
          </span>
          <span className="text-slate-300">•</span>
          <span>
            <strong className="text-slate-900 font-semibold">{totalVerifiedPrices}</strong> in stock
          </span>
          <span className="text-slate-300">•</span>
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700 font-medium"
          >
            <Terminal className="w-3 h-3" />
            <span>{isExpanded ? "Hide Logs" : `Logs (${logs.length})`}</span>
            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Expandable Technical Log Feed */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-slate-100">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] uppercase font-semibold text-slate-400">
              Live Browser &amp; Navigation Events
            </span>
            <div className="flex items-center gap-1">
              {["all", "info", "success", "error"].map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setFilter(lvl)}
                  className={`text-[10px] font-medium px-1.5 py-0.2 rounded capitalize transition-colors ${
                    filter === lvl
                      ? "bg-slate-800 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          <div
            ref={logContainerRef}
            className="bg-slate-900 rounded-lg p-2.5 font-mono text-[10px] h-32 overflow-y-auto space-y-1 text-slate-300 border border-slate-800"
          >
            {filteredLogs.length === 0 ? (
              <div className="text-slate-500 italic py-2 text-center">
                Waiting for search events...
              </div>
            ) : (
              filteredLogs.map((item, idx) => {
                const isError = item.level === "error"
                const isSuccess = item.level === "success"
                return (
                  <div key={idx} className="flex items-start gap-1.5 leading-relaxed">
                    <span className="text-slate-500 select-none shrink-0">
                      [{item.timestamp}]
                    </span>
                    <span
                      className={
                        isError
                          ? "text-rose-400 font-medium"
                          : isSuccess
                          ? "text-emerald-400 font-medium"
                          : "text-slate-300"
                      }
                    >
                      {item.message}
                    </span>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
