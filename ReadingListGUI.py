import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from tkinter.scrolledtext import ScrolledText
import json
import os
import threading
import hashlib
from datetime import datetime
from ReadingList import Book, ReadingList, DEFAULT_SAVE_PATH
from ColorPalette import colorPalette, Palettes

# ── Optional deps (cover art) ──────────────────────────────────────────────
try:
    from PIL import Image, ImageTk, ImageDraw
    import requests
    _COVERS_ENABLED = True
except ImportError:
    _COVERS_ENABLED = False

# ── Cover cache folder lives next to the save file ────────────────────────
_CACHE_DIR = os.path.join(os.path.dirname(DEFAULT_SAVE_PATH), "cover_cache")

# ── App config (persists palette choice, window size, etc.) ───────────────
_CONFIG_PATH = os.path.join(os.path.dirname(DEFAULT_SAVE_PATH), "app_config.json")

def _load_config() -> dict:
    """Load config from disk, returning defaults if missing or corrupt."""
    defaults = {"palette": "Default"}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Only keep known keys; silently drop anything unexpected
        return {**defaults, **{k: v for k, v in data.items() if k in defaults}}
    except (FileNotFoundError, json.JSONDecodeError):
        return defaults

def _save_config(data: dict) -> None:
    """Persist config dict to disk (non-fatal on failure)."""
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass  # Losing the palette pref is annoying, not catastrophic

# ── Palette ────────────────────────────────────────────────────────────────
#BG_DARK, BG_MID, BG_LIGHT, ACCENT_TEAL, ACCENT_GOLD, TEXT_MAIN, TEXT_MUTED, GREEN, RED_SOFT, SEPARATOR = ("#0D1B2A" ,"#1C2F45","#243852", "#02C3A7" ,"#FFAE00", "#EEF2F7", "#8FA8C0", "#3DD68C","#7453EC", "#1E3451")

BG_DARK, BG_MID, BG_LIGHT, ACCENT_TEAL, ACCENT_GOLD, TEXT_MAIN, TEXT_MUTED, READ, INREAD, SEPARATOR = Palettes["Default"].getPalette()
def ChangePallete(PalletteName):
    global BG_DARK, BG_MID, BG_LIGHT, ACCENT_TEAL, ACCENT_GOLD, TEXT_MAIN, TEXT_MUTED, READ, INREAD, SEPARATOR
    BG_DARK, BG_MID, BG_LIGHT, ACCENT_TEAL, ACCENT_GOLD, TEXT_MAIN, TEXT_MUTED, READ, INREAD, SEPARATOR = Palettes[PalletteName].getPalette()

FONT_TITLE   = ("Georgia", 22, "bold")
FONT_HEADING = ("Georgia", 13, "bold")
FONT_BODY    = ("Calibri", 12)
FONT_SMALL   = ("Calibri", 10)
FONT_MONO    = ("Consolas", 13)

COVER_W, COVER_H = 160, 240   # side panel thumbnail
MINI_W,  MINI_H  = 80,  120   # book details dialog


# ══════════════════════════════════════════════════════════════════════════
#  Cover-art helpers
# ══════════════════════════════════════════════════════════════════════════

def _cover_cache_path(title: str, author: str) -> str:
    key = hashlib.md5(f"{title.lower()}|{author.lower()}".encode()).hexdigest()
    os.makedirs(_CACHE_DIR, exist_ok=True)
    return os.path.join(_CACHE_DIR, f"{key}.jpg")


