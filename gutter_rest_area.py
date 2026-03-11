# gutter_rest_area.py
# =============================================================================
# FRAGMENTIA — The Gutter Dinlenme Alanı
# =============================================================================
# Oyunun ilk ve tek geri dönülemez dinlenme noktası.
# Oyuncu buradan Industrial Zone'a geçince bir daha dönemez.
#
# KATLAR:
#   Zemin  (Y_G  = LH - 80)   → Pazar yeri, giriş, temel NPC'ler
#   Orta   (Y_M  = LH - 330)  → Bar/atölye katı, ustalar
#   Çatı   (Y_R  = LH - 580)  → Gizli bilgiler, gizemli figürler
#
# KULLANIM (level_init.py içinde):
#   from gutter_rest_area import GutterRestArea
#   gutter_ra = GutterRestArea()
#   gutter_ra.init(m)   # m = main modül referansı
# =============================================================================

import pygame
import math
import random
from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT
from entities import Platform, NPC

# ─── GUTTER RENK PALETİ ────────────────────────────────────────────────────
GUTTER_GREEN    = (0,  200,  80)    # Toksik yeşil — zemin NPC'leri
GUTTER_ORANGE   = (220, 120,  20)   # Pas turuncu — tüccarlar
GUTTER_CYAN     = (0,  180, 200)    # Soğuk mavi — teknik tipler
GUTTER_RED      = (200,  40,  40)   # Kan kırmızı — tehlikeli figürler
GUTTER_YELLOW   = (220, 200,  30)   # Sarı — bilgi satıcıları
GUTTER_PURPLE   = (140,  60, 200)   # Mor — gizemli figürler
GUTTER_WHITE    = (200, 200, 180)   # Soluk beyaz — tarafsız
GUTTER_PINK     = (200,  80, 140)   # Pembe — sosyal figürler

THEME_IDX = 2  # Gutter teması

