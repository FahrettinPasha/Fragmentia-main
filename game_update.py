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

def update_game():
    """Oyun mantığı güncellemesi: fizik, dövüş, stealth, düşmanlar, pickuplar"""
    m = _m
    if m.GAME_STATE == 'LOADING':
        m.loading_timer += 1
        if m.loading_timer % 10 == 0 and m.loading_stage < len(m.fake_log_messages):
            m.loading_logs.append(m.fake_log_messages[m.loading_stage])
            m.loading_stage += 1
            m.loading_progress = min(0.95, m.loading_stage / len(m.fake_log_messages))
        if m.loading_stage >= len(m.fake_log_messages):
            m.loading_progress += 0.02
            if m.loading_progress >= 1.0:
                init_game()
                m.GAME_STATE = m.target_state_after_load

    elif m.GAME_STATE == 'CHAT' or m.GAME_STATE == 'CUTSCENE':
        m.story_manager.update(m.dt)
        if m.story_manager.is_cutscene:
            m.GAME_STATE = 'CUTSCENE'
        else:
            m.GAME_STATE = 'CHAT'

    elif m.GAME_STATE == 'NPC_CHAT':
        m.npc_cursor_timer += 1
        if m.npc_cursor_timer >= 30:
            m.npc_show_cursor = not m.npc_show_cursor
            m.npc_cursor_timer = 0

    elif m.GAME_STATE in ['PLAYING', 'ENDLESS_PLAY', 'TERMINAL']:
        current_karma = m.player_karma
        buff_stacks = (m.current_level_idx - 1) // 3
        if buff_stacks > 2:
            buff_stacks = 2
        base_speed_mult = 1.0 + (0.25 * buff_stacks)
        m.active_player_speed = PLAYER_SPEED * base_speed_mult

        # ── Karma Stamina Buff'ı ──────────────────────────────────────
        # Karma ±100'ü geçince stamina dolum hızı ve maksimum stamina artar.
        # Böylece iyi/kötü yolda kararlı oyuncular daha seri kombolar yapar.
        _karma_abs = abs(current_karma)
        if _karma_abs >= 100:
            m.player_hp.stamina_regen = STAMINA_REGEN_RATE * 1.5   # %50 daha hızlı regen
            m.player_hp.max_stamina   = int(PLAYER_MAX_STAMINA * 1.25)  # %25 daha fazla stamina
        elif _karma_abs >= 50:
            m.player_hp.stamina_regen = STAMINA_REGEN_RATE * 1.25
            m.player_hp.max_stamina   = PLAYER_MAX_STAMINA
        else:
            m.player_hp.stamina_regen = STAMINA_REGEN_RATE
            m.player_hp.max_stamina   = PLAYER_MAX_STAMINA
        # Mevcut stamina'yı yeni maksimumla sınırla
        m.player_hp.current_stamina = min(m.player_hp.current_stamina, float(m.player_hp.max_stamina))

        if m.vasil_companion:
            m.active_player_speed = PLAYER_SPEED * 1.5
            # Vasi varken stamina anında dolar (tam güç)
            m.player_hp.stamina_regen = STAMINA_REGEN_RATE * 4.0

        # ── MALİKANE STEALTHFİZİĞİ OVERRİDE ────────────────────────────
        # Normal bölüm hız hesaplamaları stealth için çok hızlı.
        # manor_stealth bölümünde tüm karma/level buff'ları bastırılır.
        _lvl_cfg_physics = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
        if _lvl_cfg_physics.get('type') == 'manor_stealth':
            m.active_player_speed   = PLAYER_SPEED * 0.80   # Normal'in %80'i

        lvl_config = m.EASY_MODE_LEVELS.get(m.current_level_idx, m.EASY_MODE_LEVELS[1])
        if lvl_config.get('type') == 'rest_area':
            if m.player_x > LOGICAL_WIDTH + 100:
                next_level = m.current_level_idx + 1
                if next_level in m.EASY_MODE_LEVELS:
                    m.current_level_idx = next_level
                    init_game()
                else:
                    m.GAME_STATE = 'GAME_COMPLETE'

        # ═════════════════════════════════════════════════════════════
        # GİZLİLİK SİSTEMİ — Her karede çalışır
        # ═════════════════════════════════════════════════════════════
        stealth_system.update(m.dt, m.player_x, m.player_y)

        # Stealth olaylarını oku (tespitler, karma bonusları, uyarılar)
        for stealth_event in stealth_system.poll_events():
            ev_type = stealth_event.get('type')
            if ev_type == 'detected':
                # Tespit edilince ekran sarsıntısı + karma cezası
                m.screen_shake = max(m.screen_shake, 10)
                m.save_manager.update_karma(-5)
                m.player_karma = m.save_manager.get_karma()
                m.karma_notification_text  = "TESPİT EDİLDİN! KARMA -5"
                m.karma_notification_timer = 90
                m.all_vfx.add(ScreenFlash((255, 50, 50), 80, 5))
            elif ev_type == 'stealth_bonus':
                # Başarılı gizlilik → karma bonusu
                bonus = stealth_event.get('value', 5)
                m.save_manager.update_karma(bonus)
                m.player_karma = m.save_manager.get_karma()
                m.karma_notification_text  = f"STEALTH BONUS! KARMA +{bonus}"
                m.karma_notification_timer = 70
            elif ev_type == 'alert':
                # Genel uyarı mesajı
                m.karma_notification_text  = stealth_event.get('message', 'UYARI!')
                m.karma_notification_timer = 60

        # ═════════════════════════════════════════════════════════════
        # GLOBAL DÖVÜŞ SİSTEMİ — Her bölümde çalışır
        # ═════════════════════════════════════════════════════════════

        # Kombo zamanlayıcısı + can yenileme her frame güncellenir
        m.combo_system.update(m.dt)
        m.player_hp.update(m.dt)

        # ── J/K Melee vuruş tespiti ───────────────────────────────────
        # Hedef havuzu: normal düşmanlar + arena düşmanları (eğer aktifse)
        _arena_targets = list(m.beat_arena.arena_enemies) if m.beat_arena.active else []
        _all_targets   = list(m.all_enemies) + _arena_targets
        melee_hits = m.combo_system.check_hits(_all_targets)
        for hit in melee_hits:
            _enemy  = hit["enemy"]
            _damage = hit["damage"]
            _vfx    = hit["vfx_type"]
            _hx, _hy = hit["hit_pos"]

            # Hasar uygula — ArenaEnemy veya normal düşman
            if hasattr(_enemy, 'take_damage'):
                _killed = _enemy.take_damage(_damage)
                m.score  += _damage * 10
                if _killed and not hasattr(_enemy, 'arena_id'):
                    # Normal düşman (CursedEnemy / DroneEnemy / TankEnemy) öldü → sprite sil
                    _enemy.kill()
                    # %18 ihtimalle can küresi düşür
                    if random.random() < 0.18:
                        _orb = HealthOrb(_enemy.rect.centerx, _enemy.rect.top)
                        m.all_health_orbs.add(_orb)
                    # Cephane düşürme (aktif silah varsa)
                    if m.active_weapon_obj is not None and random.random() < AMMO_DROP_CHANCE:
                        _ammo_drop = AmmoPickup(
                            _enemy.rect.centerx,
                            _enemy.rect.top,
                            m.active_weapon_obj.WEAPON_TYPE
                        )
                        m.all_ammo_pickups.add(_ammo_drop)
            else:
                # Fallback — take_damage metodu yoksa anında öldür
                _killed = True
                _enemy.kill()
                m.score  += 500

            # Kombo tetiklenince bildirim + skor bonusu
            if hit["combo"]:
                _combo_info = hit["combo"]
                m.score += _combo_info.get("score_bonus", 0)
                m.save_manager.update_karma(-_combo_info.get("karma", 2))
                m.player_karma = m.save_manager.get_karma()
                m.karma_notification_text  = f"KOMBO: {_combo_info['name']}!"
                m.karma_notification_timer = 70
            else:
                m.save_manager.update_karma(-2)
                m.player_karma = m.save_manager.get_karma()

            # VFX
            if _vfx == "explosion":
                m.all_vfx.add(ParticleExplosion(_hx, _hy, CURSED_PURPLE, 18))
            elif _vfx == "shockwave":
                m.all_vfx.add(Shockwave(_hx, _hy, CURSED_RED, max_radius=80, speed=12))
            elif _vfx == "lightning":
                m.all_vfx.add(LightningBolt(int(m.player_x + 15), int(m.player_y + 15),
                                          _hx, _hy, (100, 200, 255), life=8))
            else:
                m.all_vfx.add(FlameSpark(_hx, _hy, random.uniform(0, math.pi * 2),
                                       random.uniform(4, 10), (255, 150, 50), life=15))

            if _killed:
                m.enemies_killed_current_level += 1
                m.screen_shake = max(m.screen_shake, 8)
                m.all_vfx.add(ScreenFlash(CURSED_PURPLE, 40, 4))

        # VFX kuyruğunu boşalt
        for _ in m.combo_system.pop_vfx():
            pass

        # ── DASH → Tüm düşmanlara AOE hasar ─────────────────────────
        if m.is_dashing:
            _px_d = int(m.player_x + 15)
            _py_d = int(m.player_y + 15)
            _DASH_DMG    = 45
            _DASH_RADIUS = 110
            # Normal düşmanlar (all_enemies) — mevcut kod ile çakışmayı önlemek için
            # sadece ArenaEnemy türünü burada ele alıyoruz; CursedEnemy vb. zaten
            # mevcut sprite collision koduyla öldürülüyor (aşağıda).
            for _ae in _arena_targets:
                if not _ae.is_active:
                    continue
                _d = math.sqrt((_ae.rect.centerx - _px_d)**2 + (_ae.rect.centery - _py_d)**2)
                if _d < _DASH_RADIUS:
                    _dk = _ae.take_damage(_DASH_DMG, bypass_block=True)
                    m.score += _DASH_DMG * 8
                    m.save_manager.update_karma(-8)
                    m.player_karma = m.save_manager.get_karma()
                    m.all_vfx.add(ParticleExplosion(_ae.rect.centerx, _ae.rect.centery, m.METEOR_FIRE, 15))
                    m.all_vfx.add(Shockwave(_ae.rect.centerx, _ae.rect.centery,
                                          (255, 120, 0), max_radius=70, speed=14))
                    if _dk:
                        m.enemies_killed_current_level += 1
                        m.screen_shake = max(m.screen_shake, 10)
                        m.karma_notification_text  = "DASH STRIKE!"
                        m.karma_notification_timer = 40
                        m.all_vfx.add(ScreenFlash(m.METEOR_FIRE, 50, 4))

        # ── SLAM → Yere değdiğinde tüm düşmanlara AOE hasar ─────────
        if m.is_slamming and m.slam_stall_timer <= 0:
            _px_s = int(m.player_x + 15)
            _py_s = int(m.player_y + 30)
            _SLAM_DMG    = 60
            _SLAM_RADIUS = 140
            # Normal düşmanlar
            for _ne in list(m.all_enemies):
                if isinstance(_ne, EnemyBullet):
                    continue
                _ds = math.sqrt((_ne.rect.centerx - _px_s)**2 + (_ne.rect.centery - _py_s)**2)
                if _ds < _SLAM_RADIUS:
                    _slam_killed = False
                    if hasattr(_ne, 'take_damage'):
                        _slam_killed = _ne.take_damage(_SLAM_DMG)
                    else:
                        _slam_killed = True
                    if _slam_killed:
                        _ne.kill()
                        if random.random() < 0.18:
                            m.all_health_orbs.add(HealthOrb(_ne.rect.centerx, _ne.rect.top))
                    m.score += 500
                    m.save_manager.update_karma(-10)
                    m.player_karma = m.save_manager.get_karma()
                    m.enemies_killed_current_level += 1
                    m.all_vfx.add(ParticleExplosion(_ne.rect.centerx, _ne.rect.centery, PLAYER_SLAM, 18))
            # Arena düşmanları
            for _ae2 in _arena_targets:
                if not _ae2.is_active:
                    continue
                _ds2 = math.sqrt((_ae2.rect.centerx - _px_s)**2 + (_ae2.rect.centery - _py_s)**2)
                if _ds2 < _SLAM_RADIUS:
                    _sk = _ae2.take_damage(_SLAM_DMG, bypass_block=True)
                    m.score += _SLAM_DMG * 8
                    m.save_manager.update_karma(-10)
                    m.player_karma = m.save_manager.get_karma()
                    m.all_vfx.add(ParticleExplosion(_ae2.rect.centerx, _ae2.rect.centery, PLAYER_SLAM, 20))
                    m.all_vfx.add(Shockwave(_px_s, _py_s, PLAYER_SLAM, max_radius=_SLAM_RADIUS, speed=18))
                    if _sk:
                        m.enemies_killed_current_level += 1
                        m.screen_shake = max(m.screen_shake, 20)
                        m.karma_notification_text  = "SLAM KO!"
                        m.karma_notification_timer = 50
                        m.all_vfx.add(ScreenFlash(PLAYER_SLAM, 80, 6))

        # ═════════════════════════════════════════════════════════════
        # BEAT 'EM UP ARENA — Sadece arena bölümlerine özgü mantık
        # ═════════════════════════════════════════════════════════════
        if lvl_config.get('type') == 'beat_arena':
            m.camera_speed = 0   # Kamera sabit

            # Arena henüz başlamadıysa başlat
            if not m.beat_arena.active and not m.beat_arena.is_complete:
                m.beat_arena.start(lvl_config.get('arena_level_id', m.current_level_idx))

            # Arena düşmanlarını güncelle
            m.beat_arena.update(m.dt, m.frame_mul,
                              m.player_x + 15,
                              m.player_y + 15,
                              0.0)

            # Arena düşmanlarının oyuncuya saldırısı
            for atk in m.beat_arena.get_enemy_attacks():
                _pcx = atk.get("player_cx", m.player_x + 15)
                _pcy = atk.get("player_cy", m.player_y + 15)
                _dist_atk = math.sqrt((_pcx - atk["x"])**2 + (_pcy - atk["y"])**2)
                if _dist_atk < 120:
                    _died = m.player_hp.take_damage(atk["damage"])
                    m.screen_shake = max(m.screen_shake, 12)
                    m.all_vfx.add(ScreenFlash((255, 0, 0), 100, 6))
                    m.all_vfx.add(ParticleExplosion(int(m.player_x + 15), int(m.player_y + 15),
                                                  (220, 0, 0), 12))
                    if _died:
                        m.GAME_STATE = 'GAME_OVER'
                        m.high_score = max(m.high_score, int(m.score))
                        m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)
                        audio_manager.stop_music()

            # Ödül toplama
            _player_rect_d = pygame.Rect(int(m.player_x), int(m.player_y), 30, 30)
            for drop in m.beat_arena.collect_drops(_player_rect_d):
                if drop["type"] == "score":
                    m.score += drop["value"]
                    m.karma_notification_text  = f"+{drop['value']} PUAN!"
                    m.karma_notification_timer = 45
                elif drop["type"] == "karma":
                    m.save_manager.update_karma(drop["value"])
                    m.player_karma = m.save_manager.get_karma()
                    m.karma_notification_text  = f"KARMA +{drop['value']}"
                    m.karma_notification_timer = 45
                elif drop["type"] == "health":
                    m.player_hp.heal(25)
                    m.karma_notification_text  = "CAN +25"
                    m.karma_notification_timer = 45
                m.all_vfx.add(EnergyOrb(int(m.player_x + 15), int(m.player_y - 30),
                                      (255, 215, 0), 8, 20))

            # Tüm dalgalar temizlendi → bölüm geçişi
            if m.beat_arena.is_complete:
                m.score += m.beat_arena.total_bonus
                m.save_manager.update_karma(15)
                m.player_karma = m.save_manager.get_karma()
                m.beat_arena.reset()
                m.GAME_STATE = 'LEVEL_COMPLETE'
                m.save_manager.unlock_next_level('easy_mode', m.current_level_idx)
                m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)
        # ─────────────────────────────────────────────────────────────
        else:
            if m.current_level_idx != 99:
                if lvl_config.get('type') not in ('beat_arena', 'debug_arena'):
                    m.camera_speed = min(MAX_CAMERA_SPEED, m.camera_speed + SPEED_INCREMENT_RATE * m.frame_mul)
                score_gain = 0.1 * max(m.camera_speed, 1.0) * m.frame_mul
                if m.is_super_mode:
                    score_gain *= 40
                m.score += score_gain

        # ═════════════════════════════════════════════════════════════
        # MALİKANE KAMERA TAKİBİ — aşağıda platform collision sonrasına taşındı
        # ═════════════════════════════════════════════════════════════
        if lvl_config.get('type') != 'manor_stealth':
            m.manor_camera_offset_x = 0
            m.manor_camera_offset_y = 0

        # Silah yoksa klavye yönü geçerlidir

        old_x, old_y = m.player_x, m.player_y
        keys = pygame.key.get_pressed()
        horizontal_move = keys[pygame.K_d] - keys[pygame.K_a]
        if horizontal_move != 0 and not m.is_dashing and not m.is_slamming:
            m.character_state = 'running'
            m.player_direction = 1 if horizontal_move > 0 else -1  # Yön güncelle
        elif not m.is_jumping and not m.is_dashing and not m.is_slamming:
            m.character_state = 'idle'
            # player_direction değişmez → durduğunda son yönü korur

        # Silah yoksa klavye yönü geçerlidir
        is_grounded = not m.is_jumping and not m.is_slamming and not m.is_dashing
        m.character_animator.update(m.dt, m.character_state, is_grounded, m.y_velocity, m.is_dashing, m.is_slamming)

        m.last_trail_time += m.frame_mul
        if m.last_trail_time >= TRAIL_INTERVAL and (m.is_dashing or m.is_slamming):
            m.last_trail_time = 0.0
            trail_color = m.CURRENT_THEME["player_color"]
            if m.is_dashing:
                trail_color = m.METEOR_FIRE
                trail_size = random.randint(8, 14)
            elif m.is_slamming:
                trail_color = PLAYER_SLAM
                trail_size = random.randint(8, 12)
            m.trail_effects.append(TrailEffect(m.player_x + 15, m.player_y + 15, trail_color, trail_size, life=12))

        for wave in m.active_damage_waves[:]:
            wave['r'] += wave['speed'] * m.frame_mul
            wave['x'] -= m.camera_speed * m.frame_mul
            for enemy in list(m.all_enemies):
                dist = math.sqrt((enemy.rect.centerx - wave['x'])**2 + (enemy.rect.centery - wave['y'])**2)
                if dist < wave['r'] + 20 and dist > wave['r'] - 40:
                    _wave_killed = False
                    if hasattr(enemy, 'take_damage'):
                        _wave_killed = enemy.take_damage(80)
                    else:
                        _wave_killed = True
                    if _wave_killed:
                        enemy.kill()
                        if random.random() < 0.18:
                            m.all_health_orbs.add(HealthOrb(enemy.rect.centerx, enemy.rect.top))
                    m.score += 500
                    m.save_manager.update_karma(-10)
                    m.player_karma = m.save_manager.get_karma()
                    m.enemies_killed_current_level += 1
                    m.karma_notification_text = "KARMA DÜŞTÜ!"
                    m.karma_notification_timer = 60
                    m.all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, CURSED_PURPLE, 20))
                    m.all_vfx.add(ScreenFlash(CURSED_PURPLE, 30, 2))
            if wave['r'] > wave['max_r']:
                m.active_damage_waves.remove(wave)

        if m.is_dashing:
            px, py = int(m.player_x + 15), int(m.player_y + 15)
            m.dash_frame_counter += m.frame_mul
            for _ in range(4):
                inv_angle = m.dash_angle + math.pi + random.uniform(-0.5, 0.5)
                spark_speed = random.uniform(5, 15)
                color = random.choice([(255, 50, 0), (255, 150, 0), (255, 255, 100)])
                m.all_vfx.add(FlameSpark(px, py, inv_angle, spark_speed, color, life=20, size=random.randint(4, 8)))

            if int(m.dash_frame_counter) % 5 == 0:
                m.all_vfx.add(Shockwave(px, py, (255, 200, 100), max_radius=70, width=2, speed=10))

            meteor_hit_radius = 120
            enemy_hits_aoe = [e for e in m.all_enemies if math.sqrt((e.rect.centerx - px)**2 + (e.rect.centery - py)**2) < meteor_hit_radius]
            for enemy in enemy_hits_aoe:
                if isinstance(enemy, EnemyBullet):
                    continue
                _dash_killed = False
                if hasattr(enemy, 'take_damage'):
                    _dash_killed = enemy.take_damage(_DASH_DMG)
                else:
                    _dash_killed = True
                if _dash_killed:
                    enemy.kill()
                    # %18 ihtimalle can küresi düşür
                    if random.random() < 0.18:
                        m.all_health_orbs.add(HealthOrb(enemy.rect.centerx, enemy.rect.top))
                m.score += 500
                m.save_manager.update_karma(-10)
                m.player_karma = m.save_manager.get_karma()
                m.enemies_killed_current_level += 1
                m.karma_notification_text = "KARMA DÜŞTÜ!"
                m.karma_notification_timer = 60
                m.screen_shake = 10
                if m.EXPLOSION_SOUND:
                    audio_manager.play_sfx(m.EXPLOSION_SOUND)
                m.all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, m.METEOR_FIRE, 25))
                m.all_vfx.add(Shockwave(enemy.rect.centerx, enemy.rect.centery, (255, 100, 0), max_radius=90, width=4))

            if m.dash_particles_timer > 0:
                m.dash_particles_timer -= m.frame_mul
            else:
                m.dash_particles_timer = 4
                offset_x = random.randint(-5, 5)
                offset_y = random.randint(-5, 5)
                m.all_vfx.add(WarpLine(px + offset_x, py + offset_y, m.dash_angle + random.uniform(-0.15, 0.15), m.METEOR_CORE, m.METEOR_FIRE))

            m.player_x += m.dash_vx * m.frame_mul
            m.player_y += m.dash_vy * m.frame_mul
            m.player_x -= m.camera_speed * m.frame_mul

            m.dash_timer -= m.frame_mul
            if not m.vasil_companion:
                m.dash_timer -= m.frame_mul

            if m.dash_timer <= 0:
                m.is_dashing = False
        elif m.is_slamming and m.slam_stall_timer > 0:
            m.slam_stall_timer -= m.frame_mul
            m.slam_collision_check_frames += 1
            if int(m.slam_stall_timer) % 3 == 0:
                for _ in range(2):
                    angle = random.uniform(0, math.pi * 2)
                    dist = random.randint(20, 40)
                    ex = m.player_x + 15 + math.cos(angle) * dist
                    ey = m.player_y + 15 + math.sin(angle) * dist
                    m.all_vfx.add(FlameSpark(ex, ey, angle + math.pi, dist/10, PLAYER_SLAM, life=15))

            vibration = random.randint(-1, 1) if m.slam_stall_timer > 7 else 0
            m.player_x += vibration
            if m.slam_stall_timer <= 0:
                m.y_velocity = 30
                m.screen_shake = 12
                m.all_vfx.add(ParticleExplosion(m.player_x+15, m.player_y+15, PLAYER_SLAM, 12))
        else:
            if lvl_config.get('type') not in ('rest_area', 'manor_stealth', 'debug_arena'):
                m.player_x -= m.camera_speed * m.frame_mul
            if keys[pygame.K_a]:
                m.player_x -= m.active_player_speed * m.frame_mul
            if keys[pygame.K_d]:
                m.player_x += m.active_player_speed * m.frame_mul
            # Debug Arena: oyuncu ekran dışına çıkmasın
            if lvl_config.get('type') == 'debug_arena':
                m.player_x = max(0.0, min(m.player_x, float(LOGICAL_WIDTH - 28)))

            if m.is_super_mode:
                m.y_velocity = 0
                fly_speed = 15
                if keys[pygame.K_w]:
                    m.player_y -= fly_speed * m.frame_mul
                if keys[pygame.K_s]:
                    m.player_y += fly_speed * m.frame_mul
            else:
                m.player_y += m.y_velocity * m.frame_mul
                if m.is_slamming:
                    m.y_velocity += SLAM_GRAVITY * 1.8 * m.frame_mul
                else:
                    m.y_velocity += GRAVITY * m.frame_mul

        attack_sequence = []
        if attack_sequence:
            philosophical_combo = m.combat_philosophy.create_philosophical_combo(attack_sequence)
            if philosophical_combo:
                m.score *= philosophical_combo['power_multiplier']

        if m.reality_shifter.current_reality != 0:
            reality_effects = m.reality_shifter.get_current_effects()
            if 'physics' in reality_effects:
                physics = reality_effects['physics']
                if 'gravity' in physics:
                    m.y_velocity += (GRAVITY * physics['gravity'] - GRAVITY) * m.frame_mul
                if 'player_speed' in physics:
                    m.player_x += (PLAYER_SPEED * physics['player_speed'] - PLAYER_SPEED) * m.frame_mul

        if m.screen_shake > 0:
            m.screen_shake -= 1
        if m.karma_notification_timer > 0:
            m.karma_notification_timer -= 1

        # ── Silah nesnesi güncelle (cooldown, reload, SMG sekme) ───────────
        if m.active_weapon_obj is not None:
            m.active_weapon_obj.update(m.dt)
            m.gun_cooldown   = m.active_weapon_obj.cooldown
            m.is_reloading   = m.active_weapon_obj.is_reloading
            m.player_bullets = m.active_weapon_obj.bullets

            # ── DEBUG ARENA: Sınırsız cephane — şarjör bitince anında doldur
            if lvl_config.get('type') == 'debug_arena':
                if m.active_weapon_obj.bullets <= 0 and not m.active_weapon_obj.is_reloading:
                    m.active_weapon_obj.bullets    = m.active_weapon_obj.mag_size
                    m.active_weapon_obj.spare_mags = 9999
                    m.player_bullets = m.active_weapon_obj.bullets
                    m.active_weapon_obj.cooldown = 0.0

            # Dolum tamamlandıysa bildirim
            if m.is_reloading and m.active_weapon_obj.cooldown <= 0:
                m.karma_notification_text  = "ŞARJÖR TAMAM!"
                m.karma_notification_timer = 30

            # ── SMG OTOMATİK ATEŞ — sol tıka basılı tutunca sürekli ateş ──
            # get_pressed() değil mouse.get_pressed() kullanılır
            if m.active_weapon_obj.is_automatic and m.GAME_STATE == 'PLAYING':
                _manor_smg = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
                if _manor_smg.get('type') != 'manor_stealth':
                    _mouse_held = pygame.mouse.get_pressed()
                    if _mouse_held[0]:   # Sol tık basılı mı?
                        if m.active_weapon_obj.can_auto_fire(m.dt):
                            _fire_res = m.active_weapon_obj.fire()
                            if _fire_res:
                                m.player_bullets     = m.active_weapon_obj.bullets
                                m.gun_cooldown       = m.active_weapon_obj.cooldown
                                m.weapon_shoot_timer = m.active_weapon_obj.fire_interval
                                _smg_spread = getattr(m.active_weapon_obj, 'current_spread', 0.0)
                                _smg_angle  = m.aim_angle + random.uniform(-_smg_spread, _smg_spread)
                                _smg_muzzle = m.active_weapon_obj.get_muzzle_point(
                                    m.player_x + 15, m.player_y + 18, _smg_angle, m.active_weapon_obj.fire_interval
                                )
                                _px_proj = _smg_muzzle[0] if _smg_muzzle else m.player_x + 15 + math.cos(_smg_angle) * 14
                                _py_proj = _smg_muzzle[1] if _smg_muzzle else m.player_y + 18 + math.sin(_smg_angle) * 14
                                proj = PlayerProjectile(_px_proj, _py_proj, _smg_angle)
                                m.all_player_projectiles.add(proj)
                                if m.GUN_SHOT_SOUND:
                                    audio_manager.play_sfx(m.GUN_SHOT_SOUND)
                                m.all_vfx.add(ParticleExplosion(
                                    int(_px_proj + m.player_direction * 10), int(_py_proj),
                                    (0, 220, 255), 4
                                ))
                                m.screen_shake = max(m.screen_shake, 1)
        else:
            # Silah yok — eski altıpatar sayaç sistemi
            if m.gun_cooldown > 0:
                m.gun_cooldown = max(0.0, m.gun_cooldown - m.dt)
                if m.is_reloading and m.gun_cooldown <= 0:
                    m.is_reloading   = False
                    m.player_bullets = REVOLVER_MAX_BULLETS
                    m.karma_notification_text  = "ŞARJÖR TAMAM!"
                    m.karma_notification_timer = 30

        # Atış görsel sayacı azalt
        if m.weapon_shoot_timer > 0:
            m.weapon_shoot_timer = max(0.0, m.weapon_shoot_timer - m.dt)

        # ── Altıpatar sayaçları güncelle (eski uyumluluk — silah yoksa) ───
        if m.gun_cooldown > 0:
            m.gun_cooldown = max(0.0, m.gun_cooldown - m.dt)
            # Dolum tamamlandıysa şarjörü doldur
            if m.is_reloading and m.gun_cooldown <= 0:
                m.is_reloading   = False
                m.player_bullets = REVOLVER_MAX_BULLETS
                m.karma_notification_text  = "ŞARJÖR TAMAM!"
                m.karma_notification_timer = 30

        # ── Oyuncu mermilerini güncelle ──────────────────────────────────
        for _proj in list(m.all_player_projectiles):
            _proj.update(m.camera_speed, m.dt)

        # ── Mermi → düşman çarpışması ────────────────────────────────────
        _lvl_cfg_revolver = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
        if _lvl_cfg_revolver.get('type') != 'manor_stealth':
            _hit_dict = pygame.sprite.groupcollide(
                m.all_player_projectiles, m.all_enemies, True, False
            )
            for _proj_hit, _enemies_hit in _hit_dict.items():
                for _enemy_hit in _enemies_hit:
                    if hasattr(_enemy_hit, 'take_damage'):
                        _enemy_hit.take_damage(REVOLVER_DAMAGE)
                    m.score += 300
                    m.enemies_killed_current_level += 1
                    m.save_manager.update_karma(-5)  # Silah kullanımı karma maliyeti
                    m.player_karma = m.save_manager.get_karma()
                    m.karma_notification_text  = f"İSABET! -{REVOLVER_DAMAGE} HP"
                    m.karma_notification_timer = 30
                    m.all_vfx.add(ParticleExplosion(
                        _enemy_hit.rect.centerx, _enemy_hit.rect.centery,
                        (255, 100, 30), 10
                    ))
                    m.all_vfx.add(Shockwave(
                        _enemy_hit.rect.centerx, _enemy_hit.rect.centery,
                        (255, 150, 50), max_radius=50, rings=1, speed=10
                    ))
                    m.screen_shake = max(m.screen_shake, 3)
                    # Ölü düşman temizliği
                    if hasattr(_enemy_hit, 'is_active') and not _enemy_hit.is_active:
                        _enemy_hit.kill()
                        m.all_vfx.add(ParticleExplosion(
                            _enemy_hit.rect.centerx, _enemy_hit.rect.centery,
                            CURSED_PURPLE, 20
                        ))

            # Arena düşmanlarına da mermi isabet
            if lvl_config.get('type') == 'beat_arena':
                _arena_hit = pygame.sprite.groupcollide(
                    m.all_player_projectiles, m.beat_arena.arena_enemies, True, False
                )
                for _ap, _ae_list in _arena_hit.items():
                    for _ae in _ae_list:
                        if hasattr(_ae, 'take_damage'):
                            _ae.take_damage(REVOLVER_DAMAGE)
                        m.score += 300
                        m.all_vfx.add(ParticleExplosion(
                            _ae.rect.centerx, _ae.rect.centery,
                            (255, 100, 30), 10
                        ))

        PLAYER_W, PLAYER_H = 28, 42   # sprite boyutuyla eşleşir
        player_rect = pygame.Rect(int(m.player_x), int(m.player_y), PLAYER_W, PLAYER_H)
        dummy_player = type('',(object,),{'rect':player_rect})()
        enemy_hits = pygame.sprite.spritecollide(dummy_player, m.all_enemies, False)

        for enemy in enemy_hits:
            if m.has_talisman:
                enemy.kill()
                saved_soul = SavedSoul(enemy.rect.centerx, enemy.rect.centery)
                m.all_vfx.add(saved_soul)
                m.all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, (255, 215, 0), 20))
                m.all_vfx.add(Shockwave(enemy.rect.centerx, enemy.rect.centery, (255, 255, 200), max_radius=120, width=5))
                m.save_manager.update_karma(25)
                m.save_manager.add_saved_soul(1)
                m.score += 1000
                m.enemies_killed_current_level += 1
                m.karma_notification_text = "RUH KURTARILDI! (+25)"
                m.karma_notification_timer = 40
                continue

            if isinstance(enemy, EnemyBullet):
                _bullet_died = m.player_hp.take_damage(30)
                m.screen_shake = max(m.screen_shake, 10)
                m.all_vfx.add(ScreenFlash((255, 0, 0), 80, 5))
                enemy.kill()
                if _bullet_died:
                    m.GAME_STATE = 'GAME_OVER'
                    m.high_score = max(m.high_score, int(m.score))
                    m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)
                    audio_manager.stop_music()
                continue

            if m.is_dashing or m.is_slamming or m.is_super_mode:
                enemy.kill()
                m.score += 500
                if not m.is_super_mode:
                    m.save_manager.update_karma(-10)
                    m.enemies_killed_current_level += 1
                    m.karma_notification_text = "KARMA DÜŞTÜ!"
                    m.karma_notification_timer = 60
                m.screen_shake = 15
                if m.EXPLOSION_SOUND:
                    audio_manager.play_sfx(m.EXPLOSION_SOUND)
                m.all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, CURSED_PURPLE, 20))
                m.all_vfx.add(Shockwave(enemy.rect.centerx, enemy.rect.centery, GLITCH_BLACK, max_radius=80, width=5))
                pygame.time.delay(30)
            else:
                if m.player_karma <= -90 and not m.has_revived_this_run:
                    m.has_revived_this_run = True
                    m.karma_notification_text = "KARANLIK DİRİLİŞ AKTİF!"
                    m.karma_notification_timer = 120
                    m.screen_shake = 30
                    m.all_vfx.add(ScreenFlash((0, 0, 0), 150, 20))
                    for e in m.all_enemies:
                        e.kill()
                        m.all_vfx.add(ParticleExplosion(e.rect.centerx, e.rect.centery, CURSED_RED, 20))
                    m.active_damage_waves.append({'x': m.player_x + 15, 'y': m.player_y + 15, 'r': 10, 'max_r': 500, 'speed': 40})
                    m.y_velocity = -15
                    m.is_jumping = True
                else:
                    # --- CAN SİSTEMİ: Anlık ölüm yok, hasar al ---
                    _touch_died = m.player_hp.take_damage(20)
                    m.screen_shake = max(m.screen_shake, 12)
                    m.all_vfx.add(ScreenFlash((255, 0, 0), 80, 5))
                    m.all_vfx.add(ParticleExplosion(int(m.player_x + 15), int(m.player_y + 15), CURSED_RED, 10))
                    if _touch_died:
                        if m.current_level_idx == 10:
                            init_limbo()
                            m.GAME_STATE = 'PLAYING'
                            if m.npcs:
                                start_npc_conversation(m.npcs[0])
                        else:
                            m.GAME_STATE = 'GAME_OVER'
                            m.high_score = max(m.high_score, int(m.score))
                            m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)
                            audio_manager.stop_music()
                            m.all_vfx.add(ParticleExplosion(m.player_x, m.player_y, CURSED_RED, 30))

        move_rect = pygame.Rect(int(m.player_x), int(min(old_y, m.player_y)), PLAYER_W, int(abs(m.player_y - old_y)) + PLAYER_H)
        collided_platforms = pygame.sprite.spritecollide(type('',(object,),{'rect':move_rect})(), m.all_platforms, False)

        for p in collided_platforms:
            platform_top = p.rect.top
            if (old_y + PLAYER_H <= platform_top + 15) and (m.player_y + PLAYER_H >= platform_top):
                m.player_y = platform_top - PLAYER_H
                if m.is_slamming:
                    m.y_velocity = -15
                    m.screen_shake = 30
                    m.active_damage_waves.append({'x': m.player_x + 15, 'y': platform_top, 'r': 10, 'max_r': 250, 'speed': 25})
                    for i in range(2):
                        wave = Shockwave(m.player_x+15, p.rect.top, (255, 180, 80), speed=25)
                        wave.radius = 30 + i*30
                        wave.max_radius = 200 + i*60
                        m.all_vfx.add(wave)
                    m.all_vfx.add(ParticleExplosion(m.player_x+15, p.rect.top, PLAYER_SLAM, 25))
                    m.is_slamming = False
                    m.is_jumping = True
                    m.jumps_left = MAX_JUMPS - 1
                    m.character_state = 'jumping'
                else:
                    m.y_velocity = 0
                    m.is_jumping = m.is_slamming = False
                    m.jumps_left = MAX_JUMPS
                    m.character_state = 'idle'
                    m.all_vfx.add(ParticleExplosion(m.player_x+15, m.player_y+30, m.CURRENT_THEME["player_color"], 8))
                break

        # ── MALİKANE: Yatay duvar + kapı çarpışması ──────────────────────
        if lvl_config.get('type') == 'manor_stealth':
            # Dikey platform (duvar) çarpışması
            _wall_rect = pygame.Rect(int(m.player_x), int(m.player_y) + 4, PLAYER_W, PLAYER_H - 8)
            for _wp in m.all_platforms:
                if _wp.rect.height > _wp.rect.width:   # Dikey (duvar) platform
                    if _wall_rect.colliderect(_wp.rect):
                        if old_x + PLAYER_W <= _wp.rect.left + 6:
                            m.player_x = float(_wp.rect.left - PLAYER_W)
                        elif old_x >= _wp.rect.right - 6:
                            m.player_x = float(_wp.rect.right)

            # Kilitli kapı çarpışması — "CART CURT" sesi + geri it
            try:
                _door_rect_p = pygame.Rect(int(m.player_x) + 3, int(m.player_y) + 2,
                                           PLAYER_W - 6, PLAYER_H - 4)
                for _door in manor_doors:
                    if not _door.active:
                        continue
                    if _door_rect_p.colliderect(_door.rect):
                        # Sese bas (sadece ilk çarpışmada, spam olmasın)
                        if not getattr(_door, '_bump_cooldown', 0):
                            try:
                                import pygame as _pg
                                # Kısa metalik tıkırtı sesi — basit beep ile simüle
                                _bump_snd = _pg.sndarray.make_sound(
                                    __import__('numpy').array(
                                        [int(3000 * __import__('math').sin(
                                            i * 0.8 + __import__('math').sin(i * 0.3) * 2
                                        )) for i in range(4000)],
                                        dtype=__import__('numpy').int16
                                    ).reshape(-1, 1).repeat(2, axis=1)
                                )
                                _bump_snd.set_volume(0.4)
                                _bump_snd.play()
                            except Exception:
                                pass   # numpy yoksa sessiz geç
                            _door._bump_cooldown = 20   # 20 kare bekleme
                        else:
                            _door._bump_cooldown -= 1

                        # Kapıdan geri it
                        if old_x + PLAYER_W <= _door.rect.left + 10:
                            m.player_x = float(_door.rect.left - PLAYER_W - 1)
                        elif old_x >= _door.rect.right - 10:
                            m.player_x = float(_door.rect.right + 1)
                        else:
                            m.player_x = old_x
                        break
                    elif getattr(_door, '_bump_cooldown', 0):
                        _door._bump_cooldown = max(0, _door._bump_cooldown - 1)
            except NameError:
                pass   # manor_doors henüz tanımlanmamışsa sessizce geç

            # ── KAMERA TAKİBİ — tüm fizik & çarpışma sonrası ─────────────
            # Burada hesaplama yapılır ki kamera oyuncunun SON konumunu görsün.
            MANOR_MAP_WIDTH  = lvl_config.get('map_width',  3300)
            MANOR_MAP_HEIGHT = lvl_config.get('map_height', LOGICAL_HEIGHT)

            # Oyuncu merkezini hesapla
            _pcx = m.player_x + PLAYER_W / 2
            _pcy = m.player_y + PLAYER_H / 2

            # Kamera hedefi: oyuncu tam ortada olsun
            _target_cam_x = _pcx - LOGICAL_WIDTH  / 2
            _target_cam_y = _pcy - LOGICAL_HEIGHT / 2

            # Harita sınırları
            _cam_max_x = max(0, MANOR_MAP_WIDTH  - LOGICAL_WIDTH)
            _cam_max_y = max(0, MANOR_MAP_HEIGHT - LOGICAL_HEIGHT)
            _target_cam_x = max(0.0, min(float(_target_cam_x), float(_cam_max_x)))
            _target_cam_y = max(0.0, min(float(_target_cam_y), float(_cam_max_y)))

            # Hafif lerp (0.18) — kayışlı ama gecikmesiz hissini verir
            # Tam anlık istersen 1.0 yap
            _CAM_LERP = 0.22
            m.manor_camera_offset_x += (_target_cam_x - m.manor_camera_offset_x) * _CAM_LERP
            m.manor_camera_offset_y += (_target_cam_y - m.manor_camera_offset_y) * _CAM_LERP

            # ── Kasa alanı kontrolü ───────────────────────────────────────
            _safe_x = lvl_config.get("secret_safe_x", 2910)
            _safe_y = lvl_config.get("secret_safe_y", 230)
            _safe_r = lvl_config.get("secret_safe_radius", 100)
            _dx_safe = m.player_x - _safe_x
            _dy_safe = m.player_y - _safe_y
            if math.sqrt(_dx_safe * _dx_safe + _dy_safe * _dy_safe) < _safe_r:
                from mission_system import mission_manager
                mission_manager.set_flag("area_secret_safe", True)
                mission_manager.complete_objective("find_secret_safe")
                if stealth_system.active_guard_count() == 0:
                    mission_manager.complete_objective("eliminate_guards")
                if stealth_system.global_alert == 0:
                    mission_manager.complete_objective("stealth_optional_no_alert")
                    m.save_manager.update_karma(15)
                    m.player_karma = m.save_manager.get_karma()
                    m.karma_notification_text  = "MÜKEMMEL GİZLİLİK! KARMA +15"
                    m.karma_notification_timer = 120
                m.score += 20000
                m.GAME_STATE = 'LEVEL_COMPLETE'
                m.save_manager.unlock_next_level('easy_mode', m.current_level_idx)
                m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)

        # ── Can Küreleri (HealthOrb) güncelle + topla ─────────────────
        _player_rect_orb = pygame.Rect(int(m.player_x), int(m.player_y), PLAYER_W, PLAYER_H)
        for _orb in list(m.all_health_orbs):
            _orb.update(m.camera_speed, m.dt)
            if _player_rect_orb.colliderect(_orb.rect):
                m.player_hp.heal(HealthOrb.HEAL_AMOUNT)
                _orb.kill()
                m.karma_notification_text  = f"CAN +{HealthOrb.HEAL_AMOUNT}"
                m.karma_notification_timer = 45
                m.all_vfx.add(EnergyOrb(int(m.player_x + 15), int(m.player_y - 20), (0, 255, 80), 8, 20))

        # ── Silah Sandıkları güncelle ─────────────────────────────────
        for _wc in list(m.all_weapon_chests):
            _wc.update(m.camera_speed, m.dt)
            if _wc.rect.right < -50:   # Ekran dışı → sil
                _wc.kill()

        # ── Cephane Pickup'ları güncelle + topla ─────────────────────
        for _ap in list(m.all_ammo_pickups):
            _ap.update(m.camera_speed, m.dt)
            if _player_rect_orb.colliderect(_ap.rect):
                _added = 0
                if m.active_weapon_obj is not None and _ap.weapon_type == m.active_weapon_obj.WEAPON_TYPE:
                    # inventory_manager slot'unu güncelle
                    _added = inventory_manager.pickup_spare_mag(_ap.weapon_type, 1)
                    if _added == 0:
                        # Inventory slot yoksa doğrudan weapon_obj'ye ekle
                        m.active_weapon_obj.add_spare_mag(1)
                    else:
                        # weapon_obj'yi inventory slot ile senkronize et
                        _b, _s = inventory_manager.ammo_state()
                        m.active_weapon_obj.spare_mags = _s
                    m.player_bullets = m.active_weapon_obj.bullets
                _ap.kill()
                m.karma_notification_text  = "CEPHANELENDİN! +1 ŞARJÖR"
                m.karma_notification_timer = 40
                m.all_vfx.add(EnergyOrb(int(m.player_x + 15), int(m.player_y - 25),
                                      (255, 165, 0), 6, 15))

        for npc in m.npcs:
            npc.update(m.player_x, m.player_y, m.dt)
            action = m.vasil_companion.update(m.player_x, m.player_y, m.all_enemies, m.boss_manager_system, m.camera_speed)
            if action:
                act_type, target = action
                if act_type == "LASER":
                    pygame.draw.line(m.game_canvas, (0, 255, 100), (m.vasil_companion.x, m.vasil_companion.y), target.rect.center, 3)
                    target.kill()
                    m.all_vfx.add(ParticleExplosion(target.rect.centerx, target.rect.centery, (0, 255, 100), 15))
                    m.save_manager.update_karma(-5)
                    m.score += 1000

            if m.save_manager.get_karma() <= -250:
                m.vasil_companion.spike_timer += 1
                if m.vasil_companion.spike_timer > 120:
                    m.vasil_companion.spike_timer = 0
                    vis_plats = [p for p in m.all_platforms if 0 < p.rect.centerx < LOGICAL_WIDTH]
                    if vis_plats:
                        p = random.choice(vis_plats)
                        m.all_vfx.add(Shockwave(p.rect.centerx, p.rect.top, (0, 255, 100), max_radius=100, speed=15, rings=2))
                        for e in m.all_enemies:
                            if e.rect.colliderect(p.rect.inflate(0, -50)):
                                e.kill()
                                m.all_vfx.add(ParticleExplosion(e.rect.centerx, e.rect.centery, (0, 255, 100), 20))

        if m.current_level_idx in [11, 12, 13, 14, 15, 30] and m.save_manager.get_karma() <= -100 and m.vasil_companion is None:
            m.vasil_companion = VasilCompanion(m.player_x, m.player_y - 100)
            m.karma_notification_text = "VASİ KATILDI! (-100 KARMA)"
            m.karma_notification_timer = 120
            m.all_vfx.add(ScreenFlash((0, 255, 100), 100, 10))

        if m.current_level_idx in [11, 12, 13, 14, 15, 30] and m.save_manager.get_karma() == -250 and m.karma_notification_timer == 0:
             m.karma_notification_text = "VASİ TAM GÜÇ! (-250 KARMA)"
             m.karma_notification_timer = 120

        if m.current_level_idx == 30:
            if not m.level_15_cutscene_played:
                m.level_15_cutscene_played = True
                audio_manager.stop_music()
                cinematic_assets = m.asset_paths.copy()
                cinematic_assets['scenario'] = 'FINAL_MEMORY'
                AICutscene(m.screen, m.clock, cinematic_assets).run()
                m.last_time = pygame.time.get_ticks()
                m.level_15_timer = 0

                sound = load_sound_asset("assets/music/final_boss.mp3", generate_ambient_fallback, 1.0)
                audio_manager.play_music(sound)

            if not m.finisher_active:
                m.level_15_timer += m.dt
                for enemy in m.all_enemies:
                    if isinstance(enemy, (NexusBoss, AresBoss, VasilBoss)):
                        enemy.health = max(enemy.health, 1000)
                if m.level_15_timer >= 120.0:
                    m.finisher_active = True
                    m.finisher_state_timer = 0.0
                    m.finisher_type = 'GOOD' if m.player_karma >= 0 else 'BAD'
                    audio_manager.stop_music()
                    m.screen_shake = 50

            if m.finisher_active:
                m.finisher_state_timer += m.dt
                boss_target = None
                for e in m.all_enemies:
                    if isinstance(e, (NexusBoss, AresBoss, VasilBoss)):
                        boss_target = e
                        break
                if boss_target:
                    if m.finisher_type == 'GOOD':
                        if m.finisher_state_timer < 6.0:
                            if m.frame_count % 2 == 0:
                                start_x = random.choice([-100, LOGICAL_WIDTH + 100, random.randint(0, LOGICAL_WIDTH)])
                                start_y = -100 if start_x > 0 and start_x < LOGICAL_WIDTH else random.randint(0, LOGICAL_HEIGHT)
                                soul = SavedSoul(start_x, start_y)
                                dx = boss_target.x - start_x
                                dy = boss_target.y - start_y
                                dist = math.sqrt(dx*dx + dy*dy)
                                soul.vy = (dy / dist) * 25
                                soul.x += (dx / dist) * 25
                                m.all_vfx.add(soul)
                                bx = boss_target.x + random.randint(-50, 50)
                                by = boss_target.y + random.randint(-50, 50)
                                m.all_vfx.add(ParticleExplosion(bx, by, (0, 255, 255), 15))
                                m.all_vfx.add(Shockwave(bx, by, (255, 255, 100), max_radius=50, speed=10))
                            m.karma_notification_text = "TÜM DOSTLAR SALDIRIYOR!"
                            m.karma_notification_timer = 2
                        elif m.finisher_state_timer > 6.0:
                            boss_target.health = 0
                    elif m.finisher_type == 'BAD':
                        center_x = m.player_x
                        center_y = m.player_y
                        if m.vasil_companion:
                            center_x = m.vasil_companion.x
                            center_y = m.vasil_companion.y
                        if m.finisher_state_timer < 3.0:
                            if m.frame_count % 2 == 0:
                                angle = random.uniform(0, math.pi*2)
                                dist = 300 - (m.finisher_state_timer * 100)
                                px = center_x + math.cos(angle) * dist
                                py = center_y + math.sin(angle) * dist
                                pygame.draw.line(m.vfx_surface, (255, 0, 0), (px, py), (center_x, center_y), 2)
                                m.all_vfx.add(EnergyOrb(px, py, (255, 50, 50), 4, 10))
                            m.karma_notification_text = "VASİ: KIYAMET PROTOKOLÜ..."
                            m.karma_notification_timer = 2
                        elif 3.0 <= m.finisher_state_timer < 5.0:
                            if int(m.finisher_state_timer * 10) % 5 == 0:
                                m.screen_shake = 100
                                m.all_vfx.add(ScreenFlash((255, 255, 255), 255, 60))
                                m.all_vfx.add(Shockwave(center_x, center_y, (255, 0, 0), max_radius=2000, width=50, speed=100))
                                for _ in range(20):
                                    rx = random.randint(0, LOGICAL_WIDTH)
                                    ry = random.randint(0, LOGICAL_HEIGHT)
                                    m.all_vfx.add(ParticleExplosion(rx, ry, (255, 0, 0), 40))
                        elif m.finisher_state_timer > 5.0:
                            boss_target.health = 0

        if m.current_level_idx in [10, 30]:
            m.boss_manager_system.update_logic(m.current_level_idx, m.all_platforms, m.player_x, m.player_karma, m.camera_speed, m.frame_mul, is_weakened=False)
            player_hitbox = pygame.Rect(m.player_x + 5, m.player_y + 5, 20, 20)
            player_obj_data = {'x': m.player_x, 'y': m.player_y}
            is_hit = m.boss_manager_system.check_collisions(player_hitbox, player_obj_data, m.all_vfx, m.save_manager)
            if is_hit:
                m.screen_shake = 20
                m.all_vfx.add(ScreenFlash((255, 0, 0), 150, 5))
                m.all_vfx.add(ParticleExplosion(m.player_x + 15, m.player_y + 15, (200, 0, 0), 25))
                m.player_x -= 40
                m.y_velocity = -10
                current_k = m.save_manager.get_karma()
                damage = 75
                if current_k > 0:
                    m.save_manager.update_karma(-damage)
                elif current_k < 0:
                    m.save_manager.update_karma(damage)
                new_k = m.save_manager.get_karma()
                if abs(new_k) < 50:
                    m.save_manager.data["karma"] = 0
                    m.save_manager.save_data()
                    if m.current_level_idx == 10:
                        init_limbo()
                        m.GAME_STATE = 'PLAYING'
                        if m.npcs:
                            start_npc_conversation(m.npcs[0])
                    else:
                        m.GAME_STATE = 'GAME_OVER'
                        m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)
                        audio_manager.stop_music()
                else:
                    m.karma_notification_text = "İRADE HASAR ALDI!"
                    m.karma_notification_timer = 40

        lvl_config = m.EASY_MODE_LEVELS.get(m.current_level_idx, {})
        if lvl_config.get('type') == 'scrolling_boss' or m.current_level_idx == 30:
            boss_obj = None
            for e in m.all_enemies:
                if isinstance(e, (NexusBoss, AresBoss, VasilBoss)):
                    boss_obj = e
                    break
            if boss_obj:
                target_x = m.player_x + 550
                boss_obj.x = target_x
                boss_obj.rect.x = int(boss_obj.x)

        if m.GAME_STATE == 'PLAYING' and lvl_config.get('type') not in ('rest_area', 'beat_arena', 'manor_stealth', 'debug_arena'):
            base_goal = m.EASY_MODE_LEVELS.get(m.current_level_idx, m.EASY_MODE_LEVELS[1])['goal_score']
            lvl_goal = base_goal * 0.75
            # goal_score=0 olan bölümleri de standart kontrolden dışla
            # (Skor=0 → eşik=0 → ilk karede True → anlık kazanma hatası)
            if m.current_level_idx < 30 and lvl_goal > 0 and m.score >= lvl_goal:
                if m.enemies_killed_current_level == 0:
                    m.save_manager.update_karma(50)
                    m.karma_notification_text = "PASİFİST BONUSU! (+50 KARMA)"
                else:
                    m.save_manager.update_karma(5)
                m.GAME_STATE = 'LEVEL_COMPLETE'
                m.save_manager.unlock_next_level('easy_mode', m.current_level_idx)
                m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)

            m.all_platforms.update(m.camera_speed * m.frame_mul)

        m.all_enemies.update(m.camera_speed * m.frame_mul, m.dt, (m.player_x, m.player_y))
        for enemy in m.all_enemies:
            if hasattr(enemy, 'spawn_queue') and enemy.spawn_queue:
                for projectile in enemy.spawn_queue:
                    m.all_enemies.add(projectile)
            enemy.spawn_queue = []

        if lvl_config.get('type') == 'boss_fight' or m.current_level_idx == 30:
            boss_alive = False
            boss_obj = None
            for e in m.all_enemies:
                if isinstance(e, (NexusBoss, AresBoss, VasilBoss)):
                    boss_alive = True
                    boss_obj = e
                    break
            if not boss_alive and m.current_level_idx == 30:
                m.score += 150000
                audio_manager.stop_music()
                final_karma = m.save_manager.get_karma()
                ending_scenario = "GOOD_ENDING" if final_karma >= 0 else "BAD_ENDING"
                ending_assets = m.asset_paths.copy()
                ending_assets['scenario'] = ending_scenario
                final_cutscene = AICutscene(m.screen, m.clock, ending_assets)
                final_cutscene.run()
                m.GAME_STATE = 'GAME_COMPLETE'
                m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)

        for s in m.stars:
            s.update(m.camera_speed * m.frame_mul)
        m.all_vfx.update(m.camera_speed * m.frame_mul)

        for trail in m.trail_effects[:]:
            try:
                trail.update(m.camera_speed * m.frame_mul)
            except:
                trail.update(m.camera_speed * m.frame_mul, m.dt)
            if trail.life <= 0:
                m.trail_effects.remove(trail)

        if lvl_config.get('type') not in ('rest_area', 'beat_arena', 'debug_arena') and m.current_level_idx != 99:
            if m.current_level_idx <= 30:
                if len(m.all_platforms) > 0 and max(p.rect.right for p in m.all_platforms) < LOGICAL_WIDTH + 100:
                    add_new_platform()

        if m.player_y > LOGICAL_HEIGHT + 100:
            if m.current_level_idx == 10:
                init_limbo()
                m.GAME_STATE = 'PLAYING'
                if m.npcs:
                    start_npc_conversation(m.npcs[0])
            elif m.current_level_idx == 99:
                m.player_y = LOGICAL_HEIGHT - 300
                m.player_x = 100
                m.y_velocity = 0
            elif lvl_config.get('type') == 'beat_arena':
                # Arena zemininde yere gömme — sadece pozisyonu düzelt
                m.player_y = LOGICAL_HEIGHT - 150
                m.y_velocity = 0
            elif lvl_config.get('type') == 'manor_stealth':
                # Malikane'de düşme → ölüm yok, başlangıç noktasına respawn
                m.player_x, m.player_y = 120.0, float(LOGICAL_HEIGHT - 110)
                m.y_velocity = 0
                m.is_jumping = m.is_dashing = m.is_slamming = False
                m.jumps_left = MAX_JUMPS
            elif lvl_config.get('type') == 'debug_arena':
                # Debug Arena: zemin ortasına ışınlan, oyun kesilmez
                m.player_x = float(LOGICAL_WIDTH // 2 - 14)
                m.player_y = float(LOGICAL_HEIGHT - 80 - 42)
                m.y_velocity = 0
                m.is_jumping = m.is_dashing = m.is_slamming = False
                m.jumps_left = MAX_JUMPS
            else:
                m.GAME_STATE = 'GAME_OVER'
                m.high_score = max(m.high_score, int(m.score))
                m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)
                audio_manager.stop_music()
                m.all_vfx.add(ParticleExplosion(m.player_x, m.player_y, (255, 0, 0), 30))

        if m.player_x < -50:
            if m.current_level_idx == 10:
                init_limbo()
                m.GAME_STATE = 'PLAYING'
                if m.npcs:
                    start_npc_conversation(m.npcs[0])
            elif m.current_level_idx == 99:
                m.player_x = 50
            elif lvl_config.get('type') == 'beat_arena':
                m.player_x = 50   # Arena sınırı — soldan çıkış yok
            else:
                m.GAME_STATE = 'GAME_OVER'
                m.high_score = max(m.high_score, int(m.score))
                m.save_manager.update_high_score('easy_mode', m.current_level_idx, m.score)
                audio_manager.stop_music()
                m.all_vfx.add(ParticleExplosion(m.player_x, m.player_y, (255, 0, 0), 30))

        # Arena sağ sınırı
        if lvl_config.get('type') == 'beat_arena' and m.player_x > LOGICAL_WIDTH - 50:
            m.player_x = LOGICAL_WIDTH - 50

        m.rest_area_manager.update((m.player_x, m.player_y))

    ui_data = {
        'theme': m.CURRENT_THEME,
        'score': m.score,
        'high_score': m.high_score,
        'time_ms': m.time_ms,
        'settings': m.game_settings,
        'progress': m.loading_progress,
        'logs': m.loading_logs,
        'save_data': m.save_manager.data,
        'level_idx': m.current_level_idx,
        'level_data': m.EASY_MODE_LEVELS.get(m.current_level_idx, m.EASY_MODE_LEVELS[1]),
        'story_manager': m.story_manager,
        'philosophical_core': philosophical_core,
        'reality_shifter': m.reality_shifter,
        'time_layer': m.time_layer,
        'combat_philosophy': m.combat_philosophy,
        'endless_modes': m.endless_modes,
        'current_mode': m.endless_modes.current_mode if m.GAME_STATE == 'ENDLESS_PLAY' else None,
        'world_reactor': m.world_reactor,
        'npcs': m.npcs,
        'current_npc': m.current_npc,
        'npc_conversation_active': m.npc_conversation_active,
        'npc_chat_input': m.npc_chat_input,
        'npc_chat_history': m.npc_chat_history,
        'karma': m.player_karma,
        'kills': m.enemies_killed_current_level,
        'term_input': m.terminal_input,
        'term_status': m.terminal_status,
        'is_debug_arena': (m.current_level_idx == 999),
        'level_select_page': m.level_select_page,
        'has_talisman': m.has_talisman,
        # --- DÖVÜŞ SİSTEMİ ---
        'beat_arena_active': m.beat_arena.active,
        'arena_wave':  m.beat_arena.current_wave,
        'arena_total': m.beat_arena.total_waves,
        'combo_info':  m.combo_system.get_hud_info(),
        'player_hp':   m.player_hp.current_hp,
        'player_hp_max': m.player_hp.max_hp,
        # --- STAMINA ---
        'stamina':     m.player_hp.current_stamina,
        'stamina_max': m.player_hp.max_stamina,
        # --- ALTIPATAR ---
        'player_bullets': m.player_bullets,
        'gun_cooldown':   m.gun_cooldown,
        'is_reloading':   m.is_reloading,
        # --- YENİ SİLAH SİSTEMİ ---
        'active_weapon':  m.active_weapon_obj.WEAPON_TYPE if m.active_weapon_obj else None,
        'mag_size':       m.active_weapon_obj.mag_size if m.active_weapon_obj else 0,
        'spare_mags':     m.active_weapon_obj.spare_mags if m.active_weapon_obj else 0,
        'inventory_weapons': list(m.inventory_weapons),
        'chest_prompt':   any(
            math.sqrt((m.player_x + 14 - _c.rect.centerx)**2 + (m.player_y + 21 - _c.rect.centery)**2)
            < WeaponChest.INTERACT_RADIUS
            for _c in m.all_weapon_chests
        ),
    }