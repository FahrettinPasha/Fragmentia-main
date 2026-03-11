# weapon_entities.py
# Silahların fiziksel ve görsel davranışlarını tanımlar.
# Her sınıf:
#   - Ateşleme hızı / geri tepme (recoil) süreleri
#   - Gövde + Namlu dikdörtgeni çizen draw() metodu
#   - Namlu ucunu (muzzle point) hesaplayan get_muzzle_point()
#
# Bu dosya GÖRSEL KATMANI temsil eder.
# Oyun mantığı (mermi sayısı, şarjör yönetimi) weapon_system.py'dedir.
# InventoryManager ise inventory_manager.py'dedir.

import pygame
import math
import random
from settings import (
    REVOLVER_COOLDOWN, REVOLVER_RELOAD_TIME, REVOLVER_MAX_BULLETS,
    SMG_FIRE_RATE, SMG_RECOIL, SMG_MAG_SIZE
)

# ---------------------------------------------------------------------------
# YARDIMCI: Döndürülmüş dikdörtgen köşe noktaları
# ---------------------------------------------------------------------------

def _rotated_rect_points(cx, cy, length, width, angle):
    """
    Merkezi (cx, cy) olan, belirtilen uzunluk/genişlikte ve açıda
    döndürülmüş bir dikdörtgenin 4 köşesini döndürür.

    Kullanım:
        points = _rotated_rect_points(cx, cy, 30, 8, angle)
        pygame.draw.polygon(surface, color, points)
    """
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    half_l = length / 2
    half_w = width / 2

    corners = [
        (-half_l, -half_w),
        ( half_l, -half_w),
        ( half_l,  half_w),
        (-half_l,  half_w),
    ]

    rotated = []
    for lx, ly in corners:
        rx = cx + lx * cos_a - ly * sin_a
        ry = cy + lx * sin_a + ly * cos_a
        rotated.append((int(rx), int(ry)))
    return rotated


# ---------------------------------------------------------------------------
# REVOLVER — Altıpatar Görsel Sınıfı
# ---------------------------------------------------------------------------

