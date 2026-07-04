class colorPalette():
    def __init__(self,BG_lower,BG_mid,BG_upper, Buttons, SpecialColor,TextMain, TextMute, Read, InRead, Separator):
        self.BG_lower = BG_lower
        self.BG_mid = BG_mid
        self.BG_upper = BG_upper
        self.Buttons = Buttons
        self.SpecialColor = SpecialColor
        self.TextMain = TextMain
        self.TextMute = TextMute
        self.Read = Read
        self.InRead = InRead
        self.Separator = Separator

    def setPalette(self, BG_lower=None,BG_mid=None,BG_upper=None, Buttons=None, SpecialColor=None,TextMain=None, TextMute=None, Read=None, InRead=None, Separator=None):
        if BG_lower is not None:
            self.BG_lower = BG_lower
        if BG_mid is not None:
            self.BG_mid = BG_mid
        if BG_upper is not None:
            self.BG_upper = BG_upper
        if Buttons is not None:
            self.Buttons = Buttons
        if SpecialColor is not None:
            self.SpecialColor = SpecialColor
        if TextMain is not None:
            self.TextMain = TextMain
        if TextMute is not None:
            self.TextMute = TextMute
        if Read is not None:
            self.Read = Read
        if InRead is not None:
            self.InRead = InRead
        if Separator is not None:
            self.Separator = Separator

    def getPalette(self):
        return (self.BG_lower, self.BG_mid, self.BG_upper, self.Buttons, self.SpecialColor, self.TextMain, self.TextMute, self.Read, self.InRead, self.Separator)


# ── Default — deep navy / teal (unchanged, it works) ──────────────────────
DefaultPalette = colorPalette(
    "#0D1B2A",  # BG_lower   darkest panel / sidebar
    "#1C2F45",  # BG_mid     main content area
    "#243852",  # BG_upper   cards / header
    "#02C3A7",  # Buttons    teal accent
    "#FFAE00",  # Special    gold hover / highlight
    "#EEF2F7",  # TextMain   near-white
    "#8FA8C0",  # TextMute   slate-blue muted
    "#1A3D2B",  # Read       dark green row  (completed)
    "#1E1A3A",  # InRead     dark purple row (in progress)
    "#1E3451",  # Separator
)

# ── Midnight — true AMOLED dark, electric accents ─────────────────────────
MidnightPalette = colorPalette(
    "#0A0A0F",  # BG_lower   near-black sidebar
    "#13131C",  # BG_mid     main area
    "#1C1C2E",  # BG_upper   header / cards
    "#7C3AED",  # Buttons    vivid violet
    "#F59E0B",  # Special    amber hover
    "#E2E8F0",  # TextMain   soft white
    "#64748B",  # TextMute   cool grey
    "#14532D",  # Read       forest green row
    "#1E1B4B",  # InRead     deep indigo row
    "#2D2D44",  # Separator
)

# ── Parchment — warm light theme, readable in daylight ────────────────────
ParchmentPalette = colorPalette(
    "#F5F0E8",  # BG_lower   warm cream sidebar
    "#FDFAF4",  # BG_mid     main area off-white
    "#EDE8DC",  # BG_upper   header slightly darker cream
    "#6B4226",  # Buttons    rich brown
    "#C0392B",  # Special    terracotta hover
    "#2C1810",  # TextMain   dark espresso
    "#7A6552",  # TextMute   warm grey-brown
    "#D4EDDA",  # Read       soft sage green row
    "#FFF3CD",  # InRead     warm amber row
    "#C8B89A",  # Separator  tan
)

# ── Rose — muted pink / mauve, elegant not garish ─────────────────────────
RosePalette = colorPalette(
    "#2D1B2E",  # BG_lower   deep plum sidebar
    "#3D2440",  # BG_mid     rich aubergine main
    "#4A2D52",  # BG_upper   lighter plum header
    "#E879A0",  # Buttons    vivid rose
    "#F9A8D4",  # Special    blush hover
    "#FDE8F0",  # TextMain   near-white pink tint
    "#C084A0",  # TextMute   dusty mauve
    "#1C3A2A",  # Read       dark bottle-green row
    "#3B1F3F",  # InRead     deep violet row
    "#5C3566",  # Separator
)

# ── Solarized — the classic warm-toned dark, easy on eyes ─────────────────
SolarizedPalette = colorPalette(
    "#002B36",  # BG_lower   solarized base03
    "#073642",  # BG_mid     solarized base02
    "#0D4555",  # BG_upper   slightly lifted
    "#2AA198",  # Buttons    solarized cyan
    "#B58900",  # Special    solarized yellow
    "#EEE8D5",  # TextMain   solarized base2
    "#657B83",  # TextMute   solarized base00
    "#0A3020",  # Read       dark green row
    "#0D2A36",  # InRead     dark teal row
    "#1B4A58",  # Separator
)