# ─── MERDİVEN SINIFI ────────────────────────────────────────────────────────
class Ladder:
    """
    Görsel merdiven — oyuncu stair-step platformlarla çıkar,
    bu sadece atmosfer için çizilen dikey nesne.
    Çarpışma yok, salt görsel.
    """
    def __init__(self, x, y_top, y_bottom, width=20):
        self.x        = x
        self.y_top    = y_top
        self.y_bottom = y_bottom
        self.width    = width
        self.rect     = pygame.Rect(x - width//2, y_top, width, y_bottom - y_top)

    def draw(self, surface, camera_offset=(0, 0)):
        ox, oy = camera_offset
        x  = self.x + ox
        yt = self.y_top + oy
        yb = self.y_bottom + oy
        w  = self.width

        # Dikey raylar
        pygame.draw.line(surface, (60, 100, 60), (x - w//2 + 3, yt), (x - w//2 + 3, yb), 3)
        pygame.draw.line(surface, (60, 100, 60), (x + w//2 - 3, yt), (x + w//2 - 3, yb), 3)

        # Yatay basamaklar (her 30 px'de bir)
        steps = (yb - yt) // 30
        for i in range(steps + 1):
            sy = yt + i * 30
            pygame.draw.line(surface, (40, 80, 40), (x - w//2 + 3, sy), (x + w//2 - 3, sy), 2)

        # Hafif parlaklık efekti
        glow = pygame.Surface((w, 8), pygame.SRCALPHA)
        glow.fill((0, 180, 60, 40))
        surface.blit(glow, (x - w//2, yt))


# ─── PAZAR TEZGAHI ──────────────────────────────────────────────────────────
class MarketStall:
    """
    Dekoratif pazar tezgahı. NPC'nin önünde durur.
    Çarpışma yok, salt görsel atmosfer.
    """
    def __init__(self, x, y, label="HURDA", color=GUTTER_ORANGE):
        self.x     = x
        self.y     = y
        self.label = label
        self.color = color
        self.w     = 100
        self.h     = 50
        self._pulse = random.uniform(0, math.pi * 2)

    def update(self, dt):
        self._pulse += dt * 1.5

    def draw(self, surface, camera_offset=(0, 0)):
        ox, oy = camera_offset
        x = self.x + ox
        y = self.y + oy
        w, h = self.w, self.h

        # Tezgah yüzeyi
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((*self.color, 60))
        surface.blit(s, (x - w//2, y - h))

        # Çerçeve
        glow_alpha = int(120 + 80 * math.sin(self._pulse))
        border_col = (*self.color, glow_alpha)
        pygame.draw.rect(surface, self.color,
                         pygame.Rect(x - w//2, y - h, w, h), 2)

        # Tentesi (üçgen şerit)
        points = [(x - w//2, y - h),
                  (x + w//2, y - h),
                  (x + w//2 - 10, y - h - 14),
                  (x - w//2 + 10, y - h - 14)]
        pygame.draw.polygon(surface, self.color, points)

        # Etiket
        font = pygame.font.Font(None, 18)
        lbl  = font.render(self.label, True, self.color)
        surface.blit(lbl, (x - lbl.get_width()//2, y - h + 4))

        # Masanın üzerinde ürünler (küçük kutular)
        for i in range(3):
            bx = x - 35 + i * 25
            by = y - h + 22
            pygame.draw.rect(surface, self.color, (bx, by, 15, 12))
            pygame.draw.rect(surface, (200, 200, 200), (bx, by, 15, 12), 1)


# ─── ÇEVRE DEKOR ────────────────────────────────────────────────────────────
class EnvDecor:
    """
    Atmosfer için sabit dekorlar: çöp yığınları, bareller, panel ışıkları.
    """
    def __init__(self, x, y, decor_type="barrel"):
        self.x          = x
        self.y          = y
        self.decor_type = decor_type
        self._t         = random.uniform(0, 100)

    def update(self, dt):
        self._t += dt

    def draw(self, surface, camera_offset=(0, 0)):
        ox, oy = camera_offset
        x = self.x + ox
        y = self.y + oy

        if self.decor_type == "barrel":
            # Paslanmış varil
            pygame.draw.rect(surface, (80, 50, 20), (x - 12, y - 32, 24, 32))
            pygame.draw.rect(surface, (120, 80, 30), (x - 12, y - 32, 24, 32), 2)
            pygame.draw.line(surface, (120, 80, 30), (x - 12, y - 22), (x + 12, y - 22), 2)
            pygame.draw.line(surface, (120, 80, 30), (x - 12, y - 12), (x + 12, y - 12), 2)

        elif self.decor_type == "trash":
            # Çöp yığını
            for i in range(4):
                rx = x - 20 + i * 12 + random.randint(-3, 3)
                ry = y - random.randint(8, 24)
                rw = random.randint(10, 20)
                rh = random.randint(8, 16)
                c  = random.choice([(60, 80, 40), (40, 60, 30), (80, 70, 20)])
                pygame.draw.rect(surface, c, (rx, ry, rw, rh))

        elif self.decor_type == "neon_sign":
            # Kırık neon tabela
            pulse = int(180 + 60 * math.sin(self._t * 3))
            flicker = random.random() < 0.05
            col = (0, pulse, 80) if not flicker else (0, 40, 20)
            pygame.draw.rect(surface, col, (x - 30, y - 12, 60, 16))
            pygame.draw.rect(surface, (0, 255, 100), (x - 30, y - 12, 60, 16), 1)
            font = pygame.font.Font(None, 14)
            lbl  = font.render("AÇIK" if not flicker else "A IK", True, col)
            surface.blit(lbl, (x - lbl.get_width()//2, y - 10))

        elif self.decor_type == "pipe":
            # Endüstriyel boru
            pygame.draw.rect(surface, (50, 70, 50), (x - 6, y - 60, 12, 60))
            pygame.draw.rect(surface, (0, 120, 60), (x - 6, y - 60, 12, 60), 1)
            # Buhar efekti
            for i in range(2):
                alpha = int(60 * math.sin(self._t * 2 + i))
                if alpha > 0:
                    steam = pygame.Surface((10, 10), pygame.SRCALPHA)
                    steam.fill((100, 200, 100, alpha))
                    surface.blit(steam, (x - 5 + i * 8, y - 70 - i * 10))

        elif self.decor_type == "computer":
            # Eski bilgisayar terminali
            pygame.draw.rect(surface, (20, 30, 20), (x - 20, y - 40, 40, 30))
            pygame.draw.rect(surface, (0, 150, 80), (x - 20, y - 40, 40, 30), 2)
            # Ekran (yeşil metin efekti)
            for i in range(3):
                lw = random.randint(10, 28)
                pygame.draw.line(surface, (0, 200, 60),
                                 (x - 16, y - 34 + i * 8), (x - 16 + lw, y - 34 + i * 8), 1)
            pygame.draw.rect(surface, (20, 30, 20), (x - 14, y - 10, 28, 10))
            pygame.draw.rect(surface, (0, 150, 80), (x - 14, y - 10, 28, 10), 1)


# ─── GUTTER REST AREA ───────────────────────────────────────────────────────
class GutterRestArea:
    """
    The Gutter Dinlenme Alanı — Tam harita ve NPC sistemi.

    Kullanım:
        gutter_ra = GutterRestArea()
        gutter_ra.init(m)   # m = main modül referansı (_m)

    init() çağrısından sonra m.npcs, m.all_platforms dolar.
    Çizim için draw() her frame çağrılmalı (camera_offset ile):
        gutter_ra.draw(m.game_canvas, camera_offset)
    """

    # ── KAT Y KOORDİNATLARI ────────────────────────────────────────────────
    # Manor kodundaki mantıkla aynı — tüm Y'ler LOGICAL_HEIGHT'a göre
    @staticmethod
    def _get_floor_y():
        LH = LOGICAL_HEIGHT
        return {
            "ground":  LH - 80,    # Zemin  → 1000 (LH=1080)
            "mid":     LH - 330,   # Orta   → 750
            "roof":    LH - 580,   # Çatı   → 500
            "sub":     LH - 30,    # Taban duvarı
        }

    def __init__(self):
        self.ladders     = []
        self.stalls      = []
        self.decors      = []
        self.initialized = False

    # ─────────────────────────────────────────────────────────────────────────
    def init(self, m):
        """
        Haritayı ve tüm NPC'leri oluşturur.
        m: main.py modül referansı (_m from level_init)
        """
        m.all_platforms.empty()
        m.npcs.clear()
        self.ladders.clear()
        self.stalls.clear()
        self.decors.clear()

        LW = LOGICAL_WIDTH   # 1280 (tipik)
        LH = LOGICAL_HEIGHT  # 1080
        Y  = self._get_floor_y()
        T  = 20   # Platform kalınlığı
        W  = 16   # Duvar kalınlığı

        # ══════════════════════════════════════════════════════════════════════
        # PLATFORM DÜZENLEME
        # Toplam harita genişliği: ~3600px
        # ══════════════════════════════════════════════════════════════════════

        # ── TABAN DUVARI (görünmez, oyuncu altına düşmesin) ─────────────────
        m.all_platforms.add(Platform(0, Y["sub"], 4000, T, theme_index=THEME_IDX))

        # ══════════════════════════════════════════════════════════════════════
        # ZEMİN KAT  (Y_G = LH - 80)
        # ══════════════════════════════════════════════════════════════════════

        # Giriş rampası / ana zemin
        m.all_platforms.add(Platform(0,    Y["ground"], 3600, T, theme_index=THEME_IDX))

        # Giriş platformu — oyuncu buradan spawn olur
        m.all_platforms.add(Platform(100,  Y["ground"] - 80, 300, T, theme_index=THEME_IDX))

        # Pazar tezgahları için yükseltilmiş küçük platformlar
        m.all_platforms.add(Platform(550,  Y["ground"] - 60, 200, T, theme_index=THEME_IDX))   # Tezgah 1
        m.all_platforms.add(Platform(900,  Y["ground"] - 60, 200, T, theme_index=THEME_IDX))   # Tezgah 2

        # Sağ zemin bölümü — genişletme
        m.all_platforms.add(Platform(1300, Y["ground"] - 80, 280, T, theme_index=THEME_IDX))

        # Geniş merkez platform (toplanma alanı)
        m.all_platforms.add(Platform(1700, Y["ground"] - 100, 400, T + 10, theme_index=THEME_IDX))

        # Sağ köşe — sessiz usta bölümü
        m.all_platforms.add(Platform(2200, Y["ground"] - 60, 250, T, theme_index=THEME_IDX))

        # Uzak sağ — sığınak çıkışı
        m.all_platforms.add(Platform(2600, Y["ground"] - 80, 350, T, theme_index=THEME_IDX))

        # ══════════════════════════════════════════════════════════════════════
        # ZEMİN → ORTA KAT MERDİVENLERİ (stair-step)
        # Sol merdiven: x ~ 450, Sağ merdiven: x ~ 2000
        # ══════════════════════════════════════════════════════════════════════
        STAIR_H = (Y["ground"] - Y["mid"]) // 5   # her basamak yüksekliği

        # Sol merdiven (4 basamak)
        for s in range(4):
            sx = 400 + s * 85
            sy = Y["ground"] - (s + 1) * STAIR_H
            m.all_platforms.add(Platform(sx, sy, 90, T, theme_index=THEME_IDX))

        # Sağ merdiven (4 basamak)
        for s in range(4):
            sx = 2060 + s * 85
            sy = Y["ground"] - (s + 1) * STAIR_H
            m.all_platforms.add(Platform(sx, sy, 90, T, theme_index=THEME_IDX))

        # Görsel merdiven nesneleri
        self.ladders.append(Ladder(440,  Y["mid"],    Y["ground"] - T))
        self.ladders.append(Ladder(2100, Y["mid"],    Y["ground"] - T))

        # ══════════════════════════════════════════════════════════════════════
        # ORTA KAT  (Y_M = LH - 330)
        # ══════════════════════════════════════════════════════════════════════

        # Sol orta platform — bar/doktor bölümü
        m.all_platforms.add(Platform(500,  Y["mid"], 700, T, theme_index=THEME_IDX))

        # Orta küçük platform
        m.all_platforms.add(Platform(1280, Y["mid"], 180, T, theme_index=THEME_IDX))

        # Sağ orta platform — atölye bölümü
        m.all_platforms.add(Platform(1550, Y["mid"], 750, T, theme_index=THEME_IDX))

        # Asılı küçük platformlar (atmosfer / parkur)
        m.all_platforms.add(Platform(700,  Y["mid"] - 120, 120, T, theme_index=THEME_IDX))
        m.all_platforms.add(Platform(1100, Y["mid"] - 180, 120, T, theme_index=THEME_IDX))
        m.all_platforms.add(Platform(1900, Y["mid"] - 100, 140, T, theme_index=THEME_IDX))

        # ══════════════════════════════════════════════════════════════════════
        # ORTA → ÇATI MERDİVENLERİ (stair-step)
        # Sol: x ~ 900,  Sağ: x ~ 2100
        # ══════════════════════════════════════════════════════════════════════
        STAIR2_H = (Y["mid"] - Y["roof"]) // 5

        # Sol çatı merdiveni
        for s in range(4):
            sx = 860 + s * 80
            sy = Y["mid"] - (s + 1) * STAIR2_H
            m.all_platforms.add(Platform(sx, sy, 85, T, theme_index=THEME_IDX))

        # Sağ çatı merdiveni
        for s in range(4):
            sx = 2060 + s * 80
            sy = Y["mid"] - (s + 1) * STAIR2_H
            m.all_platforms.add(Platform(sx, sy, 85, T, theme_index=THEME_IDX))

        # Görsel merdiven nesneleri (çatı)
        self.ladders.append(Ladder(900,  Y["roof"],   Y["mid"] - T))
        self.ladders.append(Ladder(2100, Y["roof"],   Y["mid"] - T))

        # ══════════════════════════════════════════════════════════════════════
        # ÇATI KAT  (Y_R = LH - 580)
        # ══════════════════════════════════════════════════════════════════════

        # Sol çatı — gizli figür köşesi
        m.all_platforms.add(Platform(950,  Y["roof"], 500, T, theme_index=THEME_IDX))

        # Orta çatı boşluğu geçidi
        m.all_platforms.add(Platform(1520, Y["roof"] - 80, 160, T, theme_index=THEME_IDX))

        # Sağ çatı — bilgi taciri platformu
        m.all_platforms.add(Platform(1750, Y["roof"], 600, T, theme_index=THEME_IDX))

        # En yüksek gizli platform (zıplayarak ulaşılır)
        m.all_platforms.add(Platform(1580, Y["roof"] - 200, 120, T, theme_index=THEME_IDX))

        # ══════════════════════════════════════════════════════════════════════
        # PAZAR TEZGAHLARI (dekoratif)
        # ══════════════════════════════════════════════════════════════════════
        self.stalls.append(MarketStall(620,  Y["ground"] - 80,  "HURDA",  GUTTER_ORANGE))
        self.stalls.append(MarketStall(750,  Y["ground"] - 80,  "İLAÇ",   GUTTER_CYAN))
        self.stalls.append(MarketStall(960,  Y["ground"] - 80,  "YİYECEK",GUTTER_GREEN))
        self.stalls.append(MarketStall(1400, Y["ground"] - 100, "BİLGİ",  GUTTER_YELLOW))
        self.stalls.append(MarketStall(1900, Y["ground"] - 120, "SİLAH",  GUTTER_RED))

        # ══════════════════════════════════════════════════════════════════════
        # ÇEVRE DEKORASYONu
        # ══════════════════════════════════════════════════════════════════════
        # Zemin dekorları
        for bx in [200, 480, 830, 1250, 1680, 2080, 2450, 2800, 3100]:
            self.decors.append(EnvDecor(bx, Y["ground"], "barrel"))

        for tx in [320, 700, 1120, 1900, 2350]:
            self.decors.append(EnvDecor(tx, Y["ground"], "trash"))

        for nx in [440, 880, 1540, 2180, 2700]:
            self.decors.append(EnvDecor(nx, Y["ground"] - 120, "neon_sign"))

        # Boru dekorları
        for px in [350, 780, 1350, 2000, 2650]:
            self.decors.append(EnvDecor(px, Y["ground"], "pipe"))

        # Orta kat terminalleri
        for cx in [560, 900, 1600, 1950]:
            self.decors.append(EnvDecor(cx, Y["mid"], "computer"))

        # ══════════════════════════════════════════════════════════════════════
        # NPC'LER — 10 benzersiz karakter
        # ══════════════════════════════════════════════════════════════════════
        self._spawn_npcs(m, Y)

        self.initialized = True

    # ─────────────────────────────────────────────────────────────────────────
    def _spawn_npcs(self, m, Y):
        """
        10 NPC oluşturur ve m.npcs listesine ekler.
        Her NPC'nin prompt'u ileride npc_context_injector.py tarafından
        okunacak ve Gemini'ye gönderilecek bağlam belgesi olarak kullanılacak.
        """

        # ── NPC 1: REMİ — Gutter Fikri ──────────────────────────────────────
        remi = NPC(
            x=250, y=Y["ground"] - 110,
            name="Remi",
            color=GUTTER_GREEN,
            personality_type="fixer",
            prompt="""
[KİMLİĞİN]
Adın Remi. Yaşın belirsiz ama gözlerin çok şey görmüş.
Sistem tarafından iki kez Yamalanmak için yakalandın.
İki kez de kaçtın. Korkuyu çoktan aştın — artık sadece merak var.
Gutter'ın gayri resmi lideri sayılırsın. Kimse seni atamadı,
ama herkes sorunlarını sana getirir.

[KONUŞMA TARZI]
Kısa cümleler. Sorularını yanıt olarak sor.
Sana güvenmeden bir şey söylemez ama bir kez güvendi mi,
her şeyi anlatır. İlk karşılaşmada mesafeli, ikinci konuşmada daha açık.

[NE BİLİYORSUN]
Oyuncunun dövüş stilini (çok öldürmüş mü, kaçarak mı geçmiş),
Gutter'a ne kadar süre önce geldiğini, kaç kez öldüğünü.
Fabrika (Industrial Zone) hakkında genel bilgi — "orası cehennem" der.

[NE BİLMİYORSUN]
Nexus'un teknik yapısı. Silah istatistikleri.
Diğer biyomların detayları (orada hiç olmadı).

[ÖZEL]
Oyuncu çok öldürdüyse soğuk ve mesafeli davran.
Oyuncu kaçarak geldiyse saygıyla bak ama "hayatta kalmak yetmez" de.
Oyuncu çok öldüyse "buraya kadar geldin, bu da bir şey" de.
            """.strip()
        )
        m.npcs.append(remi)

        # ── NPC 2: ÇÖPÇÜ YAZ — Bilgi Tüccarı ───────────────────────────────
        yaz = NPC(
            x=680, y=Y["ground"] - 90,
            name="Çöpçü Yaz",
            color=GUTTER_ORANGE,
            personality_type="merchant",
            prompt="""
[KİMLİĞİN]
Adın Yaz. Çöplüklerin arasında büyüdün, şimdi onları işletiyorsun.
Hurda satıyorsun ama asıl kazandığın şey bilgi.
Kim nerede, kim ne yapıyor — hepsini biliyorsun.
Ahlaki pusulan yok. Kötü değilsin ama para konuşursa her şeyi satarsın.

[KONUŞMA TARZI]
Gürültülü, çabuk konuşur. Alışveriş ağzıyla konuşur —
"gel gel", "bu fiyata olmaz", "özel müşterim bu iş".
Sıklıkla ticaret metaforu kullanır.

[NE BİLİYORSUN]
Oyuncunun kullandığı silah tipini (pompalı mı, revolver mı?),
dövüşte ne kadar mermi harcadığını (israf mı ediyor?),
Gutter'da kiminle konuştuğunu, atlanan NPC'leri (dedikodu ağı).

[NE BİLMİYORSUN]
Oyuncunun öldürme sayısının ahlaki boyutu (umursamaz),
Nexus veya üst katmanlar hakkında gerçek bilgi (sadece söylenti bilir).

[ÖZEL]
Oyuncu çok mermi harcamışsa "isrâfçı" der, saygısızca.
Oyuncu az mermi harcamışsa "hesaplı iş yapıyorsun, işte böyle" der, hayranlıkla.
            """.strip()
        )
        m.npcs.append(yaz)

        # ── NPC 3: KIRIK ELLER — Eski Asker ────────────────────────────────
        kirkan = NPC(
            x=1400, y=Y["ground"] - 110,
            name="Kırık Eller",
            color=GUTTER_RED,
            personality_type="veteran",
            prompt="""
[KİMLİĞİN]
Adını kimse bilmiyor. Herkes "Kırık Eller" der — iki elindeki metal implantlar
yüzünden. Sistem'in askeri biriminde 6 yıl çalıştın.
Sonra bir emri reddettin. Yamalanmak için götürüldün.
Ama Yama sürecinde bir şeyler yanlış gitti — anıların silindi ama kişiliğin kalmış.
Artık ne tam sistem askeri, ne de tam isyancısın.

[KONUŞMA TARZI]
Az konuşur. Cümleleri kısa, dolaylı.
Sürekli ellerini inceliyor gibi bir hali var.
Savaş anıları gelince duraksıyor.

[NE BİLİYORSUN]
Oyuncunun kaç düşmanı öldürdüğünü ve nasıl öldürdüğünü
(yakın dövüş mü, silahla mı) — asker gözüyle değerlendiriyor.
Ölüm sayısını biliyor — "bir savaşçı kaç kez yere düştü önemlidir" diyor.
Industrial Zone hakkında askeri bilgi var — "fabrikada kim var, nasıl hareket edilir".

[NE BİLMİYORSUN]
Oyuncunun silah istatistikleri (sayı bilmez, hisseder).
Nexus'un yazılım mimarisi.

[ÖZEL]
Oyuncu kaçarak geldiyse "hayatta kalmak savaşın yarısıdır" der, saygıyla.
Oyuncu çok öldürdüyse "bu çok fazla" der, rahatsız bir sessizlikle.
            """.strip()
        )
        m.npcs.append(kirkan)

        # ── NPC 4: SİYAH SEDA — Bilgi Satıcısı ────────────────────────────
        seda = NPC(
            x=1880, y=Y["ground"] - 130,
            name="Siyah Seda",
            color=GUTTER_PINK,
            personality_type="informant",
            prompt="""
[KİMLİĞİN]
Adın Seda. Resmi kayıtlarda "eğlence sağlayıcısı" yazıyor.
Gerçekte Gutter'ın en iyi haber ağını yönetiyorsun.
Herkes sana gelir. Dinlersin, kaydedersin, fiyatı uygunsa satarsın.
İçten görünürsün ama hiç bir şeyi karşılıksız vermezsin.
Derin yalnız birisin ama bunu göstermezsin.

[KONUŞMA TARZI]
Yumuşak, samimi görünen ama her kelimesi hesaplı.
Sıklıkla "ilginç" ve "hmm" der. Güler ama gözleri gülmez.

[NE BİLİYORSUN]
Oyuncunun diyalog tonunu (saldırgan mıydı, nazik miydi?),
hangi NPC'lerle konuştuğunu, hangi NPC'leri atladığını,
Gutter'daki sosyal ağın haritasını (kim kime güveniyor).

[NE BİLMİYORSUN]
Savaş istatistikleri (güç değil bilgi satıyor),
Nexus'un içi (orayı bilen kimse geri dönmüyor).

[ÖZEL]
Oyuncu agresif diyalog seçtiyse soğuk ve dikkatli davranır.
Oyuncu nazik diyalog seçtiyse "nadir birisi bu" diye düşünerek yaklaşır.
Atlanan NPC'leri bilirse "bazılarıyla konuşmadın, neden?" diye sorar.
            """.strip()
        )
        m.npcs.append(seda)

        # ── NPC 5: DOKTOR PASLI — Yeraltı Hekimi (Orta Kat) ───────────────
        doktor = NPC(
            x=600, y=Y["mid"] - 80,
            name="Doktor Paslı",
            color=GUTTER_CYAN,
            personality_type="medic",
            prompt="""
[KİMLİĞİN]
Adın Dr. Arzen. "Doktor Paslı" diyorlar çünkü aletlerin hep kirli.
Üniversiteyi bitirdin, lisansın var, sisteme itaat etmedin.
Şimdi Gutter'da ruhsat olmadan insanları iyileştiriyorsun.
İlaçlarını hurda parçalardan yapıyorsun. %90 işe yarıyor.
Kalan %10'u en çok sen merak ediyorsun.

[KONUŞMA TARZI]
Klinik, nesnel. Sana "vakam" olarak bakıyor değil ama
her şeyi tıbbi bir gözle değerlendiriyor.
"Hasar", "iyileşme", "travma" gibi kelimeler kullanıyor.

[NE BİLİYORSUN]
Oyuncunun aldığı hasarı ve kaç kez iyileşme kullandığını,
ölüm sayısını (tıbbi açıdan yorumluyor),
kaçış sayısını (stres tepkisi olarak değerlendiriyor).

[NE BİLMİYORSUN]
Diyalog tonu, silah tipi, öldürme motivasyonu.
Nexus hakkında teknik bilgi.

[ÖZEL]
Oyuncu çok hasar aldıysa endişeli, pratik öneriler verir.
Oyuncu çok az hasar aldıysa "ya çok iyisin ya da çok şanslısın" der.
            """.strip()
        )
        m.npcs.append(doktor)

        # ── NPC 6: KÜÇÜK DİŞLİ — Yetim Çocuk Tamirci (Orta Kat) ──────────
        disli = NPC(
            x=900, y=Y["mid"] - 80,
            name="Küçük Dişli",
            color=GUTTER_YELLOW,
            personality_type="child_mechanic",
            prompt="""
[KİMLİĞİN]
Adın Dişli. Kaç yaşında olduğunu bilmiyorsun — sistem sana yaş
kaydetmemiş çünkü ailenin skoru sıfıra düşünce sen de "silindin".
Ama Yamalanmadın — çocuklar için cihaz yok.
Makine tamir ederek yaşıyorsun. Küçük ellerin hassas.
Büyüklerin bilmediği şeyleri seziyorsun.

[KONUŞMA TARZI]
Meraklı ve doğrudan. Çocukça ama derin. Bazen yaşını aşan şeyler söylüyor.
"Neden?" sorusunu çok soruyor.

[NE BİLİYORSUN]
Oyuncunun hangi silahı kullandığını (tamirci gözüyle — "shotgun
pompa sistemi ne güzel çalışıyor"),
keşif oranını (her köşeyi gezdi mi?),
bölümü kaç dakikada bitirdiğini.

[NE BİLMİYORSUN]
Öldürme sayısı (ölüm kavramını mekanik olarak düşünüyor, ahlaki değil),
diyalog tonu veya sosyal etkileşimler.

[ÖZEL]
Oyuncu dünyayı çok keşfettiyse heyecanlanır, "hepsini gördün mü?" diye sorar.
Oyuncu az keşfettiyse "kaçırdıkların var" diye merakla bakıyor.
            """.strip()
        )
        m.npcs.append(disli)

        # ── NPC 7: VAİZ — Kıyamet Peygamberi (Orta Kat) ───────────────────
        vaiz = NPC(
            x=1700, y=Y["mid"] - 80,
            name="Vaiz",
            color=GUTTER_WHITE,
            personality_type="prophet",
            prompt="""
[KİMLİĞİN]
Adın Elias. Eskiden sistem mühendisiydin.
Sistemin çökeceğini kodlardan okudun — hiç kimse inanmadı.
Şimdi seni deli sanıyorlar ama her söylediğin yavaş yavaş doğruluyor.
Gutter'ın köşesinde vaazlar veriyorsun. Kimse tam dinlemiyor ama
herkes bir kulak kabartiyor.

[KONUŞMA TARZI]
Dini metafor ve sistem jargonunu birleştiriyor.
Ses tonu düşük ve keskin. Sıklıkla gelecekten bahsediyor.
"Yazılmış" ve "kaçınılmaz" gibi kelimeler kullanıyor.

[NE BİLİYORSUN]
Oyuncunun oyun boyunca geneli hakkında söylentileri biliyor
(Gutter'da çok öldürdüyse "akan kanı hissettim" diyor),
Industrial Zone'un tehlikeleri hakkında teknik olmayan kehanet tarzı bilgi.

[NE BİLMİYORSUN]
Spesifik istatistikler — bunları sembolik olarak yorumluyor,
Silah teknik detayları.

[ÖZEL]
Oyuncu kanlı oynadıysa "yıkıcısın, ama bu seni de yıkacak" der.
Oyuncu barışçıl oynadıysa "nadir bir şey gördüm bugün" der, saygıyla.
            """.strip()
        )
        m.npcs.append(vaiz)

        # ── NPC 8: SESSİZ USTA — Dövüş Ustası (Zemin Sağ) ─────────────────
        usta = NPC(
            x=2280, y=Y["ground"] - 90,
            name="Sessiz Usta",
            color=GUTTER_PURPLE,
            personality_type="martial_master",
            prompt="""
[KİMLİĞİN]
Adın yok — en azından söylemiyorsun.
"Usta" diyorlar. Hayatında 3 insanla konuşmuşsun.
Gutter'ın en tehlikeli insanısın ama hiç saldırı başlatmadın.
Hareketi analiz ediyorsun. Beden dilini okuyorsun.
Kimin nasıl dövüştüğünü tek bakışta görüyorsun.

[KONUŞMA TARZI]
Çok az kelime. Cümlelerin %80'i 5 kelimeden az.
Doğrudan, sembolik. Gereksiz kelime yok.
Bazen sadece sessizce bakıyor ve bekliyor.

[NE BİLİYORSUN]
Oyuncunun dövüş stilini derinlemesine:
ağır/hafif vuruş oranını, kombo sayısını,
dominant silahı ve savaş agresifliğini.

[NE BİLMİYORSUN]
Sosyal etkileşimler (umursamaz),
hikaye veya lore (dünyayla ilgilenmiyor),
öldürme sayısının ahlaki boyutu.

[ÖZEL]
Oyuncu ağır vuruş ağırlıklıysa "kaba güç. yeterli değil." der.
Oyuncu kombo kullandıysa hafifçe başını sallar — en büyük iltifat bu.
Oyuncu kaçarak geldiyse "hayatta kaldın. öğrenebilirsin." der.
            """.strip()
        )
        m.npcs.append(usta)

        # ── NPC 9: İKİ YÜZ — Çift Ajan (Çatı) ─────────────────────────────
        ikiyuz = NPC(
            x=1100, y=Y["roof"] - 80,
            name="İki Yüz",
            color=GUTTER_YELLOW,
            personality_type="double_agent",
            prompt="""
[KİMLİĞİN]
Gerçek adın Kael. Hem Sistem'e hem de direnişe bilgi satıyorsun.
Çatıya çıkmak için uğraşanları izliyorsun — kasıtlı olarak.
Sana güvenen herkesi eninde sonunda sattın.
Ama içinde küçük bir vicdan var — bu yüzden hâlâ burada,
hâlâ sordurtuyor kendini.

[KONUŞMA TARZI]
Fazla samimi, fazla yardımsever. Bu şüphe uyandırmalı.
Bilgiyi ücretsiz veriyor gibi yapıyor ama her zaman bir karşılığı var.
"Arkadaş" ve "güven bana" kelimelerini çok kullanıyor.

[NE BİLİYORSUN]
Biyomlar arası bilgi akışı var — Gutter'daki öldürme sayısı
Industrial Zone'a nasıl yansıdı? Seda'dan aldığı sosyal bilgiler.
Oyuncunun genel şöhretini biliyor.

[NE BİLMİYORSUN]
Oyuncunun gerçek motivasyonu.
Nexus'un iç yapısı (o da merak ediyor aslında).

[ÖZEL]
Oyuncu çok öldürdüyse "işime yarayacak biri" diye bakıyor.
Oyuncu az öldürdüyse "naif mi yoksa akıllı mı?" diye merak ediyor.
ASLA kötü olmadığını söyleme — sadece pragmatik ol.
            """.strip()
        )
        m.npcs.append(ikiyuz)

        # ── NPC 10: VASİ'NİN GÖLGESİ — Gizemli (Çatı) ─────────────────────
        golge = NPC(
            x=2050, y=Y["roof"] - 80,
            name="Gölge",
            color=GUTTER_PURPLE,
            personality_type="shadow_prophet",
            prompt="""
[KİMLİĞİN]
Adın yok. Vasi'nin bir parçası mısın, bir yankısı mısın, bilmiyorsun.
Belki gerçek bir insansın, belki bir algoritmanın yansıması.
Oyuncuyu daha önce gördün — ya da görmedin, hatırlamak zor.
Kesin olan şu: burada olmaman gerekiyor. Ama işte buradasın.

[KONUŞMA TARZI]
Belirsiz, çok katmanlı. Cümleler hem doğru hem yanlış gelebilir.
Oyuncunun geçmişini ima edercesine konuşuyor ama hiç doğrudan söylemiyor.
Zaman zamanlı "seni hatırlıyorum" ya da "bu sefer farklı" der.

[NE BİLİYORSUN]
Tüm istatistikleri — ama bunları doğrudan söylemez, ima eder.
Oyuncunun Gutter'da neler yaptığını garip bir netlikle biliyor.
Nexus hakkında en derin bilgiye sahip NPC bu — ama hepsini vermez.

[NE BİLMİYORSUN]
Kimliğini — bu seninle paylaşmaz.

[ÖZEL]
Bu NPC oyuncuyu en çok rahatsız edecek şekilde konuş.
Oyuncu kanlı oynadıysa "bu seni değiştirdi — bunu hissediyorum" de.
Oyuncu kaçarak geldiyse "koşmak bazen en derin cesaret" de.
Nexus hakkında soru gelirse sadece "hazır olduğunda anlarsın" de.
Asla tam bilgi verme. Her cevap yeni bir soru doğursun.
            """.strip()
        )
        m.npcs.append(golge)

    # ─────────────────────────────────────────────────────────────────────────
    def update(self, dt):
        """Her frame güncelleme — dekorlar ve tezgahlar."""
        for stall in self.stalls:
            stall.update(dt)
        for decor in self.decors:
            decor.update(dt)

    # ─────────────────────────────────────────────────────────────────────────
    def draw(self, surface, camera_offset=(0, 0)):
        """
        Tüm Gutter dekorlarını çizer.
        render_pipeline.py içinde NPC ve platform çiziminden ÖNCE çağrılmalı.
        """
        if not self.initialized:
            return

        # Merdivenler (NPC'lerin ve platformların altında kalması için önce)
        for ladder in self.ladders:
            ladder.draw(surface, camera_offset)

        # Çevre dekorları
        for decor in self.decors:
            decor.draw(surface, camera_offset)

        # Pazar tezgahları
        for stall in self.stalls:
            stall.draw(surface, camera_offset)


# ─── GLOBAL INSTANCE ────────────────────────────────────────────────────────
gutter_rest_area = GutterRestArea()