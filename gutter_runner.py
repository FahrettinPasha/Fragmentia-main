# gutter_runner.py
# =============================================================================
# THE GUTTER — Bölüm 1 ve Bölüm 2 çalıştırıcısı
# main.py'dan screen ve clock alır, kendi iç döngüsünü çalıştırır.
# Geri döndürdüğü değerler: "completed" | "died" | "quit"
# =============================================================================
import pygame, math, random

# ── İÇ ÇÖZÜNÜRLÜK ─────────────────────────────────────────────────────────────
SW, SH = 1280, 720
FPS    = 60

# Dünya boyutları
WW1, WH1  = 4200, 1500      # Level 1
FLOOR1_L1 = 1200
FLOOR2_L1 = 820

WW2, WH2  = 4600, 900       # Level 2
FLOOR_L2  = 760

GRAVITY = 980.0

# ── RENKLER ──────────────────────────────────────────────────────────────────
BG      = (4,   6,  10)
BG_DEEP = (2,   3,   6)
WHITE   = (255,255,255)
CYAN    = (0,  220, 200)
AMBER   = (255,160,   0)
RED     = (200, 35,  35)
GRAY    = ( 90,105, 115)
DGRAY   = ( 45, 58,  68)
LGRAY   = (130,150, 165)
MGRAY   = ( 70, 82,  92)
BROWN   = ( 90, 72,  52)
DBROWN  = ( 52, 40,  26)
LBROWN  = (130,108,  80)
RUST    = (110, 55,  30)
DRUST   = ( 70, 30,   8)
LRUST   = (175, 85,  35)

# ══════════════════════════════════════════════════════════════════════════════
# ORTAK SINIFLAR
# ══════════════════════════════════════════════════════════════════════════════

