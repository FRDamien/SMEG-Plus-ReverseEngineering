#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
decompile_upg.py — Pipeline de décompression de la mise à jour SMEG+ en Python

Étapes (miroir des commandes PowerShell déjà utilisées) :
  1.  `gzip`  : fichiers système gzip (1f 8b) -> *.dec  (tarfile par la suite)
  2.  `bigquick` : AppBin/f_BigQuick.bin (header + octet 0x08 + zlib à 0x801) -> *.dec
  3.  `untar` : *.dec sont des archives tar -> extraction dans Data_base/
  4.  `strings` : extrait les chaînes intéressantes (TTS, voix, buffer, sonneries...)

Usage :
  python decompile_upg.py                  -> fait tout le pipeline
  python decompile_upg.py --gzip           -> étape 1 uniquement
  python decompile_upg.py --bigquick       -> étape 2 uniquement
  python decompile_upg.py --untar          -> étape 3 uniquement
  python decompile_upg.py --strings FILE   -> extrait les chaînes de FILE

Outils stdlib : gzip, zlib, tarfile, os, re, struct.
"""

import os
import re
import sys
import gzip
import zlib
import struct
import tarfile

DEFAULT_ROOT = r"C:\SMEG\SMEG_PLUS_UPG"

ZLIB_HEADER_OFFSET = 0x801   # octet 0x08 à 0x800, flux zlib (78 9C) à 0x801
DEFLATE_START = 0x803        # zlib = 2 octets d'en-tête + deflate


# ---------------------------------------------------------------- listing
def find_gzip(root):
    hits = []
    for dp, _dirs, files in os.walk(root):
        for fn in files:
            p = os.path.join(dp, fn)
            try:
                with open(p, "rb") as fh:
                    head = fh.read(2)
            except OSError:
                continue
            if head == b"\x1f\x8b" and not p.endswith(".dec"):
                hits.append(p)
    return sorted(hits)


def find_bigquick(root):
    hits = []
    for dp, _dirs, files in os.walk(root):
        for fn in files:
            if fn == "f_BigQuick.bin" and not os.path.exists(os.path.join(dp, fn) + ".dec"):
                p = os.path.join(dp, fn)
                try:
                    with open(p, "rb") as fh:
                        head = fh.read(2)
                except OSError:
                    continue
                # BigQuick : code PPC au début, octet 0x08 + zlib à 0x800/0x801
                if head[:4] in (b"\x94\x21\xFF\xE0", b"\x00\x00"):
                    hits.append(p)
                elif is_bigquick(p):
                    hits.append(p)
    return sorted(hits)


def is_bigquick(path):
    """Vérifie le flux zlib (78 9C etc.) à l'offset 0x801."""
    try:
        with open(path, "rb") as fh:
            fh.seek(ZLIB_HEADER_OFFSET)
            head = fh.read(4)
    except OSError:
        return False
    return head[:2] in (b"\x78\x01", b"\x78\x5e", b"\x78\x9c", b"\x78\xda")


# ---------------------------------------------------------------- steps
def step_gzip(root, verbose=True):
    """Étape 1 : décompresse les fichiers gzip -> *.dec"""
    for path in find_gzip(root):
        out = path + ".dec"
        if os.path.exists(out):
            continue
        try:
            with gzip.open(path, "rb") as fin, open(out, "wb") as fout:
                while True:
                    chunk = fin.read(1 << 20)
                    if not chunk:
                        break
                    fout.write(chunk)
            size = os.path.getsize(out)
            if verbose:
                print(f"[gzip] {os.path.basename(path):<32} -> {size/1e6:8.2f} Mo")
        except Exception as e:  # noqa: BLE001
            print(f"[gzip] ERREUR {path}: {e}")


