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

def handle_events():
    """Event handling: SETTINGS slider + tüm event loop"""
    m = _m
    if m.GAME_STATE == 'SETTINGS':
        for event in m.events:
            if event.type == pygame.QUIT:
                m.running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # TERMINAL, INVENTORY, NPC_CHAT kendi ESC mantıklarını
                # aşağıdaki spesifik handler'da yönetir — burada müdahale etme.
                if m.GAME_STATE not in ('TERMINAL', 'INVENTORY', 'NPC_CHAT', 'PAUSED'):
                    m.save_manager.update_settings(m.game_settings)
                    m.GAME_STATE = 'MENU'

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                is_slider_clicked = False
                for key, rect in m.active_ui_elements.items():
                    if key.startswith('slider_') and rect.collidepoint(m.mouse_pos):
                        m.dragging_slider = key
                        is_slider_clicked = True
                        slider_key_name = m.dragging_slider.replace('slider_', '')
                        relative_x = m.mouse_pos[0] - rect.x
                        value = max(0.0, min(1.0, relative_x / rect.width))
                        m.game_settings[slider_key_name] = value
                        audio_manager.update_settings(m.game_settings)
                        break

                if not is_slider_clicked:
                    if 'toggle_fullscreen' in m.active_ui_elements and m.active_ui_elements['toggle_fullscreen'].collidepoint(m.mouse_pos):
                        m.game_settings['fullscreen'] = not m.game_settings['fullscreen']
                    elif 'change_resolution' in m.active_ui_elements and m.active_ui_elements['change_resolution'].collidepoint(m.mouse_pos):
                        m.game_settings['res_index'] = (m.game_settings['res_index'] + 1) % len(AVAILABLE_RESOLUTIONS)
                    elif 'apply_changes' in m.active_ui_elements and m.active_ui_elements['apply_changes'].collidepoint(m.mouse_pos):
                        m.save_manager.update_settings(m.game_settings)
                        audio_manager.update_settings(m.game_settings)
                        apply_display_settings()
                    elif 'back' in m.active_ui_elements and m.active_ui_elements['back'].collidepoint(m.mouse_pos):
                        m.save_manager.update_settings(m.game_settings)
                        m.GAME_STATE = 'MENU'
                    elif 'reset_progress' in m.active_ui_elements and m.active_ui_elements['reset_progress'].collidepoint(m.mouse_pos):
                        m.save_manager.reset_progress()
                        m.game_settings = m.save_manager.get_settings()
                        audio_manager.update_settings(m.game_settings)

            elif event.type == pygame.MOUSEMOTION:
                if m.dragging_slider:
                    slider_key_name = m.dragging_slider.replace('slider_', '')
                    slider_rect = m.active_ui_elements[m.dragging_slider]
                    relative_x = m.mouse_pos[0] - slider_rect.x
                    value = max(0.0, min(1.0, relative_x / slider_rect.width))
                    m.game_settings[slider_key_name] = value
                    audio_manager.update_settings(m.game_settings)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if m.dragging_slider:
                    m.save_manager.update_settings(m.game_settings)
                    m.dragging_slider = None

        m.events = []

    for event in m.events:
        if event.type == pygame.QUIT:
            m.running = False

        # ── F12: Debug Arena'ya Anında Geçiş (Her state'den çalışır) ───
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
            m.current_level_idx = 999
            start_loading_sequence('PLAYING')
            print("[DEBUG] F12 → Debug Arena (ID:999) yükleniyor...")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # ── DEBUG BUTONU — her game state'de çalışır ────────────
            if m._DEBUG_BTN_RECT.collidepoint(m.mouse_pos):
                m.DEBUG_SPRITE = not m.DEBUG_SPRITE
                # DIRECT_SPRITE_TEST her zaman True — karakter hep çizilir
                _state_str = "AÇIK" if m.DEBUG_SPRITE else "KAPALI"
                print(f"[DEBUG] Toggle → {_state_str}")
                pass
            elif m.GAME_STATE == 'MENU':
                if 'story_mode' in m.active_ui_elements and m.active_ui_elements['story_mode'].collidepoint(m.mouse_pos):
                    audio_manager.stop_music()
                    IntroCutscene(m.screen, m.clock).run()  # ← DEĞİŞİKLİK 2: Giriş sahnesi
                    ai_awakening_scene = AICutscene(m.screen, m.clock, m.asset_paths)
                    cutscene_finished = ai_awakening_scene.run()
                    if cutscene_finished:
                        m.current_level_idx = 1
                        start_loading_sequence('PLAYING')
                    else:
                        m.running = False
                elif 'level_select' in m.active_ui_elements and m.active_ui_elements['level_select'].collidepoint(m.mouse_pos):
                    m.GAME_STATE = 'LEVEL_SELECT'
                    m.level_select_page = 0
                elif 'settings' in m.active_ui_elements and m.active_ui_elements['settings'].collidepoint(m.mouse_pos):
                    m.GAME_STATE = 'SETTINGS'
                elif 'cheat_terminal' in m.active_ui_elements and m.active_ui_elements['cheat_terminal'].collidepoint(m.mouse_pos):
                    m.GAME_STATE = 'TERMINAL'
                    m.terminal_input = ""
                    m.terminal_status = "KOMUT BEKLENİYOR..."
                elif 'endless' in m.active_ui_elements and m.active_ui_elements['endless'].collidepoint(m.mouse_pos):
                    m.GAME_STATE = 'ENDLESS_SELECT'
                elif 'exit' in m.active_ui_elements and m.active_ui_elements['exit'].collidepoint(m.mouse_pos):
                    m.running = False

            elif m.GAME_STATE == 'LEVEL_SELECT':
                if 'back' in m.active_ui_elements and m.active_ui_elements['back'].collidepoint(m.mouse_pos):
                    m.GAME_STATE = 'MENU'
                elif 'next_page' in m.active_ui_elements and m.active_ui_elements['next_page'].collidepoint(m.mouse_pos):
                    m.level_select_page += 1
                elif 'prev_page' in m.active_ui_elements and m.active_ui_elements['prev_page'].collidepoint(m.mouse_pos):
                    m.level_select_page = max(0, m.level_select_page - 1)
                else:
                    for key, rect in m.active_ui_elements.items():
                        if key.startswith('level_') and rect.collidepoint(m.mouse_pos):
                            level_num = int(key.split('_')[1])
                            m.current_level_idx = level_num
                            start_loading_sequence('PLAYING')
                            break

            elif m.GAME_STATE == 'ENDLESS_SELECT':
                if 'back' in m.active_ui_elements and m.active_ui_elements['back'].collidepoint(m.mouse_pos):
                    m.GAME_STATE = 'MENU'
                else:
                    for key, rect in m.active_ui_elements.items():
                        if key.startswith('mode_') and rect.collidepoint(m.mouse_pos):
                            mode_name = key.split('_')[1]
                            m.endless_modes.current_mode = mode_name
                            start_loading_sequence('ENDLESS_PLAY')
                            break

            elif m.GAME_STATE in ('PLAYING', 'ENDLESS_PLAY'):
                # ── SOL TIK: ATEŞ ET ─────────────────────────────────────
                _manor_click = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
                if _manor_click.get('type') != 'manor_stealth':
                    if m.active_weapon_obj is not None:
                        _fire_result = m.active_weapon_obj.fire()
                        if _fire_result:
                            m.player_bullets      = m.active_weapon_obj.bullets
                            m.gun_cooldown        = m.active_weapon_obj.cooldown
                            m.is_reloading        = m.active_weapon_obj.is_reloading
                            m.weapon_shoot_timer  = m.active_weapon_obj._get_fire_cooldown()
                            _inv_sl = inventory_manager.slot_for(m.active_weapon_obj.WEAPON_TYPE)
                            if _inv_sl is not None:
                                _inv_sl.current_mag = m.player_bullets
                            _spread      = getattr(m.active_weapon_obj, 'current_spread', 0.0)
                            _shoot_angle = m.aim_angle + random.uniform(-_spread, _spread)
                            _muzzle = get_weapon_muzzle_point(
                                m.active_weapon_obj.WEAPON_TYPE,
                                m.player_x + 15, m.player_y + 18,
                                _shoot_angle, m.weapon_shoot_timer
                            )
                            _px_proj = _muzzle[0] if _muzzle else m.player_x + 15 + math.cos(m.aim_angle) * 14
                            _py_proj = _muzzle[1] if _muzzle else m.player_y + 18 + math.sin(m.aim_angle) * 14
                            # ── Pompalı: tek mermi yerine saçma demeti ───────────
                            if m.active_weapon_obj.WEAPON_TYPE == "shotgun":
                                _pellet_n    = m.active_weapon_obj.PELLET_COUNT
                                _half_spread = m.active_weapon_obj.SPREAD_ANGLE / 2.0
                                for _pi in range(_pellet_n):
                                    # Saçmaları koniye eşit aralıklı dağıt
                                    _t = _pi / max(_pellet_n - 1, 1)   # 0..1
                                    _pa = (m.aim_angle - _half_spread) + _t * m.active_weapon_obj.SPREAD_ANGLE
                                    _pp = PlayerProjectile(_px_proj, _py_proj, _pa)
                                    m.all_player_projectiles.add(_pp)
                                m.screen_shake = max(m.screen_shake, 6)   # Güçlü sarsma
                            else:
                                proj = PlayerProjectile(_px_proj, _py_proj, _shoot_angle)
                                m.all_player_projectiles.add(proj)
                                m.screen_shake = max(m.screen_shake, 2)
                            if m.GUN_SHOT_SOUND:
                                audio_manager.play_sfx(m.GUN_SHOT_SOUND)
                            m.all_vfx.add(ParticleExplosion(
                                int(_px_proj), int(_py_proj), (255, 220, 80), 5
                            ))
                    elif m.gun_cooldown <= 0 and m.player_bullets > 0 and not m.is_reloading:
                        # Eski uyumluluk kodu — silahsız iken çalışmasın
                        # (player_bullets = REVOLVER_MAX_BULLETS init değeri bug'a yol açıyordu)
                        pass  # Silah yoksa ateş yok

            elif m.GAME_STATE == 'LEVEL_COMPLETE':
                if 'continue' in m.active_ui_elements and m.active_ui_elements['continue'].collidepoint(m.mouse_pos):
                    next_level = m.current_level_idx + 1
                    if next_level == 10:
                        karma = m.save_manager.get_karma()
                        scenario = "BETRAYAL" if karma >= 0 else "JUDGMENT"
                        cinematic_assets = m.asset_paths.copy()
                        cinematic_assets['scenario'] = scenario
                        audio_manager.stop_music()
                        scene = AICutscene(m.screen, m.clock, cinematic_assets)
                        scene.run()
                        m.current_level_idx = 10
                        start_loading_sequence('PLAYING')
                        continue
                    if 11 <= m.current_level_idx <= 14:
                        m.current_level_idx = next_level
                        init_game()
                        m.GAME_STATE = 'PLAYING'
                        continue
                    elif m.current_level_idx == 30:
                        m.GAME_STATE = 'GAME_COMPLETE'
                    elif next_level in m.EASY_MODE_LEVELS:
                        m.current_level_idx = next_level
                        init_game()
                        m.GAME_STATE = 'PLAYING'
                    else:
                        m.GAME_STATE = 'GAME_COMPLETE'
                elif 'return_menu' in m.active_ui_elements and m.active_ui_elements['return_menu'].collidepoint(m.mouse_pos):
                    m.GAME_STATE = 'MENU'

            elif m.GAME_STATE in ['CHAT', 'CUTSCENE']:
                if m.story_manager.state == "WAITING_CHOICE":
                    for key, rect in m.active_ui_elements.items():
                        if key.startswith('choice_') and rect.collidepoint(m.mouse_pos):
                            choice_idx = int(key.split('_')[1])
                            m.story_manager.select_choice(choice_idx)
                            break
                elif m.story_manager.waiting_for_click:
                    m.story_manager.next_line()
                    if m.story_manager.state == "FINISHED":
                        if m.story_manager.current_chapter == 0:
                            m.current_level_idx = 1
                            start_loading_sequence('PLAYING')
                        else:
                            start_loading_sequence('PLAYING')

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if m.GAME_STATE == 'INVENTORY':
                    m.GAME_STATE = 'PLAYING'
                    audio_manager.unpause_all()
                elif m.GAME_STATE == 'PLAYING':
                    m.GAME_STATE = 'MENU'
                    audio_manager.stop_music()
                elif m.GAME_STATE == 'NPC_CHAT':
                    m.GAME_STATE = 'PLAYING'
                    if m.current_npc:
                        m.current_npc.end_conversation()
                        m.current_npc = None
                elif m.GAME_STATE == 'TERMINAL':
                    m.GAME_STATE = 'PLAYING'  # Terminali kapat, oyuna dön
                elif m.GAME_STATE in ['MENU', 'SETTINGS', 'LEVEL_SELECT', 'ENDLESS_SELECT']:
                    m.running = False

            if event.key == pygame.K_p:
                if m.GAME_STATE == 'PLAYING':
                    m.GAME_STATE = 'PAUSED'
                    audio_manager.pause_all()
                elif m.GAME_STATE == 'PAUSED':
                    m.GAME_STATE = 'PLAYING'
                    audio_manager.unpause_all()

            # ── I TUŞU: ENVANTER ─────────────────────────────────────
            if event.key == pygame.K_i:
                if m.GAME_STATE == 'PLAYING':
                    m.GAME_STATE = 'INVENTORY'
                    audio_manager.pause_all()
                elif m.GAME_STATE == 'INVENTORY':
                    m.GAME_STATE = 'PLAYING'
                    audio_manager.unpause_all()

            if m.GAME_STATE == 'GAME_OVER' and event.key == pygame.K_r:
                # TAM SIFIRLAMA: envanter de temizlenir, silahsız başlanır
                inventory_manager.reset()
                m.inventory_weapons.clear()
                m.active_weapon_obj = None
                init_game()
                m.GAME_STATE = 'PLAYING'
            if m.current_level_idx == 99 and event.key == pygame.K_r:
                init_redemption_mode()
            if m.current_level_idx == 99 and event.key == pygame.K_g:
                m.save_manager.update_karma(-80)
                init_genocide_mode()

            if m.GAME_STATE == 'PLAYING' and event.key == pygame.K_e:
                closest_npc = None
                min_dist = float('inf')
                for npc in m.npcs:
                    dist = math.sqrt((m.player_x - npc.x)**2 + (m.player_y - npc.y)**2)
                    if dist < npc.talk_radius and dist < min_dist:
                        min_dist = dist
                        closest_npc = npc
                if closest_npc:
                    start_npc_conversation(closest_npc)
                else:
                    # ── Silah sandığı etkileşimi ──────────────────────────────
                    for _chest in list(m.all_weapon_chests):
                        _cx_d = math.sqrt((m.player_x + 14 - _chest.rect.centerx)**2 +
                                          (m.player_y + 21 - _chest.rect.centery)**2)
                        if _cx_d < WeaponChest.INTERACT_RADIUS:
                            _wtype = _chest.interact()
                            if _wtype:
                                # Yeni silah nesnesini oluştur
                                _new_weapon = create_weapon(_wtype)
                                if _new_weapon:
                                    _is_new = inventory_manager.unlock(_wtype, _new_weapon)
                                    if _wtype not in m.inventory_weapons:
                                        m.inventory_weapons.append(_wtype)
                                    if m.active_weapon_obj is None or _is_new:
                                        # Yeni silah → kuşan
                                        inventory_manager.switch_to(_wtype)
                                        m.active_weapon_obj = inventory_manager.active_weapon
                                        _b, _s = inventory_manager.ammo_state()
                                        if m.active_weapon_obj:
                                            m.active_weapon_obj.bullets    = _b
                                            m.active_weapon_obj.spare_mags = _s
                                        m.player_bullets  = _b
                                        m.is_reloading    = False
                                        m.gun_cooldown    = 0.0
                                        m.karma_notification_text  = f"{_wtype.upper()} ALINDI!"
                                    else:
                                        # Aynı silah zaten var → +1 yedek şarjör
                                        # unlocked_weapons bir liste; kayıtlı nesneye
                                        # switch_to üzerinden erişiyoruz.
                                        _prev_active_type = inventory_manager.active_type
                                        inventory_manager.switch_to(_wtype)
                                        _cur = inventory_manager.active_weapon
                                        if _cur is not None:
                                            _cur.add_spare_mag(1)
                                            if m.active_weapon_obj and m.active_weapon_obj.WEAPON_TYPE == _wtype:
                                                m.player_bullets = m.active_weapon_obj.bullets
                                        # Önceki aktif silaha geri dön (active_weapon_obj değişmez)
                                        if _prev_active_type and _prev_active_type != _wtype:
                                            inventory_manager.switch_to(_prev_active_type)
                                        m.karma_notification_text  = f"+1 ŞARJÖR ({_wtype.upper()})"
                                    m.karma_notification_timer = 60
                                    m.save_manager.unlock_weapon(_wtype)
                                    m.all_vfx.add(ParticleExplosion(
                                        _chest.rect.centerx, _chest.rect.centery,
                                        (255, 215, 0), 12
                                    ))
                            break

            # --- DÖVÜŞ TUŞLARI (tüm bölümlerde aktif) ---
            if m.GAME_STATE == 'PLAYING':
                px_c = int(m.player_x + 15)
                py_c = int(m.player_y + 15)
                if event.key == pygame.K_j:   # Hafif vuruş
                    if m.player_hp.consume_stamina(COST_LIGHT):
                        m.combo_system.input_light(m.player_x, m.player_y, m.player_direction)
                        m.all_vfx.add(ParticleExplosion(
                            px_c + m.player_direction * 40, py_c,
                            (255, 150, 50), 8
                        ))
                elif event.key == pygame.K_k:  # Ağır vuruş
                    if m.player_hp.consume_stamina(COST_HEAVY):
                        m.combo_system.input_heavy(m.player_x, m.player_y, m.player_direction)
                        m.all_vfx.add(Shockwave(
                            px_c + m.player_direction * 50, py_c,
                            CURSED_RED, max_radius=60, speed=12
                        ))
                        m.screen_shake = 6

            elif m.GAME_STATE == 'TERMINAL':
                if event.key == pygame.K_RETURN:
                    _cmd = m.terminal_input.strip().lower()
                    m.terminal_input = ""

                    # ── Cheat kodları (her yerden) ─────────────────────
                    if _cmd == "super_mode_on":
                        m.is_super_mode = not m.is_super_mode
                        m.terminal_status = "SÜPER MOD: " + ("AKTİF!" if m.is_super_mode else "PASİF!")

                    elif _cmd == "debug_arena":
                        m.current_level_idx = 999
                        start_loading_sequence('PLAYING')
                        m.terminal_status = "DEBUG ARENA YÜKLENİYOR..."

                    # ── Debug Arena spawn komutları ────────────────────
                    elif m.current_level_idx == 999:
                        _dbg_floor_top = LOGICAL_HEIGHT - 80
                        _sx = min(int(m.player_x) + 400, LOGICAL_WIDTH - 60)

                        if _cmd in ("help", "yardim"):
                            m.terminal_status = "KOMUTLAR: spawn cursed/tank/drone/vasil/ares/nexus/chest/ammo/health | clear enemies/all | god on/off"

                        elif _cmd == "spawn cursed":
                            # Gerçek zemin platformunu bul (debug arena'nın tam genişlikte zemini)
                            _floor_plat = next((p for p in m.all_platforms if p.rect.width > LOGICAL_WIDTH - 10), None)
                            if _floor_plat is None:
                                _floor_plat = Platform(0, _dbg_floor_top, LOGICAL_WIDTH, 80, theme_index=0)
                            _e = CursedEnemy(_floor_plat)
                            _e.rect.midbottom = (_sx, _dbg_floor_top)
                            m.all_enemies.add(_e)
                            m.terminal_status = f"OK — CursedEnemy spawn edildi ({_sx})"

                        elif _cmd == "spawn tank":
                            _floor_plat = next((p for p in m.all_platforms if p.rect.width > LOGICAL_WIDTH - 10), None)
                            if _floor_plat is None:
                                _floor_plat = Platform(0, _dbg_floor_top, LOGICAL_WIDTH, 80, theme_index=0)
                            _e = TankEnemy(_floor_plat)
                            _e.rect.midbottom = (_sx, _dbg_floor_top)
                            m.all_enemies.add(_e)
                            m.terminal_status = f"OK — TankEnemy spawn edildi ({_sx})"

                        elif _cmd == "spawn drone":
                            # DroneEnemy doğrudan x, y alır
                            _e = DroneEnemy(_sx, _dbg_floor_top - 210)
                            m.all_enemies.add(_e)
                            m.terminal_status = f"OK — DroneEnemy spawn edildi ({_sx})"

                        elif _cmd == "spawn vasil":
                            _bsx = min(int(m.player_x) + 350, LOGICAL_WIDTH - 80)
                            _b = VasilBoss(_bsx, _dbg_floor_top - 180)
                            m.all_enemies.add(_b)
                            m.terminal_status = f"OK — VasilBoss spawn edildi"

                        elif _cmd == "spawn ares":
                            _bsx = min(int(m.player_x) + 350, LOGICAL_WIDTH - 80)
                            _b = AresBoss(_bsx, _dbg_floor_top - 180)
                            m.all_enemies.add(_b)
                            m.terminal_status = f"OK — AresBoss spawn edildi"

                        elif _cmd == "spawn nexus":
                            _bsx = min(int(m.player_x) + 350, LOGICAL_WIDTH - 80)
                            _b = NexusBoss(_bsx, _dbg_floor_top - 300)
                            m.all_enemies.add(_b)
                            m.terminal_status = f"OK — NexusBoss spawn edildi"

                        elif _cmd == "spawn chest":
                            _cr = pygame.Rect(_sx, _dbg_floor_top - 50, 40, 40)
                            _c = WeaponChest(_cr)
                            m.all_weapon_chests.add(_c)
                            m.terminal_status = f"OK — WeaponChest spawn edildi ({_sx})"

                        elif _cmd == "spawn shotgun":
                            _sg = create_weapon("shotgun", spare_mags=9999)
                            if _sg:
                                inventory_manager.unlock("shotgun", _sg)
                                if "shotgun" not in m.inventory_weapons:
                                    m.inventory_weapons.append("shotgun")
                                m.terminal_status = "OK — Shotgun envanterine eklendi (3 ile kuşan)"

                        elif _cmd == "spawn ammo":
                            _ap = AmmoPickup(_sx, _dbg_floor_top - 30)
                            m.all_ammo_pickups.add(_ap)
                            m.terminal_status = f"OK — AmmoPickup spawn edildi ({_sx})"

                        elif _cmd == "spawn health":
                            _ho = HealthOrb(_sx, _dbg_floor_top - 30)
                            m.all_health_orbs.add(_ho)
                            m.terminal_status = f"OK — HealthOrb spawn edildi ({_sx})"

                        elif _cmd == "clear enemies":
                            _count = len(m.all_enemies)
                            m.all_enemies.empty()
                            m.terminal_status = f"TEMİZLENDİ — {_count} düşman silindi"

                        elif _cmd == "clear all":
                            _ec = len(m.all_enemies)
                            m.all_enemies.empty()
                            m.all_weapon_chests.empty()
                            m.all_ammo_pickups.empty()
                            m.all_health_orbs.empty()
                            m.terminal_status = f"TEMİZLENDİ — {_ec} düşman + tüm objeler silindi"

                        elif _cmd in ("god on", "god_on"):
                            m.is_super_mode = True
                            m.terminal_status = "OK — GOD MODE AKTİF (hasar yok, sınırsız stamina)"

                        elif _cmd in ("god off", "god_off"):
                            m.is_super_mode = False
                            m.terminal_status = "OK — GOD MODE PASİF"

                        else:
                            m.terminal_status = f"HATA: '{_cmd}' tanımlı değil. 'help' yaz."

                    else:
                        m.terminal_status = f"HATA: GEÇERSİZ KOD"

                elif event.key == pygame.K_BACKSPACE:
                    m.terminal_input = m.terminal_input[:-1]
                elif event.key == pygame.K_ESCAPE:
                    m.GAME_STATE = 'PLAYING'
                else:
                    if len(m.terminal_input) < 30:
                        m.terminal_input += event.unicode

            elif m.GAME_STATE == 'NPC_CHAT':
                if event.key == pygame.K_RETURN:
                    if m.npc_chat_input.strip():
                        m.npc_chat_history.append({"speaker": "Oyuncu", "text": m.npc_chat_input})
                        npc_response = "..."
                        if m.current_npc:
                            if m.current_npc.ai_active:
                                npc_response = m.story_manager.generate_npc_response(m.current_npc, m.npc_chat_input, m.npc_chat_history[:-1])
                            else:
                                game_context = f"Skor: {int(m.score)}, Bölüm: {m.current_level_idx}"
                                npc_response = m.current_npc.send_message(m.npc_chat_input, game_context)
                            m.npc_chat_history.append({"speaker": m.current_npc.name, "text": npc_response})
                        m.npc_chat_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    m.npc_chat_input = m.npc_chat_input[:-1]
                elif event.key == pygame.K_TAB:
                    if m.current_npc:
                        m.current_npc.ai_active = not m.current_npc.ai_active
                elif event.key == pygame.K_ESCAPE:
                    m.GAME_STATE = 'PLAYING'
                    if m.current_npc:
                        m.current_npc.end_conversation()
                        m.current_npc = None
                else:
                    if len(m.npc_chat_input) < 100:
                        m.npc_chat_input += event.unicode

            if m.GAME_STATE == 'PLAYING' and event.key == pygame.K_t:
                lvl_config = m.EASY_MODE_LEVELS.get(m.current_level_idx, m.EASY_MODE_LEVELS[1])
                if m.current_level_idx == 999:
                    # Debug Arena: T → Terminal aç
                    m.GAME_STATE = 'TERMINAL'
                    m.terminal_input  = ""
                    m.terminal_status = "KOMUT BEKLENİYOR... (help yaz)"
                elif lvl_config.get('type') == 'rest_area':
                    # Dinlenme alanından ayrılırken canı tam doldur (Bonfire)
                    m.player_hp.heal(m.player_hp.max_hp)
                    m.karma_notification_text  = "DİNLENDİN! CAN DOLDU"
                    m.karma_notification_timer = 60
                    next_level = m.current_level_idx + 1
                    if next_level in m.EASY_MODE_LEVELS:
                        m.current_level_idx = next_level
                        init_game()
                    else:
                        m.GAME_STATE = 'GAME_COMPLETE'

            if m.GAME_STATE == 'PLAYING':
                px, py = int(m.player_x + 15), int(m.player_y + 15)
                if event.key == pygame.K_w and m.jumps_left > 0 and not m.is_dashing:
                    m.jumps_left -= 1
                    m.is_jumping = True
                    m.is_slamming = False
                    m.y_velocity = -JUMP_POWER
                    m.character_state = 'jumping'
                    m.all_vfx.add(ParticleExplosion(px, py, m.CURRENT_THEME["player_color"], 6))
                    for _ in range(2):
                        m.all_vfx.add(EnergyOrb(px + random.randint(-10, 10),
                                                py + random.randint(-10, 10),
                                                m.CURRENT_THEME["border_color"], 4, 15))

                if event.key == pygame.K_s and m.is_jumping and not m.is_dashing and not m.is_slamming and m.player_hp.consume_stamina(COST_SLAM):
                    m.is_slamming = True
                    m.slam_stall_timer = 15
                    m.y_velocity = 0
                    m.character_state = 'slamming'
                    m.slam_collision_check_frames = 0
                    if m.SLAM_SOUND:
                        audio_manager.play_sfx(m.SLAM_SOUND)
                    m.all_vfx.add(ScreenFlash(PLAYER_SLAM, 80, 8))
                    m.all_vfx.add(Shockwave(px, py, PLAYER_SLAM, max_radius=200, rings=3, speed=25))
                    for _ in range(3):
                        m.all_vfx.add(LightningBolt(px, py,
                                                    px + random.randint(-60, 60),
                                                    py + random.randint(-60, 60),
                                                    PLAYER_SLAM, 12))

                # ── F TUŞU: SADECE SESSİZ SUİKAST (manor_stealth) ───────────
                # Ateş etmek → Sol Tık (MOUSEBUTTONDOWN aşağıda)
                if event.key == pygame.K_f:
                    _manor_lvl = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
                    if _manor_lvl.get('type') == 'manor_stealth':
                        _sk_result = stealth_system.try_stealth_kill(
                            m.player_x + 15, m.player_y + 15,
                            reach=STEALTH_KILL_REACH_PX
                        )
                        if _sk_result["success"]:
                            _gx = int(_sk_result["x"])
                            _gy = int(_sk_result["y"])
                            m.score += 3000
                            m.save_manager.update_karma(STEALTH_KILL_KARMA)
                            m.player_karma = m.save_manager.get_karma()
                            m.enemies_killed_current_level += 1
                            m.karma_notification_text  = f"SESSİZ SUİKAST! KARMA +{STEALTH_KILL_KARMA}"
                            m.karma_notification_timer = 80
                            m.all_vfx.add(ParticleExplosion(_gx, _gy, (0, 200, 100), 14))
                            m.all_vfx.add(Shockwave(_gx, _gy, (0, 180, 80),
                                                  max_radius=60, rings=1, speed=10))
                            m.screen_shake = max(m.screen_shake, 3)
                            if stealth_system.active_guard_count() == 0:
                                from mission_system import mission_manager
                                mission_manager.complete_objective("eliminate_guards")
                        else:
                            _reason = _sk_result.get("reason", "BAŞARISIZ")
                            m.karma_notification_text  = f"SUİKAST BAŞARISIZ: {_reason}"
                            m.karma_notification_timer = 60

                # ── R TUŞU: ŞARJÖR DOLDUR ─────────────────────────────────────
                if event.key == pygame.K_r and m.GAME_STATE == 'PLAYING':
                    _manor_r = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
                    if _manor_r.get('type') != 'manor_stealth':
                        if m.active_weapon_obj is not None:
                            # inventory_manager slot'undan reload kontrolü
                            _inv_slot = inventory_manager.slot_for(m.active_weapon_obj.WEAPON_TYPE)
                            _can_reload = (_inv_slot is not None and _inv_slot.can_reload)
                            if _can_reload and m.active_weapon_obj.start_reload():
                                # inventory slot'unu da güncelle
                                if _inv_slot:
                                    _inv_slot.spare_mags  -= 0  # weapon_system.update() düşürecek
                                m.gun_cooldown = m.active_weapon_obj.cooldown
                                m.is_reloading = True
                                m.player_bullets = m.active_weapon_obj.bullets
                                if m.RELOAD_SOUND:
                                    audio_manager.play_sfx(m.RELOAD_SOUND)
                                m.karma_notification_text  = "ŞARJÖR DOLUYOR..."
                                m.karma_notification_timer = 40
                        elif not m.is_reloading and m.player_bullets < REVOLVER_MAX_BULLETS:
                            # Eski uyumluluk
                            m.is_reloading  = True
                            m.gun_cooldown  = REVOLVER_RELOAD_TIME
                            if m.RELOAD_SOUND:
                                audio_manager.play_sfx(m.RELOAD_SOUND)
                            m.karma_notification_text  = "ŞARJÖR DOLUYOR..."
                            m.karma_notification_timer = 40

                # ── 1/2 TUŞLARI: SİLAH DEĞİŞTİR ─────────────────────────────
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3) and m.GAME_STATE == 'PLAYING':
                    _slot = 0 if event.key == pygame.K_1 else (1 if event.key == pygame.K_2 else 2)
                    if _slot < len(m.inventory_weapons):
                        _switch_type = m.inventory_weapons[_slot]
                        # Zaten aktif silahsa değiştirme
                        if m.active_weapon_obj is None or m.active_weapon_obj.WEAPON_TYPE != _switch_type:
                            # switch_by_slot_index: per-type dict'ten doğru nesneyi alır
                            _switched = inventory_manager.switch_by_slot_index(_slot)
                            if _switched:
                                # Tipe özel nesne yoksa yeni oluştur ve kaydet
                                if inventory_manager.active_weapon is None:
                                    _new_wobj = create_weapon(_switch_type)
                                    if _new_wobj:
                                        inventory_manager.active_weapon = _new_wobj
                                # active_weapon artık doğru tipe ait nesneyi döner
                                m.active_weapon_obj = inventory_manager.active_weapon
                                _b, _s = inventory_manager.ammo_state()
                                if m.active_weapon_obj:
                                    m.active_weapon_obj.bullets    = _b
                                    m.active_weapon_obj.spare_mags = _s
                                m.player_bullets     = _b
                                m.is_reloading       = False
                                m.gun_cooldown       = 0.0
                                m.weapon_shoot_timer = 0.0
                                m.karma_notification_text  = f"SİLAH: {_switch_type.upper()}"
                                m.karma_notification_timer = 40

                if event.key == pygame.K_SPACE and m.player_hp.consume_stamina(COST_DASH) and not m.is_dashing:
                    m.is_dashing = True
                    # Malikane bölümünde dash mesafesi kısaltılır (kaçış adımı)
                    _manor_dash_cfg = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
                    m.dash_timer = (DASH_DURATION // 3) if _manor_dash_cfg.get('type') == 'manor_stealth' else DASH_DURATION
                    m.screen_shake = 8
                    m.dash_particles_timer = 0
                    m.dash_frame_counter = 0.0
                    m.character_state = 'dashing'
                    if m.DASH_SOUND:
                        audio_manager.play_sfx(m.DASH_SOUND)
                    m.all_vfx.add(ScreenFlash(m.METEOR_CORE, 80, 6))
                    m.all_vfx.add(Shockwave(px, py, m.METEOR_FIRE, max_radius=120, rings=2, speed=15))
                    keys = pygame.key.get_pressed()
                    dx = (keys[pygame.K_d] - keys[pygame.K_a])
                    dy = (keys[pygame.K_s] - keys[pygame.K_w])
                    if dx == 0 and dy == 0:
                        dx = 1
                    mag = math.sqrt(dx*dx + dy*dy)
                    m.dash_vx, m.dash_vy = (dx/mag)*DASH_SPEED, (dy/mag)*DASH_SPEED
                    m.is_jumping = True
                    m.y_velocity = 0
                    m.dash_angle = math.atan2(m.dash_vy, m.dash_vx)

                # ── DEBUG ARENA: Manuel Düşman Spawner (Numpad 1 / 2 / 3) ─
                # Güvenlik kapısı: Sadece PLAYING state + Debug Arena (ID:999)
                if m.GAME_STATE == 'PLAYING' and m.current_level_idx == 999:
                    # Zemin platformunun üst kenarı (debug_arena: LOGICAL_HEIGHT - 80)
                    _dbg_floor_top = LOGICAL_HEIGHT - 80
                    # Oyuncunun sağına +400 px ofset, ekran dışına çıkmasın
                    _dbg_spawn_x = min(int(m.player_x) + 400, LOGICAL_WIDTH - 50)

                    if event.key == pygame.K_KP1:
                        # CursedEnemy — standart yakın dövüş düşmanı (boy ~60px)
                        _dbg_y = _dbg_floor_top - 60
                        _dbg_enemy = CursedEnemy(_dbg_spawn_x, _dbg_y)
                        m.all_enemies.add(_dbg_enemy)
                        print(f"[DBG SPAWN] CursedEnemy → ({_dbg_spawn_x}, {_dbg_y})")

                    elif event.key == pygame.K_KP2:
                        # TankEnemy — ağır düşman (boy ~70px)
                        _dbg_y = _dbg_floor_top - 70
                        _dbg_enemy = TankEnemy(_dbg_spawn_x, _dbg_y)
                        m.all_enemies.add(_dbg_enemy)
                        print(f"[DBG SPAWN] TankEnemy  → ({_dbg_spawn_x}, {_dbg_y})")

                    elif event.key == pygame.K_KP3:
                        # DroneEnemy — uçan düşman, zeminden 150px yukarıda
                        _dbg_y = _dbg_floor_top - 60 - 150
                        _dbg_enemy = DroneEnemy(_dbg_spawn_x, _dbg_y)
                        m.all_enemies.add(_dbg_enemy)
                        print(f"[DBG SPAWN] DroneEnemy → ({_dbg_spawn_x}, {_dbg_y})")