# level_init.py
# =============================================================================
# FRAGMENTIA — Seviye Başlatma ve Geçiş Fonksiyonları
# =============================================================================
# main.py'dan ayrıştırılmıştır.
# Paylaşılan durum değişkenlerine _m (main modül referansı) üzerinden erişir.
# Kullanım: main.py içinde `level_init.register_main_module(sys.modules[__name__])`
# çağrıldıktan sonra bu modüldeki tüm fonksiyonlar kullanılabilir olur.
# =============================================================================

import pygame
import random
import gc

from settings import *
from settings import STEALTH_KILL_REACH_PX, STEALTH_KILL_KARMA
from game_config import (EASY_MODE_LEVELS, BULLET_SPEED, BOSS_HEALTH, BOSS_DAMAGE,
                         BOSS_FIRE_RATE, BOSS_INVULNERABILITY_TIME,
                         LIMBO_VASIL_PROMPT, LIMBO_ARES_PROMPT,
                         CURSED_PURPLE, GLITCH_BLACK, CURSED_RED)
from settings import (COST_DASH, COST_SLAM, COST_HEAVY, COST_LIGHT,
                      PLAYER_MAX_STAMINA, STAMINA_REGEN_RATE, STAMINA_REGEN_DELAY,
                      REVOLVER_MAX_BULLETS, REVOLVER_DAMAGE, REVOLVER_COOLDOWN,
                      REVOLVER_RELOAD_TIME, PLAYER_BULLET_SPEED)
from entities import (Platform, NPC, CursedEnemy, DroneEnemy, TankEnemy,
                      ParallaxBackground, WeaponChest, AmmoPickup)
from weapon_system import create_weapon
from inventory_manager import inventory_manager
from stealth_system import stealth_system
from utils import (load_sound_asset, generate_ambient_fallback,
                   generate_calm_ambient, audio_manager)
from local_bosses import NexusBoss, AresBoss, VasilBoss
from combat_system import PlayerHealth
from gutter_rest_area import gutter_rest_area

# ---------------------------------------------------------------------------
# MODÜL REFERANS SİSTEMİ
# ---------------------------------------------------------------------------
_m = None  # main.py modül nesnesi — register_main_module() ile doldurulur.

def register_main_module(main_module):
    """
    main.py modül referansını kaydeder.
    run_game_loop() çalışmadan önce mutlaka çağrılmalıdır.
    """
    global _m
    _m = main_module

# =============================================================================
# GUARDIAN (VASİ) KESİNTİ TETİKLEYİCİSİ
# =============================================================================

def trigger_guardian_interruption():
    """Karma sıfırlandığında Vasi'nin araya girip savaşı durdurması."""
    m = _m
    m.boss_manager_system.clear_all_attacks()
    m.all_enemies.empty()
    m.GAME_STATE = 'CHAT'
    m.story_manager.set_dialogue(
        "VASI",
        "SİSTEM UYARISI: İrade bütünlüğü kritik seviyenin altında... Müdahale ediliyor.",
        is_cutscene=True
    )

# =============================================================================
# EKRAN / AYARLAR
# =============================================================================

def apply_display_settings():
    m = _m
    target_res = AVAILABLE_RESOLUTIONS[m.game_settings['res_index']]
    if m.game_settings['fullscreen']:
        m.current_display_w, m.current_display_h = LOGICAL_WIDTH, LOGICAL_HEIGHT
        flags = pygame.SCALED | pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
    else:
        m.current_display_w, m.current_display_h = target_res
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
    m.screen = pygame.display.set_mode(
        (m.current_display_w, m.current_display_h), flags, vsync=1
    )

# =============================================================================
# PLATFORM ÜRETME
# =============================================================================

