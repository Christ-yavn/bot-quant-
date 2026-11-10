import os, shutil

repo_root = r"C:\Users\CHRIST\Desktop\IA\ANTIGRAVITY\projets\general project   quant bot deriv"
src_mql5 = os.path.join(repo_root, "src", "mql5")
archive_legacy = os.path.join(repo_root, "archive", "mql5_legacy")
mt5_experts = r"C:\Users\CHRIST\AppData\Roaming\MetaQuotes\Terminal\FB9A56D617EDDDFE29EE54EBEFFE96C1\MQL5\Experts"

os.makedirs(archive_legacy, exist_ok=True)

print("=== 1. NETTOYAGE DANS MT5 EXPERTS ===")
mt5_files_to_remove = [
    "DerivBoomCrashHFT_v830_Ultimate.ex5",
    "DerivBoomCrashHFT_v830_Ultimate.mq5",
    "DerivBoomCrashHFT_v830_Ultimate.mq5.compile.log",
    "Deriv_VolSqueeze_Breakout_EA_v3.compile.log",
    "Deriv_VolSqueeze_Breakout_EA_v3.mq5.compile.log",
    "metaeditor_compile.log"
]
for fname in mt5_files_to_remove:
    fpath = os.path.join(mt5_experts, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f"Supprimé de MT5 Experts: {fname}")

print("\n=== 2. NETTOYAGE ET CLASSEMENT DANS SRC/MQL5 DU REPO ===")
# Anciens fichiers .ex5 à supprimer de src/mql5
old_src_ex5 = [
    "DerivBoomCrashHFT_v6.ex5",
    "DerivBoomCrashHFT_v7.ex5",
    "DerivBoomCrashHFT_v8.ex5",
    "DerivBoomCrashHFT_v830_Ultimate.ex5",
    "Deriv_VolSqueeze_Breakout_EA.ex5",
    "OpenAuditedCharts.ex5"
]
for fname in old_src_ex5:
    fpath = os.path.join(src_mql5, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f"Supprimé ancien ex5: {fname}")

# Anciens fichiers sources .mq5 à classer dans archive/mql5_legacy
old_src_mq5 = [
    "DerivBoomCrashHFT_v6.mq5",
    "DerivBoomCrashHFT_v7.mq5",
    "DerivBoomCrashHFT_v8.mq5",
    "DerivBoomCrashHFT_v830_Ultimate.mq5",
    "Deriv_VolSqueeze_Breakout_EA.mq5",
    "OpenAuditedCharts.mq5"
]
for fname in old_src_mq5:
    src_path = os.path.join(src_mql5, fname)
    dst_path = os.path.join(archive_legacy, fname)
    if os.path.exists(src_path):
        shutil.move(src_path, dst_path)
        print(f"Classé dans archive: {fname} -> archive/mql5_legacy/{fname}")

print("\n=== 3. SUPPRESSION DES ANCIENS .EX5 DANS ARCHIVE ===")
# L'utilisateur a explicitement demandé de supprimer les anciens fichiers point exe / ex5
archive_ex5 = [
    "Deriv_VolSqueeze_Breakout_EA_v3_30.ex5",
    "Deriv_VolSqueeze_Breakout_EA_v3_31.ex5",
    "Deriv_VolSqueeze_Breakout_EA_v3_40.ex5",
    "Deriv_VolSqueeze_Breakout_EA_v3_50.ex5"
]
for fname in archive_ex5:
    fpath = os.path.join(archive_legacy, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f"Supprimé ancien ex5 archivé: {fname}")

print("\n=== 4. VÉRIFICATION DE L'ÉTAT FINAL ===")
print("Fichiers dans src/mql5/ :")
for f in os.listdir(src_mql5):
    print("  -", f)

print("\nFichiers dans MT5 Experts (racine) :")
for f in os.listdir(mt5_experts):
    if os.path.isfile(os.path.join(mt5_experts, f)):
        print("  -", f)

print("\nOpération de nettoyage et de classement terminée avec succès !")
