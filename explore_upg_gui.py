#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
explore_upg_gui.py — Interface Tkinter de l'explorateur de mises à jour SMEG+

Gestion de C:\SMEG\SMEG_PLUS_UPG. Reuse des outils de explore_upg.py :
    taille(), magie(), crc32_fichier(), remplacer(), DEFAULT_ROOT

Usage :
    python explore_upg_gui.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import winsound  # Windows : lecture audio directe depuis Tk
except ImportError:
    winsound = None

try:
    from explore_upg import DEFAULT_ROOT, taille, magie, crc32_fichier, remplacer
except ImportError:  # si on lance depuis un autre dossier
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from explore_upg import DEFAULT_ROOT, taille, magie, crc32_fichier, remplacer

IMG_FILTERS = [("Images", "*.png *.bmp *.jpg *.jpeg *.gif *.rcc"), ("Sons/Voix", "*.wav *.mp3 *.ogg"), ("Tous", "*")]


class ExplorerGUI:
    def __init__(self, root):
        self.root = root
        self.root_dir = DEFAULT_ROOT
        self.selected = None  # (path, is_dir)

        # --- barre d'outils
        top = tk.Frame(root, padx=4, pady=4)
        top.pack(fill="x")
        tk.Button(top, text="Rafraîchir", command=self.refresh).pack(side="left")
        tk.Button(top, text="Aller dans…", command=self.goto_dir).pack(side="left", padx=2)
        tk.Button(top, text="Remplacer l'élément sélectionné", command=self.cmd_replacer).pack(side="left", padx=2)
        tk.Button(top, text="CRC32 de la sélection", command=self.cmd_crc).pack(side="left", padx=2)

        self.entry = tk.Entry(top)
        self.entry.bind("<Return>", lambda e: self.find())
        self.entry.pack(side="left", fill="x", expand=True, padx=4)
        tk.Button(top, text="Rechercher", command=self.find).pack(side="left")

        # --- arborescence (gauche) + détails (droite)
        main = tk.Frame(root)
        main.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        main.columnconfigure(0, weight=1)   # colonne arbre
        main.columnconfigure(1, weight=1)   # colonne détails
        main.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(main, show="tree")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_select())
        self.tree.bind("<<TreeviewOpen>>", lambda e: self.on_open())
        self._loaded = set()  # dossiers déjà remplis
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.detail = tk.Frame(main, width=320)
        self.detail.pack_propagate(False)
        self.detail.grid(row=0, column=1, sticky="nsew")
        tk.Label(self.detail, text="Sélection", font=("", 10, "bold")).pack(anchor="w", pady=(0, 2))

        self.lab_path = tk.Label(self.detail, text="", justify="left", anchor="w", wraplength=300)
        self.lab_path.pack(fill="x")
        self.lab_taille = tk.Label(self.detail, text="")
        self.lab_taille.pack(fill="x")
        self.lab_type = tk.Label(self.detail, text="")
        self.lab_type.pack(fill="x")
        self.lab_crc = tk.Label(self.detail, text="")
        self.lab_crc.pack(fill="x")

        self.btn_sound = tk.Button(self.detail, text="🔊 Lire le son", command=self.cmd_sound,
                                   state="disabled")
        self.btn_sound.pack(anchor="w", pady=(4, 2))

        self.img_label = tk.Label(self.detail, width=300)
        self.img_label.pack(fill="x", pady=(6, 2))
        self._photo = None  # référence au PhotoImage (évite le GC)

        # --- barre d'état
        self.status = tk.Label(root, text=f"Racine : {self.root_dir}", anchor="w",
                               bg="#eee", relief="sunken")
        self.status.pack(side="bottom", fill="x")

        self.refresh()

    # ------------------------------------------------------------- tree
    def _populate(self, node_id, path):
        if path in self._loaded:
            return
        self._loaded.add(path)
        try:
            entries = sorted(os.scandir(path), key=lambda e: (e.is_file(), e.name))
        except OSError:
            return
        for e in entries:
            if e.is_dir():
                nid = self.tree.insert(node_id, "end", text=e.name + "/", values=(e.path,))
                self.tree.insert(nid, 0, text="…", values=(None,))  # placeholder
            else:
                self.tree.insert(node_id, "end", text=e.name, values=(e.path,))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._loaded = set()
        root_nid = self.tree.insert("", "end", text=os.path.basename(self.root_dir) or self.root_dir,
                                    values=(self.root_dir,))
        self._populate(root_nid, self.root_dir)
        self.status.config(text=f"Racine : {self.root_dir}")

    # ------------------------------------------------------------- events
    def on_open(self):
        """Double-clic sur un dossier : supprime le placeholder et charge les enfants."""
        item = self.tree.focus()
        if not item:
            return
        values = self.tree.item(item)["values"]
        if not values or not values[0] or not os.path.isdir(values[0]):
            return
        path = values[0]
        for child in self.tree.get_children(item):
            if self.tree.item(child)["text"].startswith("…"):
                self.tree.delete(child)
        self._populate(item, path)

    def on_select(self):
        sel = self.tree.selection()
        if not sel:
            self._clear_detail()
            return
        item = sel[0]
        values = self.tree.item(item)["values"]
        if not values or not values[0]:
            self._clear_detail()
            return
        path = values[0]
        is_dir = os.path.isdir(path)
        self.selected = (path, is_dir)
        if is_dir:
            self._clear_detail()
            return
        self.lab_path.config(text=path)
        self.lab_taille.config(text=f"Taille : {taille(os.path.getsize(path))}")
        self.lab_type.config(text=f"Type : {magie(path)}")
        self.lab_crc.config(text=f"CRC32 : 0x{crc32_fichier(path):08X}")
        self._preview(path)

    def _preview(self, path):
        """Affiche l'image sélectionnée (si PNG/BMP...) et active le bouton son."""
        photo = None
        try:
            photo = tk.PhotoImage(file=path)
        except tk.TclError:
            photo = None
        if photo is not None and photo.width() > 0:
            self._photo = photo
            self.img_label.config(image=photo)
        else:
            self._photo = None
            self.img_label.config(image="")
        is_sound = os.path.isfile(path) and path.lower().endswith(
            (".wav", ".mp3", ".ogg", ".aac", ".flac", ".au", ".amr"))
        self.btn_sound.config(state="normal" if (is_sound and winsound) else "disabled")

    def _clear_detail(self):
        for w in (self.lab_path, self.lab_taille, self.lab_type, self.lab_crc):
            w.config(text="")
        self.img_label.config(image="")
        self._photo = None
        self.btn_sound.config(state="disabled")

    # ------------------------------------------------------------- actions
    def goto_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.root_dir = d
            self.refresh()

    def find(self):
        pat = self.entry.get().strip().lower()
        if not pat:
            return
        hits = [p2 for p, _dirs, files in os.walk(self.root_dir) for f in files
                for p2 in [os.path.join(p, f)] if pat in p2.lower()]
        msg = "\n".join(f"  {os.path.relpath(p, self.root_dir)}" for p in sorted(hits)) or "  (aucun)"
        messagebox.showinfo("Résultats", f"{len(hits)} fichiers :\n{msg[:1500]}")

    def cmd_replacer(self):
        sel = self.selected
        if not sel or sel[1]:
            messagebox.showwarning("Sélection vide", "Sélectionnez un fichier dans l'arborescence.")
            return
        cible = sel[0]
        source = filedialog.askopenfilename(
            title=f"Choisir le nouvel élément pour\n{cible}",
            filetypes=IMG_FILTERS, initialdir=os.path.dirname(cible) or self.root_dir)
        if not source:
            return
        remplacer(cible, source)
        self.refresh()

    def cmd_crc(self):
        sel = self.selected
        if not sel or sel[1] or not os.path.isfile(sel[0]):
            messagebox.showwarning("Sélection vide", "Sélectionnez un fichier dans l'arborescence.")
            return
        messagebox.showinfo("CRC32", f"0x{crc32_fichier(sel[0]):08X}\n\n{sel[0]}")

    def cmd_sound(self):
        """Joue le son sélectionné avec winsound (WAV, non bloquant)."""
        sel = self.selected
        if not sel or sel[1] or winsound is None:
            return
        try:
            winsound.PlaySound(sel[0], winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Erreur son", f"Impossible de jouer : {e}")


def main():
    root = tk.Tk()
    root.title("Explorateur de mises à jour SMEG+")
    root.geometry("1000x650")
    app = ExplorerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