def add_new_platform(start_x=None):
    m = _m
    if start_x is None:
        if len(m.all_platforms) > 0:
            rightmost = max(m.all_platforms, key=lambda p: p.rect.right)
            gap = random.randint(GAP_MIN, GAP_MAX)
            start_x = rightmost.rect.right + gap
        else:
            start_x = LOGICAL_WIDTH

    width = random.randint(PLATFORM_MIN_WIDTH, PLATFORM_MAX_WIDTH)
    y = random.choice(PLATFORM_HEIGHTS)
    new_plat = Platform(start_x, y, width, 50)
    m.all_platforms.add(new_plat)

    if m.current_level_idx in [10, 30]:
        return

    has_enemy = False
    lvl_props = EASY_MODE_LEVELS.get(m.current_level_idx, {})

    if not lvl_props.get("no_enemies") and width > 120 and random.random() < 0.4:
        enemy_roll = random.random()
        if m.current_level_idx >= 7 and enemy_roll < 0.15:
            enemy = TankEnemy(new_plat)
        elif m.current_level_idx >= 4 and enemy_roll < 0.35:
            drone_y = y - random.randint(50, 150)
            enemy = DroneEnemy(new_plat.rect.centerx, drone_y)
        else:
            enemy = CursedEnemy(new_plat)
        m.all_enemies.add(enemy)
        has_enemy = True

    if has_enemy:
        safe_gap = random.randint(150, 250)
        safe_start_x = new_plat.rect.right + safe_gap
        safe_width = random.randint(PLATFORM_MIN_WIDTH, PLATFORM_MAX_WIDTH)
        possible_heights = [h for h in PLATFORM_HEIGHTS if abs(h - y) <= VERTICAL_GAP]
        if not possible_heights:
            possible_heights = PLATFORM_HEIGHTS
        safe_y = random.choice(possible_heights)
        safe_plat = Platform(safe_start_x, safe_y, safe_width, 50)
        safe_plat.theme_index = m.CURRENT_THEME
        m.all_platforms.add(safe_plat)
    elif width >= CHEST_MIN_PLATFORM_W and random.random() < CHEST_SPAWN_CHANCE:
        chest = WeaponChest(new_plat.rect)
        m.all_weapon_chests.add(chest)

# =============================================================================
# YÜKLENİYOR EKRANI
# =============================================================================

def start_loading_sequence(next_state_override=None):
    m = _m
    m.GAME_STATE = 'LOADING'
    m.loading_progress = 0.0
    m.loading_logs = []
    m.loading_timer = 0
    m.loading_stage = 0
    m.target_state_after_load = next_state_override if next_state_override else 'PLAYING'
    # --- OPTİMİZASYON: Yükleme ekranında çöp topla ---
    gc.collect()
    m.MAX_VFX_COUNT = 100
    m.MAX_DASH_VFX_PER_FRAME = 5

# =============================================================================
# HIKÂYE BÖLÜMÜ BAŞLATMA
# =============================================================================

def start_story_chapter(chapter_id):
    m = _m
    m.story_manager.load_chapter(chapter_id)
    m.GAME_STATE = 'CHAT'

    if chapter_id == 0:
        m.all_platforms.empty()
        m.all_enemies.empty()
        m.all_vfx.empty()
        base_plat = Platform(0, LOGICAL_HEIGHT - 100, LOGICAL_WIDTH, 100, theme_index=2)
        m.all_platforms.add(base_plat)
        bed1 = Platform(400, LOGICAL_HEIGHT - 180, 200, 30, theme_index=2)
        bed2 = Platform(800, LOGICAL_HEIGHT - 180, 200, 30, theme_index=2)
        m.all_platforms.add(bed1)
        m.all_platforms.add(bed2)
        m.player_x, m.player_y = 200.0, float(LOGICAL_HEIGHT - 250)
        m.y_velocity = 0
        m.camera_speed = 0
        m.CURRENT_THEME = THEMES[2]
        m.active_background = ParallaxBackground(
            f"{BG_DIR}/gutter_far.png", speed_mult=0.0
        )

# =============================================================================
# DİNLENME ALANI BAŞLATMA
# =============================================================================