def _placeholder_image(w: int, h: int, title: str):
    """Navy placeholder with teal border and truncated title."""
    img = Image.new("RGB", (w, h), color=(28, 47, 69))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(2, 195, 167), width=2)
    draw.rectangle([8, 8, 16, h - 8], fill=(2, 195, 167))   # spine accent
    words = title.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if len(test) > 11:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y = h // 2 - len(lines) * 8
    for ln in lines[:5]:
        draw.text((w // 2, y), ln, fill=(238, 242, 247), anchor="mm")
        y += 16
    return img


def fetch_cover(title: str, author: str, callback) -> None:
    """Non-blocking: fetch cover from Google Books (primary) or Open Library (fallback)."""
    def _worker():
        path = _cover_cache_path(title, author)
        if os.path.exists(path):
            callback(path)
            return
        if not _COVERS_ENABLED:
            callback(None)
            return

        # Helper to save image from URL
        def save_from_url(url, callback):
            try:
                resp = requests.get(url, timeout=6)
                resp.raise_for_status()
                with open(path, "wb") as f:
                    f.write(resp.content)
                callback(path)
            except Exception:
                callback(None)

        # 1. Try Google Books
        try:
            q = urllib.parse.quote(f"{title} {author}")
            url = f"https://www.googleapis.com/books/v1/volumes?q={q}&maxResults=1"
            resp = requests.get(url, timeout=6)
            data = resp.json()
            if "items" in data:
                # Get best available cover (extraLarge or large)
                cover_link = None
                img_links = data["items"][0]["volumeInfo"].get("imageLinks", {})
                for size in ["extraLarge", "large", "medium", "thumbnail"]:
                    if size in img_links:
                        cover_link = img_links[size]
                        break
                if cover_link:
                    save_from_url(cover_link, callback)
                    return
        except Exception:
            pass

        # 2. Fallback to Open Library
        try:
            q = "+".join((title + " " + author).split())
            r = requests.get(
                f"https://openlibrary.org/search.json?q={q}&limit=3&fields=cover_i",
                timeout=6
            )
            r.raise_for_status()
            cover_id = None
            for doc in r.json().get("docs", []):
                if "cover_i" in doc:
                    cover_id = doc["cover_i"]
                    break
            if cover_id:
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                save_from_url(cover_url, callback)
                return
        except Exception:
            pass

        callback(None)

    threading.Thread(target=_worker, daemon=True).start()



def load_tk_image(path_or_none, w: int, h: int, title: str = ""):
    """Return a Tk PhotoImage scaled to (w, h), or None if Pillow missing."""
    if not _COVERS_ENABLED:
        return None
    try:
        if path_or_none and os.path.exists(path_or_none):
            img = Image.open(path_or_none).convert("RGB")
        else:
            img = _placeholder_image(w, h, title)
        img = img.resize((w, h), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════
#  Styled button
# ══════════════════════════════════════════════════════════════════════════

class StyledButton(tk.Button):
    def __init__(self, parent, text, command, bg=None, fg=None,
                 font=("Calibri", 12, "bold"), padx=14, pady=5, **kw):
        _bg = bg if bg is not None else ACCENT_TEAL
        _fg = fg if fg is not None else BG_DARK
        super().__init__(parent, text=text, command=command,
                         bg=_bg, fg=_fg, font=font,
                         activebackground=ACCENT_GOLD, activeforeground=BG_DARK,
                         relief="flat", cursor="hand2",
                         padx=padx, pady=pady, bd=0, **kw)
        self.bind("<Enter>", lambda e: self.config(bg=ACCENT_GOLD, fg=BG_DARK))
        self.bind("<Leave>", lambda e: self.config(bg=_bg, fg=_fg))


# ══════════════════════════════════════════════════════════════════════════
#  Main application
# ══════════════════════════════════════════════════════════════════════════

class ReadingListGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Personal Reading List — ISI 2025–2026")
        self.root.geometry("1280x700")
        self.root.minsize(960, 600)

        # ── Restore last-used palette before anything is drawn ────────────
        self._config = _load_config()
        saved_palette = self._config.get("palette", "Default")
        if saved_palette in Palettes:
            ChangePallete(saved_palette)

        self.root.configure(bg=BG_DARK)

        self.reading_list = ReadingList()
        # Keep PhotoImage refs alive (Tk GC bug)
        self._photo_cache: dict = {}
        self._current_cover_key = None

        self._load_on_start()
        self._build_layout()
        self.refresh()

        self.root.bind("<Control-a>", lambda e: self.add_book_dialog())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Control-s>", lambda e: self.save_data())
        self.root.bind("<Delete>",    lambda e: self.delete_selected())
        self.root.bind("<Control-e>", lambda e: self.edit_book_dialog())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────── Layout ───────────────────────────────────
    def _build_layout(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=BG_DARK, width=220)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)

        logo = tk.Frame(sb, bg=BG_DARK)
        logo.pack(fill="x", pady=(24, 8), padx=16)
        tk.Label(logo, text="📚", font=("Calibri", 34), bg=BG_DARK,
                 fg=ACCENT_TEAL).pack()
        tk.Label(logo, text="Reading List", font=FONT_HEADING,
                 bg=BG_DARK, fg=TEXT_MAIN).pack()
        tk.Label(logo, text="ISI · 2025–2026", font=FONT_SMALL,
                 bg=BG_DARK, fg=TEXT_MUTED).pack(pady=(0, 9))

        tk.Frame(sb, bg=SEPARATOR, height=1).pack(fill="x", padx=16)

        tk.Label(sb, text="FILTER", font=("Calibri", 9, "bold"),
                 bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w", padx=20, pady=(12, 6))

        self.filter_var = tk.StringVar(value="all")
        for label, val in [("All Books","all"),("Unread","unread"),
                            ("In Progress","progress"),("Completed","completed")]:
            btn = tk.Radiobutton(sb, text=label, variable=self.filter_var,
                                 value=val, command=self.refresh,
                                 bg=BG_DARK, fg=TEXT_MAIN, selectcolor=BG_MID,
                                 activebackground=BG_DARK, activeforeground=ACCENT_TEAL,
                                 font=FONT_BODY, indicatoron=False,
                                 relief="flat", bd=0, padx=20, pady=1,
                                 anchor="w", cursor="hand2")
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=ACCENT_TEAL))
            btn.bind("<Leave>", lambda e, b=btn: b.config(fg=TEXT_MAIN))

        tk.Frame(sb, bg=SEPARATOR, height=0).pack(fill="x", padx=16, pady=10)
        tk.Label(sb, text="ACTIONS", font=("Calibri", 9, "bold"),
                 bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w", padx=20, pady=(0, 2))

        for label, cmd in [
            ("➕  Add Book",        self.add_book_dialog),
            ("✏️  Edit Book",        self.edit_book_dialog),
            ("📖  Update Progress", self.update_progress_dialog),
            ("⭐  Rate Book",        self.rate_book_dialog),
            ("🗑️  Delete Book",      self.delete_selected),
            ("🔄  Sort",             self.sort_dialog),
            (" CHANGE PALETTE ",       self.palette_dialog)
        ]:
            b = tk.Button(sb, text=label, command=cmd,
                          bg=BG_DARK, fg=TEXT_MAIN, font=FONT_BODY,
                          activebackground=BG_MID, activeforeground=ACCENT_TEAL,
                          relief="flat", anchor="w", padx=15, pady=1,
                          bd=0, cursor="hand2")
            b.pack(fill="x")
            b.bind("<Enter>", lambda e, btn=b: btn.config(bg=BG_MID, fg=ACCENT_TEAL))
            b.bind("<Leave>", lambda e, btn=b: btn.config(bg=BG_DARK, fg=TEXT_MAIN))

        tk.Frame(sb, bg=SEPARATOR, height=1).pack(fill="x", padx=15, pady=10)
        tk.Label(sb, text="Shortcuts:\nCtrl+A: Add | Ctrl+E: Edit\nCtrl+S: Save | Ctrl+F: Search",font=FONT_SMALL, bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w", padx=5, pady=(0, 4))


    def _build_main(self):
        main = tk.Frame(self.root, bg=BG_MID)
        main.grid(row=0, column=1, sticky="nsew")
        main.rowconfigure(2, weight=1)
        main.columnconfigure(0, weight=1)

        # Header
        header = tk.Frame(main, bg=BG_DARK, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(1, weight=1)
        tk.Label(header, text="My Reading List", font=FONT_TITLE,
                 bg=BG_DARK, fg=TEXT_MAIN).grid(row=0, column=0, padx=24, pady=14, sticky="w")
        StyledButton(header, "💾 Save", self.save_data,
                     bg=ACCENT_TEAL, fg=BG_DARK,
                     font=("Calibri", 12, "bold"), padx=10, pady=4
                     ).grid(row=0, column=1, padx=(0,6), pady=14, sticky="e")
        StyledButton(header, "📊  Statistics", self.show_statistics,
                     bg=BG_MID, fg=ACCENT_TEAL).grid(row=0, column=2, padx=(0,6), pady=14, sticky="e")
        StyledButton(header, "📄  Export PDF", self.export_pdf,
                     bg=ACCENT_GOLD, fg= BG_MID).grid(row=0, column=3, padx=(0,6), pady=14, sticky="e")
        StyledButton(header,"Load Reading List", lambda: self._browse_file("ReadingList", "r"),
                     bg=BG_MID, fg=ACCENT_TEAL).grid(row=0, column=5, padx=(0,6), pady=14, sticky="e")
        sf = tk.Frame(header, bg=BG_DARK)
        sf.grid(row=0, column=4, padx=20, pady=14, sticky="e")
        tk.Label(sf, text="🔍", font=("Calibri", 13),
                 bg=BG_DARK, fg=TEXT_MUTED).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *_: self.refresh())
        self.search_entry = tk.Entry(sf, textvariable=self.search_var,
                                     bg=BG_MID, fg=TEXT_MAIN,
                                     insertbackground=TEXT_MAIN,
                                     font=FONT_BODY, relief="flat", width=26, bd=0)
        self.search_entry.pack(side="left", padx=(6,0), ipady=4)
        tk.Button(sf, text="✕", command=lambda: self.search_var.set(""),
                  bg=BG_DARK, fg=TEXT_MUTED, font=("Calibri", 10),
                  relief="flat", bd=0, cursor="hand2").pack(side="left", padx=4)

        # Stats strip
        self.stats_frame = tk.Frame(main, bg=BG_DARK)
        self.stats_frame.grid(row=1, column=0, sticky="ew")
        self._stat_labels = {}
        for key, cap in [("total","Total Books"),("completed","Completed"),
                         ("progress","In Progress"),("unread","Unread"),
                         ("avg_rating","Avg Rating")]:
            col = tk.Frame(self.stats_frame, bg=BG_DARK)
            col.pack(side="left", padx=20, pady=5)
            lbl = tk.Label(col, text="0", font=("Georgia", 20, "bold"),
                           bg=BG_DARK, fg=ACCENT_TEAL)
            lbl.pack()
            tk.Label(col, text=cap, font=FONT_SMALL,
                     bg=BG_DARK, fg=TEXT_MUTED).pack()
            self._stat_labels[key] = lbl

        tk.Frame(main, bg=SEPARATOR, height=1).grid(row=1, column=0, sticky="ew")

        # Content area — table + cover panel
        content = tk.Frame(main, bg=BG_MID)
        content.grid(row=2, column=0, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        # Table
        tf = tk.Frame(content, bg=BG_MID)
        tf.grid(row=0, column=0, sticky="nsew")
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Book.Treeview",
                        background=BG_MID, fieldbackground=BG_MID,
                        foreground=TEXT_MAIN, rowheight=40,
                        font=FONT_BODY, borderwidth=0)
        style.configure("Book.Treeview.Heading",
                        background=BG_DARK, foreground=ACCENT_TEAL,
                        font=("Calibri", 11, "bold"), relief="flat")
        style.map("Book.Treeview",
                  background=[("selected", BG_LIGHT)],
                  foreground=[("selected", ACCENT_TEAL)])

        cols = ("Title","Author","Year","Language","Pages","Progress","Rating","Notes")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  style="Book.Treeview", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        widths = {"Title":220,"Author":150,"Year":50,"Language":80,
                  "Pages":50,"Progress":150,"Rating":70,"Notes":50}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by_col(c))
            self.tree.column(col, width=widths.get(col,100),
                             anchor="w" if col=="Title" else "center")

        self.tree.tag_configure("completed",   background=READ)
        self.tree.tag_configure("in_progress", background=INREAD)
        self.tree.tag_configure("unread",      background=BG_MID)
        self.tree.tag_configure("odd",         background=BG_LIGHT)
        self.tree.bind("<Double-1>", self.show_book_details)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── Cover panel ───────────────────────────────────────────────────
        if _COVERS_ENABLED:
            cp = tk.Frame(content, bg=BG_DARK, width=COVER_W + 24)
            cp.grid(row=0, column=1, sticky="ns")
            cp.grid_propagate(False)

            # "Now Viewing" label
            tk.Label(cp, text="NOW VIEWING", font=("Calibri", 8, "bold"),
                     bg=BG_DARK, fg=TEXT_MUTED).pack(pady=(14, 6))

            self._cover_img_label = tk.Label(cp, bg=BG_DARK, cursor="hand2")
            self._cover_img_label.pack(padx=12)
            self._cover_img_label.bind("<Button-1>", self.show_book_details)

            # Thin teal divider under cover
            tk.Frame(cp, bg=ACCENT_TEAL, height=2).pack(fill="x", padx=12, pady=(8,4))

            self._cover_title_lbl = tk.Label(cp, text="", bg=BG_DARK,
                                             fg=TEXT_MAIN, font=("Calibri", 9, "bold"),
                                             wraplength=COVER_W, justify="center")
            self._cover_title_lbl.pack(padx=6)
            self._cover_author_lbl = tk.Label(cp, text="", bg=BG_DARK,
                                              fg=ACCENT_TEAL,
                                              font=("Calibri", 8, "italic"),
                                              wraplength=COVER_W, justify="center")
            self._cover_author_lbl.pack(padx=6, pady=(2,0))

            # Fetching indicator
            self._cover_status_lbl = tk.Label(cp, text="", bg=BG_DARK,
                                              fg=TEXT_MUTED,
                                              font=("Calibri", 8, "italic"))
            self._cover_status_lbl.pack(pady=(4,0))

            self._cover_panel = cp
            self._show_placeholder_cover()
        else:
            self._cover_panel = None

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(main, textvariable=self.status_var,
                 bg=BG_DARK, fg=TEXT_MUTED, font=FONT_SMALL,
                 anchor="w", padx=16, pady=5).grid(row=3, column=0, sticky="ew")

    # ─────────────────────────── Cover panel ──────────────────────────────
    def _clear_cover_cache(self):
        if os.path.exists(_CACHE_DIR):
            for fname in os.listdir(_CACHE_DIR):
                path = os.path.join(_CACHE_DIR, fname)
                if os.path.isfile(path):
                    os.remove(path)
    def _show_placeholder_cover(self):
        if not _COVERS_ENABLED or self._cover_panel is None:
            return
        ph = load_tk_image(None, COVER_W, COVER_H, "Select\na book")
        if ph:
            self._cover_img_label.config(image=ph)
            self._cover_img_label.image = ph
        self._cover_title_lbl.config(text="Select a book")
        self._cover_author_lbl.config(text="")
        self._cover_status_lbl.config(text="")

    def _on_select(self, event=None):
        if not _COVERS_ENABLED or self._cover_panel is None:
            return
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        filtered = self._get_filtered()
        if not (0 <= idx < len(filtered)):
            return
        book = filtered[idx]
        cover_key = f"{book.title}|{book.author}"
        if cover_key == self._current_cover_key:
            return
        self._current_cover_key = cover_key

        # Instant placeholder
        ph = load_tk_image(None, COVER_W, COVER_H, book.title)
        if ph:
            self._cover_img_label.config(image=ph)
            self._cover_img_label.image = ph
        self._cover_title_lbl.config(text=book.title)
        self._cover_author_lbl.config(text=book.author)
        self._cover_status_lbl.config(text="fetching…")

        # Check cache first to avoid "fetching" flicker on known books
        cached_path = _cover_cache_path(book.title, book.author)
        if os.path.exists(cached_path):
            photo = load_tk_image(cached_path, COVER_W, COVER_H, book.title)
            if photo:
                self._photo_cache[cover_key] = photo
                self._cover_img_label.config(image=photo)
                self._cover_img_label.image = photo
            self._cover_status_lbl.config(text="")
            return

        def on_fetched(path):
            if self._current_cover_key != cover_key:
                return
            photo = load_tk_image(path, COVER_W, COVER_H, book.title)
            if photo:
                self._photo_cache[cover_key] = photo
                self._cover_img_label.config(image=photo)
                self._cover_img_label.image = photo
            status = "" if path else "no cover found"
            self._cover_status_lbl.config(text=status)

        fetch_cover(book.title, book.author, on_fetched)

    # ─────────────────────────── Data ─────────────────────────────────────
    def _load_on_start(self):
        if os.path.exists(DEFAULT_SAVE_PATH):
            if messagebox.askyesno("Load Data",
                                   "A saved reading list was found.\nLoad it?"):
                self.reading_list.load_from_file()
    def _browse_file(self, title, mode="r"):
        if mode == "r":
            path = filedialog.askopenfilename(title=title,
                                              filetypes=[("JSON Files", "*.json")])
        else:
            path = filedialog.asksaveasfilename(title=title, defaultextension=".json",
                                                filetypes=[("JSON Files", "*.json")])
        if path:
            self.reading_list.load_from_file(path) if mode == "r" else self.reading_list.save_to_file(path)
            self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        books = self._get_filtered()
        for i, book in enumerate(books):
            status = ("completed"   if book.ReadingLevel >= 100
                      else "in_progress" if book.ReadingLevel > 0
                      else "unread")
            bar  = self._progress_bar(book.ReadingLevel)
            tags = (status,) + (("odd",) if i % 2 else ())
            flag = "💬" if book.Comments.strip() else ""
            self.tree.insert("", "end",
                             values=(book.title, book.author, book.year,
                                     book.OriginalLanguage, book.nb_pages,
                                     bar, f"{book.Rating}/10", flag),
                             tags=tags)
        self._update_stats()
        self.status_var.set(f"Showing {len(books)} book{'s' if len(books)!=1 else ''}")

    def _progress_bar(self, pct):
        filled = int(pct / 10)
        return "█" * filled + "░" * (10 - filled) + f"  {pct:.0f}%"

    def _get_filtered(self):
        f = self.filter_var.get()
        if f == "unread":      books = self.reading_list.get_unread_books()
        elif f == "progress":  books = self.reading_list.get_in_progress_books()
        elif f == "completed": books = self.reading_list.get_completed_books()
        else:                  books = self.reading_list.books[:]
        q = self.search_var.get().lower().strip()
        if q:
            books = [b for b in books if q in b.title.lower()
                     or q in b.author.lower()
                     or q in b.OriginalLanguage.lower()]
        return books

    def _update_stats(self):
        bs     = self.reading_list.books
        comp   = len(self.reading_list.get_completed_books())
        prog   = len(self.reading_list.get_in_progress_books())
        unread = len(self.reading_list.get_unread_books())
        rated  = [b.Rating for b in bs if b.Rating > 0]
        avg    = f"{sum(rated)/len(rated):.1f}" if rated else "—"
        self._stat_labels["total"].config(text=str(len(bs)))
        self._stat_labels["completed"].config(text=str(comp))
        self._stat_labels["progress"].config(text=str(prog))
        self._stat_labels["unread"].config(text=str(unread))
        self._stat_labels["avg_rating"].config(text=avg)

    def _sort_by_col(self, col):
        mapping = {"Title":"SortBooksByTitle","Author":"SortBooksByAuthor",
                   "Year":"SortBooksByYear","Progress":"SortBooksByReadingLevel","Rating":"SortBooksByRating",
                   "Language":"SortBooksByOriginalLanguage","Pages":"SortBooksByPages",
                   "Notes":"SortBooksByComments"}
        if col in mapping:
            getattr(self.reading_list, mapping[col])()
            self.refresh()

    def _get_selected_book(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a book first.")
            return None
        idx = self.tree.index(sel[0])
        filtered = self._get_filtered()
        if 0 <= idx < len(filtered):
            s = filtered[idx]
            for i, b in enumerate(self.reading_list.books):
                if b.title == s.title and b.author == s.author:
                    return i, b
        return None

    # ─────────────────────────── Dialogs ──────────────────────────────────
    def _make_dialog(self, title, width=420, height=400):
        d = tk.Toplevel(self.root)
        d.title(title)
        d.geometry(f"{width}x{height}")
        d.configure(bg=BG_DARK)
        d.transient(self.root)
        d.grab_set()
        d.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width()  - width)  // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        d.geometry(f"+{x}+{y}")
        return d

    def _form_row(self, parent, label, row, default=""):
        tk.Label(parent, text=label, font=FONT_BODY, bg=BG_DARK,
                 fg=TEXT_MUTED, anchor="w").grid(row=row, column=0,
                                                  sticky="w", pady=6, padx=(0,12))
        var = tk.StringVar(value=str(default))
        entry = tk.Entry(parent, textvariable=var, font=FONT_BODY,
                         bg=BG_MID, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                         relief="flat", bd=0, width=28)
        entry.grid(row=row, column=1, sticky="ew", pady=6, ipady=5, padx=4)
        return var
    def _rebuild_ui(self):
        """Destroy all widgets and rebuild with the current palette globals."""
        for widget in self.root.winfo_children():
            widget.destroy()
        self._photo_cache.clear()
        self._current_cover_key = None
        self._build_layout()
        self.refresh()

    def palette_dialog(self):
        d = self._make_dialog("Change Color Palette", 360, 60 + 46 * len(Palettes))
        #Add a slider to browse through palettes
        
        tk.Label(d, text="Select a Color Palette", font=FONT_HEADING,
                 bg=BG_DARK, fg=ACCENT_TEAL).pack(pady=(16, 12), padx=20)
        
        for name in Palettes:
            def handler(n=name, dlg=d):
                ChangePallete(n)
                # ── Persist the choice so it survives restart ─────────────
                self._config["palette"] = n
                _save_config(self._config)
                dlg.destroy()
                self._rebuild_ui()
            StyledButton(d, name, handler, bg=BG_MID, fg=TEXT_MAIN).pack(fill="x", padx=40, pady=4)
            
    def add_book_dialog(self):
        d = self._make_dialog("Add New Book", 460, 380)
        tk.Label(d, text="Add New Book", font=FONT_HEADING,
                 bg=BG_DARK, fg=ACCENT_TEAL).pack(pady=(16,4), padx=20, anchor="w")
        tk.Frame(d, bg=ACCENT_TEAL, height=2).pack(fill="x", padx=20)
        form = tk.Frame(d, bg=BG_DARK, padx=20, pady=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        v_title    = self._form_row(form, "Title",    0)
        v_author   = self._form_row(form, "Author",   1)
        v_year     = self._form_row(form, "Year",     2)
        v_pages    = self._form_row(form, "Pages",    3)
        v_language = self._form_row(form, "Language", 4, "Unknown")

        def save():
            try:
                title  = v_title.get().strip()
                author = v_author.get().strip()
                year   = int(v_year.get().strip())
                pages  = int(v_pages.get().strip())
                lang   = v_language.get().strip() or "Unknown"
                if not title or not author:
                    messagebox.showerror("Error", "Title and Author are required!", parent=d)
                    return
                if pages <= 0:
                    messagebox.showerror("Error", "Pages must be positive!", parent=d)
                    return
                self.reading_list.add_book(Book(title, author, year, pages, lang))
                self.refresh()
                self.status_var.set(f"✅ Added '{title}'")
                # Pre-fetch cover in background
                if _COVERS_ENABLED:
                    fetch_cover(title, author, lambda p: None)
                d.destroy()
            except ValueError as e:
                messagebox.showerror("Error",
                    str(e) if "already in" in str(e)
                    else "Year and Pages must be numbers.", parent=d)

        bf = tk.Frame(d, bg=BG_DARK)
        bf.pack(pady=8)
        StyledButton(bf, "Save Book", save).pack(side="left", padx=6)
        StyledButton(bf, "Cancel", d.destroy, bg=BG_MID, fg=TEXT_MAIN).pack(side="left", padx=6)

    def edit_book_dialog(self):
        res = self._get_selected_book()
        if not res: return
        idx, book = res
        d = self._make_dialog("Edit Book", 460, 420)
        tk.Label(d, text="Edit Book", font=FONT_HEADING,
                 bg=BG_DARK, fg=ACCENT_TEAL).pack(pady=(16,4), padx=20, anchor="w")
        tk.Frame(d, bg=ACCENT_TEAL, height=2).pack(fill="x", padx=20)
        form = tk.Frame(d, bg=BG_DARK, padx=20, pady=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        v_title    = self._form_row(form, "Title",    0, book.title)
        v_author   = self._form_row(form, "Author",   1, book.author)
        v_year     = self._form_row(form, "Year",     2, book.year)
        v_pages    = self._form_row(form, "Pages",    3, book.nb_pages)
        v_language = self._form_row(form, "Language", 4, book.OriginalLanguage)

        def save():
            try:
                title  = v_title.get().strip()
                author = v_author.get().strip()
                year   = int(v_year.get().strip())
                pages  = int(v_pages.get().strip())
                lang   = v_language.get().strip() or "Unknown"
                if not title or not author:
                    messagebox.showerror("Error", "Title and Author are required!", parent=d)
                    return
                if pages <= 0:
                    messagebox.showerror("Error", "Pages must be positive!", parent=d)
                    return
                if title.lower() != book.title.lower() or author.lower() != book.author.lower():
                    self.reading_list.books.pop(idx)
                    is_dup = self.reading_list._is_duplicate(Book(title,author,year,pages,lang))
                    self.reading_list.books.insert(idx, book)
                    if is_dup:
                        messagebox.showerror("Error",
                            f"'{title}' by {author} is already in your list.", parent=d)
                        return
                    # Invalidate old cover
                    self._photo_cache.pop(f"{book.title}|{book.author}", None)
                    if _COVERS_ENABLED:
                        fetch_cover(title, author, lambda p: None)
                book.title = title
                book.author = author
                book.year = year
                book.OriginalLanguage = lang
                if pages != book.nb_pages:
                    pages_read = round(book.ReadingLevel / 100 * book.nb_pages)
                    book.nb_pages = pages
                    book.update_reading_level(min(pages_read, pages))
                self._current_cover_key = None
                self.refresh()
                self.status_var.set(f"✏️  '{title}' updated")
                d.destroy()
            except ValueError:
                messagebox.showerror("Error", "Year and Pages must be numbers.", parent=d)

        bf = tk.Frame(d, bg=BG_DARK)
        bf.pack(pady=8)
        StyledButton(bf, "Save Changes", save).pack(side="left", padx=6)
        StyledButton(bf, "Cancel", d.destroy, bg=BG_MID, fg=TEXT_MAIN).pack(side="left", padx=6)

    def update_progress_dialog(self):
        res = self._get_selected_book()
        if not res: return
        _, book = res
        pages = simpledialog.askinteger("Update Progress",
                                        f"Pages read for '{book.title}'\n(max {book.nb_pages}):",
                                        minvalue=0, maxvalue=book.nb_pages,
                                        parent=self.root)
        if pages is not None:
            book.update_reading_level(pages)
            self.refresh()
            if book.ReadingLevel >= 100:
                messagebox.showinfo("Completed!", f"You've finished '{book.title}'!")
            self.status_var.set(f"📖 Progress updated — {book.ReadingLevel:.0f}%")

    def rate_book_dialog(self):
        res = self._get_selected_book()
        if not res: return
        _, book = res
        rating = simpledialog.askfloat("Rate Book",
                                       f"Rating for '{book.title}' (0–10):",
                                       minvalue=0.0, maxvalue=10.0,
                                       parent=self.root)
        if rating is not None:
            try:
                book.update_rating(rating)
                self.refresh()
                self.status_var.set(f"⭐ Rated '{book.title}' → {rating}/10")
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def delete_selected(self):
        res = self._get_selected_book()
        if not res: return
        _, book = res
        if messagebox.askyesno("Confirm Delete",
                               f"Remove '{book.title}' from your list?",
                               parent=self.root):
            self._photo_cache.pop(f"{book.title}|{book.author}", None)
            self.reading_list.remove_book(book)
            self._current_cover_key = None
            self.refresh()
            if _COVERS_ENABLED:
                self._show_placeholder_cover()
            self.status_var.set(f"🗑️ Removed '{book.title}'")

    def show_book_details(self, event=None):
        res = self._get_selected_book()
        if not res: return
        _, book = res

        d_w = 800 if _COVERS_ENABLED else 600
        d_h = 600 if _COVERS_ENABLED else 520
        d = self._make_dialog("Book Details", d_w, d_h)

        # Top: cover + title
        top = tk.Frame(d, bg=BG_DARK)
        top.pack(fill="x", padx=20, pady=(16, 0))

        if _COVERS_ENABLED:
            cf = tk.Frame(top, bg=BG_DARK)
            cf.pack(side="left", padx=(0, 16))
            clbl = tk.Label(cf, bg=BG_DARK)
            clbl.pack()
            ph = load_tk_image(None, MINI_W, MINI_H, book.title)
            if ph:
                clbl.config(image=ph)
                clbl.image = ph

            def _update_dialog_cover(path):
                photo = load_tk_image(path, MINI_W, MINI_H, book.title)
                if photo:
                    clbl.config(image=photo)
                    clbl.image = photo

            # Use cache if available, otherwise fetch
            cached = _cover_cache_path(book.title, book.author)
            if os.path.exists(cached):
                _update_dialog_cover(cached)
            else:
                fetch_cover(book.title, book.author, _update_dialog_cover)

        meta = tk.Frame(top, bg=BG_DARK)
        meta.pack(side="left", fill="both", expand=True)
        tk.Label(meta, text=book.title, font=FONT_HEADING,
                 bg=BG_DARK, fg=ACCENT_TEAL,
                 wraplength=420, justify="left").pack(anchor="w")
        tk.Label(meta, text=f"by {book.author}", font=FONT_BODY,
                 bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w", pady=(2, 8))

        tk.Frame(d, bg=ACCENT_TEAL, height=2).pack(fill="x", padx=20, pady=(8, 0))

        info = tk.Frame(d, bg=BG_DARK, padx=20)
        info.pack(fill="x")
        for label, val in [("Year", str(book.year)),
                            ("Language", book.OriginalLanguage),
                            ("Pages", str(book.nb_pages)),
                            ("Progress", f"{book.ReadingLevel:.1f}%"),
                            ("Rating", f"{book.Rating}/10")]:
            row = tk.Frame(info, bg=BG_DARK)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, font=("Calibri",11,"bold"),
                     bg=BG_DARK, fg=TEXT_MUTED, width=12, anchor="w").pack(side="left")
            tk.Label(row, text=val, font=FONT_BODY,
                     bg=BG_DARK, fg=TEXT_MAIN, anchor="w").pack(side="left")

        tk.Label(d, text="Notes & Comments", font=("Calibri",10,"bold"),
                 bg=BG_DARK, fg=TEXT_MUTED).pack(anchor="w", padx=15, pady=(12,4))
        txt = ScrolledText(d, wrap="word", width=64, height=10,
                           bg=BG_MID, fg=TEXT_MAIN, font=FONT_MONO,
                           insertbackground=TEXT_MAIN, relief="flat", bd=0)
        txt.pack(padx=20, fill="x")
        existing = book.Comments.strip()
        txt.insert("1.0", existing if existing else "")

        def save_comments():
            new_text = txt.get("1.0", "end-1c").strip()
            book.Comments = new_text + "\n" if new_text else ""
            self.refresh()
            self.status_var.set(f"💬 Comments saved for '{book.title}'")
            d.destroy()

        btn_row = tk.Frame(d, bg=BG_DARK)
        btn_row.pack(pady=10)
        StyledButton(btn_row, "💾 Save Comments", save_comments).pack(side="left", padx=6)
        StyledButton(btn_row, "Close", d.destroy, bg=BG_MID, fg=TEXT_MAIN).pack(side="left", padx=6)

    def sort_dialog(self):
        d = self._make_dialog("Sort Books", 300, 430)
        tk.Label(d, text="Sort books by", font=FONT_HEADING,
                 bg=BG_DARK, fg=ACCENT_TEAL).pack(pady=(16, 12))
        for label, cmd in [
            ("📖  Title",        self.reading_list.SortBooksByTitle),
            ("✍️  Author",        self.reading_list.SortBooksByAuthor),
            ("📅  Year",          self.reading_list.SortBooksByYear),
            ("📊  Reading Level", self.reading_list.SortBooksByReadingLevel),
            ("⭐  Rating",        self.reading_list.SortBooksByRating),
            ("🗣️  Language",      self.reading_list.SortBooksByOriginalLanguage),
            ("📄  Pages",         self.reading_list.SortBooksByPages),
            ("💬  Comments",      self.reading_list.SortBooksByComments)
        ]:
            StyledButton(d, label, lambda c=cmd: [c(), self.refresh(), d.destroy()],
                         bg=BG_MID, fg=TEXT_MAIN).pack(fill="x", padx=30, pady=4)

    def show_statistics(self):
        bs = self.reading_list.books
        rbs = self.reading_list.get_completed_books()
        if not bs:
            messagebox.showinfo("Statistics", "No books in your list yet!")
            return
        comp   = len(rbs)
        prog   = len(self.reading_list.get_in_progress_books())
        unread = len(self.reading_list.get_unread_books())
        pages  = sum(b.nb_pages for b in bs)
        read_pages = sum(b.nb_pages for b in rbs) + sum(int(b.ReadingLevel/100 * b.nb_pages) for b in self.reading_list.get_in_progress_books())
        rated  = [b.Rating for b in bs if b.Rating > 0]
        avg    = f"{sum(rated)/len(rated):.1f}/10" if rated else "No ratings yet"
        top    = max(bs, key=lambda b: b.Rating, default=None)

        d = self._make_dialog("Reading Statistics", 460, 400)
        tk.Label(d, text="📊 Statistics", font=FONT_HEADING,
                 bg=BG_DARK, fg=ACCENT_TEAL).pack(pady=(16,4), padx=20, anchor="w")
        tk.Frame(d, bg=ACCENT_TEAL, height=2).pack(fill="x", padx=20, pady=4)
        frame = tk.Frame(d, bg=BG_DARK, padx=24)
        frame.pack(fill="x", pady=4)
        stats = [("Total Books", str(len(bs))), ("Completed", str(comp)),
                 ("In Progress", str(prog)), ("Unread", str(unread)),
                 ("Total Pages", f"{pages:,}"), ("Pages Read", f"{read_pages:,}"),
                ("Average Rating", avg)]
        if top:
            stats.append(("Top Rated", f"{top.title} ({top.Rating}/10)"))
        for label, val in stats:
            row = tk.Frame(frame, bg=BG_DARK)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, font=("Calibri",11),
                     bg=BG_DARK, fg=TEXT_MUTED, width=16, anchor="w").pack(side="left")
            tk.Label(row, text=val, font=("Calibri",11,"bold"),
                     bg=BG_DARK, fg=TEXT_MAIN, anchor="w").pack(side="left")
        StyledButton(d, "Close", d.destroy).pack(pady=14)

    # ─────────────────────────── I/O ──────────────────────────────────────
    def save_data(self):
        self.reading_list.save_to_file()
        self.status_var.set(f"💾 Saved to {DEFAULT_SAVE_PATH}")

    def _on_close(self):
        answer = messagebox.askyesnocancel(
            "Save before closing?",
            "Would you like to save your reading list before exiting?",
            parent=self.root)
        if answer is None:
            return
        if answer:
            self.reading_list.save_to_file()
        self.root.destroy()

    def export_pdf(self):
        if not self.reading_list.books:
            messagebox.showinfo("Export PDF", "No books to export!", parent=self.root)
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                            Table, TableStyle, HRFlowable)
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
        except ImportError:
            messagebox.showerror("Missing Library",
                "reportlab is required.\n\nRun:  pip install reportlab", parent=self.root)
            return

        default_name = f"reading_list_{datetime.now().strftime('%Y%m%d')}.pdf"
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export Reading List as PDF",
            defaultextension=".pdf", filetypes=[("PDF files","*.pdf")],
            initialfile=default_name)
        if not path:
            return
        #BG_DARK, BG_MID, BG_LIGHT, ACCENT_TEAL, ACCENT_GOLD, TEXT_MAIN, TEXT_MUTED, GREEN, RED_SOFT, SEPARATOR = ("#0D1B2A" ,"#1C2F45","#243852", "#02C3A7" ,"#FFAE00", "#EEF2F7", "#8FA8C0", "#3DD68C","#7453EC", "#1E3451")
        # ----- Colors (same as yours) -----
        C_DARK  = colors.HexColor(BG_DARK)
        C_MID   = colors.HexColor(BG_MID)
        C_LIGHT = colors.HexColor(BG_LIGHT)
        C_TEAL  = colors.HexColor(ACCENT_TEAL)
        C_GOLD  = colors.HexColor(ACCENT_GOLD)
        C_TEXT  = colors.HexColor(TEXT_MAIN)
        C_MUTED = colors.HexColor(TEXT_MUTED)
        C_GREEN = colors.HexColor(READ)
        C_PROG  = colors.HexColor(INREAD)

        # ----- Paragraph styles -----
        ts = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=22,
                            textColor=C_TEAL, alignment=TA_CENTER, spaceAfter=15)
        ss = ParagraphStyle("S", fontName="Helvetica", fontSize=10,
                            textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=16)
        sec_s  = ParagraphStyle("Sc", fontName="Helvetica-Bold", fontSize=13,
                                textColor=C_GOLD, spaceBefore=18, spaceAfter=6)
        body_s = ParagraphStyle("B", fontName="Helvetica", fontSize=9,
                                textColor=C_TEXT, leading=13)
        cmt_s  = ParagraphStyle("C", fontName="Helvetica-Oblique", fontSize=12,
                                textColor=C_MUTED, leading=12, leftIndent=12, rightIndent=12)
        hdr_s  = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=8,
                                textColor=C_TEAL)

        doc = SimpleDocTemplate(path, pagesize=A4,
                                leftMargin=1.8*cm, rightMargin=1.8*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        # ----- Dark background for every page -----
        def dark_bg(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(C_DARK)
            canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            canvas.setFillColor(C_TEAL)
            canvas.rect(0, A4[1]-6, A4[0], 6, fill=1, stroke=0)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(C_MUTED)
            canvas.drawRightString(A4[0]-1.8*cm, 1.2*cm, f"Page {doc.page}")
            canvas.restoreState()

        # ----- Prepare statistics -----
        bs      = self.reading_list.books
        comp    = len(self.reading_list.get_completed_books())
        prog    = len(self.reading_list.get_in_progress_books())
        unread  = len(self.reading_list.get_unread_books())
        rated   = [b.Rating for b in bs if b.Rating > 0]
        avg_r   = f"{sum(rated)/len(rated):.1f}/10" if rated else "—"
        total_p = sum(b.nb_pages for b in bs)

        # ----- Build the story (list of flowables) -----
        story = [Spacer(1, 0.3*cm)]
        story.append(Paragraph("📚  Personal Reading List", ts))
        story.append(Paragraph(f"ISI · 2025–2026  ·  Exported {datetime.now().strftime('%d %B %Y')}", ss))
        story.append(HRFlowable(width="100%", thickness=1, color=C_TEAL, spaceAfter=12))

        # Statistics table
        stat_data = [[
            Paragraph(f"<b>{len(bs)}</b><br/>Total", body_s),
            Paragraph(f"<b>{comp}</b><br/>Completed", body_s),
            Paragraph(f"<b>{prog}</b><br/>In Progress", body_s),
            Paragraph(f"<b>{unread}</b><br/>Unread", body_s),
            Paragraph(f"<b>{avg_r}</b><br/>Avg Rating", body_s),
            Paragraph(f"<b>{total_p:,}</b><br/>Total Pages", body_s),
        ]]
        stat_tbl = Table(stat_data, colWidths=[2.7*cm]*6)
        stat_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), C_MID),
            ("ALIGN",        (0,0),(-1,-1), "CENTER"),
            ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
            ("BOX",          (0,0),(-1,-1), 1, C_LIGHT),
            ("INNERGRID",    (0,0),(-1,-1), 0.5, C_LIGHT),
            ("TOPPADDING",   (0,0),(-1,-1), 8),
            ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ]))
        story.append(stat_tbl)
        story.append(Spacer(1, 0.5*cm))

        # ----- Column widths for the mini‑tables (one row each) -----
        col_w = [6.5*cm, 3.5*cm, 1.5*cm, 2*cm, 2.5*cm, 2.5*cm]

        # Helper to create a one‑row table for a single book
        def make_book_table(book, row_bg):
            filled = int(book.ReadingLevel / 10)
            bar = "█"*filled + "░"*(10-filled) + f" {book.ReadingLevel:.0f}%"
            rating = f"{book.Rating}/10" if book.Rating > 0 else "—"
            row = [
                Paragraph(book.title, body_s),
                Paragraph(book.author, body_s),
                Paragraph(str(book.year), body_s),
                Paragraph(book.OriginalLanguage, body_s),
                Paragraph(bar, ParagraphStyle("bar", fontName="Courier",
                        fontSize=7, textColor=C_TEAL)),
                Paragraph(rating, body_s),
            ]
            tbl = Table([row], colWidths=col_w, splitByRow=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",   (0,0),(-1,0), row_bg),
                ("TEXTCOLOR",    (0,0),(-1,0), C_TEXT),
                ("FONTNAME",     (0,0),(-1,0), "Helvetica"),
                ("FONTSIZE",     (0,0),(-1,0), 8),
                ("ALIGN",        (2,0),(-1,0), "CENTER"),
                ("VALIGN",       (0,0),(-1,0), "TOP"),
                ("TOPPADDING",   (0,0),(-1,0), 5),
                ("BOTTOMPADDING",(0,0),(-1,0), 5),
                ("BOX",          (0,0),(-1,0), 0.4, C_LIGHT),
                ("INNERGRID",    (0,0),(-1,-1), 0.4, C_LIGHT),
            ]))
            return tbl

        # Process each section (Completed, In Progress, Unread)
        for sec_title, books, row_bg in [
            ("✅  Completed",   self.reading_list.get_completed_books(),   C_GREEN),
            ("📖  In Progress", self.reading_list.get_in_progress_books(), C_PROG),
            ("⏳  Unread",      self.reading_list.get_unread_books(),      C_MID),
        ]:
            if not books:
                continue
            story.append(Paragraph(sec_title, sec_s))

            for book in books:
                # Add the book's mini‑table
                story.append(make_book_table(book, row_bg))
                # Add the comment immediately after, if any
                if book.Comments.strip():
                    story.append(Spacer(1, 0.1*cm))
                    comment_text = book.Comments.strip()
                    # Escape XML special chars and convert newlines to <br/>
                    import xml.sax.saxutils as saxutils
                    comment_text = saxutils.escape(comment_text)
                    comment_text = comment_text.replace('\n', '<br/>')
                    comment_text = f"💬  {comment_text}"
                    story.append(Paragraph(comment_text, cmt_s))
                    story.append(Spacer(1, 0.2*cm))
                else:
                    story.append(Spacer(1, 0.1*cm))

            story.append(Spacer(1, 0.3*cm))

        # Build the PDF
        doc.build(story, onFirstPage=dark_bg, onLaterPages=dark_bg)
        self.status_var.set(f"📄 Exported → {os.path.basename(path)}")
        messagebox.showinfo("Export Complete", f"PDF saved to:\n{path}", parent=self.root)

def main():
    root = tk.Tk()
    app = ReadingListGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()