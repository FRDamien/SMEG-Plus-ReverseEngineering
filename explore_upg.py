#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
explore_upg.py — Outil d'exploration et d'edition des fichiers de mise a jour SMEG+

Gestion de C:\SMEG\SMEG_PLUS_UPG (extraction de SMEG_PLUS_UPG.zip).
Explorateur interactif + outils pour echanger des elements comme les
images et les sonneries.

Usage :
  python explore_upg.py                          -> mode explorateur interactif
  python explore_upg.py tree                     -> arborescence complète
  python explore_upg.py find  <ext>              -> fichiers par extension (png wav ttsconf ...)
  python explore_upg.py info <fichier>           -> infos + magie de l'en-tete
  python explore_upg.py repl <fichier> <source>  -> remplace un fichier (fait un .bak)
  python explore_upg.py crc  <fichier>           -> CRC32 d'un fichier

Outils stdlib uniquement (zlib, os, shutil).
"""

import os
import sys
import zlib
import shutil

DEFAULT_ROOT = r"C:\SMEG\SMEG_PLUS_UPG"


# ---------------------------------------------------------------- utils
def taille(n):
    n = float(n)
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if n < 1024 or unit == "To":
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} To"


def magie(path):
    """Décrit ce que contient le fichier (magic : gzip, PNG, WAV, PPC...)."""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return "[!] inacessible"
    if len(head) < 4:
        return "fichier vide"
    if head[:2] == b"\x1f\x8b":
        return "gzip (1f 8b)  [a decompresser]"
    if head[:2] in (b"\x78\x01", b"\x78\x5e", b"\x78\x9c", b"\x78\xda"):
        return "zlib (" + head[:2].hex() + ")"
    if head[:4] == b"\x89PNG":
        return "PNG image"
    if head[:2] == b"BM":
        return "BMP image"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "WAV sonnerie"
    if head[:4] == b"PK\x03\x04":
        return "zip"
    if head[:4] == b"ustar":
        return "archive tar"
    if head[:4] == b"SQLite format 3":
        return "base de donnees SQLite"
    if head[:6] == b"94 21 FF":
        return "code PowerPC big-endian (PPC)"
    return "donnees binaires " + head[:8].hex()


def crc32_fichier(path):
    h = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h = zlib.crc32(chunk, h)
    return h & 0xFFFFFFFF


# ---------------------------------------------------------------- listing
def afficher_dir(d):
    print(f"\n== {d}")
    try:
        entries = sorted(os.scandir(d), key=lambda e: e.name)
    except OSError as e:
        print("  [!] ", e)
        return
    for e in entries:
        try:
            if e.is_dir():
                print(f"  [d] {e.name}/")
            else:
                print(f"  [f] {e.name:<32} {taille(e.stat().st_size):>12}  {magie(e.path)}")
        except OSError:
            pass


def arborescence(root):
    print(f"Arbre de {root}\n")
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        print("  " * depth + os.path.basename(dirpath) + "/")
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            print("  " * (depth + 1) + f"{fn:<32} {taille(os.path.getsize(p))}")
        dirnames.sort()


def find(root, pat):
    print(f"Fichiers correspondant a '*{pat}*' sous {root}\n")
    hits = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if pat.lower() in fn.lower():
                p = os.path.join(dirpath, fn)
                hits.append(p)
    for p in sorted(hits):
        print(f"  {os.path.relpath(p, root):<64} {taille(os.path.getsize(p))}")


def info_fichier(path):
    if not os.path.isfile(path):
        print("[!] introuvable :", path)
        return
    print(f"{path}")
    print(f"  Taille : {taille(os.path.getsize(path))}")
    print(f"  Type   : {magie(path)}")


# ---------------------------------------------------------------- edition
def remplacer(cible, source):
    if not os.path.isfile(cible):
        print("[!] fichier cible introuvable :", cible)
        return
    if not os.path.isfile(source):
        print("[!] fichier source introuvable :", source)
        return
    backup = cible + ".bak"
    shutil.copy2(cible, backup)
    shutil.copy2(source, cible)
    print(f"[*] {cible}\n    remplace par : {source}")
    print(f"[*] backup : {backup}")
    print("[i] rappel : si le fichier est dans BSP/, recalcule les 5 CRCs de")
    print("    la chaîne (analyse claude.txt l.83-95) : dbsystem.bin(o.36),")
    print("    vxWorks.bin.inf, flasher.inf, flasher.crc")


# ---------------------------------------------------------------- repl
def explore(root=DEFAULT_ROOT):
    print(f"Explorateur de mise a jour — {root}")
    print("commandes : cd <dir> | ls [dir] | find <ext> | info <f> | repl <cible> <src> | quit")
    afficher_dir(root)
    while True:
        try:
            line = input("\nsmup> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir")
            return
        if not line:
            continue
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd in ("q", "quit", "exit"):
            return
        elif cmd == "cd":
            d = arg or root
            if os.path.isdir(d):
                afficher_dir(d)
            else:
                print("[!] dossier introuvable :", d)
        elif cmd == "ls":
            afficher_dir(arg if arg and os.path.isdir(arg) else root)
        elif cmd == "find":
            if arg:
                find(root, arg)
            else:
                print("usage: find <ext>  (ex: find png)")
        elif cmd == "info":
            if arg and os.path.isfile(arg):
                info_fichier(arg)
            else:
                print("usage: info <fichier>")
        elif cmd == "repl":
            a = arg.split(None, 1)
            if len(a) == 2:
                remplacer(a[0], a[1])
            else:
                print("usage: repl <cible> <source>")
        elif cmd == "crc":
            if arg and os.path.isfile(arg):
                print(f"CRC32 de {arg} : 0x{crc32_fichier(arg):08X}")
            else:
                print("usage: crc <fichier>")
        else:
            print(f"[?] commande inconnue : {cmd}")


# ---------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    root = DEFAULT_ROOT
    if args and os.path.isdir(args[0]):
        root = args[0]

    if not args or args[0] in ("-i", "--interactive"):
        explore(root)
        return

    cmd = args[0]
    if cmd == "tree":
        arborescence(root)
    elif cmd == "find":
        find(root, args[1] if len(args) > 1 else "")
    elif cmd == "info":
        info_fichier(args[1] if len(args) > 1 else root)
    elif cmd == "repl":
        if len(args) >= 3:
            remplacer(args[1], args[2])
        else:
            print("usage: repl <cible> <source>")
    elif cmd == "crc":
        if len(args) >= 2 and os.path.isfile(args[1]):
            print(f"CRC32 de {args[1]} : 0x{crc32_fichier(args[1]):08X}")
        else:
            print("usage: crc <fichier>")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
