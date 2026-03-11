# =============================================================================
# AUTO-GENERATED — main.py bölünmesinden üretilmiştir.
# Tüm paylaşılan değişkenlere m. (main modülü) üzerinden erişilir.
# =============================================================================
import pygame
import sys
import random
import math
import os
import json
import gc

from settings import *
from settings import STEALTH_KILL_REACH_PX, STEALTH_KILL_KARMA
from game_config import (EASY_MODE_LEVELS, BULLET_SPEED,
                         CURSED_PURPLE, GLITCH_BLACK, CURSED_RED)
from settings import (COST_DASH, COST_SLAM, COST_HEAVY, COST_LIGHT,
                      PLAYER_MAX_STAMINA, STAMINA_REGEN_RATE, STAMINA_REGEN_DELAY,
                      REVOLVER_MAX_BULLETS, REVOLVER_DAMAGE, REVOLVER_COOLDOWN,
                      REVOLVER_RELOAD_TIME, PLAYER_BULLET_SPEED)
from entities import (PlayerProjectile, WeaponChest, AmmoPickup, HealthOrb,
                      CursedEnemy, DroneEnemy, TankEnemy)
from local_bosses import NexusBoss, AresBoss, VasilBoss, EnemyBullet
from boss_entities import VasilCompanion
from vfx import (LightningBolt, FlameSpark, GhostTrail, SpeedLine, Shockwave,
                 EnergyOrb, ParticleExplosion, ScreenFlash, SavedSoul)
from utils import (load_sound_asset, draw_text, draw_animated_player,
                   wrap_text, draw_text_with_shadow, get_silent_sound,
                   audio_manager, generate_ambient_fallback, generate_calm_ambient)
from animations import TrailEffect
from drawing_utils import (rotate_point, draw_legendary_revolver, draw_smg_placeholder,
                           draw_cinematic_overlay, draw_background_hero,
                           get_weapon_muzzle_point, draw_background_boss_silhouette,
                           draw_npc_chat)
from ui_system import render_ui
from story_system import StoryManager
from cutscene import AICutscene, IntroCutscene
from combat_system import ComboSystem, BeatArenaManager, PlayerHealth, CombatHUD
from weapon_system import Revolver, SMG, Shotgun, create_weapon
from inventory_manager import inventory_manager
from stealth_system import stealth_system
from save_system import SaveManager
from level_init import (init_game, init_limbo, init_redemption_mode,
                        init_genocide_mode, start_npc_conversation,
                        start_loading_sequence, add_new_platform,
                        trigger_guardian_interruption)
from auxiliary_systems import (RestAreaManager, NexusHub, PhilosophicalCore,
                                RealityShiftSystem, TimeLayerSystem,
                                CombatPhilosophySystem, LivingSoundtrack,
                                EndlessFragmentia, ReactiveFragmentia, LivingNPC,
                                FragmentiaDistrict, PhilosophicalTitan, WarpLine)

_m = None

def register_main_module(main_module):
    """main.py modül referansını kaydet."""
    global _m
    _m = main_module

