"""
patch_victorian.py  —  Bir kerelik çalıştır, sonra silebilirsin.
Kullanım:  python patch_victorian.py
"""
import os, sys

TARGET = "victorian_mansion.py"
if not os.path.exists(TARGET):
    print(f"HATA: '{TARGET}' bulunamadı. Bu scripti Fragmentia-main klasöründe çalıştır.")
    sys.exit(1)

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

# ── Zaten patch uygulandıysa tekrar uygulama ─────────────────────────────────
if "def run_scene" in src:
    print("Zaten patch uygulanmış, bir şey değiştirilmedi.")
    sys.exit(0)

# ── 1. Patch: pygame.quit()+sys.exit() satırını standalone kontrolüyle değiştir
OLD_EXIT = "    gc.enable(); gc.collect(); pygame.quit(); sys.exit()"
NEW_EXIT = (
    "    # --- FRAGMENTIA PATCH: standalone modda kapat, sub-scene modda geri dön ---\n"
    "    if globals().get('_vm_standalone', True):\n"
    "        gc.enable(); gc.collect(); pygame.quit(); sys.exit()\n"
    "    else:\n"
    "        gc.collect(); gc.disable()\n"
    "        return"
)

if OLD_EXIT not in src:
    # Farklı biçimde yazılmışsa satırı bul
    import re
    pattern = r"    gc\.enable\(\).*?pygame\.quit\(\).*?sys\.exit\(\)"
    match = re.search(pattern, src)
    if match:
        OLD_EXIT = match.group(0)
    else:
        print("UYARI: 'pygame.quit()+sys.exit()' satırı bulunamadı — patch kısmen uygulanacak.")
        OLD_EXIT = None

if OLD_EXIT:
    src = src.replace(OLD_EXIT, NEW_EXIT, 1)

# ── 2. Patch: F11 tuşunu event döngüsüne ekle ────────────────────────────────
OLD_F12 = "                if ev.key==pygame.K_F12: debug=not debug"
NEW_F12 = (
    "                if ev.key==pygame.K_F12: debug=not debug\n"
    "                if ev.key==pygame.K_F11: running=False  # FRAGMENTIA'ya dön"
)
if OLD_F12 in src:
    src = src.replace(OLD_F12, NEW_F12, 1)

# ── 3. Patch: run_scene() + globals dosyanın sonuna ekle ─────────────────────
APPEND = '''

# ═══════════════════════════════════════════════════════════════════════════════
#  FRAGMENTIA ENTEGRASYON PATCH  (patch_victorian.py tarafından eklendi)
# ═══════════════════════════════════════════════════════════════════════════════

_vm_standalone = True   # True → bağımsız, False → FRAGMENTIA sub-scene modu


def run_scene(ext_screen=None, ext_clock=None):
    """
    FRAGMENTIA F11 entry point.
    ext_screen / ext_clock verilirse FRAGMENTIA'nın mevcut yüzeylerini kullanır.
    Verilmezse bağımsız (standalone) modda çalışır.
    """
    global screen, clock, game_surf, _zoom, F_SM, F_MD, F_IT, _ft, _vm_standalone

    gc.collect()
    gc.disable()

    if ext_screen is not None:
        _vm_standalone = False
        screen     = ext_screen
        clock      = ext_clock
    else:
        _vm_standalone = True

    # Render yüzeyini ve fontları yenile
    game_surf = pygame.Surface((SW, SH))
    _zoom     = 1.0
    F_SM = pygame.font.SysFont("georgia", 14)
    F_MD = pygame.font.SysFont("georgia", 19, bold=True)
    F_IT = pygame.font.SysFont("georgia", 16, italic=True)

    main()   # ESC veya F11 → running=False → main() biter → buraya döner
'''

src = src + APPEND

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

print("✓ Patch başarıyla uygulandı!")
print("  Artık 'python main.py' çalıştırabilirsin.")
print("  Oyun içinde F11 → Ashford Manor, ESC/F11 → FRAGMENTIA'ya dön.")