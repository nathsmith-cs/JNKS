export interface AccentColor {
  name: string;
  hex: string;
  hexDark: string;
  rgb: string;
  rgbDark: string;
  hueShift: number;
}

export const accentColors: Record<string, AccentColor> = {
  orange: {
    name: "Orange",
    hex: "#f97316",
    hexDark: "#ea580c",
    rgb: "249, 115, 22",
    rgbDark: "234, 88, 12",
    hueShift: 232,
  },
  blue: {
    name: "Blue",
    hex: "#3b82f6",
    hexDark: "#2563eb",
    rgb: "59, 130, 246",
    rgbDark: "37, 99, 235",
    hueShift: 16,
  },
  purple: {
    name: "Purple",
    hex: "#8b5cf6",
    hexDark: "#7c3aed",
    rgb: "139, 92, 246",
    rgbDark: "124, 58, 237",
    hueShift: 0,
  },
  green: {
    name: "Green",
    hex: "#22c55e",
    hexDark: "#16a34a",
    rgb: "34, 197, 94",
    rgbDark: "22, 163, 74",
    hueShift: 115,
  },
  red: {
    name: "Red",
    hex: "#ef4444",
    hexDark: "#dc2626",
    rgb: "239, 68, 68",
    rgbDark: "220, 38, 38",
    hueShift: 269,
  },
  pink: {
    name: "Pink",
    hex: "#ec4899",
    hexDark: "#db2777",
    rgb: "236, 72, 153",
    rgbDark: "219, 39, 119",
    hueShift: 289,
  },
  cyan: {
    name: "Cyan",
    hex: "#06b6d4",
    hexDark: "#0891b2",
    rgb: "6, 182, 212",
    rgbDark: "8, 145, 178",
    hueShift: 31,
  },
};

export const defaultAccentKey = "orange";