def render_frame():
    """Render pipeline: arkaplan → entityler → oyuncu → UI"""
    m = _m
    if m.GAME_STATE in ['MENU', 'SETTINGS', 'LOADING', 'LEVEL_SELECT', 'ENDLESS_SELECT']:
        m.game_canvas.fill(DARK_BLUE)
        for s in m.stars:
            s.draw(m.game_canvas)
            s.update(0.5)
        m.active_ui_elements = render_ui(m.game_canvas, m.GAME_STATE, ui_data, m.mouse_pos)
    else:
        # ════════════════════════════════════════════════════════════════
        # ÇİZİM SIRASI — Bu sıra kesinlikle değiştirilmemeli.
        # Bir katman bir öncekinin üstüne biter; en son çizilen en üstte
        # görünür.
        #
        #  1. game_canvas.fill()          → Ekranı temizle
        #  2. active_background.draw()    → Uzak parallax arkaplan
        #  3. stars                       → Yıldızlar
        #  4. boss silhouette             → Arkaplan boss gölgesi
        #  5. platforms                   → Platformlar
        #  6. enemies / boss              → Düşmanlar
        #  7. npcs                        → NPC figürleri
        #  8. OYUNCU                      → Karakter (sprite/fallback)
        #  9. vasil_companion             → Yardımcı figür
        # 10. vfx_surface blit            → Partiküller / trail (oyuncunun
        #                                   üstünde değil — ÖNÜNDE)
        # 11. UI / HUD                    → Skor, karma, timer
        # 12. NPC chat / cinematic        → Diyalog kutuları
        # ════════════════════════════════════════════════════════════════

        # ── Kamera sarsma ofseti ─────────────────────────────────────
        try:
            m.anim_params = m.character_animator.get_draw_params()
        except:
            m.anim_params = {}
        m.anim_offset = m.anim_params.get('screen_shake_offset', (0, 0))
        m.global_offset = (
            random.randint(-m.screen_shake, m.screen_shake),
            random.randint(-m.screen_shake, m.screen_shake)
        ) if m.screen_shake > 0 else (0, 0)
        m.render_offset = (
            m.global_offset[0] + int(m.anim_offset[0]),
            m.global_offset[1] + int(m.anim_offset[1])
        )

        # ── Malikane kamera ofseti — platformları ve düşmanları kaydır ──
        # manor_stealth bölümünde tüm dünya nesneleri manor_camera_offset_x/y
        # kadar kaydırılarak çizilir; oyuncu ise ekran ortasında sabit görünür.
        m._manor_draw_ox = -m.manor_camera_offset_x  # platform blit ofseti (negatif = sola kaydır)
        m._manor_draw_oy = -m.manor_camera_offset_y  # dikey ofset (negatif = yukarı kaydır)
        m._manor_render_offset = (
            m.render_offset[0] + m._manor_draw_ox,
            m.render_offset[1] + m._manor_draw_oy
        )

        # Render pipeline boyunca güvenli erişim için lvl_config garantisi
        lvl_config = m.EASY_MODE_LEVELS.get(m.current_level_idx, m.EASY_MODE_LEVELS[1])

        # ── 1. Ekranı temizle ────────────────────────────────────────
        if m.reality_shifter.current_reality != 0:
            reality_effect = m.reality_shifter.get_visual_effect()
            m.game_canvas.fill(reality_effect.get('bg_color', m.CURRENT_THEME["bg_color"]))
        elif m.time_layer.current_era != 'present':
            era_data = m.time_layer.eras[m.time_layer.current_era]
            m.game_canvas.fill(era_data.get('bg_color', m.CURRENT_THEME["bg_color"]))
        else:
            m.game_canvas.fill(m.CURRENT_THEME["bg_color"])

        # ── 2. Uzak parallax arkaplan ────────────────────────────────
        if m.active_background:
            m.active_background.draw(m.game_canvas)

        # ── 3. Yıldızlar ─────────────────────────────────────────────
        for s in m.stars:
            s.draw(m.game_canvas)

        # ── 4. Boss arkaplan gölgesi ─────────────────────────────────
        if m.current_level_idx in [10, 30]:
            current_k = m.save_manager.get_karma()
            draw_background_boss_silhouette(m.game_canvas, current_k, LOGICAL_WIDTH, LOGICAL_HEIGHT)

        # ── VFX yüzeyini sıfırla (henüz game_canvas'a bitmeyecek) ───
        m.vfx_surface.fill((0, 0, 0, 0))

        # ── 5. Platformlar ───────────────────────────────────────────
        for p in m.all_platforms:
            # Malikane bölümünde kamera oyuncuyu 2D takip eder;
            # platformlar X ve Y ofseti uygulanarak çizilir.
            _p_draw_rect = p.rect.move(m._manor_draw_ox, m._manor_draw_oy)
            _old_rect = p.rect
            p.rect = _p_draw_rect
            p.draw(m.game_canvas, m.CURRENT_THEME)
            p.rect = _old_rect

        # ── 6. Düşmanlar / Boss ──────────────────────────────────────
        m.boss_manager_system.draw(m.game_canvas)
        for e in m.all_enemies:
            # Malikane kamera ofseti (X ve Y) uygulanır
            if (m._manor_draw_ox != 0 or m._manor_draw_oy != 0) and hasattr(e, 'rect'):
                _e_ox, _e_oy = e.rect.x, e.rect.y
                e.rect.x += m._manor_draw_ox
                e.rect.y += m._manor_draw_oy
                e.draw(m.game_canvas, theme=m.CURRENT_THEME)
                e.rect.x = _e_ox
                e.rect.y = _e_oy
            else:
                e.draw(m.game_canvas, theme=m.CURRENT_THEME)

        # ── 6b. Beat Arena Düşmanları + HUD ──────────────────────────
        if lvl_config.get('type') == 'beat_arena':
            m.beat_arena.draw(m.game_canvas)

        # ── Can Kürelerini çiz ────────────────────────────────────────
        for _orb in m.all_health_orbs:
            _orb.draw(m.game_canvas, m.render_offset, m.CURRENT_THEME)

        # ── Silah Sandıkları çiz ──────────────────────────────────────
        for _wc in m.all_weapon_chests:
            _wc.draw(m.game_canvas)
            _wc.draw_prompt(m.game_canvas, m.player_x + 14, m.player_y + 21)

        # ── Cephane Pickup'larını çiz ─────────────────────────────────
        for _ap in m.all_ammo_pickups:
            _ap.draw(m.game_canvas)

        # ── Kombo sistemi hitbox (her bölümde) ───────────────────────
        m.combo_system.draw(m.vfx_surface)

        # ── Combat HUD (her bölümde) — kombo zinciri ────────────────
        # HP + Stamina barları ui_system.py içinde render edilir (Step 12).
        # Kombo zinciri her bölümde görünür
        hud_info = m.combo_system.get_hud_info()
        if hud_info.get('chain') or hud_info.get('last_combo'):
            m.combat_hud.draw(m.game_canvas, hud_info)

        # VFX partikülleri ve trail'leri ayrı yüzeye çiz
        for v in m.all_vfx:
            v.draw(m.vfx_surface)
        for trail in m.trail_effects:
            trail.draw(m.vfx_surface)

        # ── Oyuncu mermilerini çiz (VFX yüzeyi üstünde) ──────────────
        for _p in m.all_player_projectiles:
            _p.draw(m.game_canvas)

        # ── 7. NPC'ler ───────────────────────────────────────────────
        for npc in m.npcs:
            npc.draw(m.game_canvas, m.render_offset)

        # ── 7b. Gizlilik katmanı (kameralar, vizyon konileri, şüphe HUD) ──
        stealth_system.draw(m.game_canvas, camera_offset=(m._manor_draw_ox, m._manor_draw_oy))

        # ── 8. OYUNCU ────────────────────────────────────────────────
        if m.GAME_STATE in ('PLAYING', 'PAUSED', 'GAME_OVER', 'LEVEL_COMPLETE',
                          'ENDLESS_PLAY', 'CHAT', 'CUTSCENE') and m.GAME_STATE != 'GAME_OVER':

            # Duruma göre renk belirle (fallback için kullanılır)
            p_color = m.CURRENT_THEME["player_color"]
            if m.is_dashing:
                p_color = m.METEOR_CORE
            elif m.is_slamming:
                p_color = PLAYER_SLAM
            elif m.is_super_mode:
                p_color = (255, 215, 0)
            try:
                modified_color = m.character_animator.get_modified_color(p_color)
            except:
                modified_color = p_color

            # Talisman halkası — oyuncunun etrafında altın çember
            if m.has_talisman:
                t = pygame.time.get_ticks() * 0.005
                px, py = int(m.player_x + 15) + m.render_offset[0], int(m.player_y + 15) + m.render_offset[1]
                radius = 35 + math.sin(t) * 5
                pygame.draw.circle(m.game_canvas, (255, 215, 0), (px, py), int(radius), 2)
                for i in range(3):
                    angle = t + (i * 2.09)
                    ox = math.cos(angle) * radius
                    oy = math.sin(angle) * radius
                    pygame.draw.circle(m.game_canvas, (255, 255, 200), (int(px + ox), int(py + oy)), 4)

            # ── Sprite karesini al ───────────────────────────────────
            current_sprite = m.character_animator.get_current_frame(
                m.dt, m.character_state, m.player_direction
            )

            _px = int(m.player_x) + m.render_offset[0] + int(-m.manor_camera_offset_x)
            _py = int(m.player_y) + m.render_offset[1] + int(-m.manor_camera_offset_y)

            # ── DEBUG: print + sheet görselleştirme ──────────────────
            if m.DEBUG_SPRITE:
                # ── 1. Sprite sheet'i bir kez yükle (lazy init) ──────
                if m._test_sheet is None:
                    try:
                        import os as _os
                        if _os.path.exists(m._test_sheet_path):
                            m._test_sheet = pygame.image.load(
                                m._test_sheet_path
                            ).convert_alpha()
                            print(
                                f"[DEBUG] Sheet yüklendi: {m._test_sheet_path} "
                                f"→ boyut={m._test_sheet.get_size()}"
                            )
                        else:
                            # Dosya yoksa hata vermemek için dummy surface
                            m._test_sheet = pygame.Surface((1, 1), pygame.SRCALPHA)
                            print(
                                f"[DEBUG] HATA: Sheet bulunamadı → {m._test_sheet_path}\n"
                                f"        Dosya yolunu ve klasör yapısını kontrol et."
                            )
                    except Exception as _e:
                        m._test_sheet = pygame.Surface((1, 1), pygame.SRCALPHA)
                        print(f"[DEBUG] Sheet yüklenirken istisna: {_e}")

                # ── 2. Sheet'i sol üst köşede göster ─────────────────
                # Sadece gerçek bir surface ise (1×1 dummy değilse) blit et
                if m._test_sheet and m._test_sheet.get_width() > 1:
                    # Sheet çok büyükse yarıya küçült, 400px'i geçmesin
                    _ts_w, _ts_h = m._test_sheet.get_size()
                    _max_preview = 400
                    if _ts_w > _max_preview or _ts_h > _max_preview:
                        _scale_f = _max_preview / max(_ts_w, _ts_h)
                        _preview = pygame.transform.scale(
                            m._test_sheet,
                            (int(_ts_w * _scale_f), int(_ts_h * _scale_f))
                        )
                    else:
                        _preview = m._test_sheet

                    # Koyu yarı saydam arka plan — sheet görünürlüğü için
                    _bg = pygame.Surface(
                        (_preview.get_width() + 6, _preview.get_height() + 20),
                        pygame.SRCALPHA
                    )
                    _bg.fill((0, 0, 0, 180))
                    m.game_canvas.blit(_bg, (97, 97))
                    m.game_canvas.blit(_preview, (100, 100))

                    # Etiket: dosya adı + boyut bilgisi
                    _lbl_font = pygame.font.Font(None, 20)
                    _lbl = _lbl_font.render(
                        f"SHEET TEST: {_ts_w}x{_ts_h}px  |  m.DEBUG_SPRITE=True kapat",
                        True, (255, 255, 0)
                    )
                    m.game_canvas.blit(_lbl, (100, 100 + _preview.get_height() + 3))

                    # Sheet'in üstüne grid çiz: her 64px'de bir çizgi
                    _grid_color = (255, 0, 255)  # Magenta — kolayca görülür
                    _frame_size = 64             # Sprite frame boyutu (64×64)
                    _gx0, _gy0 = 100, 100
                    # Dikey çizgiler
                    for _gx in range(0, _preview.get_width() + 1, int(_frame_size * (_preview.get_width() / _ts_w))):
                        pygame.draw.line(
                            m.game_canvas, _grid_color,
                            (_gx0 + _gx, _gy0),
                            (_gx0 + _gx, _gy0 + _preview.get_height()), 1
                        )
                    # Yatay çizgiler
                    for _gy in range(0, _preview.get_height() + 1, int(_frame_size * (_preview.get_height() / _ts_h))):
                        pygame.draw.line(
                            m.game_canvas, _grid_color,
                            (_gx0, _gy0 + _gy),
                            (_gx0 + _preview.get_width(), _gy0 + _gy), 1
                        )

                # ── 3. Konsolda koordinat yazdır (60 karede bir) ──────
                m._debug_print_counter += 1
                if m._debug_print_counter >= 60:
                    m._debug_print_counter = 0
                    _sprite_info = (
                        f"{current_sprite.get_size()}" if current_sprite
                        else "None (sprite yüklenemedi — fallback aktif)"
                    )
                    print(
                        f"[DEBUG] m.player_x={m.player_x:.1f}  m.player_y={m.player_y:.1f} | "
                        f"m.render_offset={m.render_offset} | "
                        f"ekran_pos=({_px},{_py}) | "
                        f"state={m.character_state} | dir={m.player_direction} | "
                        f"Sprite={_sprite_info}"
                    )

            if m.DIRECT_SPRITE_TEST:
                # ════════════════════════════════════════════════════
                # YÜRÜME ANİMASYONU — 4 frame, 4×2 grid (üst satır)
                # Sheet: 1024×1024 px
                # Grid : 4 kolon × 2 satır → her frame 256×512 px
                # Satır 0 (üst): sağa koşu → 4 frame yüklenir
                # Satır 1 (alt): sola koşu → flip ile üretilir
                # PNG: convert_alpha() — kendi şeffaflığını kullanır
                # ════════════════════════════════════════════════════

                if m._direct_sprite is None:
                    import os as _os2

                    _COLS          = 4      # Yatay frame sayısı  (4×2 grid)
                    _ROWS          = 2      # Her iki satırı da yükle → 8 frame
                    _SHEET_FRAMES  = _COLS * _ROWS   # = 8
                    _SHEET_FRAME_W = 256    # Her frame genişliği (1024/4)
                    _SHEET_FRAME_H = 512    # Her frame yüksekliği (1024/2)
                    _DISPLAY_W     = 120    # Ekranda gösterilecek genişlik
                    _DISPLAY_H     = 180    # Ekranda gösterilecek yükseklik

                    _candidates = [
                        "assets/sprites/player_walk.png",
                        "assets/sprites/player/player_walk.png",
                        "assets/player_walk.png",
                        "player_walk.png",
                        m._direct_sprite_path,
                    ]

                    _walk_frames = []
                    for _candidate in _candidates:
                        if _os2.path.exists(_candidate):
                            try:
                                _sheet_raw = pygame.image.load(_candidate).convert_alpha()
                                # PNG'nin kendi alpha kanalını kullan — colorkey gerekmez

                                # Grid'i soldan sağa, yukarıdan aşağıya tara
                                for _row in range(_ROWS):
                                    for _col in range(_COLS):
                                        _sx = _col * _SHEET_FRAME_W
                                        _sy = _row * _SHEET_FRAME_H

                                        _frame_surf = pygame.Surface(
                                            (_SHEET_FRAME_W, _SHEET_FRAME_H),
                                            pygame.SRCALPHA
                                        )
                                        _frame_surf.blit(
                                            _sheet_raw, (0, 0),
                                            (_sx, _sy, _SHEET_FRAME_W, _SHEET_FRAME_H)
                                        )
                                        _frame_scaled = pygame.transform.scale(
                                            _frame_surf, (_DISPLAY_W, _DISPLAY_H)
                                        )
                                        _walk_frames.append(_frame_scaled)

                                print(
                                    f"[WALK] ✓ {_SHEET_FRAMES} frame yüklendi: {_candidate}\n"
                                    f"[WALK]   Grid: {_COLS}×{_ROWS}  "
                                    f"Ham: {_SHEET_FRAME_W}×{_SHEET_FRAME_H}  "
                                    f"→ Ekran: {_DISPLAY_W}×{_DISPLAY_H}"
                                )
                                break
                            except Exception as _le:
                                print(f"[WALK] Yükleme hatası: {_le}")

                    if _walk_frames:
                        m._direct_sprite = _walk_frames
                    else:
                        _fb = pygame.Surface((60, 90))
                        _fb.fill((255, 0, 100))
                        _fb.blit(pygame.font.Font(None, 40).render("?", True, (255,255,255)), (18, 30))
                        m._direct_sprite = [_fb]
                        print("[WALK] ✗ Dosya bulunamadı! → assets/sprites/player_walk.png")

                # ── Frame seç ────────────────────────────────────────
                _frames_list = m._direct_sprite if isinstance(m._direct_sprite, list) else [m._direct_sprite]
                _ANIM_FPS    = 5.0
                _anim_t      = (pygame.time.get_ticks() / 1000.0) % (len(_frames_list) / _ANIM_FPS)
                _frame_idx   = int(_anim_t * _ANIM_FPS) % len(_frames_list)

                # Idle'da dondur — yürürken animasyon oynar
                if m.character_state == 'idle':
                    _frame_idx = 0

                _cur_frame = _frames_list[_frame_idx]

                # Sola gidince ters çevir
                if m.player_direction == -1:
                    _cur_frame = pygame.transform.flip(_cur_frame, True, False)

                # ── Hitbox hizalama ───────────────────────────────────
                _hitbox_w, _hitbox_h = 28, 42
                _sprite_w  = _cur_frame.get_width()
                _sprite_h  = _cur_frame.get_height()
                _off_x = (_hitbox_w - _sprite_w) // 2   # Yatay ortala
                _off_y = _hitbox_h - _sprite_h           # Alt kenar hizala

                _draw_x = int(m.player_x) + m.render_offset[0] + _off_x
                _draw_y = int(m.player_y) + m.render_offset[1] + _off_y

                # ── KARAKTERİ HER ZAMAN ÇİZ ──────────────────────────
                m.game_canvas.blit(_cur_frame, (_draw_x, _draw_y))

                # ── DEBUG KATMANI — sadece DEBUG_SPRITE açıksa ───────
                if m.DEBUG_SPRITE:
                    m.game_canvas.blit(_cur_frame, (200, 200))
                    _lf = pygame.font.Font(None, 20)
                    m.game_canvas.blit(
                        _lf.render(f"FRAME {_frame_idx+1}/{len(_frames_list)}  |  {m.character_state}", True, (255,255,0)),
                        (200, 185)
                    )
                    pygame.draw.rect(m.game_canvas, (255, 255, 0),
                        (_draw_x, _draw_y, _sprite_w, _sprite_h), 2)
                    pygame.draw.rect(m.game_canvas, (0, 255, 255),
                        (int(m.player_x) + m.render_offset[0],
                         int(m.player_y) + m.render_offset[1],
                         _hitbox_w, _hitbox_h), 1)

            elif current_sprite is not None:
                # ── NORMAL SPRITE MODU ───────────────────────────────
                _sw, _sh = current_sprite.get_size()
                _target_w, _target_h = 28, 42

                if _sw != _target_w or _sh != _target_h:
                    current_sprite = pygame.transform.scale(
                        current_sprite, (_target_w, _target_h)
                    )

                try:
                    _params  = m.character_animator.get_draw_params()
                    _sx      = _params.get('squash',   1.0)
                    _sy      = _params.get('stretch',  1.0)
                    _sc      = _params.get('scale',    1.0)
                    _rot_deg = math.degrees(_params.get('rotation', 0.0))
                    _new_w   = max(1, int(_target_w * _sx * _sc))
                    _new_h   = max(1, int(_target_h * _sy * _sc))
                    if _new_w != _target_w or _new_h != _target_h:
                        current_sprite = pygame.transform.scale(
                            current_sprite, (_new_w, _new_h)
                        )
                    if abs(_rot_deg) > 0.5:
                        current_sprite = pygame.transform.rotate(
                            current_sprite, -_rot_deg
                        )
                    _blit_x = _px - (current_sprite.get_width()  - _target_w) // 2
                    _blit_y = _py - (current_sprite.get_height() - _target_h) // 2
                except Exception:
                    _blit_x, _blit_y = _px, _py

                m.game_canvas.blit(current_sprite, (_blit_x, _blit_y))

                if m.DEBUG_SPRITE:
                    pygame.draw.rect(
                        m.game_canvas, (255, 0, 0),
                        (_px, _py, 28, 42), 2
                    )

            else:
                # ── FALLBACK: Placeholder dikdörtgen ─────────────────
                _pw, _ph = 28, 42
                _ps = pygame.Surface((_pw, _ph), pygame.SRCALPHA)
                _ps.fill((*modified_color[:3], 100))
                m.game_canvas.blit(_ps, (_px, _py))
                pygame.draw.rect(m.game_canvas, modified_color, (_px, _py, _pw, _ph), 2)

                if m.DEBUG_SPRITE:
                    pygame.draw.rect(
                        m.game_canvas, (255, 0, 0),
                        (_px, _py, _pw, _ph), 2
                    )
        # ── 8. OYUNCU SONU ───────────────────────────────────────────

        # ── 8b. SİLAH ÇİZİMİ — oyuncunun üstünde, partiküllerin altında ──
        if (m.GAME_STATE in ('PLAYING', 'PAUSED', 'ENDLESS_PLAY', 'CHAT')
                and m.active_weapon_obj is not None
                and m.active_weapon_obj.visual is not None):
            _wep_base_x = int(m.player_x) + m.render_offset[0] + int(-m.manor_camera_offset_x)
            _wep_base_y = int(m.player_y) + m.render_offset[1] + int(-m.manor_camera_offset_y)
            _wep_pivot_x = _wep_base_x + 14   # hitbox merkezi X
            _wep_pivot_y = _wep_base_y + 22   # omuz hizası Y
            m.active_weapon_obj.draw(
                m.game_canvas,
                _wep_pivot_x, _wep_pivot_y,
                m.aim_angle, m.weapon_shoot_timer
            )

            # ── DEBUG: Spread (dağılım) konisi ───────────────────────────
            if m.DEBUG_SPRITE and m.active_weapon_obj is not None:
                _sp_cur  = getattr(m.active_weapon_obj, 'current_spread', 0.0)
                _sp_max  = getattr(m.active_weapon_obj, '_spread_max', 0.2)
                _sp_rec  = getattr(m.active_weapon_obj, '_spread_recovery', 2.5)
                _sp_inc  = getattr(m.active_weapon_obj, '_spread_inc', 0.05)
                _sp_pct  = min(1.0, _sp_cur / max(_sp_max, 0.001))   # 0..1 (clamp: spread > _spread_max olursa renk taşmaz)
                _cone_r  = 160   # Koni yarıçapı (piksel)
                _px0     = _wep_pivot_x
                _py0     = _wep_pivot_y

                # ── 1. DOLU MAKSİMUM KONİ (sabit gri, arka plan) ─────────
                _steps = 24
                _max_pts = [(_px0, _py0)]
                for _i in range(_steps + 1):
                    _a = m.aim_angle - _sp_max + (2 * _sp_max * _i / _steps)
                    _max_pts.append((
                        int(_px0 + math.cos(_a) * _cone_r),
                        int(_py0 + math.sin(_a) * _cone_r)
                    ))
                _max_surf = pygame.Surface(
                    (m.game_canvas.get_width(), m.game_canvas.get_height()), pygame.SRCALPHA
                )
                if len(_max_pts) >= 3:
                    pygame.draw.polygon(_max_surf, (180, 180, 180, 18), _max_pts)
                    pygame.draw.lines(_max_surf, (180, 180, 180, 60), False,
                                      [_max_pts[1], _max_pts[0], _max_pts[-1]], 1)
                m.game_canvas.blit(_max_surf, (0, 0))

                # ── 2. DOLU MEVCUT KONİ (yeşil→turuncu→kırmızı renk geçişi) ─
                if _sp_cur > 0.001:
                    _r_col = int(50  + 205 * _sp_pct)
                    _g_col = int(230 - 180 * _sp_pct)
                    _cur_pts = [(_px0, _py0)]
                    for _i in range(_steps + 1):
                        _a = m.aim_angle - _sp_cur + (2 * _sp_cur * _i / _steps)
                        _cur_pts.append((
                            int(_px0 + math.cos(_a) * _cone_r),
                            int(_py0 + math.sin(_a) * _cone_r)
                        ))
                    _cur_surf = pygame.Surface(
                        (m.game_canvas.get_width(), m.game_canvas.get_height()), pygame.SRCALPHA
                    )
                    _fill_alpha = int(30 + 60 * _sp_pct)
                    if len(_cur_pts) >= 3:
                        pygame.draw.polygon(_cur_surf, (_r_col, _g_col, 20, _fill_alpha), _cur_pts)
                        # Kenar çizgileri (pivot → iki uç nokta)
                        pygame.draw.line(_cur_surf, (_r_col, _g_col, 20, 200),
                                         (_px0, _py0), _cur_pts[1], 2)
                        pygame.draw.line(_cur_surf, (_r_col, _g_col, 20, 200),
                                         (_px0, _py0), _cur_pts[-1], 2)
                    m.game_canvas.blit(_cur_surf, (0, 0))

                # ── 3. MERKEZ NİŞAN ÇİZGİSİ ─────────────────────────────
                _aim_ex = int(_px0 + math.cos(m.aim_angle) * _cone_r)
                _aim_ey = int(_py0 + math.sin(m.aim_angle) * _cone_r)
                pygame.draw.line(m.game_canvas, (0, 255, 120), (_px0, _py0), (_aim_ex, _aim_ey), 1)
                # Nokta ucu
                pygame.draw.circle(m.game_canvas, (0, 255, 120), (_aim_ex, _aim_ey), 3)

                # ── 4. BİLGİ PANELİ ─────────────────────────────────────
                _pf = pygame.font.Font(None, 18)
                _bar_x  = _px0 + 14
                _bar_y  = _py0 - 58
                _bar_w  = 90
                _bar_h  = 7
                # Panel arka plan
                _panel = pygame.Surface((110, 72), pygame.SRCALPHA)
                _panel.fill((0, 0, 0, 160))
                m.game_canvas.blit(_panel, (_bar_x - 4, _bar_y - 4))
                # Spread bar
                pygame.draw.rect(m.game_canvas, (60, 60, 60),    (_bar_x, _bar_y,            _bar_w, _bar_h))
                pygame.draw.rect(m.game_canvas, (_r_col if _sp_cur > 0.001 else 50,
                                               _g_col if _sp_cur > 0.001 else 230, 20),
                                              (_bar_x, _bar_y, int(_bar_w * _sp_pct), _bar_h))
                pygame.draw.rect(m.game_canvas, (120, 120, 120), (_bar_x, _bar_y, _bar_w, _bar_h), 1)
                # Metinler
                _wname = m.active_weapon_obj.WEAPON_TYPE.upper()
                m.game_canvas.blit(_pf.render(f"[{_wname}] SPREAD", True, (200, 200, 200)),
                                 (_bar_x, _bar_y - 14))
                m.game_canvas.blit(_pf.render(f"cur  {_sp_cur:.3f} rad", True, (255, 220, 60)),
                                 (_bar_x, _bar_y + 10))
                m.game_canvas.blit(_pf.render(f"max  {_sp_max:.3f} rad", True, (160, 160, 160)),
                                 (_bar_x, _bar_y + 24))
                m.game_canvas.blit(_pf.render(f"+inc {_sp_inc:.3f}  rec {_sp_rec:.1f}/s", True, (120, 200, 255)),
                                 (_bar_x, _bar_y + 38))
                m.game_canvas.blit(_pf.render(f"{int(_sp_pct * 100):3d}%", True,
                                            (int(50+205*_sp_pct), int(230-180*_sp_pct), 20)),
                                 (_bar_x + 68, _bar_y + 10))

        # ── 9. Yardımcı figür ────────────────────────────────────────
        if m.vasil_companion:
            m.vasil_companion.draw(m.game_canvas)

        # ── 10. VFX partikülleri game_canvas üstüne blit ────────────
        # NOT: vfx_surface oyuncunun üstüne değil, render_offset ile
        # kamera sarsmasını yansıtarak blit edilir. Trail/partiküller
        # oyuncunun üstünde görünür — bu kasıtlı (ön plan efekti).
        m.game_canvas.blit(m.vfx_surface, m.render_offset)

        # ── DEBUG TOGGLE BUTONU (her zaman en üstte) ────────────────
        # Renk: açıkken yeşil, kapalıyken gri; hover'da parlıyor.
        if m.DEBUG_SPRITE:
            _btn_bg    = (0, 160, 0)   if m._debug_btn_hover else (0, 110, 0)
            _btn_bdr   = (0, 255, 50)
            _btn_label = "■ DEBUG KAPAT"
        else:
            _btn_bg    = (60, 60, 60)  if m._debug_btn_hover else (35, 35, 35)
            _btn_bdr   = (120, 120, 120)
            _btn_label = "□ DEBUG AÇ"
        # Yarı saydam arka plan
        _btn_surf = pygame.Surface(
            (m._DEBUG_BTN_RECT.width, m._DEBUG_BTN_RECT.height), pygame.SRCALPHA
        )
        _btn_surf.fill((*_btn_bg, 210))
        m.game_canvas.blit(_btn_surf, m._DEBUG_BTN_RECT.topleft)
        # Çerçeve
        pygame.draw.rect(m.game_canvas, _btn_bdr, m._DEBUG_BTN_RECT, 1)
        # Metin
        _btn_txt = m._debug_btn_font.render(_btn_label, True, (220, 220, 220))
        _btn_txt_x = m._DEBUG_BTN_RECT.x + (m._DEBUG_BTN_RECT.width  - _btn_txt.get_width())  // 2
        _btn_txt_y = m._DEBUG_BTN_RECT.y + (m._DEBUG_BTN_RECT.height - _btn_txt.get_height()) // 2
        m.game_canvas.blit(_btn_txt, (_btn_txt_x, _btn_txt_y))
        # ─────────────────────────────────────────────────────────────

        # Karma bildirimi
        if m.karma_notification_timer > 0:
            font = pygame.font.Font(None, 40)
            color = (255, 50, 50) if "DÜŞTÜ" in m.karma_notification_text else (0, 255, 100)
            if "DİRİLİŞ" in m.karma_notification_text:
                color = (200, 50, 200)
            draw_text_with_shadow(m.game_canvas, m.karma_notification_text, font,
                                 (LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2 - 100), color, align="center")

        # Bölüm 30 hayatta kalma sayacı
        if m.current_level_idx == 30 and not m.finisher_active:
            remaining = max(0, 120 - m.level_15_timer)
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            time_str = f"HAYATTA KAL: {mins:02}:{secs:02}"
            text_color = (255, 50, 50) if m.frame_count % 60 < 30 else (255, 255, 255)
            font_timer = pygame.font.Font(None, 60)
            draw_text_with_shadow(m.game_canvas, time_str, font_timer,
                                 (LOGICAL_WIDTH//2, 80), text_color, align="center")

        # ── 11. NPC sohbet / sinematik katman ───────────────────────
        if m.GAME_STATE == 'NPC_CHAT':
            draw_npc_chat(m.game_canvas, m.current_npc, m.npc_chat_history,
                          m.npc_chat_input, m.npc_show_cursor, LOGICAL_WIDTH, LOGICAL_HEIGHT)

        if m.GAME_STATE in ['CHAT', 'CUTSCENE']:
            m.active_ui_elements = draw_cinematic_overlay(
                m.game_canvas, m.story_manager, m.time_ms, m.mouse_pos
            )

        # Dinlenme alanı tuş ipuçları
        if m.GAME_STATE == 'PLAYING':
            lvl_config = m.EASY_MODE_LEVELS.get(m.current_level_idx, m.EASY_MODE_LEVELS[1])
            if lvl_config.get('type') == 'rest_area':
                font = pygame.font.Font(None, 24)
                instructions = [
                    "E: NPC ile konuş", "T: Sonraki bölüme geç",
                    "WASD: Hareket et", "Sağa git → Otomatik geçiş"
                ]
                y_offset = LOGICAL_HEIGHT - 120
                for instruction in instructions:
                    text_surf = font.render(instruction, True, (200, 255, 200))
                    m.game_canvas.blit(text_surf, (40, y_offset))
                    y_offset += 25
            elif lvl_config.get('type') == 'beat_arena':
                font = pygame.font.Font(None, 24)
                instructions = [
                    "J: Hafif Vuruş    K: Ağır Vuruş",
                    "WASD: Hareket / Zıplama",
                    "Kombo: J+J+J / J+J+K / H+H ...",
                    "Tüm dalgaları temizle → Bölüm geçer"
                ]
                y_offset = LOGICAL_HEIGHT - 105
                for instruction in instructions:
                    text_surf = font.render(instruction, True, (255, 200, 100))
                    m.game_canvas.blit(text_surf, (40, y_offset))
                    y_offset += 25
            elif lvl_config.get('type') == 'manor_stealth':
                # Malikane özel HUD: suikast ipucu + aktif muhafız sayacı
                _mfont = pygame.font.Font(None, 24)
                _guard_count = stealth_system.active_guard_count()
                _manor_hints = [
                    "F: Sessiz Suikast (Arkadan, Şüphe < %50)",
                    "WASD: Hareket   SPACE: Dash",
                    f"Aktif Muhafız: {_guard_count}",
                    "Hedef: Gizli Kasaya Ulaş →",
                ]
                _mhud_y = LOGICAL_HEIGHT - 100
                for _mh in _manor_hints:
                    _mh_surf = _mfont.render(_mh, True, (200, 150, 80))
                    m.game_canvas.blit(_mh_surf, (40, _mhud_y))
                    _mhud_y += 24
            elif lvl_config.get('type') == 'debug_arena':
                # Debug Arena HUD: geliştirici ipuçları
                _db_font = pygame.font.Font(None, 24)
                _db_hints = [
                    "[ DEBUG ARENA - GELISTIRICI MODU ]",
                    "WASD: Hareket   W: Zipla   SPACE: Dash",
                    "J: Hafif  K: Agir  S(havada): Slam",
                    "ESC: Menuye Don   F12: Debug Arena'ya Don",
                ]
                _db_y = LOGICAL_HEIGHT - 105
                for _dh in _db_hints:
                    _dh_surf = _db_font.render(_dh, True, (80, 220, 80))
                    m.game_canvas.blit(_dh_surf, (40, _db_y))
                    _db_y += 24
                # Sağ üst köşeye kırmızı "DEBUG" etiketi
                _db_tag = pygame.font.Font(None, 26).render("[ DEBUG ARENA ]", True, (255, 50, 50))
                m.game_canvas.blit(_db_tag, (LOGICAL_WIDTH - _db_tag.get_width() - 12, 8))
            else:
                # Normal bölümlerde köşede kısa ipucu
                _hint_font = pygame.font.Font(None, 22)
                _hint = _hint_font.render("J: Hafif  K: Ağır  SPACE: Dash  S↓: Slam", True, (180, 180, 180))
                m.game_canvas.blit(_hint, (LOGICAL_WIDTH - _hint.get_width() - 12, LOGICAL_HEIGHT - 30))

        # Yakındaki NPC ekosistemi figürleri
        for npc in m.npc_ecosystem:
            if abs(npc.x - m.player_x) < 500 and abs(npc.y - m.player_y) < 400:
                npc.draw(m.game_canvas, m.render_offset)

        # ── 12. UI / HUD (en üstte) ─────────────────────────────────
        if m.GAME_STATE not in ['CHAT', 'CUTSCENE']:
            current_score_int = int(m.score)
            should_update_ui = (
                m.cached_ui_surface is None or
                current_score_int != m.last_score or
                m.frame_count % 10 == 0 or
                m.GAME_STATE == 'INVENTORY' or  # Envanter her frame güncellenir
                m.GAME_STATE == 'TERMINAL'    # Terminal her frame güncellenir (cursor blink)
            )
            if should_update_ui:
                m.last_score = current_score_int
                m.cached_ui_surface = pygame.Surface(
                    (LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA
                )
                m.last_active_ui_elements = render_ui(
                    m.cached_ui_surface, m.GAME_STATE, ui_data, m.mouse_pos
                )
            m.game_canvas.blit(m.cached_ui_surface, (0, 0))
            m.active_ui_elements = m.last_active_ui_elements

    target_res = AVAILABLE_RESOLUTIONS[m.game_settings['res_index']]
    if m.game_settings['fullscreen']:
        if target_res != (LOGICAL_WIDTH, LOGICAL_HEIGHT):
            scaled_small = pygame.transform.scale(m.game_canvas, target_res)
            final_game_image = pygame.transform.scale(scaled_small, m.screen.get_size())
        else:
            final_game_image = pygame.transform.scale(m.game_canvas, m.screen.get_size())
    else:
        final_game_image = pygame.transform.scale(m.game_canvas, m.screen.get_size())

    master_vol = m.game_settings.get("sound_volume", 0.7)
    music_vol = m.game_settings.get("music_volume", 0.5)
    effects_vol = m.game_settings.get("effects_volume", 0.8)

    if 'AMBIENT_CHANNEL' in locals() and AMBIENT_CHANNEL:
        try:
            AMBIENT_CHANNEL.set_volume(master_vol * music_vol)
        except Exception:
            pass

    if 'FX_CHANNEL' in locals() and FX_CHANNEL:
        try:
            FX_CHANNEL.set_volume(master_vol * effects_vol)
        except Exception:
            pass