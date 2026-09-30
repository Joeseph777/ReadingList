// Palettes mirrored 1:1 from ColorPalette.py — same names, same hex values.
// Keys map to CSS custom properties applied on <html> via applyPalette().
const PALETTES = {
  Default: {
    bgLower: "#0D1B2A", bgMid: "#1C2F45", bgUpper: "#243852",
    buttons: "#02C3A7", special: "#FFAE00",
    textMain: "#EEF2F7", textMute: "#8FA8C0",
    read: "#1A3D2B", inRead: "#1E1A3A", separator: "#1E3451",
  },
  Midnight: {
    bgLower: "#0A0A0F", bgMid: "#13131C", bgUpper: "#1C1C2E",
    buttons: "#7C3AED", special: "#F59E0B",
    textMain: "#E2E8F0", textMute: "#64748B",
    read: "#14532D", inRead: "#1E1B4B", separator: "#2D2D44",
  },
  Parchment: {
    bgLower: "#F5F0E8", bgMid: "#FDFAF4", bgUpper: "#EDE8DC",
    buttons: "#6B4226", special: "#C0392B",
    textMain: "#2C1810", textMute: "#7A6552",
    read: "#D4EDDA", inRead: "#FFF3CD", separator: "#C8B89A",
  },
  Rose: {
    bgLower: "#2D1B2E", bgMid: "#3D2440", bgUpper: "#4A2D52",
    buttons: "#E879A0", special: "#F9A8D4",
    textMain: "#FDE8F0", textMute: "#C084A0",
    read: "#1C3A2A", inRead: "#3B1F3F", separator: "#5C3566",
  },
  Solarized: {
    bgLower: "#002B36", bgMid: "#073642", bgUpper: "#0D4555",
    buttons: "#2AA198", special: "#B58900",
    textMain: "#EEE8D5", textMute: "#657B83",
    read: "#0A3020", inRead: "#0D2A36", separator: "#1B4A58",
  },
  Persona: {
    bgLower: "#0D0D0D", bgMid: "#1A1A1A", bgUpper: "#252525",
    buttons: "#CC0000", special: "#FF4444",
    textMain: "#F5F5F5", textMute: "#888888",
    read: "#1A0A0A", inRead: "#0A0A1A", separator: "#333333",
  },
  Forest: {
    bgLower: "#0F2A1F", bgMid: "#1C3B2A", bgUpper: "#234D36",
    buttons: "#6BBF59", special: "#F4C542",
    textMain: "#EAF7E5", textMute: "#8CB38A",
    read: "#00782C", inRead: "#2C3E2B", separator: "#2C5A3A",
  },
  Ocean: {
    bgLower: "#0A1C2E", bgMid: "#102B44", bgUpper: "#1A3F5C",
    buttons: "#00B4D8", special: "#FFB703",
    textMain: "#E6F7FF", textMute: "#7AA2B8",
    read: "#0F2E2A", inRead: "#1C2A4F", separator: "#1E5370",
  },
  Sunset: {
    bgLower: "#2D1B2A", bgMid: "#402337", bgUpper: "#5C2E3E",
    buttons: "#F07D5B", special: "#FFB347",
    textMain: "#FFF0E6", textMute: "#C29B8A",
    read: "#2E2A1F", inRead: "#3E2740", separator: "#6E4A5E",
  },
  Monochrome: {
    bgLower: "#1A1A1A", bgMid: "#2B2B2B", bgUpper: "#3A3A3A",
    buttons: "#A0A0A0", special: "#C0C0C0",
    textMain: "#F0F0F0", textMute: "#808080",
    read: "#1E1E1E", inRead: "#252525", separator: "#4A4A4A",
  },
  Pastel: {
    bgLower: "#E8D5E0", bgMid: "#F2E8F0", bgUpper: "#FDF0F5",
    buttons: "#A7C7B3", special: "#F4B9B2",
    textMain: "#4A3B4A", textMute: "#9A8B9A",
    read: "#D0E5D4", inRead: "#F5E0D4", separator: "#CBB8CC",
  },
};

function applyPalette(name) {
  const p = PALETTES[name] || PALETTES.Default;
  const root = document.documentElement.style;
  root.setProperty("--bg-lower", p.bgLower);
  root.setProperty("--bg-mid", p.bgMid);
  root.setProperty("--bg-upper", p.bgUpper);
  root.setProperty("--buttons", p.buttons);
  root.setProperty("--special", p.special);
  root.setProperty("--text-main", p.textMain);
  root.setProperty("--text-mute", p.textMute);
  root.setProperty("--read", p.read);
  root.setProperty("--in-read", p.inRead);
  root.setProperty("--separator", p.separator);
  localStorage.setItem("rl_palette", name);
}

function currentPaletteName() {
  return localStorage.getItem("rl_palette") || "Default";
}
