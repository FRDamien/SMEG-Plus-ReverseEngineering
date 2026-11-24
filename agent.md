# agent.md — SMEG+ Package / Reverse Engineering (C4 Picasso, SMEG 5.43.A.R2)

Package ZIP d'origine : `SMEG_PLUS_UPG.zip` (≈1,07 Go). Extraction dans `C:\SMEG\SMEG_PLUS_UPG\`.

## 1. Structure du package (de l'archive ZIP)

| Chemin | Taille approximative | Rôle |
|---|---|---|
| `BSP/SMEG_PLUS_512/` & `BSP/SMEG_PLUS_256/` | | |
| `…/vxWorks.bin` | 6,713,360 / 6,713,840 | BSP principal (VxWorks 6.7 PowerPC) |
| `…/dbsystem.bin` | 40 | Header descripteur image |
| `…/flasher.inf`, `…/flasher.crc` | 125 / 4 | Manifeste + CRC |
| `BSP_SMEG_PLUS_256_ctrl.bin` / `BSP_SMEG_PLUS_512_ctrl.bin` | 1636 | Ctrl bins |
| `ctrl.bin` (5068), `flasher.inf` (125), `flasher.crc` (4) | | |
| `contract.dat` (29696) | | DRM |
| `upgrade.out`, `upgrade_256.out`, `upgrade_lib.out`, `UpgPlugin.out` + `.inf` | | Apps de mise à jour |
| `AUDIO_BT/` (system.bin 24 703 097, system_data.bin 74 210, system_ctrl.bin 222 868, smeg.inf 89, AppBin/f_BigQuick.bin 13 759 869) | | |
| `AUDIO_BT_256/` (system.bin 8 867 403, system_data.bin 74 210, AppBin/f_BigQuick.bin 13 759 747) | | |
| `HARMONY/BigHarmony_1..5/BIG_HARMONY.bin` | 26 443 776 / 28 008 448 / 27 152 384 / 6 612 992 / 6 447 104 | Images d'harmony |
| `NAV/` (voir suite) | | |
| `RENESAS/FPComSMEG.mot` (368 814) | | Fichier app |
| `USERGUIDE/` | | Guide utilisateur |

## 2. Formats clés

### BSP — chaîne de CRC (cadre de modification fiable)
5 CRC cascades à recompiler si on modifie (déjà dans `analyse claude.txt` l. 83-95) :
`vxWorks.bin → dbsystem.bin (octet 8, auto-CRC à l'offset 36) → flasher.inf → flasher.crc`.

### system.bin / system_data.bin (AUDIO_BT, AUDIO_BT_256, NAV)
Gzip (`1f 8b 08`) → tar extrait avec `tar.exe`. Décompressés en `*.dec` :
- `AUDIO_BT_256\system.bin.dec` (12,9 Mo), `AUDIO_BT\system.bin.dec` (33,3 Mo), `NAV\system.bin.dec` (33,6 Mo)
- Contenu (tar) : `Data_base/` (smeg.inf, media.inf, boardfs/graphics/sqlite/TMP)

### smeg.inf (dans `Data_base/`, tars)
- `VER: SMEG5.43.A.R2`, `GUI_VER: 32.00`
- `BSP_CRC32: 1931141747` (256) / `1898196070` (AUDIO_BT, NAV)
- `BIGQUICK_CRC32: -1014972455` / `972925749` / `2003021792`

### Format BigQuick (`AppBin\f_BigQuick.bin` → `.dec`)
- Décompression : zlib standard (octet 0x08 à 0x801), PowerShell `DeflateStream` à 0x803 → `f_BigQuick.bin.dec` ≈ 30,93 Mo (AUDIO_BT et AUDIO_BT_256).
- Début du code (PPC) identique : `94 21 FF E0 7C 08 02 A6 93 41 00 08 3F 40 01 04 90 01 00 24 38 1A 40 08 7C 09 03 A6 93 61 00 0C` (= prologue vxWorks typique).
- Chaînes notables (offset hex dans le `.dec`) :
  - `0x018D934C` : `download_allsymbol`
  - `0x018D9378` / `0x01965B74` : `/SYSTEM/Application/PKG/abs_symbols_light.txt.gz`, `abs_symbols_base.txt.gz`, `abs_symbols.txt.gz` (fichiers de symboles ! présents dans `Application/PKG/`)
  - Symboles : `Symbol '%c' [%s] added at @=%p rtn = %d group = %d`, `Symbol TEXT/DATA/BSS [%s] rejected…`, `dlsym : Symbol '%s' not found !`
  - Décompression interne : `Error to uncompress`, `Error Invalid uncompress size = %d`, `dlfcn_gz_uncompress: res = %d dest_size = %d`
  - Misc : `dyn buffer`, `No Buffer Allocated`, `Impossible translating from RDS to TTS`, `BTLInit:C_OBJ_PTR_Table:Open ret ERROR`, `g_ssm_boot_time_b/e_download_allsymbol`, `C_SSM_BOOT_MONITOR::PrintBuffer`, `Delayed startup in progress…`
- Fichiers de symboles disponibles : `Application/PKG/abs_symbols.txt.gz` (82 691), `abs_symbols_base.txt.gz` (1 091 397), `abs_symbols_light.txt.gz` (337), `abs_symbols_nav.txt.gz` (9 238), `symbols_bsp.txt.gz` (194 281) — pour Ghidra.

