"""
CVCV Name Generator — Desktop GUI
Built with CustomTkinter for a polished, production-grade experience.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import os
import string
import glob
from itertools import product


# ── Embedded generator / filter / engine ────────────────────────────────────

class CVCVGenerator:
    def __init__(self, vowels=None, consonants=None, add_vowels=None,
                 add_consonants=None, include_y=False, first=None):
        default_vowels = "aeiou"
        if include_y:
            default_vowels += "y"
        base_vowels = vowels if vowels else default_vowels
        if add_vowels:
            base_vowels += add_vowels
        self.vowels = "".join(sorted(set(base_vowels.lower())))

        if consonants:
            base_consonants = consonants
        else:
            base_consonants = "".join(c for c in string.ascii_lowercase if c not in self.vowels)
        if add_consonants:
            base_consonants += add_consonants
        self.consonants = "".join(sorted(set(base_consonants.lower())))
        self.first = first.lower() if first else None

    def generate(self):
        if self.first:
            if self.first not in self.consonants:
                raise ValueError(f"First letter '{self.first}' must exist in consonant set.")
            first_letters = self.first
        else:
            first_letters = self.consonants
        for c1, v1, c2, v2 in product(first_letters, self.vowels, self.consonants, self.vowels):
            yield c1 + v1 + c2 + v2


class NoFilter:
    def apply(self, n): return True

class OnlyRepeatingVowels:
    def apply(self, n): return n[1] == n[3]

class OnlyRepeatingConsonants:
    def apply(self, n): return n[0] == n[2]

class OnlyRepeatingBoth:
    def apply(self, n): return n[0] == n[2] and n[1] == n[3]

FILTERS = {
    "None":               NoFilter(),
    "Repeating Vowels":   OnlyRepeatingVowels(),
    "Repeating Consonants": OnlyRepeatingConsonants(),
    "Repeating Both":     OnlyRepeatingBoth(),
}


class NameEngine:
    def __init__(self, generator, name_filter, suffix=""):
        self.generator = generator
        self.name_filter = name_filter
        self.suffix = suffix

    def run(self):
        for name in self.generator.generate():
            if self.name_filter.apply(name):
                yield name + self.suffix

    def export_grouped(self, folder="output"):
        os.makedirs(folder, exist_ok=True)
        grouped = {}
        for name in self.run():
            grouped.setdefault(name[0], []).append(name)

        if self.generator.first:
            allowed_letters = {self.generator.first}
        else:
            allowed_letters = set(self.generator.consonants)

        for file_path in glob.glob(os.path.join(folder, "*.txt")):
            letter = os.path.basename(file_path).replace(".txt", "")
            if letter not in allowed_letters:
                os.remove(file_path)

        written = []
        for letter in allowed_letters:
            file_path = os.path.join(folder, f"{letter}.txt")
            names = grouped.get(letter, [])
            with open(file_path, "w") as f:
                f.write("\n".join(names))
            written.append(file_path)
        return written, sum(len(v) for v in grouped.values())


# ── Palette & constants ──────────────────────────────────────────────────────

DARK_BG      = "#0e0e12"
PANEL_BG     = "#16161d"
CARD_BG      = "#1c1c26"
ACCENT       = "#7c6af7"        # electric violet
ACCENT2      = "#4fc3f7"        # icy cyan
SUCCESS      = "#43d9a0"
WARN         = "#f5a623"
TEXT_PRIMARY = "#f0eeff"
TEXT_MUTED   = "#6e6e8a"
BORDER       = "#2a2a3a"

FONT_DISPLAY = ("SF Pro Display", 22, "bold")
FONT_LABEL   = ("SF Pro Text",   11)
FONT_SMALL   = ("SF Pro Text",   10)
FONT_MONO    = ("JetBrains Mono", 11)
FONT_MONO_SM = ("JetBrains Mono", 10)


# ── Main App ─────────────────────────────────────────────────────────────────

class CVCVApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("CVCV Name Generator")
        self.geometry("980x720")
        self.minsize(860, 640)
        self.configure(fg_color=DARK_BG)

        self._results: list[str] = []
        self._running = False

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=0, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⬡  CVCV", font=("SF Pro Display", 18, "bold"),
            text_color=ACCENT
        ).pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            header, text="Name Generator",
            font=("SF Pro Display", 18), text_color=TEXT_PRIMARY
        ).pack(side="left", pady=12)

        self._status_lbl = ctk.CTkLabel(
            header, text="Ready", font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        self._status_lbl.pack(side="right", padx=20)

        # ── Body split ──────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=DARK_BG)
        body.pack(fill="both", expand=True, padx=0, pady=0)
        body.grid_columnconfigure(0, weight=0, minsize=300)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_results_panel(body)

    def _section(self, parent, title):
        """Titled section card."""
        outer = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=10)
        ctk.CTkLabel(
            outer, text=title.upper(), font=("SF Pro Display", 9, "bold"),
            text_color=ACCENT, anchor="w"
        ).pack(fill="x", padx=14, pady=(10, 4))
        sep = ctk.CTkFrame(outer, fg_color=BORDER, height=1, corner_radius=0)
        sep.pack(fill="x", padx=14, pady=(0, 8))
        return outer

    def _row(self, parent, label, widget_fn, **kw):
        """Label + widget row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkLabel(row, text=label, font=FONT_LABEL, text_color=TEXT_MUTED,
                     width=130, anchor="w").pack(side="left")
        w = widget_fn(row, **kw)
        w.pack(side="left", fill="x", expand=True)
        return w

    def _entry(self, parent, placeholder="", **kw):
        return ctk.CTkEntry(
            parent, placeholder_text=placeholder,
            fg_color="#0e0e12", border_color=BORDER, border_width=1,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            font=FONT_MONO, corner_radius=6, height=30, **kw
        )

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        sidebar = ctk.CTkScrollableFrame(
            parent, fg_color=PANEL_BG, corner_radius=0, width=300,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=ACCENT
        )
        sidebar.grid(row=0, column=0, sticky="nsew")

        # ── LETTERS section ──────────────────────────────────────────────────
        sec1 = self._section(sidebar, "Letter Sets")
        sec1.pack(fill="x", padx=12, pady=(14, 6))

        self._vowels_var = tk.StringVar()
        self._row(sec1, "Vowels", self._entry,
                  placeholder="default: aeiou",
                  textvariable=self._vowels_var)

        self._add_vowels_var = tk.StringVar()
        self._row(sec1, "Add Vowels", self._entry,
                  placeholder="e.g. y",
                  textvariable=self._add_vowels_var)

        self._consonants_var = tk.StringVar()
        self._row(sec1, "Consonants", self._entry,
                  placeholder="default: all non-vowels",
                  textvariable=self._consonants_var)

        self._add_consonants_var = tk.StringVar()
        self._row(sec1, "Add Consonants", self._entry,
                  placeholder="e.g. ng",
                  textvariable=self._add_consonants_var)

        # include-y toggle
        tog_row = ctk.CTkFrame(sec1, fg_color="transparent")
        tog_row.pack(fill="x", padx=14, pady=(0, 10))
        self._include_y = tk.BooleanVar(value=False)
        ctk.CTkLabel(tog_row, text="Include Y as vowel", font=FONT_LABEL,
                     text_color=TEXT_MUTED, anchor="w").pack(side="left")
        ctk.CTkSwitch(
            tog_row, text="", variable=self._include_y,
            button_color=ACCENT, progress_color=ACCENT,
            button_hover_color="#5b4fd4", width=42, height=20
        ).pack(side="right")

        # ── FILTER section ───────────────────────────────────────────────────
        sec2 = self._section(sidebar, "Pattern Filter")
        sec2.pack(fill="x", padx=12, pady=(0, 6))

        self._filter_var = tk.StringVar(value="None")
        filter_row = ctk.CTkFrame(sec2, fg_color="transparent")
        filter_row.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(filter_row, text="Filter", font=FONT_LABEL,
                     text_color=TEXT_MUTED, width=130, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(
            filter_row, values=list(FILTERS.keys()),
            variable=self._filter_var,
            fg_color=DARK_BG, button_color=ACCENT,
            button_hover_color="#5b4fd4", dropdown_fg_color=CARD_BG,
            text_color=TEXT_PRIMARY, font=FONT_LABEL,
            corner_radius=6, width=150
        ).pack(side="left")

        # ── OPTIONS section ──────────────────────────────────────────────────
        sec3 = self._section(sidebar, "Options")
        sec3.pack(fill="x", padx=12, pady=(0, 6))

        self._suffix_var = tk.StringVar()
        self._row(sec3, "Suffix", self._entry,
                  placeholder="e.g. ly, io, ai",
                  textvariable=self._suffix_var)

        self._first_var = tk.StringVar()
        self._row(sec3, "Pin First Letter", self._entry,
                  placeholder="single consonant",
                  textvariable=self._first_var)
        ctk.CTkLabel(
            sec3, text="Pin restricts output to one starting consonant.",
            font=FONT_SMALL, text_color=TEXT_MUTED, anchor="w", wraplength=250
        ).pack(fill="x", padx=14, pady=(0, 10))

        # ── ACTIONS ──────────────────────────────────────────────────────────
        sec4 = self._section(sidebar, "Actions")
        sec4.pack(fill="x", padx=12, pady=(0, 14))

        btn_cfg = dict(corner_radius=8, height=36, font=("SF Pro Display", 12, "bold"))

        self._gen_btn = ctk.CTkButton(
            sec4, text="▶  Generate",
            fg_color=ACCENT, hover_color="#5b4fd4",
            command=self._run_generate, **btn_cfg
        )
        self._gen_btn.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(
            sec4, text="⬡  Export to Folder",
            fg_color=CARD_BG, hover_color=BORDER, border_color=ACCENT,
            border_width=1, text_color=ACCENT,
            command=self._run_export, **btn_cfg
        ).pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(
            sec4, text="⬇  Save Results as TXT",
            fg_color=CARD_BG, hover_color=BORDER, border_color=BORDER,
            border_width=1, text_color=TEXT_MUTED,
            command=self._save_txt, **btn_cfg
        ).pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(
            sec4, text="✕  Clear",
            fg_color="transparent", hover_color="#2a0a0a",
            border_color="#4a1a1a", border_width=1, text_color="#c06060",
            command=self._clear_results, **btn_cfg
        ).pack(fill="x", padx=14, pady=(0, 10))

    # ── Results panel ────────────────────────────────────────────────────────

    def _build_results_panel(self, parent):
        right = ctk.CTkFrame(parent, fg_color=DARK_BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Toolbar strip
        toolbar = ctk.CTkFrame(right, fg_color=PANEL_BG, corner_radius=0, height=42)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)

        self._count_lbl = ctk.CTkLabel(
            toolbar, text="0 names", font=("SF Pro Display", 11, "bold"),
            text_color=ACCENT2
        )
        self._count_lbl.pack(side="left", padx=16, pady=10)

        # Search
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="🔍  Filter results…",
            textvariable=self._search_var,
            fg_color=DARK_BG, border_color=BORDER, border_width=1,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            font=FONT_MONO_SM, corner_radius=6, height=28, width=200
        )
        search_entry.pack(side="right", padx=16, pady=7)

        ctk.CTkLabel(
            toolbar, text="Search:", font=FONT_SMALL, text_color=TEXT_MUTED
        ).pack(side="right", pady=7)

        # Results textbox
        self._results_box = ctk.CTkTextbox(
            right,
            fg_color=CARD_BG, text_color=TEXT_PRIMARY,
            font=FONT_MONO,
            corner_radius=0,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
            wrap="none",
            state="disabled",
            border_width=0
        )
        self._results_box.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Progress bar (hidden initially)
        self._progress = ctk.CTkProgressBar(
            right, fg_color=CARD_BG, progress_color=ACCENT,
            corner_radius=0, height=3
        )
        self._progress.grid(row=2, column=0, sticky="ew")
        self._progress.set(0)
        self._progress.grid_remove()

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _make_generator(self):
        vowels     = self._vowels_var.get().strip() or None
        consonants = self._consonants_var.get().strip() or None
        add_v      = self._add_vowels_var.get().strip() or None
        add_c      = self._add_consonants_var.get().strip() or None
        first      = self._first_var.get().strip() or None
        include_y  = self._include_y.get()

        gen = CVCVGenerator(
            vowels=vowels, consonants=consonants,
            add_vowels=add_v, add_consonants=add_c,
            include_y=include_y, first=first
        )
        filt   = FILTERS[self._filter_var.get()]
        suffix = self._suffix_var.get().strip()
        return NameEngine(generator=gen, name_filter=filt, suffix=suffix)

    def _run_generate(self):
        if self._running:
            return
        self._running = True
        self._gen_btn.configure(state="disabled", text="Generating…")
        self._status("Generating…", WARN)
        self._progress.grid()
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        threading.Thread(target=self._generate_thread, daemon=True).start()

    def _generate_thread(self):
        try:
            engine = self._make_generator()
            names = list(engine.run())
            self.after(0, self._finish_generate, names, None)
        except Exception as e:
            self.after(0, self._finish_generate, [], str(e))

    def _finish_generate(self, names, error):
        self._running = False
        self._gen_btn.configure(state="normal", text="▶  Generate")
        self._progress.stop()
        self._progress.grid_remove()

        if error:
            messagebox.showerror("Error", error)
            self._status(f"Error: {error}", "#c06060")
            return

        self._results = names
        self._display(names)
        self._status(f"Done — {len(names):,} names generated", SUCCESS)
        self._count_lbl.configure(text=f"{len(names):,} names")

    def _display(self, names):
        self._results_box.configure(state="normal")
        self._results_box.delete("1.0", "end")
        if names:
            # Display in 6-column grid
            cols = 6
            lines = []
            for i in range(0, len(names), cols):
                chunk = names[i:i+cols]
                lines.append("   ".join(f"{n:<8}" for n in chunk))
            self._results_box.insert("end", "\n".join(lines))
        else:
            self._results_box.insert("end", "\n  No names matched the current settings.")
        self._results_box.configure(state="disabled")

    def _on_search(self, *_):
        query = self._search_var.get().lower()
        if not self._results:
            return
        filtered = [n for n in self._results if query in n] if query else self._results
        self._display(filtered)
        self._count_lbl.configure(
            text=f"{len(filtered):,} / {len(self._results):,} names"
        )

    def _run_export(self):
        folder = filedialog.askdirectory(title="Select export folder")
        if not folder:
            return
        try:
            engine = self._make_generator()
            written, total = engine.export_grouped(folder=folder)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {total:,} names to {len(written)} file(s)\nin:\n{folder}"
            )
            self._status(f"Exported {total:,} names → {folder}", SUCCESS)
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            self._status(f"Export failed: {e}", "#c06060")

    def _save_txt(self):
        if not self._results:
            messagebox.showwarning("Nothing to Save", "Generate names first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            title="Save Results"
        )
        if not path:
            return
        with open(path, "w") as f:
            f.write("\n".join(self._results))
        self._status(f"Saved {len(self._results):,} names → {path}", SUCCESS)

    def _clear_results(self):
        self._results = []
        self._results_box.configure(state="normal")
        self._results_box.delete("1.0", "end")
        self._results_box.configure(state="disabled")
        self._count_lbl.configure(text="0 names")
        self._search_var.set("")
        self._status("Cleared", TEXT_MUTED)

    def _status(self, msg, color=TEXT_MUTED):
        self._status_lbl.configure(text=msg, text_color=color)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        import customtkinter
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
        import customtkinter as ctk

    app = CVCVApp()
    app.mainloop()