"""
patch_render_fix.py  —  Bir kerelik çalıştır.
Fragmentia-main klasöründeyken:  python patch_render_fix.py
"""
import sys

TARGET = "victorian_mansion.py"

OLD = """        fade.draw(game_surf)

        # ── ZOOM BLIT: game_surf → screen ─────────────────────
        if abs(_zoom-1.0) < 0.005:
            screen.blit(game_surf,(0,0))
        else:
            fcx = int(_zoom_focus_x - cx)
            fcy = int(_zoom_focus_y - cy)
            vw = int(SW / _zoom)
            vh = int(SH / _zoom)
            # vw/vh game_surf sınırını aşamasın
            vw = min(vw, SW)
            vh = min(vh, SH)
            src_x = clamp(fcx - vw//2, 0, SW - vw)
            src_y = clamp(fcy - vh//2, 0, SH - vh)
            sub = game_surf.subsurface((src_x, src_y, vw, vh))
            pygame.transform.scale(sub, (SW, SH), screen)"""

NEW = """        fade.draw(game_surf)

        # ── ZOOM BLIT: game_surf → screen ─────────────────────
        # screen.get_size() kullanılır; FRAGMENTIA fullscreen modunda
        # SW/SH != screen boyutu olabileceği için sabit tuple kullanılmaz.
        _scr_w, _scr_h = screen.get_size()
        if abs(_zoom-1.0) < 0.005:
            if (_scr_w, _scr_h) == (SW, SH):
                screen.blit(game_surf,(0,0))
            else:
                pygame.transform.scale(game_surf, (_scr_w, _scr_h), screen)
        else:
            fcx = int(_zoom_focus_x - cx)
            fcy = int(_zoom_focus_y - cy)
            vw = int(SW / _zoom)
            vh = int(SH / _zoom)
            vw = min(vw, SW)
            vh = min(vh, SH)
            src_x = clamp(fcx - vw//2, 0, SW - vw)
            src_y = clamp(fcy - vh//2, 0, SH - vh)
            sub = game_surf.subsurface((src_x, src_y, vw, vh))
            pygame.transform.scale(sub, (_scr_w, _scr_h), screen)"""

with open(TARGET, encoding="utf-8") as f:
    src = f.read()

if "_scr_w, _scr_h = screen.get_size()" in src:
    print("Zaten uygulanmış, bir şey değiştirilmedi.")
    sys.exit(0)

if OLD not in src:
    print("HATA: Hedef blok bulunamadı — victorian_mansion.py farklı bir versiyonda olabilir.")
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

print("✓ Render düzeltmesi uygulandı! Artık 'python main.py' çalıştırabilirsin.")