def init_rest_area():
    m = _m
    m.camera_speed = 0
    m.CURRENT_THEME = THEMES[4]
    m.all_platforms.empty()
    platform_width = 400
    gap = 200
    npc_spawn_index = 0

    for i in range(len(NPC_PERSONALITIES)):
        personality = NPC_PERSONALITIES[i]
        name = NPC_NAMES[i]
        color = NPC_COLORS[i]
        if personality == "merchant":
            continue
        if personality == "warrior" and m.player_karma <= 0:
            continue

        x = npc_spawn_index * (platform_width + gap) + 200
        y = LOGICAL_HEIGHT - 100
        platform = Platform(x, y, platform_width, 50, theme_index=4)
        m.all_platforms.add(platform)
        npc_x = x + platform_width // 2
        npc_y = y - 80
        prompt = NPC_PROMPTS.get(personality, "...")
        npc = NPC(npc_x, npc_y, name, color, personality, prompt)
        if personality == "philosopher":
            npc.talk_radius = 250
        m.npcs.append(npc)
        npc_spawn_index += 1

    center_x = (npc_spawn_index * (platform_width + gap)) + 200
    center_platform = Platform(center_x, LOGICAL_HEIGHT - 150, 600, 60, theme_index=4)
    m.all_platforms.add(center_platform)

# =============================================================================
# GUTTER DİNLENME ALANI BAŞLATMA
# =============================================================================

def init_gutter_rest_area():
    """
    The Gutter'a özgü çok katlı dinlenme alanını başlatır.
    Manor kamera sistemi kullanılır — oyuncu haritayı özgürce gezer.

    Katlar:
      - Zemin  (Y = LH - 80)  → Pazar yeri, 4 NPC
      - Orta   (Y = LH - 330) → Bar/atölye, 3 NPC
      - Çatı   (Y = LH - 580) → Gizli figürler, 2 NPC
    """
    m = _m
    m.camera_speed = 0
    m.CURRENT_THEME = THEMES[2]   # Gutter teması

    # Manor kamera sistemini sıfırla — oyuncu haritayı scroll ederek gezer
    m.manor_camera_offset_x = 0
    m.manor_camera_offset_y = 0

    # Haritayı ve NPC'leri oluştur
    gutter_rest_area.init(m)

    # Oyuncu spawn noktası — giriş platformu üzeri
    m.player_x = 200.0
    m.player_y = float(LOGICAL_HEIGHT - 200)
    m.y_velocity = 0

# =============================================================================
# LİMBO BAŞLATMA
# =============================================================================

