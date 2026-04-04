"use client";

import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { useAccentColor } from "@/components/accent-color-provider";
import { accentColors } from "@/lib/accent-colors";

export function AccentColorSelector() {
  const { accentKey, setAccentKey } = useAccentColor();
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ top: 0, right: 0 });

  useEffect(() => {
    if (open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setCoords({
        top: rect.bottom + 8,
        right: window.innerWidth - rect.right,
      });
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <>
      <button
        ref={buttonRef}
        onClick={() => setOpen(!open)}
        className="h-5 w-5 rounded-full border-2 border-white/20 transition-transform hover:scale-110 focus:outline-none"
        style={{ backgroundColor: accentColors[accentKey].hex }}
        aria-label="Change accent color"
      />
      {open &&
        createPortal(
          <div
            ref={dropdownRef}
            className="fixed z-[100] flex gap-2 rounded-xl border border-white/10 bg-black/80 p-3 backdrop-blur-md"
            style={{ top: coords.top, right: coords.right }}
          >
            {Object.entries(accentColors).map(([key, color]) => (
              <button
                key={key}
                onClick={() => {
                  setAccentKey(key);
                  setOpen(false);
                }}
                className={`h-6 w-6 rounded-full transition-all hover:scale-110 focus:outline-none ${
                  key === accentKey
                    ? "ring-2 ring-white ring-offset-2 ring-offset-black"
                    : ""
                }`}
                style={{ backgroundColor: color.hex }}
                aria-label={color.name}
                title={color.name}
              />
            ))}
          </div>,
          document.body
        )}
    </>
  );
}
