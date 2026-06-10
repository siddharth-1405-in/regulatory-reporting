"use client";
import { X } from "lucide-react";

export function Drawer({ open, onClose, title, eyebrow, children, width = 460 }: {
  open: boolean; onClose: () => void; title: string; eyebrow?: string;
  children: React.ReactNode; width?: number;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-uq-dark-purple/20" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full bg-white shadow-card border-l border-uq-border flex flex-col"
        style={{ width }}>
        <header className="flex items-start justify-between px-4 py-3 border-b border-uq-border">
          <div>
            {eyebrow && <div className="eyebrow mb-0.5">{eyebrow}</div>}
            <h3 className="panel-title">{title}</h3>
          </div>
          <button onClick={onClose} className="text-uq-muted hover:text-uq-purple"><X size={18} /></button>
        </header>
        <div className="flex-1 overflow-auto p-4">{children}</div>
      </aside>
    </div>
  );
}
