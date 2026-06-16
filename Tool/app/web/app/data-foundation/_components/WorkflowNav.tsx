"use client";
import clsx from "clsx";
import { Check } from "lucide-react";

export type Stage = "ingestion" | "validation" | "rules" | "elements" | "signoff";

export const STAGES: { key: Stage; label: string; hint: string }[] = [
  { key: "ingestion", label: "Data Ingestion", hint: "Connect sources or upload" },
  { key: "validation", label: "Data Validation", hint: "Completeness & integrity" },
  { key: "rules", label: "Rule Engine", hint: "Transformation logic" },
  { key: "elements", label: "Report-Ready Data Elements", hint: "Review & submit" },
  { key: "signoff", label: "Submission & Sign-off", hint: "Maker · Checker" },
];

export function WorkflowNav({ active, onSelect, done }: {
  active: Stage; onSelect: (s: Stage) => void; done?: Partial<Record<Stage, boolean>>;
}) {
  const activeIdx = STAGES.findIndex((s) => s.key === active);
  return (
    <div className="panel p-2 flex items-stretch">
      {STAGES.map((s, i) => {
        const isActive = s.key === active;
        const isDone = done?.[s.key] ?? i < activeIdx;
        return (
          <div key={s.key} className="flex items-center flex-1 min-w-0">
            <button onClick={() => onSelect(s.key)}
              className={clsx("flex items-center gap-2 px-2.5 py-1.5 rounded-row flex-1 min-w-0 text-left transition",
                isActive ? "bg-uq-alt-light" : "hover:bg-uq-near-white")}>
              <span className={clsx("grid place-items-center w-6 h-6 rounded-full shrink-0 font-display font-extrabold text-[11px]",
                isActive ? "bg-uq-symbol text-white"
                  : isDone ? "bg-ok/15 text-ok" : "bg-uq-light-lavender text-uq-purple")}>
                {isDone && !isActive ? <Check className="w-3.5 h-3.5" strokeWidth={3} /> : i + 1}
              </span>
              <span className="min-w-0">
                <span className={clsx("block font-display font-bold text-[11.5px] leading-tight truncate",
                  isActive ? "text-uq-dark-purple" : "text-uq-mid")}>{s.label}</span>
                <span className="block text-[9px] text-uq-muted uppercase tracking-wider truncate">{s.hint}</span>
              </span>
            </button>
            {i < STAGES.length - 1 && <span className="w-4 h-px bg-uq-border shrink-0" />}
          </div>
        );
      })}
    </div>
  );
}