class Cam:
    def __init__(self):
        self.x=0.;self.y=0.;self.st=0.;self.si=0.
        self.sx=0;self.sy=0;self.sf=1.
    def update(self, dt, px, py, f, ww, wh):
        self.sf += (f - self.sf) * min(1., 4.*dt)
        tx = max(0., min(float(ww-SW), px - SW//2 + self.sf*140.))
        ty = max(0., min(float(wh-SH), py - SH//2 - 60))
        self.x += (tx-self.x)*min(1.,6.*dt)
        self.y += (ty-self.y)*min(1.,6.*dt)
        if self.st > 0:
            self.st -= dt
            i = int(self.si)
            self.sx = random.randint(-i,i)
            self.sy = random.randint(-i,i)
        else:
            self.sx = self.sy = 0
        self.x = max(0., min(float(ww-SW), self.x))
        self.y = max(0., min(float(wh-SH), self.y))
    def shake(self, i, d=.3): self.si=i; self.st=d
    @property
    def ox(self): return int(self.x)+self.sx
    @property
    def oy(self): return int(self.y)+self.sy


def resolve(rect, vy, plats):
    on = False
    for p in plats:
        if vy >= 0 and rect.colliderect(p):
            rect.bottom = p.top; vy = 0.; on = True
    return vy, on


class Player:
    W=22; H=40; HP=6
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, self.W, self.H)
        self.vx=0.; self.vy=0.; self.on=False; self.f=1
        self.hp=self.HP; self.hc=0.; self.dc=0.; self.dt=0.; self.ac=0.
        self.alive=True
    def take_hit(self, cam):
        if self.hc > 0: return
        self.hp = max(0, self.hp-1); self.hc=.6; cam.shake(5,.2)
        self.vx = -self.f*160.; self.vy = -100.
        if self.hp <= 0: self.alive = False
    def update(self, dt, plats):
        for a in ("hc","dc","dt","ac"):
            v = getattr(self,a)
            if v > 0: setattr(self, a, max(0., v-dt))
        if self.dt > 0:
            self.vx = self.f*460.
        else:
            keys = pygame.key.get_pressed()
            mv = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - \
                 (keys[pygame.K_a] or keys[pygame.K_LEFT])
            if mv: self.f = mv
            self.vx = mv*200.
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]) and self.on:
            self.vy=-470.; self.on=False
        self.vy = min(self.vy + GRAVITY*dt, 1400)
        self.rect.x += int(self.vx*dt)
        self.rect.x = max(0, self.rect.x)
        self.rect.y += int(self.vy*dt)
        self.vy, self.on = resolve(self.rect, self.vy, plats)
    def dash(self):
        if self.dc <= 0: self.dt=.13; self.dc=.65; self.vy=min(self.vy,0)
    def draw(self, surf, ox, oy):
        if self.hc > 0 and int(self.hc*12)%2==0: return
        bx=self.rect.x-ox; by=self.rect.y-oy
        if self.dt > 0:
            for i in range(1,4):
                s = pygame.Surface((self.W,self.H), pygame.SRCALPHA)
                s.fill((*CYAN, max(0,70-i*24)))
                surf.blit(s, (bx-self.f*i*12, by))
        pygame.draw.rect(surf, RED if self.hc>0 else WHITE, (bx,by,self.W,self.H))
        pygame.draw.rect(surf, CYAN, (bx+3,by-14,16,14))
        bw=38; pygame.draw.rect(surf,(40,10,10),(bx-8,by-24,bw,5))
        pygame.draw.rect(surf, RED, (bx-8,by-24,int(bw*self.hp/self.HP),5))


class Grunt:          # Level 1 düşmanı
    W=26; H=42; HP=3
    def __init__(self, x, y):
        self.rect=pygame.Rect(x,y,self.W,self.H)
        self.vy=0.; self.hp=self.HP; self.f=-1
        self.state="patrol"; self.st=0.; self.at=0.
        self.pd=random.choice([-1,1]); self.pt=random.uniform(1.,2.5); self.ptimer=0.
    def hit(self, cam):
        if self.state=="dead": return
        self.hp -= 1; cam.shake(5,.18)
        if self.hp<=0: self.state="dead"
        else: self.state="stun"; self.st=.35; self.vy=-130.
    def update(self, dt, player, plats, eq):
        if self.state=="dead": return
        self.vy+=GRAVITY*dt; self.rect.y+=int(self.vy*dt)
        self.vy,_=resolve(self.rect,self.vy,plats)
        dx=player.rect.centerx-self.rect.centerx; dist=abs(dx)
        if self.state=="stun":
            self.st-=dt
            if self.st<=0: self.state="patrol"
            return
        if self.state=="patrol":
            self.ptimer+=dt; self.rect.x+=int(self.pd*85.*dt); self.f=self.pd
            if self.ptimer>self.pt: self.pd*=-1;self.ptimer=0;self.pt=random.uniform(1.,2.5)
            if dist<300: self.state="chase"
        elif self.state=="chase":
            self.f=1 if dx>0 else -1; self.rect.x+=int(self.f*140.*dt)
            if dist<50: self.state="attack"
            if dist>450: self.state="patrol"
        elif self.state=="attack":
            self.f=1 if dx>0 else -1; self.at+=dt
            if self.at>=.55:
                self.at=0.
                dy=abs(player.rect.centery-self.rect.centery)
                if abs(dx)<55 and dy<self.H+10: eq.append({"t":"HIT"})
            if dist>70: self.state="chase"; self.at=0.
    def draw(self, surf, ox, oy):
        if self.state=="dead": return
        bx=self.rect.x-ox; by=self.rect.y-oy
        col=(80,40,25) if self.state=="stun" else BROWN
        pygame.draw.rect(surf,col,(bx,by,self.W,self.H))
        pygame.draw.rect(surf,DGRAY,(bx+2,by+4,10,14))
        pygame.draw.rect(surf,DGRAY,(bx+14,by+4,10,14))
        pygame.draw.line(surf,LGRAY,(bx+2,by+4),(bx+12,by+4),1)
        pygame.draw.line(surf,LGRAY,(bx+14,by+4),(bx+24,by+4),1)
        pygame.draw.rect(surf,BROWN,(bx+3,by-12,20,12))
        ex=bx+15 if self.f>0 else bx+5
        pygame.draw.rect(surf,RED,(ex,by-8,5,4))
        bw=34; pygame.draw.rect(surf,(40,10,10),(bx-3,by-19,bw,4))
        pygame.draw.rect(surf,(200,35,35),(bx-3,by-19,int(bw*self.hp/self.HP),4))


class Scavenger:       # Level 2 düşmanı
    W=26; H=42; HP=3
    def __init__(self, x, y):
        self.rect=pygame.Rect(x,y,self.W,self.H)
        self.vy=0.; self.hp=self.HP; self.f=-1
        self.state="patrol"; self.st=0.; self.at=0.
        self.pd=random.choice([-1,1]); self.pt=random.uniform(1.,2.2); self.ptimer=0.
    def hit(self, cam):
        if self.state=="dead": return
        self.hp-=1; cam.shake(4,.14)
        if self.hp<=0: self.state="dead"
        else: self.state="stun"; self.st=.32; self.vy=-110.
    def update(self, dt, player, plats, eq):
        if self.state=="dead": return
        self.vy+=GRAVITY*dt; self.rect.y+=int(self.vy*dt)
        self.vy,_=resolve(self.rect,self.vy,plats)
        self.rect.x=max(0,min(self.rect.x,WW2-self.W))
        dx=player.rect.centerx-self.rect.centerx; dist=abs(dx)
        if self.state=="stun":
            self.st-=dt
            if self.st<=0: self.state="patrol"
            return
        if self.state=="patrol":
            self.ptimer+=dt; self.rect.x+=int(self.pd*80.*dt); self.f=self.pd
            if self.ptimer>self.pt: self.pd*=-1;self.ptimer=0;self.pt=random.uniform(1.,2.2)
            if dist<320: self.state="chase"
        elif self.state=="chase":
            self.f=1 if dx>0 else -1; self.rect.x+=int(self.f*135.*dt)
            if dist<50: self.state="attack"
            if dist>460: self.state="patrol"
        elif self.state=="attack":
            self.f=1 if dx>0 else -1; self.at+=dt
            if self.at>=.55:
                self.at=0.
                if abs(dx)<55 and abs(player.rect.centery-self.rect.centery)<self.H+10:
                    eq.append({"t":"HIT"})
            if dist>72: self.state="chase"; self.at=0.
    def draw(self, surf, ox, oy):
        if self.state=="dead": return
        bx=self.rect.x-ox; by=self.rect.y-oy
        col=(100,48,24) if self.state=="stun" else RUST
        pygame.draw.rect(surf,col,(bx,by,self.W,self.H))
        pygame.draw.rect(surf,DGRAY,(bx+2,by+5,9,13))
        pygame.draw.rect(surf,DGRAY,(bx+15,by+5,9,13))
        pygame.draw.rect(surf,LRUST,(bx+3,by-10,18,10))
        ex=bx+17 if self.f>0 else bx+3
        pygame.draw.rect(surf,(195,38,18),(ex,by-6,5,4))
        bw=36; pygame.draw.rect(surf,(50,12,12),(bx-4,by-18,bw,4))
        pygame.draw.rect(surf,(210,30,30),(bx-4,by-18,int(bw*self.hp/self.HP),4))


class Debris:
    def __init__(self, x, y, w, h, floor_y=None):
        self.x=float(x); self.y=float(y); self.w=w; self.h=h
        self.vx=random.uniform(-240,240); self.vy=random.uniform(-380,-60)
        self.rot=0.; self.rot_spd=random.uniform(-300,300)
        self.bounce=0; self.floor_y=float(floor_y) if floor_y else None; self.alive=True
        self.col=random.choice([BROWN,DBROWN,GRAY,DGRAY,RUST])
    def update(self, dt):
        self.vy+=GRAVITY*dt; self.x+=self.vx*dt; self.y+=self.vy*dt
        self.rot+=self.rot_spd*dt
        if self.floor_y and self.y+self.h > self.floor_y:
            self.y=self.floor_y-self.h; self.vy*=-0.28
            self.vx*=0.65; self.rot_spd*=0.5; self.bounce+=1
            if self.bounce>4 or abs(self.vy)<12: self.vy=0; self.vx*=0.8
        if abs(self.x) > 8000: self.alive=False
    def draw(self, surf, ox, oy):
        sx=int(self.x-ox); sy=int(self.y-oy)
        if not(-80<sx<SW+80 and -80<sy<SH+80): return
        s=pygame.Surface((self.w,self.h),pygame.SRCALPHA)
        pygame.draw.rect(s,self.col,(0,0,self.w,self.h))
        pygame.draw.rect(s,LGRAY,(0,0,self.w,self.h),1)
        rs=pygame.transform.rotate(s,self.rot%360)
        surf.blit(rs,(sx-rs.get_width()//2, sy-rs.get_height()//2))


class HillGuard:       # Level 2 mini boss
    W=34; H=52; HP_MAX=8
    def __init__(self, x, cam):
        self.rect=pygame.Rect(x,FLOOR_L2-self.H,self.W,self.H)
        self.x=float(x); self.y=float(FLOOR_L2-self.H)
        self.vy=0.; self.hp=self.HP_MAX; self.f=-1; self.cam=cam
        self.state="idle"; self.phase_t=0.; self.anim_t=0.
        self.alive=True; self.debris=[]; self.slam_debris=[]
        self.charge_vx=0.; self.charge_t=0.
    def hit(self, cam):
        if self.state in ("dead","charge"): return False
        self.hp-=1; cam.shake(7,.22)
        if self.hp<=0:
            self.state="dead"; self.alive=False
            for _ in range(20):
                d=Debris(self.rect.centerx+random.randint(-40,40),
                         self.rect.centery,random.randint(8,26),random.randint(8,18))
                self.debris.append(d)
        else:
            self.state="stun"; self.phase_t=0.
        return True
    def update(self, dt, player, plats, eq):
        for d in self.debris+self.slam_debris: d.update(dt)
        self.debris=[d for d in self.debris if d.alive]
        self.slam_debris=[d for d in self.slam_debris if d.alive]
        if not self.alive: return
        self.anim_t+=dt; self.phase_t+=dt
        self.vy+=GRAVITY*dt; self.y+=self.vy*dt; self.rect.y=int(self.y)
        self.vy,on=resolve(self.rect,self.vy,plats)
        if on: self.y=float(self.rect.y)
        dx=player.rect.centerx-self.rect.centerx
        dist=abs(dx); self.f=1 if dx>0 else -1
        if self.state=="idle":
            if self.phase_t>1.6: self.state="walk"; self.phase_t=0.
        elif self.state=="walk":
            self.x+=self.f*50.*dt; self.rect.x=int(self.x)
            if dist<180: self.state="windup"; self.phase_t=0.
            if self.phase_t>5.: self.state="idle"; self.phase_t=0.
        elif self.state=="windup":
            if int(self.anim_t*12)%2==0: self.rect.x=int(self.x)+random.randint(-3,3)
            if self.phase_t>=0.9:
                self.state="charge"; self.phase_t=0.
                self.charge_vx=self.f*320.; self.cam.shake(14,.5)
                for _ in range(10):
                    d=Debris(self.rect.centerx,FLOOR_L2-10,
                             random.randint(8,22),random.randint(6,16))
                    self.slam_debris.append(d)
        elif self.state=="charge":
            self.x+=self.charge_vx*dt; self.rect.x=int(self.x)
            self.charge_t+=dt
            if self.rect.colliderect(player.rect): eq.append({"t":"HIT"})
            if self.charge_t>=0.4: self.state="stun"; self.phase_t=0.; self.charge_t=0.
        elif self.state=="stun":
            if self.phase_t>=1.2: self.state="walk"; self.phase_t=0.
        self.rect.x=max(2700, min(self.rect.x, WW2-self.W))
    def draw(self, surf, ox, oy):
        for d in self.debris+self.slam_debris: d.draw(surf,ox,oy)
        if not self.alive: return
        sx=int(self.rect.x-ox); sy=int(self.rect.y-oy)
        col=(130,70,30) if self.state=="stun" else RUST
        pygame.draw.rect(surf,col,(sx,sy,self.W,self.H))
        pygame.draw.rect(surf,MGRAY,(sx+1,sy+3,self.W-2,30))
        pygame.draw.rect(surf,LGRAY,(sx+1,sy+3,self.W-2,30),2)
        for xi in range(3,self.W-3,7):
            pygame.draw.line(surf,DGRAY,(sx+xi,sy+5),(sx+xi,sy+31),1)
        pygame.draw.rect(surf,(88,65,42),(sx+5,sy-16,24,16))
        ex=sx+24 if self.f>0 else sx+2
        pygame.draw.rect(surf,RED,(ex,sy-11,7,5))
        pygame.draw.rect(surf,MGRAY,(sx-6,sy+2,10,18))
        pygame.draw.rect(surf,MGRAY,(sx+self.W-4,sy+2,10,18))
        if self.state=="stun": pygame.draw.rect(surf,CYAN,(sx-3,sy-3,self.W+6,self.H+6),2)
        if self.state=="windup":
            sh=int(math.sin(self.anim_t*40)*4)
            pygame.draw.rect(surf,AMBER,(sx-3+sh,sy-3,self.W+6,self.H+6),2)
        bw=48; pygame.draw.rect(surf,(50,10,10),(sx-7,sy-28,bw,6))
        pygame.draw.rect(surf,RED,(sx-7,sy-28,int(bw*max(0.,self.hp/self.HP_MAX)),6))
        pygame.draw.rect(surf,MGRAY,(sx-7,sy-28,bw,6),1)


class FallingScrap:
    BURST=2.4; PAUSE=1.8
    def __init__(self, x1, x2):
        self.x1=x1; self.x2=x2
        self.pieces=[]; self.spawn_t=0.; self.active=False
        self.cycle_t=0.; self.raining=True
    def try_activate(self, px):
        if not self.active and px>self.x1-350: self.active=True
    def update(self, dt):
        if not self.active: return
        self.cycle_t+=dt
        limit=self.BURST if self.raining else self.PAUSE
        if self.cycle_t>=limit: self.cycle_t=0.; self.raining=not self.raining
        if self.raining:
            self.spawn_t+=dt
            if self.spawn_t>0.065:
                self.spawn_t=0.
                sx=random.uniform(self.x1,self.x2)
                self.pieces.append({
                    "x":float(sx),"y":-30.,
                    "w":random.randint(10,44),"h":random.randint(6,20),
                    "vy":random.uniform(250,560),
                    "rot":random.uniform(0,360),"rs":random.uniform(-230,230),
                    "col":random.choice([BROWN,DBROWN,GRAY,DGRAY,RUST,LGRAY]),
                    "alive":True
                })
        for p in self.pieces:
            p["y"]+=p["vy"]*dt; p["rot"]+=p["rs"]*dt
            if p["y"]>3000: p["alive"]=False
        self.pieces=[p for p in self.pieces if p["alive"]]
    def check_hit(self, prect):
        for p in self.pieces:
            pr=pygame.Rect(int(p["x"]-p["w"]//2),int(p["y"]-p["h"]//2),p["w"],p["h"])
            if pr.colliderect(prect): return True
        return False
    def draw(self, surf, ox, oy):
        for p in self.pieces:
            sx=int(p["x"]-ox); sy=int(p["y"]-oy)
            if not(-80<sx<SW+80 and -80<sy<SH+80): continue
            s=pygame.Surface((p["w"],p["h"]),pygame.SRCALPHA)
            pygame.draw.rect(s,p["col"],(0,0,p["w"],p["h"]))
            pygame.draw.rect(s,LGRAY,(0,0,p["w"],p["h"]),1)
            rs=pygame.transform.rotate(s,p["rot"]%360)
            surf.blit(rs,(sx-rs.get_width()//2,sy-rs.get_height()//2))


class ColPlat:
    def __init__(self, x, y, w, cam, floor_y):
        self.rect=pygame.Rect(x,y,w,18); self.t=-1.; self.fallen=False
        self.cam=cam; self.sd=False; self.debris=[]; self._floor_y=floor_y; self._fade=1.0
    def trigger(self):
        if self.t<0: self.t=0.
    def update(self, dt, eq):
        for d in self.debris: d.update(dt)
        self.debris=[d for d in self.debris if d.alive]
        if self.t<0: return
        self.t+=dt
        if self.t>=.55 and not self.sd: self.sd=True; self.cam.shake(8,.55)
        if self.t>=.55: self._fade=max(0.,1.0-(self.t-.55)/.55)
        if self.t>=1.1 and not self.fallen:
            self.fallen=True; eq.append({"t":"COL"})
            x_cur=self.rect.x
            while x_cur<self.rect.right:
                pw=random.randint(18,44); pw=min(pw,self.rect.right-x_cur)
                ph=random.randint(10,22)
                d=Debris(x_cur+pw//2,self.rect.y,pw,ph,floor_y=self._floor_y)
                self.debris.append(d); x_cur+=pw
    def draw(self, surf, ox, oy):
        for d in self.debris: d.draw(surf,ox,oy)
        if self._fade<=0: return
        dr=self.rect.move(-ox,-oy)
        if self.t>.55: dr=dr.move(random.randint(-2,2),0)
        alpha=int(255*self._fade)
        s=pygame.Surface((dr.w,dr.h),pygame.SRCALPHA)
        if self.t>.55:
            r2=min(1.,(self.t-.55)/.55)
            c=(int(60+140*r2),int(45*(1-r2)),int(30*(1-r2)),alpha)
        else: c=(*BROWN,alpha)
        pygame.draw.rect(s,c,(0,0,dr.w,dr.h))
        pygame.draw.rect(s,(*LBROWN,alpha),(0,0,dr.w,dr.h),2)
        surf.blit(s,(dr.x,dr.y))


# ── ÇİZİM YARDIMCILARI ───────────────────────────────────────────────────────
def draw_plat(surf, r, ox, oy, scrap=False, col=None):
    dr=r.move(-ox,-oy)
    if dr.x+dr.w<-80 or dr.x>SW+80: return
    if dr.y+dr.h<-80 or dr.y>SH+80: return
    base=col or (DBROWN if scrap else DGRAY)
    edge=LBROWN if scrap else LGRAY
    pygame.draw.rect(surf,base,dr)
    pygame.draw.line(surf,edge,(dr.x,dr.y),(dr.x+dr.w,dr.y),3)
    pygame.draw.line(surf,GRAY,(dr.x,dr.y),(dr.x,dr.y+dr.h),1)
    pygame.draw.line(surf,(20,28,34),(dr.x,dr.y+dr.h),(dr.x+dr.w,dr.y+dr.h),2)
    pygame.draw.line(surf,(20,28,34),(dr.x+dr.w,dr.y),(dr.x+dr.w,dr.y+dr.h),2)
    if dr.h>12:
        lc=(55,38,22) if scrap else (35,46,55)
        for iy in range(6,dr.h,10):
            pygame.draw.line(surf,lc,(dr.x+2,dr.y+iy),(dr.x+dr.w-2,dr.y+iy),1)


def draw_tunnel_l1(surf, ox, oy):
    x1=1500-ox; x2=2200-ox; tw=700
    ceil_y=560-oy; floor_y=FLOOR2_L1-oy
    if x2<-120 or x1>SW+120: return
    pygame.draw.rect(surf,DGRAY,(x1,0,tw,ceil_y))
    pygame.draw.line(surf,LGRAY,(x1,ceil_y),(x2,ceil_y),3)
    for iy in range(8,max(8,ceil_y),12):
        pygame.draw.line(surf,(28,38,46),(x1+2,iy),(x2-2,iy),1)
    for i in range(0,tw,22):
        h=6+((i*7)%14)
        pygame.draw.line(surf,GRAY,(x1+i,ceil_y),(x1+i+9,ceil_y+h),2)
    pygame.draw.rect(surf,DBROWN,(x1-70,ceil_y,70,floor_y-ceil_y))
    pygame.draw.line(surf,LBROWN,(x1,ceil_y),(x1,floor_y),3)
    pygame.draw.rect(surf,DBROWN,(x2,ceil_y,70,floor_y-ceil_y))
    pygame.draw.line(surf,LBROWN,(x2,ceil_y),(x2,floor_y),3)


def draw_corridor_l2(surf, ox, oy):
    x1=1500-ox; x2=2100-ox; tw=600
    ceil_y=460-oy; floor_y=FLOOR_L2-oy
    if x2<-120 or x1>SW+120: return
    pygame.draw.rect(surf,DGRAY,(x1,0,tw,ceil_y))
    pygame.draw.line(surf,LGRAY,(x1,ceil_y),(x2,ceil_y),3)
    for iy in range(8,max(8,ceil_y),12):
        pygame.draw.line(surf,(28,38,46),(x1+2,iy),(x2-2,iy),1)
    pygame.draw.rect(surf,DBROWN,(x1-70,ceil_y,70,floor_y-ceil_y))
    pygame.draw.line(surf,LBROWN,(x1,ceil_y),(x1,floor_y),3)
    pygame.draw.rect(surf,DBROWN,(x2,ceil_y,70,floor_y-ceil_y))
    pygame.draw.line(surf,LBROWN,(x2,ceil_y),(x2,floor_y),3)


def draw_grave_markers(surf, ox, oy):
    markers=[
        (70,52,6,0),(160,40,5,1),(260,58,7,2),(380,44,5,0),(490,62,6,1),
        (610,48,5,3),(730,55,7,0),(850,42,5,2),(970,60,6,1),(1080,46,5,0),
        (1200,54,6,3),(1320,40,5,2),(1440,58,7,0),
        (2150,50,6,1),(2300,44,5,0),(2420,60,7,2),(2550,48,5,3),
        (2760,55,6,0),(2880,42,5,1),(2980,58,7,2),
    ]
    for wx,gh,gw,tp in markers:
        sx=wx-ox; sy=FLOOR_L2-oy
        if sx<-50 or sx>SW+50: continue
        pygame.draw.rect(surf,DRUST,(sx-gw//2,sy-gh,gw,gh))
        pygame.draw.line(surf,(60,32,12),(sx-gw-4,sy-int(gh*0.5)),(sx+gw+4,sy-int(gh*0.5)),1)
        if tp==1:
            pygame.draw.rect(surf,RUST,(sx-3,sy-gh,6,6))
        elif tp==2:
            pygame.draw.rect(surf,DGRAY,(sx-gw//2,sy-gh,gw,5))


def draw_settlement_glow(surf, ox, oy, t, boss_dead):
    if not boss_dead: return
    ex=4200-ox
    a=int(min(255,t*40))
    for i in range(3):
        r=20+i*12
        s=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
        pygame.draw.circle(s,(255,160,40,max(0,a-i*60)),(r,r),r)
        surf.blit(s,(ex-r,SH//2-r))


# ── FONT YÜKLE ────────────────────────────────────────────────────────────────
def _load_fonts():
    try:
        fhud  = pygame.font.SysFont("Courier New",13)
        fdead = pygame.font.SysFont("Courier New",34,bold=True)
        fbig  = pygame.font.SysFont("Courier New",38,bold=True)
        fmed  = pygame.font.SysFont("Courier New",22,bold=True)
        fsml  = pygame.font.SysFont("Courier New",13)
    except Exception:
        fhud  = pygame.font.Font(None,16)
        fdead = pygame.font.Font(None,40)
        fbig  = pygame.font.Font(None,48)
        fmed  = pygame.font.Font(None,28)
        fsml  = pygame.font.Font(None,16)
    return fhud,fdead,fbig,fmed,fsml


# ══════════════════════════════════════════════════════════════════════════════
# SİNEMATİKLER — LEVEL 1
# ══════════════════════════════════════════════════════════════════════════════
class Opening_L1:
    IY=400
    def __init__(self,sw,sh):
        self.sw=sw;self.sh=sh;self.t=0.;self.done=False;self.imp=False
        self.debris=[];self.dust=[]
        try: self.f1=pygame.font.SysFont("Courier New",26,bold=True);self.f2=pygame.font.SysFont("Courier New",15)
        except: self.f1=pygame.font.Font(None,32);self.f2=pygame.font.Font(None,20)
    def update(self,dt):
        self.t+=dt
        if self.t>=1.5 and not self.imp:
            self.imp=True;cx=self.sw//2
            for _ in range(42):
                a=random.uniform(0,math.pi);s=random.uniform(80,460)
                self.debris.append([cx,self.IY,math.cos(a)*s*random.choice([-1,1]),-math.sin(a)*s,
                    random.uniform(.5,2.2),0.,random.choice([BROWN,DBROWN,GRAY,DGRAY,RUST]),random.randint(3,14)])
            for _ in range(24):
                angle=random.uniform(0,math.tau);speed=random.uniform(40,200)
                self.dust.append({"x":float(cx),"y":float(self.IY),"vx":math.cos(angle)*speed,
                    "vy":math.sin(angle)*speed-30,"life":random.uniform(.9,2.4),"t":0.,"r":random.randint(4,18)})
        for d in self.debris: d[5]+=dt;d[3]+=700*dt;d[0]+=d[2]*dt;d[1]+=d[3]*dt
        for du in self.dust: du["t"]+=dt;du["x"]+=du["vx"]*dt;du["y"]+=du["vy"]*dt;du["vy"]+=140*dt
        self.dust=[du for du in self.dust if du["t"]<du["life"]]
        if self.t>=6.5: self.done=True
        return self.done
    def draw(self,surf):
        t=self.t;surf.fill(BG)
        for i in range(0,self.sw,110): pygame.draw.rect(surf,DGRAY,(i,self.sh//2,12,self.sh//2))
        pygame.draw.rect(surf,DBROWN,(0,self.IY+38,self.sw,self.sh))
        for d in self.debris:
            if d[5]<d[4]: a=max(0,1-d[5]/d[4]);s=max(1,int(d[7]*a));pygame.draw.rect(surf,d[6],(int(d[0])-s//2,int(d[1])-s//2,s,s))
        for du in self.dust:
            prog=du["t"]/du["life"];a=int(110*(1-prog));r=max(1,int(du["r"]*(1-prog*0.5)))
            s=pygame.Surface((r*2,r*2),pygame.SRCALPHA);pygame.draw.circle(s,(130,110,85,a),(r,r),r);surf.blit(s,(int(du["x"])-r,int(du["y"])-r))
        px=self.sw//2
        if t<1.5: e=min(t/1.5,1.)**3;py=int(-120+(self.IY+120)*e);st=int(10+(t/1.5)*28);pygame.draw.rect(surf,WHITE,(px-10,py,20,st))
        elif t<2.1: p=(t-1.5)/.6;pygame.draw.rect(surf,WHITE,(px-10,self.IY-16+int(p*20),20,36))
        elif t<3.0: p=(t-2.1)/.9;h=int(12+p*30);pygame.draw.rect(surf,WHITE,(px-10,self.IY+38-h,20,h))
        else: pygame.draw.rect(surf,WHITE,(px-10,self.IY,20,40))
        if 1.5<=t<=1.63: a=int(255*(1-(t-1.5)/.13));s=pygame.Surface((self.sw,self.sh),pygame.SRCALPHA);s.fill((255,255,255,a));surf.blit(s,(0,0))
        if t>3.2:
            fa=int(255*min(1.,(t-3.2)/.5))
            bw=500;bh=80;bx=self.sw//2-bw//2;by=80
            bs=pygame.Surface((bw,bh),pygame.SRCALPHA);bs.fill((0,0,0,int(195*(fa/255))));surf.blit(bs,(bx,by))
            pygame.draw.rect(surf,(*CYAN,fa),(bx,by,bw,bh),1)
            s1=self.f1.render("THE GUTTER",True,CYAN);s1.set_alpha(fa);surf.blit(s1,(bx+14,by+8))
            s2=self.f2.render("ABANDONED SCRAP ZONE",True,(155,195,175));s2.set_alpha(fa);surf.blit(s2,(bx+14,by+46))
        if t>5.8: a=int(255*min(1.,(t-5.8)/.7));fo=pygame.Surface((self.sw,self.sh));fo.set_alpha(a);fo.fill(BG);surf.blit(fo,(0,0))


class EndScene_L1:
    def __init__(self,sw,sh):
        self.sw=sw;self.sh=sh;self.t=0.;self.done=False
        try: self.f1=pygame.font.SysFont("Courier New",28,bold=True);self.f2=pygame.font.SysFont("Courier New",14)
        except: self.f1=pygame.font.Font(None,34);self.f2=pygame.font.Font(None,18)
    def update(self,dt): self.t+=dt;self.done=self.t>5.2;return self.done
    def draw(self,surf):
        a=int(255*min(1.,self.t/.75));fo=pygame.Surface((self.sw,self.sh));fo.set_alpha(a);fo.fill(BG_DEEP);surf.blit(fo,(0,0))
        if self.t>1.3:
            ta=int(255*min(1.,(self.t-1.3)/.6));s=self.f1.render("DEEPER LEVEL",True,CYAN);s.set_alpha(ta);surf.blit(s,(self.sw//2-s.get_width()//2,self.sh//2-28))
        if self.t>2.3:
            ta2=int(255*min(1.,(self.t-2.3)/.5));s2=self.f2.render("SETTLEMENT DETECTED  —  HUMAN TERRITORY",True,(95,150,128));s2.set_alpha(ta2);surf.blit(s2,(self.sw//2-s2.get_width()//2,self.sh//2+16))


# ══════════════════════════════════════════════════════════════════════════════
# SİNEMATİKLER — LEVEL 2
# ══════════════════════════════════════════════════════════════════════════════
class Opening_L2:
    IY=440
    def __init__(self,sw,sh):
        self.sw=sw;self.sh=sh;self.t=0.;self.done=False;self.imp=False
        self.debris=[]
        try: self.f1=pygame.font.SysFont("Courier New",34,bold=True);self.f2=pygame.font.SysFont("Courier New",14)
        except: self.f1=pygame.font.Font(None,44);self.f2=pygame.font.Font(None,18)
    def update(self,dt):
        self.t+=dt
        if self.t>=1.4 and not self.imp:
            self.imp=True;cx=self.sw//2
            for _ in range(36):
                a=random.uniform(0,math.pi);s=random.uniform(70,380)
                self.debris.append([cx,self.IY,math.cos(a)*s*random.choice([-1,1]),-math.sin(a)*s,
                    random.uniform(.4,1.8),0.,random.choice([RUST,DRUST,GRAY,DGRAY,BROWN]),random.randint(3,12)])
        for d in self.debris: d[5]+=dt;d[3]+=700*dt;d[0]+=d[2]*dt;d[1]+=d[3]*dt
        if self.t>=6.0: self.done=True
        return self.done
    def draw(self,surf):
        t=self.t;surf.fill(BG)
        pygame.draw.rect(surf,DBROWN,(0,self.IY+36,self.sw,self.sh))
        pygame.draw.line(surf,(65,42,22),(0,self.IY+36),(self.sw,self.IY+36),2)
        for i,gx in enumerate([80,210,380,560,740,910,1090,1200]):
            gh=28+((i*13)%28);gw=4+((i*5)%7);gy=self.IY+36
            pygame.draw.rect(surf,DRUST,(gx-gw//2,gy-gh,gw,gh))
            pygame.draw.line(surf,(60,32,12),(gx-gw-5,gy-int(gh*0.5)),(gx+gw+5,gy-int(gh*0.5)),1)
        for d in self.debris:
            if d[5]<d[4]: a=max(0,1-d[5]/d[4]);s=max(1,int(d[7]*a));pygame.draw.rect(surf,d[6],(int(d[0])-s//2,int(d[1])-s//2,s,s))
        px=self.sw//2-11
        if t<1.4: e=min(t/1.4,1.)**3;py=int(-110+(self.IY+110)*e);st=int(8+(t/1.4)*26);pygame.draw.rect(surf,WHITE,(px,py,22,st))
        elif t<2.0: p=(t-1.4)/.6;pygame.draw.rect(surf,WHITE,(px,self.IY-14+int(p*18),22,36))
        elif t<3.0: p=(t-2.0)/1.0;h=int(10+p*32);pygame.draw.rect(surf,WHITE,(px,self.IY+36-h,22,h))
        else: pygame.draw.rect(surf,WHITE,(px,self.IY,22,40));pygame.draw.rect(surf,(0,200,180),(px+3,self.IY-14,16,14))
        if 1.4<=t<=1.55: a=int(255*(1-(t-1.4)/.15));s=pygame.Surface((self.sw,self.sh),pygame.SRCALPHA);s.fill((255,255,255,a));surf.blit(s,(0,0))
        if t>3.0:
            fa=int(255*min(1.,(t-3.0)/.6))
            bw=500;bh=86;bx=self.sw//2-bw//2;by=85
            bs=pygame.Surface((bw,bh),pygame.SRCALPHA);bs.fill((0,0,0,int(195*(fa/255))));surf.blit(bs,(bx,by))
            pygame.draw.rect(surf,(*RUST,fa),(bx,by,bw,bh),1)
            s1=self.f1.render("HURDA MEZARLIGI",True,AMBER);s1.set_alpha(fa);surf.blit(s1,(bx+14,by+8))
            s2=self.f2.render("BOLUM 02  -  SCRAP GRAVEYARD",True,(145,110,68));s2.set_alpha(fa);surf.blit(s2,(bx+14,by+54))
        if t>5.2: a=int(255*min(1.,(t-5.2)/.6));fo=pygame.Surface((self.sw,self.sh));fo.set_alpha(a);fo.fill(BG);surf.blit(fo,(0,0))


class EndScene_L2:
    def __init__(self,sw,sh):
        self.sw=sw;self.sh=sh;self.t=0.;self.done=False;self.fire_t=0.
        try:
            self.f1=pygame.font.SysFont("Courier New",48,bold=True)
            self.f2=pygame.font.SysFont("Courier New",15)
            self.f3=pygame.font.SysFont("Courier New",13)
        except:
            self.f1=pygame.font.Font(None,60);self.f2=pygame.font.Font(None,20);self.f3=pygame.font.Font(None,17)
    def update(self,dt): self.t+=dt;self.fire_t+=dt;self.done=self.t>7.0;return self.done
    def draw(self,surf):
        a=int(255*min(1.,self.t/1.1));fo=pygame.Surface((self.sw,self.sh));fo.set_alpha(a);fo.fill(BG);surf.blit(fo,(0,0))
        if self.t>1.0:
            ba=int(255*min(1.,(self.t-1.0)/1.4))
            pygame.draw.rect(surf,(18,13,8),(0,self.sh//2+40,self.sw,100))
            for i,(bkx,bkh,bkw) in enumerate([(140,90,52),(240,75,44),(345,100,60),(460,82,48),(570,95,55),(680,70,42),(800,88,50)]):
                bs2=pygame.Surface((bkw,bkh),pygame.SRCALPHA);bs2.fill((24,15,8,ba))
                pygame.draw.rect(bs2,(50,30,14,ba),(0,0,bkw,bkh),1)
                if ba>100:
                    wa=int(ba*0.4*(0.6+0.4*math.sin(self.fire_t*2.8+i)))
                    pygame.draw.rect(bs2,(200,140,40,wa),(8,bkh-28,12,10))
                surf.blit(bs2,(bkx,self.sh//2+40-bkh))
            for fi,(fx,fy_off) in enumerate([(185,55),(305,48),(415,62),(530,50),(645,58),(755,45)]):
                flk=0.55+0.45*math.sin(self.fire_t*3.8+fi*1.2);fa2=int(ba*flk)
                gs=pygame.Surface((30,30),pygame.SRCALPHA);pygame.draw.circle(gs,(255,155,30,int(fa2*0.28)),(15,15),13);surf.blit(gs,(fx-15,self.sh//2+40-fy_off-15))
                sc=pygame.Surface((10,10),pygame.SRCALPHA);pygame.draw.circle(sc,(255,205,75,fa2),(5,5),4);surf.blit(sc,(fx-5,self.sh//2+40-fy_off-5))
        if self.t>1.8:
            ta=int(255*min(1.,(self.t-1.8)/.8));s=self.f1.render("UNKNOWN SETTLEMENT",True,(195,150,50));s.set_alpha(ta);surf.blit(s,(self.sw//2-s.get_width()//2,self.sh//2-60))
        if self.t>3.0:
            ta2=int(255*min(1.,(self.t-3.0)/.7));s2=self.f2.render("Hurda barakalar. Ates isiklari. Insan sesleri.",True,(110,85,50));s2.set_alpha(ta2);surf.blit(s2,(self.sw//2-s2.get_width()//2,self.sh//2+22))
        if self.t>4.4:
            ta3=int(255*min(1.,(self.t-4.4)/.6));s3=self.f3.render("Ama oyuncu henuz oraya gitmiyor...",True,(72,58,36));s3.set_alpha(ta3);surf.blit(s3,(self.sw//2-s3.get_width()//2,self.sh//2+50))


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 1 DÖNGÜSÜ
# ══════════════════════════════════════════════════════════════════════════════
def _run_level1(screen, clock, canvas, fhud, fdead, fbig, fmed):
    cam=Cam(); eq=[]
    state="cutscene"
    opening=Opening_L1(SW,SH); endscene=EndScene_L1(SW,SH)
    dead_t=0.; end_done=False; col_rm=False; game_t=0.; hint_t=0.; HINT_DUR=5.0

    FLOOR1=FLOOR1_L1; FLOOR2=FLOOR2_L1

    plats=[
        pygame.Rect(0,    FLOOR1,1500,160),
        pygame.Rect(1300, FLOOR2,1800, 20),
        pygame.Rect(3300, FLOOR1, 900,160),
        pygame.Rect(  40,1120,200,22), pygame.Rect(160,1050,170,22),
        pygame.Rect(  90, 970,160,22), pygame.Rect(270, 908,195,22),
        pygame.Rect( 200, 838,145,22), pygame.Rect(390, 768,185,22),
        pygame.Rect( 310, 692,140,22), pygame.Rect(490, 618,195,22),
        pygame.Rect( 410, 538,165,22), pygame.Rect(590, 458,215,22),
        pygame.Rect( 510, 378,160,22),
        pygame.Rect( 690, 308,240,22),
        pygame.Rect( 970, 400,175,22),
        pygame.Rect(1100, 530,175,22),
        pygame.Rect(1210, 670,160,22),
        pygame.Rect(1660, 750,120,18), pygame.Rect(1840, 700,110,18),
        pygame.Rect(2010, 750,120,18), pygame.Rect(2110, 700,110,18),
        pygame.Rect(2250, 760,120,18), pygame.Rect(2430, 720,120,18),
        pygame.Rect(2580, 760,120,18),
    ]
    colp=ColPlat(3060,FLOOR2-20,240,cam,FLOOR1)
    plats.append(colp.rect)

    enemies=[Grunt(960,290), Grunt(2760,800), Grunt(2900,800)]
    falling_scrap=FallingScrap(2200,2700)
    player=Player(55,FLOOR1-44)
    ZONE_END_X=3950

    while True:
        dt=min(clock.tick(FPS)/1000.,.05)

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                return "quit"
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: return "quit"
                if ev.key==pygame.K_r and state=="dead":
                    return "died"
                if state=="play":
                    if ev.key in(pygame.K_j,pygame.K_z,pygame.K_LCTRL):
                        if player.ac<=0:
                            player.ac=.32
                            hx=player.rect.centerx+player.f*52
                            hr=pygame.Rect(hx-18,player.rect.y,36,player.H)
                            for e in enemies:
                                if e.state!="dead" and hr.colliderect(e.rect): e.hit(cam)
                    if ev.key in(pygame.K_k,pygame.K_x,pygame.K_LSHIFT): player.dash()

        for e2 in eq:
            if e2["t"]=="HIT" and state=="play":
                player.take_hit(cam)
                if not player.alive: state="dead"; dead_t=0.
            elif e2["t"]=="COL" and not col_rm:
                col_rm=True
                if colp.rect in plats: plats.remove(colp.rect)
        eq.clear()

        if state=="cutscene":
            if opening.update(dt):
                state="play"; player.rect.topleft=(55,FLOOR1-44); hint_t=0.
        elif state=="play":
            hint_t+=dt; game_t+=dt
            player.update(dt,plats)
            colp.update(dt,eq)
            falling_scrap.try_activate(player.rect.centerx)
            falling_scrap.update(dt)
            if falling_scrap.check_hit(player.rect): player.take_hit(cam)
            for e in enemies: e.update(dt,player,plats,eq)
            if player.rect.top>WH1+80:
                player.hp=0; player.alive=False; state="dead"; dead_t=0.
            if not colp.fallen and player.rect.colliderect(colp.rect) and player.vy>=0:
                colp.trigger()
            cam.update(dt,player.rect.centerx,player.rect.centery,player.f,WW1,WH1)
            if pygame.Rect(ZONE_END_X,FLOOR1-200,80,400).colliderect(player.rect) and not end_done:
                end_done=True; state="endseq"
        elif state=="endseq":
            game_t+=dt
            if endscene.update(dt): return "completed"
        elif state=="dead":
            dead_t+=dt
            if dead_t>3.: return "died"

        ox=cam.ox; oy=cam.oy

        if state=="cutscene":
            opening.draw(canvas)
        else:
            canvas.fill(BG)
            for r in plats:
                if col_rm and r is colp.rect: continue
                scrap_look=(r.x<1500 and r.h<50)
                draw_plat(canvas,r,ox,oy,scrap=scrap_look)
            colp.draw(canvas,ox,oy)
            draw_tunnel_l1(canvas,ox,oy)
            falling_scrap.draw(canvas,ox,oy)
            for e in enemies: e.draw(canvas,ox,oy)
            if player.alive: player.draw(canvas,ox,oy)
            ex_line=ZONE_END_X-ox
            pygame.draw.line(canvas,CYAN,(ex_line,0),(ex_line,SH),1)
            if state in("endseq","done"): endscene.draw(canvas)
            # Kontrol ipucu
            if state=="play" and hint_t<HINT_DUR:
                alpha=255
                if hint_t>HINT_DUR-1.2: alpha=int(255*(HINT_DUR-hint_t)/1.2)
                bw=680;bh=160;bx2=SW//2-bw//2;by2=SH//2-bh//2
                hs=pygame.Surface((bw,bh),pygame.SRCALPHA)
                hs.fill((0,0,0,int(210*(alpha/255)))); canvas.blit(hs,(bx2,by2))
                pygame.draw.rect(canvas,(*CYAN,alpha),(bx2,by2,bw,bh),2)
                lines=[("A  D  HAREKET   W  ZIPLA",fbig),("J  SALDIRI   /   K  DASH",fmed)]
                for i,(txt,fnt) in enumerate(lines):
                    s=fnt.render(txt,True,CYAN if i==0 else AMBER); s.set_alpha(alpha)
                    canvas.blit(s,(SW//2-s.get_width()//2,by2+14+i*56))
            # HUD
            if state=="play":
                for i in range(player.HP):
                    c=RED if i<player.hp else (30,16,16)
                    pygame.draw.rect(canvas,c,(14+i*22,14,16,8))
                    pygame.draw.rect(canvas,(75,18,18),(14+i*22,14,16,8),1)
            # Ölüm
            if state=="dead":
                fo=pygame.Surface((SW,SH)); fo.set_alpha(min(210,int(dead_t*105))); fo.fill(BG); canvas.blit(fo,(0,0))
                dm=fdead.render("// TERMINATED //",True,RED); canvas.blit(dm,(SW//2-dm.get_width()//2,SH//2-20))
                dm2=fhud.render("R  yeniden basla",True,(115,28,28)); canvas.blit(dm2,(SW//2-dm2.get_width()//2,SH//2+18))

        # Ekrana ölçekle
        pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()


# ══════════════════════════════════════════════════════════════════════════════
# LEVEL 2 DÖNGÜSÜ
# ══════════════════════════════════════════════════════════════════════════════
def _run_level2(screen, clock, canvas, fhud, fdead, fbig, fmed, fsml):
    cam=Cam(); eq=[]
    state="cutscene"
    opening=Opening_L2(SW,SH); endscene=EndScene_L2(SW,SH)
    dead_t=0.; end_done=False; game_t=0.; hint_t=0.; HINT_DUR=5.0

    FLOOR=FLOOR_L2
    ZONE_BOSS_X=3500; ZONE_END_X=4200
    ZONE_HILL_X=2700

    plats=[
        pygame.Rect(0,FLOOR,4600,140),
        pygame.Rect(200,FLOOR-80,140,18),  pygame.Rect(450,FLOOR-60,120,18),
        pygame.Rect(700,FLOOR-90,130,18),  pygame.Rect(950,FLOOR-65,110,18),
        pygame.Rect(1150,FLOOR-80,140,18),
        pygame.Rect(1640,FLOOR-120,110,18),pygame.Rect(1840,FLOOR-85,100,18),
        pygame.Rect(1990,FLOOR-120,110,18),
        pygame.Rect(2780,FLOOR-90,160,18), pygame.Rect(2980,FLOOR-175,150,18),
        pygame.Rect(3160,FLOOR-260,160,18),pygame.Rect(3340,FLOOR-340,150,18),
        pygame.Rect(3500,FLOOR-410,200,22),
        pygame.Rect(3760,FLOOR-290,140,18),pygame.Rect(3920,FLOOR-170,140,18),
        pygame.Rect(4070,FLOOR-80,130,18),
    ]

    enemies=[
        Scavenger(850,FLOOR-42),Scavenger(1050,FLOOR-42),
        Scavenger(1600,FLOOR-42),Scavenger(1980,FLOOR-42),
    ]
    boss=HillGuard(3520,cam)
    boss_dead=False; boss_fight=False
    falling_scrap=FallingScrap(2100,2700)
    player=Player(55,FLOOR-44)

    while True:
        dt=min(clock.tick(FPS)/1000.,.05)

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: return "quit"
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: return "quit"
                if ev.key==pygame.K_r and state=="dead": return "died"
                if state=="play":
                    if ev.key in(pygame.K_j,pygame.K_z,pygame.K_LCTRL):
                        if player.ac<=0:
                            player.ac=.32
                            hx=player.rect.centerx+player.f*52
                            hr=pygame.Rect(hx-18,player.rect.y,36,player.H)
                            for e in enemies:
                                if e.state!="dead" and hr.colliderect(e.rect): e.hit(cam)
                            if not boss_dead and hr.colliderect(boss.rect): boss.hit(cam)
                    if ev.key in(pygame.K_k,pygame.K_x,pygame.K_LSHIFT): player.dash()

        for e2 in eq:
            if e2["t"]=="HIT" and state=="play":
                player.take_hit(cam)
                if not player.alive: state="dead"; dead_t=0.
        eq.clear()

        if state=="cutscene":
            if opening.update(dt):
                state="play"; player.rect.topleft=(55,FLOOR-44); hint_t=0.
        elif state=="play":
            hint_t+=dt; game_t+=dt
            player.update(dt,plats)
            falling_scrap.try_activate(player.rect.centerx)
            falling_scrap.update(dt)
            if falling_scrap.check_hit(player.rect): player.take_hit(cam)
            for e in enemies: e.update(dt,player,plats,eq)
            if not boss_dead:
                if player.rect.x>ZONE_BOSS_X-200 and not boss_fight: boss_fight=True
                boss.update(dt,player,plats,eq)
                if not boss.alive: boss_dead=True; cam.shake(18,1.0)
            if player.rect.top>WH2+80:
                player.hp=0; player.alive=False; state="dead"; dead_t=0.
            cam.update(dt,player.rect.centerx,player.rect.centery,player.f,WW2,WH2)
            if player.rect.x>ZONE_END_X and boss_dead and not end_done:
                end_done=True; state="endseq"
        elif state=="endseq":
            game_t+=dt
            if endscene.update(dt): return "completed"
        elif state=="dead":
            dead_t+=dt
            if dead_t>3.: return "died"

        ox=cam.ox; oy=cam.oy

        if state=="cutscene":
            opening.draw(canvas)
        else:
            canvas.fill((5,7,9))
            for iy2 in range(0,SH,100):
                pygame.draw.line(canvas,(7,10,13),(0,iy2),(SW,iy2),1)
            draw_grave_markers(canvas,ox,oy)
            for r in plats:
                hill_plat=(r.x>=ZONE_HILL_X and r.h<50)
                draw_plat(canvas,r,ox,oy,col=DBROWN if hill_plat else None)
            draw_corridor_l2(canvas,ox,oy)
            falling_scrap.draw(canvas,ox,oy)
            for e in enemies: e.draw(canvas,ox,oy)
            boss.draw(canvas,ox,oy)
            if player.alive: player.draw(canvas,ox,oy)
            draw_settlement_glow(canvas,ox,oy,game_t,boss_dead)
            ex_line=ZONE_END_X-ox
            pygame.draw.line(canvas,AMBER,(ex_line,0),(ex_line,SH),1)
            if state in("endseq","done"): endscene.draw(canvas)
            # Boss ipucu
            if boss_fight and not boss_dead:
                tip=fsml.render("Sarji durdurunca STUN olur - o zaman vur!",True,AMBER)
                canvas.blit(tip,(SW//2-tip.get_width()//2,SH-40))
            # Kontrol ipucu
            if state=="play" and hint_t<HINT_DUR:
                alpha=255
                if hint_t>HINT_DUR-1.2: alpha=int(255*(HINT_DUR-hint_t)/1.2)
                bw=640;bh=120;bx3=SW//2-bw//2;by3=SH//2-bh//2
                hs=pygame.Surface((bw,bh),pygame.SRCALPHA); hs.fill((0,0,0,int(210*(alpha/255)))); canvas.blit(hs,(bx3,by3))
                pygame.draw.rect(canvas,(*RUST,alpha),(bx3,by3,bw,bh),2)
                lines=[("A D HAREKET   W ZIPLA   K DASH",fbig),("J SALDIRI  -  Boss sarj sonrasi STUN'da vur",fmed)]
                for i,(txt,fn) in enumerate(lines):
                    s=fn.render(txt,True,AMBER if i==0 else CYAN); s.set_alpha(alpha)
                    canvas.blit(s,(SW//2-s.get_width()//2,by3+12+i*50))
            # HUD
            if state=="play":
                for i in range(player.HP):
                    c=RED if i<player.hp else (30,16,16)
                    pygame.draw.rect(canvas,c,(14+i*22,14,16,8))
                    pygame.draw.rect(canvas,(75,18,18),(14+i*22,14,16,8),1)
                if boss_fight and not boss_dead:
                    bw2=200; pygame.draw.rect(canvas,(42,10,10),(SW//2-bw2//2,SH-28,bw2,10))
                    pygame.draw.rect(canvas,RED,(SW//2-bw2//2,SH-28,int(bw2*max(0.,boss.hp/boss.HP_MAX)),10))
                    pygame.draw.rect(canvas,RUST,(SW//2-bw2//2,SH-28,bw2,10),1)
                    lb=fhud.render("TEPE BEKCISI",True,LRUST); canvas.blit(lb,(SW//2-lb.get_width()//2,SH-44))
            # Ölüm
            if state=="dead":
                fo=pygame.Surface((SW,SH)); fo.set_alpha(min(210,int(dead_t*105))); fo.fill((5,7,9)); canvas.blit(fo,(0,0))
                dm=fdead.render("// TERMINATED //",True,RED); canvas.blit(dm,(SW//2-dm.get_width()//2,SH//2-20))
                dm2=fhud.render("R  yeniden basla",True,(115,28,28)); canvas.blit(dm2,(SW//2-dm2.get_width()//2,SH//2+18))

        pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()


# ══════════════════════════════════════════════════════════════════════════════
# ANA ÇALIŞTIRICISI
# ══════════════════════════════════════════════════════════════════════════════
def run(level_num: int, screen: pygame.Surface,
        clock: pygame.time.Clock, save_manager=None) -> str:
    """
    Bölüm 1 veya 2'yi çalıştırır. Ana oyun ekranını geçici olarak devralır.
    Döndürür: 'completed' | 'died' | 'quit'
    """
    # 1280x720 iç tuval — ana ekrana ölçeklenir
    canvas = pygame.Surface((SW, SH))
    fhud, fdead, fbig, fmed, fsml = _load_fonts()

    if level_num == 1:
        return _run_level1(screen, clock, canvas, fhud, fdead, fbig, fmed)
    elif level_num == 2:
        return _run_level2(screen, clock, canvas, fhud, fdead, fbig, fmed, fsml)
    return "quit"