class RevolverVisual:
    """
    Altıpatar silahının GÖRSEL bileşeni.

    Özellikler:
    - Gövde: altın çerçeveli koyu dikdörtgen  (uzun, dar)
    - Namlu: neon sarı ince dikdörtgen         (kısa, uca bağlı)
    - Geri tepme: atış sonrası namlu hafifçe geriye çekilir

    draw(surface, cx, cy, angle, shoot_timer)
        → muzzle_point (tuple[int,int]) döndürür
    """

    # ── Renkler ─────────────────────────────────────────────────────────────
    BODY_COLOR    = (80,  60,  20)    # Koyu bronz gövde
    BARREL_COLOR  = (255, 215,  0)    # Altın namlu
    GRIP_COLOR    = (50,  30,  10)    # Koyu kahve kabza
    ACCENT_COLOR  = (220, 180,  0)    # Neon sarı aksesuar
    MUZZLE_COLOR  = (255, 240, 100)   # Namlu ucu parıltısı
    FLASH_COLOR   = (255, 255, 150)   # Ateş çakması

    # ── Boyutlar ────────────────────────────────────────────────────────────
    BODY_LEN   = 26    # Gövde uzunluğu (px)
    BODY_W     = 8     # Gövde genişliği (px)
    BARREL_LEN = 20    # Namlu uzunluğu (gövdeden itibaren)
    BARREL_W   = 5     # Namlu genişliği
    GRIP_LEN   = 12    # Kabza uzunluğu (gövdeye dik)
    GRIP_W     = 6     # Kabza genişliği

    # ── Recoil sabitler ─────────────────────────────────────────────────────
    RECOIL_PUSH   = 6    # Geri çekilme miktarı (px)
    RECOIL_ANGLE  = 0.25 # Yukarı kalkma miktarı (radyan)
    RECOIL_WINDOW = 0.15 # Saniye — bu süre içinde geri tepme görünür

    def __init__(self):
        self._flash_timer = 0.0   # Ateş çakması için kalan süre

    def update(self, dt: float):
        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt)

    def notify_fired(self):
        """Silah ateş ettiğinde çağrılır — flash başlatır."""
        self._flash_timer = 0.06

    def get_muzzle_point(self, cx: float, cy: float, angle: float,
                         shoot_timer: float = 0.0):
        """
        Namlu ucunun dünya koordinatını hesaplar.
        Recoil uygulanmış pivot kullanılır.
        Mermiler bu noktadan fırlatılmalıdır.
        """
        pivot_x, pivot_y, final_angle = self._compute_pivot_and_angle(
            cx, cy, angle, shoot_timer)
        cos_a = math.cos(final_angle)
        sin_a = math.sin(final_angle)
        total_reach = self.BODY_LEN + self.BARREL_LEN
        mx = pivot_x + cos_a * total_reach
        my = pivot_y + sin_a * total_reach
        return (int(mx), int(my))

    def _compute_pivot_and_angle(self, cx, cy, angle, shoot_timer):
        """Recoil hesabını yapar, pivot ve final açı döndürür."""
        recoil_offset = 0.0
        recoil_angle  = 0.0
        if 0 < shoot_timer < self.RECOIL_WINDOW:
            t = (self.RECOIL_WINDOW - shoot_timer) / self.RECOIL_WINDOW
            recoil_offset = -self.RECOIL_PUSH * t
            recoil_angle  = -self.RECOIL_ANGLE * t

        final_angle = angle + recoil_angle
        pivot_x = cx + math.cos(angle) * recoil_offset
        pivot_y = cy + math.sin(angle) * recoil_offset
        return pivot_x, pivot_y, final_angle

    def draw(self, surface: pygame.Surface,
             cx: float, cy: float,
             angle: float, shoot_timer: float = 0.0):
        """
        Altıpatarı çizer. Muzzle point (namlu ucu) döndürür.

        Parametreler:
            surface       : Çizilecek yüzey
            cx, cy        : Silah pivot noktası (oyuncu elinin orta noktası)
            angle         : Radyan cinsinden bakış açısı
            shoot_timer   : Son atıştan bu yana geçen süre (sn) — recoil için
        """
        pivot_x, pivot_y, final_angle = self._compute_pivot_and_angle(
            cx, cy, angle, shoot_timer)

        # ── FLIP: Sola bakarken silahı dikey eksende aynala ─────────────────
        # |açı| > π/2 demek fare karakterin solunda → sola bakıyor
        facing_left = abs(angle) > (math.pi / 2)
        flip_sign   = -1 if facing_left else 1   # Dikey (perp) yönü tersine çevir

        cos_a = math.cos(final_angle)
        sin_a = math.sin(final_angle)

        # ── KOL (Arm) — omuzdan (cx,cy) silah pivotuna ──────────────────────
        arm_color = (55, 35, 65)
        pygame.draw.line(surface, arm_color,
                         (int(cx), int(cy)), (int(pivot_x), int(pivot_y)), 5)

        # ── Gövde (Body) ────────────────────────────────────────────────────
        body_cx = pivot_x + cos_a * (self.BODY_LEN / 2)
        body_cy = pivot_y + sin_a * (self.BODY_LEN / 2)
        body_pts = _rotated_rect_points(body_cx, body_cy,
                                        self.BODY_LEN, self.BODY_W, final_angle)
        pygame.draw.polygon(surface, self.BODY_COLOR, body_pts)
        pygame.draw.polygon(surface, self.ACCENT_COLOR, body_pts, 1)

        # ── Kabza (Grip) — gövdenin ortasından aşağı ──────────────────────
        grip_base_x = pivot_x + cos_a * (self.BODY_LEN * 0.35)
        grip_base_y = pivot_y + sin_a * (self.BODY_LEN * 0.35)
        # Kabza gövdeye dik yönde — sola bakarken aynalı
        perp_x = -sin_a * flip_sign
        perp_y =  cos_a * flip_sign
        grip_pts = [
            (int(grip_base_x + perp_x * 2),              int(grip_base_y + perp_y * 2)),
            (int(grip_base_x - perp_x * 2),              int(grip_base_y - perp_y * 2)),
            (int(grip_base_x - perp_x * 2 + cos_a * self.GRIP_LEN),
             int(grip_base_y - perp_y * 2 + sin_a * (self.GRIP_LEN * 0.5) + perp_y * self.GRIP_W)),
            (int(grip_base_x + perp_x * 2 + cos_a * (self.GRIP_LEN * 0.8)),
             int(grip_base_y + perp_y * 2 + sin_a * (self.GRIP_LEN * 0.3) + perp_y * self.GRIP_W)),
        ]
        pygame.draw.polygon(surface, self.GRIP_COLOR, grip_pts)

        # ── Namlu (Barrel) ───────────────────────────────────────────────────
        barrel_start_x = pivot_x + cos_a * self.BODY_LEN
        barrel_start_y = pivot_y + sin_a * self.BODY_LEN
        barrel_cx = barrel_start_x + cos_a * (self.BARREL_LEN / 2)
        barrel_cy = barrel_start_y + sin_a * (self.BARREL_LEN / 2)
        barrel_pts = _rotated_rect_points(barrel_cx, barrel_cy,
                                          self.BARREL_LEN, self.BARREL_W, final_angle)
        pygame.draw.polygon(surface, self.BARREL_COLOR, barrel_pts)

        # ── Namlu ucu (Muzzle tip) ───────────────────────────────────────────
        total_reach = self.BODY_LEN + self.BARREL_LEN
        mx = pivot_x + cos_a * total_reach
        my = pivot_y + sin_a * total_reach

        # Muzzle halkası
        pygame.draw.circle(surface, self.MUZZLE_COLOR, (int(mx), int(my)), 3)

        # ── Ateş çakması (Flash) ─────────────────────────────────────────────
        if self._flash_timer > 0:
            flash_r = random.randint(5, 9)
            pygame.draw.circle(surface, self.FLASH_COLOR, (int(mx), int(my)), flash_r)
            pygame.draw.circle(surface, (255, 255, 255),  (int(mx), int(my)), max(1, flash_r // 2))

        # ── Pivot noktası işareti ────────────────────────────────────────────
        pygame.draw.circle(surface, self.ACCENT_COLOR, (int(pivot_x), int(pivot_y)), 3)

        return (int(mx), int(my))


# ---------------------------------------------------------------------------
# SMG — Hafif Makinali Görsel Sınıfı
# ---------------------------------------------------------------------------

class SMGVisual:
    """
    SMG'nin GÖRSEL bileşeni.

    Özellikler:
    - Gövde: koyu mavi-gri kalın dikdörtgen   (uzun)
    - Şarjör çıkıntısı: gövdenin altından aşağı
    - Namlu: neon mavi ince dikdörtgen          (gövdenin önünden)
    - Recoil: birikimli sekme açısı (SMG_RECOIL)
    - Otomatik ateş titremesi

    draw(surface, cx, cy, angle, shoot_timer, accumulated_recoil)
        → muzzle_point döndürür
    """

    # ── Renkler ─────────────────────────────────────────────────────────────
    BODY_COLOR    = (55,  75,  95)    # Koyu mavi-gri gövde
    BARREL_COLOR  = (0,  210, 255)    # Neon mavi namlu
    MAG_COLOR     = (35,  55,  70)    # Şarjör rengi
    ACCENT_COLOR  = (0,  180, 230)    # Neon mavi aksesuar şeridi
    STOCK_COLOR   = (40,  60,  75)    # Dipçik
    FLASH_COLOR   = (0,  230, 255)    # Ateş çakması

    # ── Boyutlar ────────────────────────────────────────────────────────────
    BODY_LEN   = 32    # Gövde uzunluğu
    BODY_W     = 10    # Gövde genişliği
    BARREL_LEN = 22    # Namlu uzunluğu
    BARREL_W   = 5     # Namlu genişliği
    MAG_H      = 14    # Şarjör yüksekliği
    MAG_W      = 8     # Şarjör genişliği
    STOCK_LEN  = 10    # Dipçik uzunluğu
    STOCK_W    = 7     # Dipçik genişliği

    # ── Recoil ──────────────────────────────────────────────────────────────
    SHAKE_MAX  = 1.5   # Titreme miktarı (px)
    SHAKE_WIN  = 0.08  # Titreme penceresi (sn)

    def __init__(self):
        self._flash_timer = 0.0
        self._accumulated_recoil = 0.0   # Birikimli sekme açısı (rad)

    def update(self, dt: float):
        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt)
        # Sekme zamanla sıfıra yaklaşır
        if self._accumulated_recoil != 0:
            decay = dt * 3.0
            if abs(self._accumulated_recoil) < decay:
                self._accumulated_recoil = 0.0
            else:
                self._accumulated_recoil -= math.copysign(decay, self._accumulated_recoil)

    def notify_fired(self):
        """Her ateş etmede çağrılır. Flash ve sekme birikimi."""
        self._flash_timer = 0.05
        self._accumulated_recoil = min(
            self._accumulated_recoil + SMG_RECOIL,
            SMG_RECOIL * 6   # Maksimum birikim
        )

    def get_muzzle_point(self, cx: float, cy: float, angle: float,
                         shoot_timer: float = 0.0):
        """Namlu ucunun koordinatını döndürür (mermi başlangıç noktası)."""
        _, _, _, mx, my = self._compute_parts(cx, cy, angle, shoot_timer)
        return (int(mx), int(my))

    def _compute_parts(self, cx, cy, angle, shoot_timer):
        """Pivot, final açı ve muzzle hesaplar."""
        # Titreme (ateş anında)
        shake_x = shake_y = 0.0
        if 0 < shoot_timer < self.SHAKE_WIN:
            shake_x = random.uniform(-self.SHAKE_MAX, self.SHAKE_MAX)
            shake_y = random.uniform(-self.SHAKE_MAX, self.SHAKE_MAX)

        final_angle = angle + self._accumulated_recoil
        pivot_x = cx + shake_x
        pivot_y = cy + shake_y

        cos_a = math.cos(final_angle)
        sin_a = math.sin(final_angle)

        # Namlu ucu
        total_reach = self.BODY_LEN + self.BARREL_LEN
        mx = pivot_x + cos_a * total_reach
        my = pivot_y + sin_a * total_reach

        return pivot_x, pivot_y, final_angle, mx, my

    def draw(self, surface: pygame.Surface,
             cx: float, cy: float,
             angle: float, shoot_timer: float = 0.0):
        """
        SMG'yi çizer. Muzzle point döndürür.

        Parametreler:
            surface       : Çizilecek yüzey
            cx, cy        : Pivot noktası (oyuncu el ortası)
            angle         : Radyan bakış açısı
            shoot_timer   : Son atıştan bu yana süre (sn)
        """
        pivot_x, pivot_y, final_angle, mx, my = self._compute_parts(
            cx, cy, angle, shoot_timer)

        # ── FLIP: Sola bakarken dikey eksende aynala ─────────────────────────
        facing_left = abs(angle) > (math.pi / 2)
        flip_sign   = -1 if facing_left else 1

        cos_a = math.cos(final_angle)
        sin_a = math.sin(final_angle)
        perp_x = -sin_a * flip_sign
        perp_y =  cos_a * flip_sign

        # ── KOL (Arm) — omuzdan (cx,cy) silah pivotuna ──────────────────────
        arm_color = (40, 55, 70)
        pygame.draw.line(surface, arm_color,
                         (int(cx), int(cy)), (int(pivot_x), int(pivot_y)), 6)

        # ── Dipçik (Stock) — pivot'un gerisinde ──────────────────────────
        stock_cx = pivot_x - cos_a * (self.STOCK_LEN / 2)
        stock_cy = pivot_y - sin_a * (self.STOCK_LEN / 2)
        stock_pts = _rotated_rect_points(stock_cx, stock_cy,
                                         self.STOCK_LEN, self.STOCK_W, final_angle)
        pygame.draw.polygon(surface, self.STOCK_COLOR, stock_pts)

        # ── Gövde (Body) ─────────────────────────────────────────────────
        body_cx = pivot_x + cos_a * (self.BODY_LEN / 2)
        body_cy = pivot_y + sin_a * (self.BODY_LEN / 2)
        body_pts = _rotated_rect_points(body_cx, body_cy,
                                        self.BODY_LEN, self.BODY_W, final_angle)
        pygame.draw.polygon(surface, self.BODY_COLOR, body_pts)

        # Neon aksesuar şeridi (gövde üzerinde ince highlight)
        accent_cx = pivot_x + cos_a * (self.BODY_LEN * 0.4)
        accent_cy = pivot_y + sin_a * (self.BODY_LEN * 0.4)
        acc_pts = _rotated_rect_points(accent_cx, accent_cy, 8, self.BODY_W + 2, final_angle)
        pygame.draw.polygon(surface, self.ACCENT_COLOR, acc_pts, 1)

        # ── Şarjör çıkıntısı (Mag) — gövdenin altından aşağı ─────────────
        mag_root_x = pivot_x + cos_a * (self.BODY_LEN * 0.5)
        mag_root_y = pivot_y + sin_a * (self.BODY_LEN * 0.5)
        mag_pts = [
            (int(mag_root_x + perp_x * (self.BODY_W // 2)),
             int(mag_root_y + perp_y * (self.BODY_W // 2))),
            (int(mag_root_x - perp_x * 2),
             int(mag_root_y - perp_y * 2)),
            (int(mag_root_x - perp_x * 2 + cos_a * self.MAG_W
                 + perp_x * self.MAG_H),
             int(mag_root_y - perp_y * 2 + sin_a * self.MAG_W
                 + perp_y * self.MAG_H)),
            (int(mag_root_x + perp_x * (self.BODY_W // 2) + cos_a * self.MAG_W
                 + perp_x * self.MAG_H),
             int(mag_root_y + perp_y * (self.BODY_W // 2) + sin_a * self.MAG_W
                 + perp_y * self.MAG_H)),
        ]
        pygame.draw.polygon(surface, self.MAG_COLOR, mag_pts)
        pygame.draw.polygon(surface, self.ACCENT_COLOR, mag_pts, 1)

        # ── Namlu (Barrel) ─────────────────────────────────────────────────
        barrel_start_x = pivot_x + cos_a * self.BODY_LEN
        barrel_start_y = pivot_y + sin_a * self.BODY_LEN
        barrel_cx = barrel_start_x + cos_a * (self.BARREL_LEN / 2)
        barrel_cy = barrel_start_y + sin_a * (self.BARREL_LEN / 2)
        barrel_pts = _rotated_rect_points(barrel_cx, barrel_cy,
                                          self.BARREL_LEN, self.BARREL_W, final_angle)
        pygame.draw.polygon(surface, self.BARREL_COLOR, barrel_pts)

        # ── Namlu ucu halkası ──────────────────────────────────────────────
        pygame.draw.circle(surface, self.BARREL_COLOR, (int(mx), int(my)), 3)

        # ── Muzzle flash (ateş anında) ──────────────────────────────────────
        if self._flash_timer > 0:
            flash_r = random.randint(4, 8)
            pygame.draw.circle(surface, self.FLASH_COLOR, (int(mx), int(my)), flash_r)
            pygame.draw.circle(surface, (255, 255, 255),  (int(mx), int(my)), max(1, flash_r // 2))
            # Yan parlamalar (SMG için çapraz)
            for _d_angle in (-0.4, 0.4):
                ex = mx + math.cos(final_angle + _d_angle) * flash_r
                ey = my + math.sin(final_angle + _d_angle) * flash_r
                pygame.draw.line(surface, self.FLASH_COLOR,
                                 (int(mx), int(my)), (int(ex), int(ey)), 2)

        # ── Pivot noktası ──────────────────────────────────────────────────
        pygame.draw.circle(surface, self.ACCENT_COLOR, (int(pivot_x), int(pivot_y)), 3)

        return (int(mx), int(my))