# ── Persona — red/black/white done properly ───────────────────────────────
PersonaPalette = colorPalette(
    "#0D0D0D",  # BG_lower   true black sidebar
    "#1A1A1A",  # BG_mid     dark grey main
    "#252525",  # BG_upper   charcoal header
    "#CC0000",  # Buttons    persona red
    "#FF4444",  # Special    bright red hover
    "#F5F5F5",  # TextMain   clean white
    "#888888",  # TextMute   mid grey
    "#1A0A0A",  # Read       deep blood-red row
    "#0A0A1A",  # InRead     near-black blue row
    "#333333",  # Separator
)
# ── Forest — natural greens, earthy and restful ───────────────────────────
ForestPalette = colorPalette(
    "#0F2A1F",  # BG_lower   deep forest sidebar
    "#1C3B2A",  # BG_mid     mossy main area
    "#234D36",  # BG_upper   leaf green header
    "#6BBF59",  # Buttons    fresh lime
    "#F4C542",  # Special    warm sunflower hover
    "#EAF7E5",  # TextMain   pale mint white
    "#8CB38A",  # TextMute   muted sage
    "#00782C",  # Read       dark evergreen row
    "#2C3E2B",  # InRead     olive row
    "#2C5A3A",  # Separator  medium green
)

# ── Ocean — deep blue / cyan, calm and focused ────────────────────────────
OceanPalette = colorPalette(
    "#0A1C2E",  # BG_lower   abyss sidebar
    "#102B44",  # BG_mid     deep ocean main
    "#1A3F5C",  # BG_upper   wave header
    "#00B4D8",  # Buttons    bright cyan
    "#FFB703",  # Special    golden starfish hover
    "#E6F7FF",  # TextMain   icy white
    "#7AA2B8",  # TextMute   steel blue
    "#0F2E2A",  # Read       dark teal row
    "#1C2A4F",  # InRead     navy row
    "#1E5370",  # Separator  lighter blue
)

# ── Sunset — warm orange, coral, and dusk purple ──────────────────────────
SunsetPalette = colorPalette(
    "#2D1B2A",  # BG_lower   dark plum sidebar
    "#402337",  # BG_mid     aubergine main
    "#5C2E3E",  # BG_upper   burgundy header
    "#F07D5B",  # Buttons    coral
    "#FFB347",  # Special    orange hover
    "#FFF0E6",  # TextMain   warm off-white
    "#C29B8A",  # TextMute   dusty rose
    "#2E2A1F",  # Read       dark bronze row
    "#3E2740",  # InRead     dark violet row
    "#6E4A5E",  # Separator  muted purple
)

# ── Monochrome — clean grayscale, distraction-free ────────────────────────
MonochromePalette = colorPalette(
    "#1A1A1A",  # BG_lower   nearly black sidebar
    "#2B2B2B",  # BG_mid     dark grey main
    "#3A3A3A",  # BG_upper   light charcoal header
    "#A0A0A0",  # Buttons    mid grey
    "#C0C0C0",  # Special    light silver hover
    "#F0F0F0",  # TextMain   white
    "#808080",  # TextMute   50% grey
    "#1E1E1E",  # Read       blackish row
    "#252525",  # InRead     dark grey row
    "#4A4A4A",  # Separator  medium grey
)

# ── Pastel — soft, gentle colors, low contrast for casual use ─────────────
PastelPalette = colorPalette(
    "#E8D5E0",  # BG_lower   lavender grey sidebar
    "#F2E8F0",  # BG_mid     blush off-white main
    "#FDF0F5",  # BG_upper   soft pink header
    "#A7C7B3",  # Buttons    seafoam green
    "#F4B9B2",  # Special    peach hover
    "#4A3B4A",  # TextMain   dark lavender grey
    "#9A8B9A",  # TextMute   muted lavender
    "#D0E5D4",  # Read       pale green row
    "#F5E0D4",  # InRead     peach row
    "#CBB8CC",  # Separator  soft lilac
)


Palettes = {
    "Default":   DefaultPalette,
    "Midnight":  MidnightPalette,
    "Parchment": ParchmentPalette,
    "Rose":      RosePalette,
    "Solarized": SolarizedPalette,
    "Persona":   PersonaPalette,
    "Forest":    ForestPalette,
    "Ocean":     OceanPalette,
    "Sunset":    SunsetPalette,
    "Monochrome": MonochromePalette,
    "Pastel":    PastelPalette,
}