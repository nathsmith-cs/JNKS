"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import {
  accentColors,
  defaultAccentKey,
  type AccentColor,
} from "@/lib/accent-colors";

interface AccentColorContextType {
  accentKey: string;
  accent: AccentColor;
  setAccentKey: (key: string) => void;
}

const AccentColorContext = createContext<AccentColorContextType>({
  accentKey: defaultAccentKey,
  accent: accentColors[defaultAccentKey],
  setAccentKey: () => {},
});

export function useAccentColor() {
  return useContext(AccentColorContext);
}

function applyAccentToDOM(color: AccentColor) {
  const root = document.documentElement;
  root.style.setProperty("--primary", color.hex);
  root.style.setProperty("--ring", color.hex);
  root.style.setProperty("--chart-1", color.hex);
  root.style.setProperty("--sidebar-primary", color.hex);
  root.style.setProperty("--sidebar-ring", color.hex);
}

export function AccentColorProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [accentKey, setAccentKeyState] = useState(defaultAccentKey);

  useEffect(() => {
    const stored = localStorage.getItem("accent-color");
    if (stored && accentColors[stored]) {
      setAccentKeyState(stored);
      applyAccentToDOM(accentColors[stored]);
    } else {
      applyAccentToDOM(accentColors[defaultAccentKey]);
    }
  }, []);

  const setAccentKey = useCallback((key: string) => {
    if (!accentColors[key]) return;
    setAccentKeyState(key);
    localStorage.setItem("accent-color", key);
    applyAccentToDOM(accentColors[key]);
  }, []);

  return (
    <AccentColorContext.Provider
      value={{
        accentKey,
        accent: accentColors[accentKey],
        setAccentKey,
      }}
    >
      {children}
    </AccentColorContext.Provider>
  );
}