def step_bigquick(root, verbose=True):
    """Étape 2 : décompresse les flux BigQuick (zlib) -> *.dec"""
    for path in find_bigquick(root):
        out = path + ".dec"
        if os.path.exists(out):
            continue
        try:
            with open(path, "rb") as fh:
                hdr = fh.read(8)
                if len(hdr) >= 8:
                    word0, word1 = struct.unpack(">ii", hdr[:8])
                else:
                    word0, word1 = 0, 0
                fh.seek(DEFLATE_START)
                d = zlib.decompressobj(-15)  # deflate brut (sans en-tête zlib)
                out_size = 0
                with open(out, "wb") as fout:
                    while not d.eof:
                        chunk = fh.read(1 << 20)
                        if not chunk:
                            break
                        data = d.decompress(chunk)
                        out_size += len(data)
                        fout.write(data)
            if verbose:
                print(f"[bigquick] {os.path.basename(path):<28} word1={word1 & 0xFFFFFFFF:#010x} -> "
                      f"{out_size/1e6:8.2f} Mo")
        except Exception as e:  # noqa: BLE001
            print(f"[bigquick] ERREUR {path}: {e}")


def step_untar(root, verbose=True):
    """Étape 3 : extrait les archives tar (*.dec) vers Data_base/ etc."""
    for dp, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith(".dec"):
                continue
            p = os.path.join(dp, fn)
            try:
                with tarfile.open(p, "r:*") as tf:
                    tf.extractall(path=dp)
                if verbose:
                    n = sum(1 for _ in tf)
                    print(f"[untar] {fn:<32} -> {os.path.relpath(dp, root)}")
            except (tarfile.TarError, OSError):
                pass  # pas une archive tar, on continue


# ---------------------------------------------------------------- strings
def extract_strings(path, minlen=6, patterns=None, limit=None):
    """Extrait les chaînes imprimables avec leurs offsets (fichiers binaires)."""
    pat = re.compile(rb"[\x20-\x7e]{%d,}" % minlen)
    result = []
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return result
    for m in pat.finditer(data):
        s = m.group().decode("latin-1")
        if patterns is None or any(pat.search(s) for pat in patterns):
            result.append((m.start(), s))
            if limit and len(result) >= limit:
                break
    return result


def step_strings(path, patterns=None, limit=60):
    """Étape 4 : affiche les chaînes intéressantes (TTS, voix, buffer...)."""
    if not os.path.isfile(path):
        print(f"[!] introuvable : {path}")
        return
    size = os.path.getsize(path)
    print(f"[strings] {path} ({size/1e6:.2f} Mo)")
    hits = extract_strings(path, minlen=6, patterns=patterns, limit=limit)
    print(f"  {len(hits)} chaînes affichées (limite {limit}) :")
    for off, s in hits:
        print(f"  0x{off:08X} : {s[:120]}")


# ---------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    root = DEFAULT_ROOT
    if args and os.path.isdir(args[0]):
        root = args[0]

    do_gzip = do_bq = do_untar = do_strings = False
    files_strings = []
    for a in args:
        if a == "--gzip":
            do_gzip = True
        elif a == "--bigquick":
            do_bq = True
        elif a == "--untar":
            do_untar = True
        elif a == "--strings":
            do_strings = True
        elif a.startswith("--strings="):
            do_strings = True
            files_strings.append(a.split("=", 1)[1])

    if not any((do_gzip, do_bq, do_untar, do_strings)):
        do_gzip = do_bq = do_untar = do_strings = True

    print(f"Racine : {root}")
    if do_gzip:
        step_gzip(root)
    if do_bq:
        step_bigquick(root)
    if do_untar:
        step_untar(root)
    if do_strings:
        pats = [re.compile(p, re.IGNORECASE) for p in
                (r"tts|voice|ltts7|delay|buffer|fifo|a2dp|bluetooth|amalia|jitter|crc32",
                 r"symbol|_init|_fini|error", )]
        for f in files_strings:
            step_strings(f, patterns=pats)
        if not files_strings:
            # échantillons des fichiers BigQuick déjà décompressés
            for rel in (r"AUDIO_BT\AppBin\f_BigQuick.bin.dec",
                        r"AUDIO_BT_256\AppBin\f_BigQuick.bin.dec"):
                step_strings(os.path.join(root, rel), patterns=pats, limit=40)


if __name__ == "__main__":
    main()
