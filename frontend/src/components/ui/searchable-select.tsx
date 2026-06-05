"use client";

import { Check, ChevronsUpDown, Search } from "lucide-react";
import type { KeyboardEvent } from "react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export type SearchableSelectOption = {
  value: string;
  label: string;
  description?: string | null;
};

export function SearchableSelect({
  value,
  onChange,
  options,
  placeholder = "Select option",
  disabled = false,
  className,
  ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: SearchableSelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
}) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [menuPosition, setMenuPosition] = useState<{
    bottom?: number;
    left: number;
    maxHeight: number;
    top?: number;
    width: number;
  } | null>(null);

  const selected = options.find((option) => option.value === value);
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return options;
    return options.filter((option) =>
      `${option.label} ${option.description ?? ""}`.toLowerCase().includes(normalized),
    );
  }, [options, query]);

  useEffect(() => {
    if (!open) return;
    searchRef.current?.focus();
    setActiveIndex(0);
  }, [open]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (!rootRef.current?.contains(target) && !menuRef.current?.contains(target)) {
        setOpen(false);
      }
    }
    window.document.addEventListener("mousedown", onPointerDown);
    return () => window.document.removeEventListener("mousedown", onPointerDown);
  }, []);

  useLayoutEffect(() => {
    if (!open) return;

    function updatePosition() {
      const trigger = triggerRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const gap = 8;
      const spaceBelow = viewportHeight - rect.bottom - gap;
      const spaceAbove = rect.top - gap;
      const openBelow = spaceBelow >= 220 || spaceBelow >= spaceAbove;
      const maxHeight = Math.max(180, Math.min(320, openBelow ? spaceBelow : spaceAbove));
      const width = Math.min(Math.max(rect.width, 260), viewportWidth - (gap * 2));
      setMenuPosition({
        left: Math.min(Math.max(gap, rect.left), Math.max(gap, viewportWidth - width - gap)),
        width,
        maxHeight,
        ...(openBelow ? { top: rect.bottom + gap } : { bottom: viewportHeight - rect.top + gap }),
      });
    }

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  function selectOption(option: SearchableSelectOption) {
    onChange(option.value);
    setQuery("");
    setOpen(false);
  }

  function onKeyDown(event: KeyboardEvent) {
    if (disabled) return;
    if (!open && ["ArrowDown", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      setOpen(true);
      return;
    }
    if (!open) return;
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, Math.max(filtered.length - 1, 0)));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
      return;
    }
    if (event.key === "Enter" && filtered[activeIndex]) {
      event.preventDefault();
      selectOption(filtered[activeIndex]);
    }
  }

  return (
    <div ref={rootRef} className={cn("relative", className)} onKeyDown={onKeyDown}>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        role="combobox"
        aria-expanded={open}
        aria-label={ariaLabel ?? placeholder}
        className={cn(
          "flex h-11 w-full items-center justify-between gap-2 rounded-lg border border-line bg-elevated px-3 text-left text-sm text-foreground shadow-sm outline-none transition",
          "hover:border-info/45 focus:border-info/70 disabled:cursor-not-allowed disabled:opacity-60",
        )}
        onClick={() => setOpen((current) => !current)}
      >
        <span className={cn("min-w-0 truncate", !selected && "text-muted")}>
          {selected?.label ?? placeholder}
        </span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted" />
      </button>

      {open && menuPosition && typeof window !== "undefined" && createPortal(
        <div
          ref={menuRef}
          className="isolate overflow-hidden rounded-lg border border-line bg-panel shadow-panel"
          onKeyDown={onKeyDown}
          style={{
            position: "fixed",
            zIndex: 2147483647,
            left: menuPosition.left,
            top: menuPosition?.top,
            bottom: menuPosition?.bottom,
            width: menuPosition.width,
            maxWidth: "calc(100vw - 1rem)",
          }}
        >
          <div className="relative border-b border-line">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              ref={searchRef}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActiveIndex(0);
              }}
              className="h-11 w-full bg-elevated px-10 text-sm text-foreground outline-none placeholder:text-muted"
              placeholder="Search"
              aria-label="Search options"
            />
          </div>
          <div className="overflow-y-auto p-1" style={{ maxHeight: menuPosition?.maxHeight ?? 256 }}>
            {filtered.length === 0 && (
              <div className="px-3 py-3 text-sm text-muted">No options found</div>
            )}
            {filtered.map((option, index) => {
              const active = index === activeIndex;
              const checked = option.value === value;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  aria-selected={checked}
                  className={cn(
                    "flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm text-foreground outline-none transition",
                    active ? "bg-primary/20" : "hover:bg-elevated",
                  )}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => selectOption(option)}
                >
                  <Check className={cn("mt-0.5 h-4 w-4 shrink-0 text-info", !checked && "opacity-0")} />
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{option.label}</span>
                    {option.description && (
                      <span className="mt-0.5 block truncate text-xs text-muted">{option.description}</span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
        </div>,
        window.document.body,
      )}
    </div>
  );
}