def init_limbo():
    m = _m
    m.boss_manager_system.reset()
    m.current_level_idx = 99
    m.all_platforms.empty()
    m.all_enemies.empty()
    m.all_vfx.empty()
    m.npcs.clear()
    m.camera_speed = 0
    m.y_velocity = 0
    m.CURRENT_THEME = THEMES[2]

    # Limbo için arka plan (karanlık gutter teması)
    m.active_background = ParallaxBackground(
        f"{BG_DIR}/gutter_far.png", speed_mult=0.0
    )

    center_plat = Platform(LOGICAL_WIDTH//2 - 400, LOGICAL_HEIGHT - 150, 800, 50, theme_index=4)
    m.all_platforms.add(center_plat)
    m.player_x = LOGICAL_WIDTH // 2 - 100
    m.player_y = LOGICAL_HEIGHT - 250

    karma = m.save_manager.get_karma()
    npc_name = ""
    npc_prompt = ""
    npc_color = (255, 255, 255)
    personality = "guide"

    if karma >= 0:
        npc_name = "SAVAŞÇI ARES"
        npc_prompt = LIMBO_ARES_PROMPT
        npc_color = (255, 50, 50)
        personality = "warrior"
    else:
        npc_name = "VASİ"
        npc_prompt = LIMBO_VASIL_PROMPT
        npc_color = (0, 255, 100)
        personality = "philosopher"

    limbo_npc = NPC(
        x=LOGICAL_WIDTH // 2 + 100,
        y=LOGICAL_HEIGHT - 230,
        name=npc_name,
        color=npc_color,
        personality_type=personality,
        prompt=npc_prompt
    )
    limbo_npc.ai_active = True
    m.npcs.append(limbo_npc)
    audio_manager.stop_music()

# =============================================================================
# KURTULUŞ MODU BAŞLATMA
# =============================================================================

def init_redemption_mode():
    m = _m
    m.current_level_idx = 11
    m.has_talisman = True
    m.all_platforms.empty()
    m.all_enemies.empty()
    m.all_vfx.empty()
    m.npcs.clear()
    m.boss_manager_system.reset()
    m.CURRENT_THEME = THEMES[0]
    start_plat = Platform(0, LOGICAL_HEIGHT - 100, 600, 50)
    m.all_platforms.add(start_plat)
    m.player_x = 100
    m.player_y = LOGICAL_HEIGHT - 250
    m.camera_speed = INITIAL_CAMERA_SPEED * 1.5
    m.y_velocity = 0

    sound = load_sound_asset("assets/music/cyber_chase.mp3", generate_ambient_fallback, 0.8)
    audio_manager.play_music(sound)

# =============================================================================
# SOYKIKIM MODU BAŞLATMA
# =============================================================================

def init_genocide_mode():
    m = _m
    m.current_level_idx = 11
    m.all_platforms.empty()
    m.all_enemies.empty()
    m.all_vfx.empty()
    m.npcs.clear()
    m.boss_manager_system.reset()
    m.CURRENT_THEME = THEMES[1]
    start_plat = Platform(0, LOGICAL_HEIGHT - 100, 600, 50)
    m.all_platforms.add(start_plat)
    m.player_x = 100
    m.player_y = LOGICAL_HEIGHT - 250
    m.camera_speed = INITIAL_CAMERA_SPEED * 1.6
    m.y_velocity = 0
    m.vasil_companion = None

    sound = load_sound_asset("assets/music/final_ascension.mp3", generate_ambient_fallback, 0.8)
    audio_manager.play_music(sound)

# =============================================================================
# NPC SOHBET BAŞLATMA
# =============================================================================

def start_npc_conversation(npc):
    m = _m
    m.current_npc = npc
    m.npc_conversation_active = True
    npc_chat_input = ""          # Orijinal davranışı koru (local değişken)
    m.npc_chat_history = []
    greeting = npc.start_conversation()
    m.npc_chat_history.append({"speaker": npc.name, "text": greeting})
    m.GAME_STATE = 'NPC_CHAT'

# =============================================================================
# ANA OYUN BAŞLATMA — Her bölüm geçişinde çağrılır
# =============================================================================

def init_game():
    """
    Aktif bölümü (current_level_idx) sıfırlar ve başlatır.
    Tür tespiti: EASY_MODE_LEVELS[current_level_idx]['type']
    """
    m = _m

    # --- OPTİMİZASYON: Oyun sırasında GC'yi kapat ---
    gc.disable()

    m.cached_ui_surface = None
    m.last_score = -1

    lvl_config = EASY_MODE_LEVELS.get(m.current_level_idx, EASY_MODE_LEVELS[1])

    # ── Arka Plan Seçimi ─────────────────────────────────────────────────────
    theme_idx  = lvl_config.get('theme_index', 0)
    theme_name = THEMES[theme_idx % len(THEMES)].get('name', 'unknown').lower()

    _BG_MAP = {
        2: "gutter",
        3: "industrial",
        0: "neon_city",
        1: "nexus",
        4: "safe_zone",
    }
    bg_key = _BG_MAP.get(theme_idx, "neon_city")
    m.active_background = ParallaxBackground(
        f"{BG_DIR}/{bg_key}_far.png",
        speed_mult=BG_LAYER_FAR_SPEED
    )

    if m.current_level_idx < 11:
        m.has_talisman = False
        m.vasil_companion = None
        m.has_revived_this_run = False

    m.active_player_speed = PLAYER_SPEED
    m.boss_manager_system.reset()

    # --- DÖVÜŞ SİSTEMİ SIFIRLA ---
    m.combo_system.reset()
    m.beat_arena.reset()
    m.player_hp = PlayerHealth(ARENA_PLAYER_HP,
                               max_stamina=PLAYER_MAX_STAMINA,
                               stamina_regen=STAMINA_REGEN_RATE)
    m.all_health_orbs.empty()
    m.npcs.clear()
    m.current_npc = None
    m.npc_conversation_active = False
    m.npc_chat_input = ""
    m.npc_chat_history = []

    # ────────────────────────────────────────────────────────────────────────
    # BÖLÜM TÜRÜNE GÖRE ÖZEL KURULUM
    # ────────────────────────────────────────────────────────────────────────

    if lvl_config.get('type') == 'rest_area':
        m.camera_speed = 0
        m.CURRENT_THEME = THEMES[4]
        init_rest_area()
        m.player_x, m.player_y = 200.0, float(LOGICAL_HEIGHT - 180)
        m.y_velocity = 0
        music_file = random.choice(REST_AREA_MUSIC) if REST_AREA_MUSIC else "calm_ambient.mp3"
        m.current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_calm_ambient, 0.6
        )
        audio_manager.play_music(m.current_level_music)

    elif lvl_config.get('type') == 'gutter_rest_area':
        # ─────────────────────────────────────────────────────────────────────
        # GUTTER DİNLENME ALANI — Çok katlı, manor kamera sistemiyle
        # ─────────────────────────────────────────────────────────────────────
        init_gutter_rest_area()
        music_file = lvl_config.get('music_file', 'calm_ambient.mp3')
        m.current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_calm_ambient, 0.5
        )
        audio_manager.play_music(m.current_level_music)

    elif lvl_config.get('type') == 'beat_arena':
        # --- BEAT 'EM UP ARENA BAŞLATMA ---
        m.camera_speed = 0
        m.CURRENT_THEME = THEMES[theme_idx]
        m.player_x, m.player_y = 200.0, float(LOGICAL_HEIGHT - 180)
        m.y_velocity = 0
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        m.current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_ambient_fallback, 1.0
        )
        audio_manager.play_music(m.current_level_music)
        m.all_platforms.empty()
        floor_plat = Platform(0, LOGICAL_HEIGHT - 80, LOGICAL_WIDTH, 80, theme_index=theme_idx)
        m.all_platforms.add(floor_plat)
        # Arena henüz başlatılmadı — PLAYING loop içinde start() çağrılacak
        m.beat_arena.reset()

    elif lvl_config.get('type') == 'boss_fight':
        pass

    elif lvl_config.get('type') == 'manor_stealth':
        # ─────────────────────────────────────────────────────────────────────
        # MALİKANE SIZDIRMA — camera_speed=0, 2D kameraya kilitli
        # ─────────────────────────────────────────────────────────────────────
        m.camera_speed = 0
        m.CURRENT_THEME = THEMES[theme_idx]
        m.player_x, m.player_y = 120.0, float(LOGICAL_HEIGHT - 110)
        m.y_velocity = 0
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        m.current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_ambient_fallback, 0.5
        )
        audio_manager.play_music(m.current_level_music)

        # ══════════════════════════════════════════════════════════════════════
        # MALİKANE BİNA PLANI — Tüm Y koordinatları ekran içinde
        # KAT Y TABANLARI (platform.rect.top):
        #   Zemin  Y_G  = LH - 80   = 1000
        #   1. Kat Y_F1 = LH - 290  =  790
        #   2. Kat Y_F2 = LH - 510  =  570
        #   Çatı   Y_RF = LH - 730  =  350
        # ══════════════════════════════════════════════════════════════════════
        m.all_platforms.empty()
        _ti = theme_idx
        _LH = LOGICAL_HEIGHT   # 1080

        Y_G  = _LH - 80    # 1000 — Zemin kat
        Y_F1 = _LH - 290   #  790 — 1. Kat
        Y_F2 = _LH - 510   #  570 — 2. Kat
        Y_RF = _LH - 730   #  350 — Çatı / Kasa katı
        T = 20              # Platform kalınlığı
        W = 18              # Duvar kalınlığı

        # ─── DIŞ YAPI ──────────────────────────────────────────────────────
        m.all_platforms.add(Platform(40,   Y_RF, W, _LH - Y_RF + 80, theme_index=_ti))
        m.all_platforms.add(Platform(3160, Y_RF, W, _LH - Y_RF + 80, theme_index=_ti))

        # ─── ZEMİN KAT (Y_G = 1000) ────────────────────────────────────────
        m.all_platforms.add(Platform(60,   Y_G, 860, T, theme_index=_ti))
        m.all_platforms.add(Platform(920,  Y_F1 + T, W, Y_G - Y_F1, theme_index=_ti))
        m.all_platforms.add(Platform(940,  Y_G, 960, T, theme_index=_ti))
        m.all_platforms.add(Platform(1900, Y_F1 + T, W, Y_G - Y_F1, theme_index=_ti))
        m.all_platforms.add(Platform(1920, Y_G, 1240, T, theme_index=_ti))

        # ─── ZEMİN → 1. KAT MERDİVENLERİ ──────────────────────────────────
        for _s in range(4):
            m.all_platforms.add(Platform(130 + _s * 95, Y_G - (_s + 1) * 52, 100, T, theme_index=_ti))
        for _s in range(4):
            m.all_platforms.add(Platform(2600 + _s * 95, Y_G - (_s + 1) * 52, 100, T, theme_index=_ti))

        # ─── 1. KAT (Y_F1 = 790) ───────────────────────────────────────────
        m.all_platforms.add(Platform(60,   Y_F1, 1240, T, theme_index=_ti))
        m.all_platforms.add(Platform(1300, Y_F2 + T, W, Y_F1 - Y_F2, theme_index=_ti))
        m.all_platforms.add(Platform(1320, Y_F1, 1840, T, theme_index=_ti))

        # ─── 1. KAT → 2. KAT MERDİVENLERİ ────────────────────────────────
        for _s in range(4):
            m.all_platforms.add(Platform(1090 + _s * 95, Y_F1 - (_s + 1) * 55, 105, T, theme_index=_ti))
        for _s in range(4):
            m.all_platforms.add(Platform(2780 + _s * 90, Y_F1 - (_s + 1) * 55, 100, T, theme_index=_ti))

        # ─── 2. KAT (Y_F2 = 570) ───────────────────────────────────────────
        m.all_platforms.add(Platform(60,   Y_F2, 3100, T, theme_index=_ti))
        # Havalandırma rafları (gizlenme/atlama)
        m.all_platforms.add(Platform(350,  Y_F2 - 130, 160, T, theme_index=_ti))
        m.all_platforms.add(Platform(620,  Y_F2 - 240, 160, T, theme_index=_ti))
        m.all_platforms.add(Platform(900,  Y_F2 - 130, 160, T, theme_index=_ti))
        m.all_platforms.add(Platform(1700, Y_F2 - 130, 160, T, theme_index=_ti))
        m.all_platforms.add(Platform(2000, Y_F2 - 240, 160, T, theme_index=_ti))
        m.all_platforms.add(Platform(2400, Y_F2 - 130, 160, T, theme_index=_ti))
        m.all_platforms.add(Platform(2200, Y_RF + T, W, Y_F2 - Y_RF, theme_index=_ti))

        # ─── 2. KAT → ÇATI MERDİVENLERİ ───────────────────────────────────
        for _s in range(5):
            m.all_platforms.add(Platform(2480 + _s * 80, Y_F2 - (_s + 1) * 72, 90, T, theme_index=_ti))

        # ─── ÇATI / KASA KATI (Y_RF = 350) ────────────────────────────────
        m.all_platforms.add(Platform(60,   Y_RF, 1740, T, theme_index=_ti))
        m.all_platforms.add(Platform(2000, Y_RF, 1160, T, theme_index=_ti))
        # KASA PLATFORMU — hedef: x=2700, y=Y_RF-120=230
        m.all_platforms.add(Platform(2700, Y_RF - 120, 420, T + 8, theme_index=_ti))

    elif lvl_config.get('type') == 'debug_arena':
        # ─────────────────────────────────────────────────────────────────────
        # DEBUG ARENA BAŞLATMA
        # ─────────────────────────────────────────────────────────────────────
        m.camera_speed = 0
        m.CURRENT_THEME = THEMES[theme_idx]
        m.all_platforms.empty()
        m.all_enemies.empty()
        m.all_vfx.empty()
        _debug_floor = Platform(0, LOGICAL_HEIGHT - 80, LOGICAL_WIDTH, 80, theme_index=theme_idx)
        m.all_platforms.add(_debug_floor)
        m.all_platforms.add(Platform(LOGICAL_WIDTH // 2 - 200, LOGICAL_HEIGHT - 280, 400, 30, theme_index=theme_idx))
        m.all_platforms.add(Platform(LOGICAL_WIDTH // 2 - 100, LOGICAL_HEIGHT - 480, 200, 30, theme_index=theme_idx))
        m.player_x = float(LOGICAL_WIDTH // 2 - 14)
        m.player_y = float(LOGICAL_HEIGHT - 80 - 42)
        m.y_velocity = 0
        # ── DEBUG ARENA: Her iki silahı ver, sınırsız cephane ──────────────
        _DEBUG_MAG = 9999
        for _dbg_wtype in ('revolver', 'smg', 'shotgun'):
            _dbg_wpn = create_weapon(_dbg_wtype, spare_mags=_DEBUG_MAG)
            if _dbg_wpn:
                _dbg_wpn.bullets    = _dbg_wpn.mag_size
                _dbg_wpn.spare_mags = _DEBUG_MAG
                inventory_manager.unlock(_dbg_wtype, _dbg_wpn)
                if _dbg_wtype not in m.inventory_weapons:
                    m.inventory_weapons.append(_dbg_wtype)
        inventory_manager.switch_to('revolver')
        m.active_weapon_obj = inventory_manager.active_weapon
        if m.active_weapon_obj:
            m.active_weapon_obj.spare_mags = _DEBUG_MAG
            m.player_bullets = m.active_weapon_obj.bullets
        m.gun_cooldown = 0.0
        m.is_reloading = False
        m.karma_notification_text  = "DEBUG ARENA | 1:Revolver 2:SMG 3:Pompalı | T:Terminal | Num1-3:Spawn"
        m.karma_notification_timer = 180
        music_file = lvl_config.get('music_file', 'calm_ambient.mp3')
        m.current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_calm_ambient, 0.5
        )
        audio_manager.play_music(m.current_level_music)

    elif lvl_config.get('type') == 'scrolling_boss':
        mult = lvl_config.get('speed_mult', 1.0)
        m.camera_speed = (INITIAL_CAMERA_SPEED * 1.25) * mult
        m.CURRENT_THEME = THEMES[theme_idx]
        m.player_x, m.player_y = 150.0, float(LOGICAL_HEIGHT - 300)
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        m.current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_ambient_fallback, 1.0
        )
        audio_manager.play_music(m.current_level_music)
        m.all_platforms.empty()
        start_plat = Platform(0, LOGICAL_HEIGHT - 50, 400, 50)
        m.all_platforms.add(start_plat)

        karma = m.save_manager.get_karma()
        boss_spawn_x = LOGICAL_WIDTH - 300
        boss = None
        if karma <= -20:
            boss = AresBoss(boss_spawn_x, LOGICAL_HEIGHT - 200)
        elif karma >= 20:
            boss = VasilBoss(boss_spawn_x, 100)
        else:
            boss = NexusBoss(boss_spawn_x, LOGICAL_HEIGHT - 400)
        if boss:
            boss.ignore_camera_speed = True
            m.all_enemies.add(boss)

    else:
        # Normal kaydırmalı bölüm (varsayılan)
        mult = lvl_config.get('speed_mult', 1.0)
        if m.current_level_idx == 10 and mult <= 0.1:
            mult = 1.4
        m.camera_speed = (INITIAL_CAMERA_SPEED * 1.25) * mult
        m.CURRENT_THEME = THEMES[theme_idx]
        m.player_x, m.player_y = 150.0, float(LOGICAL_HEIGHT - 300)
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        m.current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_ambient_fallback, 1.0
        )
        audio_manager.play_music(m.current_level_music)
        m.all_platforms.empty()
        start_plat = Platform(0, LOGICAL_HEIGHT - 50, 400, 50)
        m.all_platforms.add(start_plat)
        current_right = 400
        while current_right < LOGICAL_WIDTH + 200:
            add_new_platform()
            if len(m.all_platforms) > 0:
                current_right = max(p.rect.right for p in m.all_platforms)
            else:
                current_right += 200

        if m.current_level_idx == 30:
            karma = m.save_manager.get_karma()
            boss = None
            if karma <= -20:
                boss = AresBoss(LOGICAL_WIDTH - 300, LOGICAL_HEIGHT - 200)
            elif karma >= 20:
                boss = VasilBoss(LOGICAL_WIDTH // 2, 100)
            else:
                boss = NexusBoss(LOGICAL_WIDTH - 300, LOGICAL_HEIGHT - 400)
            if boss:
                boss.ignore_camera_speed = True
                m.all_enemies.add(boss)

    # ── Bölüm 30: Boss sağlığını maksimuma çek ──────────────────────────────
    if m.current_level_idx == 30:
        for e in m.all_enemies:
            if hasattr(e, 'health'):
                e.max_health = 50000
                e.health = 50000

    # ── Ortak Sıfırlama ──────────────────────────────────────────────────────
    m.y_velocity = m.score = m.dash_timer = m.screen_shake = m.slam_stall_timer = 0
    m.is_jumping = m.is_dashing = m.is_slamming = False
    m.jumps_left = MAX_JUMPS
    m.dash_particles_timer = 0
    m.dash_angle = 0.0
    m.dash_frame_counter = 0.0
    m.character_state = 'idle'
    m.slam_collision_check_frames = 0
    m.active_damage_waves.clear()
    m.trail_effects.clear()
    m.last_trail_time = 0.0
    m.player_karma = m.save_manager.get_karma()
    m.enemies_killed_current_level = 0
    m.karma_notification_timer = 0
    m.CURRENT_SHAPE = random.choice(PLAYER_SHAPES)
    m.all_enemies.empty()
    m.all_vfx.empty()
    m.character_animator.__init__()

    # ── Silah Sistemi Sıfırla ─────────────────────────────────────────────────
    m.all_weapon_chests.empty()
    m.all_ammo_pickups.empty()
    m.active_weapon_obj  = None
    m.weapon_shoot_timer = 0.0
    # inventory_weapons listesi bölümler arası korunur — silmiyoruz.

    if inventory_manager.unlocked_weapons:
        _restore_type = inventory_manager.active_type or inventory_manager.unlocked_weapons[0]
        inventory_manager.switch_to(_restore_type)
        m.active_weapon_obj = inventory_manager.active_weapon
        if m.active_weapon_obj is not None:
            _b, _s = inventory_manager.ammo_state()
            m.active_weapon_obj.bullets    = _b
            m.active_weapon_obj.spare_mags = _s
            m.player_bullets = _b

    if m.active_weapon_obj is None:
        m.player_bullets = 0
    m.gun_cooldown  = 0.0
    m.is_reloading  = False
    m.all_player_projectiles.empty()

    # ── Gizlilik Seviyesi Kurulumu ────────────────────────────────────────────
    stealth_system.setup_level(m.current_level_idx)

    # ── Malikane: Önbelleğe alınmış bayrakları temizle ───────────────────────
    if lvl_config.get('type') == 'manor_stealth':
        from mission_system import mission_manager
        mission_manager.set_flag("area_secret_safe", False)