### TTS — `NAV/SD_DIR_TTS.bin.dec` (885 Mo)
Catalogue de voix (26 939 chaînes contenant "TTS/voice/LTTS7") :
```xml
<voice name="Amalia-A" mothertongue="PortuguesePt" basename="Amalia">
    <library name="LTTS7${basename}" entrypoint="${basename}" />
    <info description="Portuguese female voice" age="37" gender="female" basepitch="150" ... />
    <flavour codec="LTTS7CodecMsx" frequency="16000" bitrate="32800" rank="10" name="…" />
</voice>
```
Voix : Amalia-A, Anna-B, Bernard-A, Carmen-A, Chinese, Croatian, CroatianFemale-B, CroatianMale-B…

### NAV — images, sonneries, détails
- Images : `AVR_IMG1..8.png`, radio logos (`DK_TheVoice.png` 14 757, …), PNG par pays (FR_*, AT_*, BE_*, CH_*, CZ_*, …), GUI (`pgen_*.png`, `background_*.css`).
- Sonneries (WAV) : `NAV/ring_tones/` — `ring1RT.wav` (157 018), `ring2RT.wav` (315 816), `ring3RT.wav` (316 264), `ring4RT.wav` (156 830), `ring5RT.wav` (313 838), `busyRT.wav` (396 206), `errorRT.wav`, `koRT.wav`, `okRT.wav`; plus dans `NAV/` : `MM_HoldOn_*.wav` (8 kHz), `Welcome.wav`, `Abandon.wav`…
- Système nav : `sd_dir.bin` (4 009 353), `SD_DIR_desc.bin`, `system.bin` (24 902 910), `system_data.bin` (74 210), `f_BigQuick.bin` (16 371 616), `DB_*` sqlite, GUI XML.
- Cheats : `libcheatcode_*.out` + `.txt.gz` (BT, BTINFO, BTADC, BTSTARTER, AUDIOINFO, MIRE, SYSMON, TUNERINFO…) dans `Application/CCOD/`.

### Décompression complète en Python (`decompile_upg.py`) — terminé
- Pipeline : `python decompile_upg.py` (stdlib : gzip, zlib, tarfile, os, re, struct).
- Étapes : `[gzip]` (fichiers `*.txt.gz` → `.dec`), `[bigquick]` (`f_BigQuick.bin` → `.dec`), `[untar]` (`*.dec` → `Data_base/`), `[strings]` (chaînes avec offsets sur `f_BigQuick.bin.dec`).
- Flags : `--gzip`, `--bigquick`, `--untar`, `--strings[=fichier]`, racine par défaut `C:\SMEG\SMEG_PLUS_UPG`.
- Nouveautés découvertes : `Application/PKG/abs_symbols_base.txt.gz` (≈5,9 Mo décompressé), `abs_symbols.txt.gz`, `abs_symbols_light.txt.gz`, `abs_symbols_nav.txt.gz` (AUDIO_BT_256), `symbols_bsp.txt.gz` ; `NAV/AppBin/f_BigQuick.bin.dec` (39,86 MB — app NAV, offsets : 0x01E77208 `download_allsymbol`) ; `NAV/Application/CCOD/libcheatcode_{GPSINFO,MAPSPEED,SIMSPEED}.out(.txt.gz)` décompressés par `[gzip]`.

## 3. À faire pour un patch (nouvelle image / sonnerie)

1. Modifier la ressource cible (ex. PNG dans `NAV/…` ou WAV dans `sd_dir.bin.dec` — à repackager).
2. Recalculer les CRC32 (`.inf`, `*_ctrl.bin`) et `flasher.crc` — les tables sont connues (voir chaîne 5 CRC du txt l. 83-95).
3. Reflasher le ZIP (repack dans la structure de `SMEG_PLUS_UPG.zip`).
4. Si en BigQuick : recompresser le flux zlib et mettre à jour `word[1]` dans le header.

## 4. Outils disponibles
PowerShell 5.x, `Expand-Archive`, `System.IO.Compression` (GZipStream, DeflateStream), `tar.exe`. À vérifier : python3, ghidra, objdump.

## 5. Ghidra — installé (≈544 Mo)
- Installation : `C:\opt\Ghidra\ghidra_12.2_PUBLIC` — lancer `ghidraRun.bat`
- Java 25 (Temurin) mis à `C:\opt\jdk-25\jdk-25.0.5.1+2\bin` → `java` (25.0.5.1) maintenant sur PATH
- Importer : `C:\SMEG\SMEG_PLUS_UPG\AUDIO_BT\AppBin\f_BigQuick.bin.dec` (32,43 Mo) et `C:\SMEG\SMEG_PLUS_UPG\NAV\AppBin\f_BigQuick.bin.dec` (39,86 Mo) — langage Ghidra `PowerPC:BE:32`

## 6. Repos thématiques (prior art)
- **KRoperUK/smeg-plus-patches** — outils : `tools/patch_smeg.py` (patchs app + cascade CRC), `tools/patch_media.py`, `tools/build_package.py`, `tools/ppcemu.py`, `tools/ppcdis.py`/`xref.py`/`callers.py`, `tools/symdiff.py`, `tools/fingerprint.py`, `tools/ringtones.py`, `tools/mkelf.py`, `tools/elfsyms.py`. Adresses v5.43.A.R2 (ex. `IsAUXSRCAvailable()` = 0x02247858). Docs : docs/PATCHES.md, docs/TOOLCHAIN.md.
- **bousqi/SMEG_PLUS** — ghidra/, UPGRADE.md, VXWORKS.md, memory map (vxWorks @ 0x00200000, f_BigQuick @ 0x01000000).
