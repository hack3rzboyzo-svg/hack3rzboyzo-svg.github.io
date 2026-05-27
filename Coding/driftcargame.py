"""
Drift Race - Championship Edition (Python / pygame port)

Run:
    pip install pygame
    python drift_race.py

Controls:
    P1: WASD  (Space = drift brake, Left-Shift = chase cam in single player)
    P2: Arrow keys  (Right-Shift = drift brake) -- local multiplayer mode
    ESC: back to menu
"""

import math
import sys
import json
import pygame
from copy import deepcopy

# ---------------- Config ----------------

SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

CARS = [
    dict(id="blaze", name="Blaze",  color=(255,107,26),  accel=0.95, top=8.5, handling=0.95),
    dict(id="apex",  name="Apex",   color=(0,212,255),   accel=0.85, top=9.2, handling=0.88),
    dict(id="fury",  name="Fury",   color=(255,46,99),   accel=1.00, top=8.0, handling=1.00),
    dict(id="viper", name="Viper",  color=(0,255,136),   accel=0.88, top=8.8, handling=0.92),
    dict(id="ghost", name="Ghost",  color=(168,85,247),  accel=0.82, top=9.5, handling=0.86),
    dict(id="storm", name="Storm",  color=(251,191,36),  accel=0.92, top=8.6, handling=0.94),
]

# ---------------- Tracks (Catmull-Rom) ----------------

def catmull_rom(p0, p1, p2, p3, t):
    t2, t3 = t*t, t*t*t
    return (
        0.5*((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
        0.5*((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3),
    )

def build_centerline(controls, samples=512):
    n = len(controls)
    out = []
    seg = samples // n
    for i in range(n):
        p0, p1, p2, p3 = controls[(i-1)%n], controls[i], controls[(i+1)%n], controls[(i+2)%n]
        for j in range(seg):
            out.append(catmull_rom(p0, p1, p2, p3, j/seg))
    return out

def build_walls(center, halfw):
    outer, inner = [], []
    n = len(center)
    for i in range(n):
        a, b = center[i], center[(i+1)%n]
        nx, ny = -(b[1]-a[1]), (b[0]-a[0])
        L = math.hypot(nx, ny) or 1.0
        nx, ny = nx/L, ny/L
        outer.append((a[0]+nx*halfw, a[1]+ny*halfw))
        inner.append((a[0]-nx*halfw, a[1]-ny*halfw))
    return outer, inner

TRACKS = {
    "oval": dict(
        id="oval", name="Classic Oval", desc="Wide sweeping turns, high speed",
        width=2400, height=1500, isEllipse=True, halfWidth=130,
        cx=1200, cy=750, rx=900, ry=500, pads=[],
    ),
    "kart": dict(
        id="kart", name="Kart Circuit", desc="Tight hairpin & chicane", boost=True,
        width=2400, height=1600, halfWidth=110,
        controls=[
            (400,800),(400,400),(800,250),(1300,300),(1700,200),(2050,450),
            (2050,900),(1800,1100),(1500,950),(1300,1150),(1500,1350),(1100,1400),
            (700,1300),(400,1100)
        ],
        pads=[dict(t=0.10), dict(t=0.55)],
    ),
    "mountain": dict(
        id="mountain", name="Mountain Pass", desc="Smooth serpentine S-curves",
        width=2600, height=1400, halfWidth=120,
        controls=[
            (350,700),(600,400),(1000,500),(1300,300),(1700,400),(2050,250),
            (2300,500),(2300,900),(2000,1100),(1600,1000),(1200,1200),(800,1100),(450,1000)
        ],
        pads=[],
    ),
    "hairpin": dict(
        id="hairpin", name="Hairpin Circuit", desc="Three brutal hairpins + jumps", boost=True,
        width=2400, height=1500, halfWidth=105,
        controls=[
            (400,750),(400,300),(800,250),(800,650),(1200,650),(1200,250),
            (1700,250),(1700,750),(2050,750),(2050,1200),(1600,1250),(1600,950),
            (1100,950),(1100,1250),(700,1250),(400,1150)
        ],
        pads=[dict(t=0.05), dict(t=0.40), dict(t=0.75)],
    ),
}

_track_cache = {}
def get_track(tid):
    if tid in _track_cache:
        return _track_cache[tid]
    t = deepcopy(TRACKS[tid])
    if not t.get("isEllipse"):
        t["center"] = build_centerline(t["controls"], 512)
        outer, inner = build_walls(t["center"], t["halfWidth"])
        t["outer"], t["inner"] = outer, inner
        s, n = t["center"][0], t["center"][1]
        dx, dy = n[0]-s[0], n[1]-s[1]
        L = math.hypot(dx,dy) or 1
        fx, fy = dx/L, dy/L
        px, py = -fy, fx
        ang = math.atan2(fx, -fy)
        t["startPositions"] = [
            (s[0]-px*30, s[1]-py*30, ang),
            (s[0]+px*30, s[1]+py*30, ang),
            (s[0]-px*30+fx*60, s[1]-py*30+fy*60, ang),
            (s[0]+px*30+fx*60, s[1]+py*30+fy*60, ang),
        ]
        t["jumpPads"] = []
        for p in t.get("pads", []):
            idx = int(p["t"] * len(t["center"]))
            a, b = t["center"][idx], t["center"][(idx+1)%len(t["center"])]
            ddx, ddy = b[0]-a[0], b[1]-a[1]
            DL = math.hypot(ddx,ddy) or 1
            t["jumpPads"].append(dict(x=a[0], y=a[1], dx=ddx/DL, dy=ddy/DL, r=t["halfWidth"]*0.55))
    else:
        t["startPositions"] = [
            (t["cx"]-30, t["cy"]+t["ry"], math.pi/2),
            (t["cx"]+30, t["cy"]+t["ry"], math.pi/2),
            (t["cx"]-30, t["cy"]+t["ry"]-60, math.pi/2),
            (t["cx"]+30, t["cy"]+t["ry"]-60, math.pi/2),
        ]
        t["jumpPads"] = []
    _track_cache[tid] = t
    return t

def nearest_cl(track, x, y, hint=-1):
    c = track["center"]
    N = len(c)
    best, bd = 0, float("inf")
    if hint >= 0:
        for k in range(-8, 9):
            i = (hint + k) % N
            dx, dy = c[i][0]-x, c[i][1]-y
            d = dx*dx + dy*dy
            if d < bd:
                bd = d; best = i
        if bd < (track["halfWidth"]*1.4)**2:
            return best
    for i in range(N):
        dx, dy = c[i][0]-x, c[i][1]-y
        d = dx*dx + dy*dy
        if d < bd:
            bd = d; best = i
    return best

# ---------------- Car / Physics ----------------

ACCEL_SCALE = 0.18
FRICTION = 0.985
DRIFT_FRICTION = 0.97
TURN_RATE = 0.045

class Car:
    def __init__(self, label, spec, is_ai, start, controls=None):
        self.label = label
        self.spec = spec
        self.is_ai = is_ai
        self.controls = controls
        self.x, self.y, self.angle = start
        self.vx = self.vy = 0.0
        self.speed = 0.0
        self.drifting = False
        self.is_airborne = False
        self.airborne_timer = 0.0
        self.lap = 0
        self.total_time = 0.0
        self.best_lap = float("inf")
        self.lap_start = 0.0
        self.crossed_half = False
        self.finished = False
        self.finish_time = 0.0
        self.cl_hint = 0
        self.last_pad = -1

def steer_toward(car, tx, ty):
    dx, dy = tx-car.x, ty-car.y
    desired = math.atan2(dx, -dy)
    diff = desired - car.angle
    while diff > math.pi: diff -= 2*math.pi
    while diff < -math.pi: diff += 2*math.pi
    return dict(
        up=True, down=False,
        left=diff < -0.05, right=diff > 0.05,
        brake=abs(diff) > 0.5 and car.speed > 6,
    )

def ai_input(car, track):
    if track.get("isEllipse"):
        ang = math.atan2(car.x-track["cx"], -(car.y-track["cy"]))
        look = ang + 0.18
        tx = track["cx"] + math.sin(look) * track["rx"]
        ty = track["cy"] - math.cos(look) * track["ry"]
        return steer_toward(car, tx, ty)
    idx = nearest_cl(track, car.x, car.y, car.cl_hint)
    car.cl_hint = idx
    ahead = track["center"][(idx+14) % len(track["center"])]
    return steer_toward(car, ahead[0], ahead[1])

def step(car, dt, track, sens, all_cars, total_laps, on_boost=None):
    if car.finished:
        return
    car.total_time += dt
    inp = ai_input(car, track) if car.is_ai else car.controls
    accel = (1 if inp["up"] else 0) - (1 if inp["down"] else 0)
    steer = (1 if inp["right"] else 0) - (1 if inp["left"] else 0)
    speed = math.hypot(car.vx, car.vy)
    turnK = TURN_RATE * sens * car.spec["handling"] * (0.4 + min(1, speed/6)*0.6)
    car.angle += steer * turnK

    sa, ca = math.sin(car.angle), math.cos(car.angle)
    fx, fy = sa, -ca
    a = accel * car.spec["accel"] * ACCEL_SCALE
    car.vx += fx * a
    car.vy += fy * a

    car.drifting = bool(inp["brake"])
    f = DRIFT_FRICTION if car.drifting else FRICTION
    lat_x, lat_y = -ca, -sa
    lat_v = car.vx*lat_x + car.vy*lat_y
    grip = 0.12 if car.drifting else 0.55
    car.vx -= lat_x * lat_v * grip
    car.vy -= lat_y * lat_v * grip
    car.vx *= f; car.vy *= f

    cap = car.spec["top"] * (1.5 if car.is_airborne else 1.0)
    cur = math.hypot(car.vx, car.vy)
    if cur > cap:
        car.vx = car.vx/cur*cap
        car.vy = car.vy/cur*cap
    car.speed = cur

    car.x += car.vx
    car.y += car.vy

    if car.is_airborne:
        car.airborne_timer -= dt
        if car.airborne_timer <= 0:
            car.is_airborne = False

    # jump pads
    pads = track.get("jumpPads", [])
    for i, p in enumerate(pads):
        dx, dy = car.x - p["x"], car.y - p["y"]
        if dx*dx + dy*dy < p["r"]**2 and car.last_pad != i:
            car.is_airborne = True
            car.airborne_timer = 0.9
            boost = car.spec["top"] * 1.3
            car.vx = p["dx"] * boost
            car.vy = p["dy"] * boost
            car.last_pad = i
            if not car.is_ai and on_boost:
                on_boost()
    near = False
    for p in pads:
        dx, dy = car.x-p["x"], car.y-p["y"]
        if dx*dx+dy*dy < (p["r"]*1.5)**2:
            near = True; break
    if not near:
        car.last_pad = -1

    # walls
    if track.get("isEllipse"):
        rx, ry, hw = track["rx"], track["ry"], track["halfWidth"]
        ex_o = ((car.x-track["cx"])/(rx+hw))**2 + ((car.y-track["cy"])/(ry+hw))**2
        if ex_o > 1:
            nx = (car.x-track["cx"])/rx
            ny = (car.y-track["cy"])/ry
            nl = math.hypot(nx,ny) or 1
            ux, uy = nx/nl, ny/nl
            car.x -= ux*3; car.y -= uy*3
            dot = car.vx*ux + car.vy*uy
            car.vx -= 1.6*dot*ux; car.vy -= 1.6*dot*uy
            car.vx *= 0.7; car.vy *= 0.7
        ex_i = ((car.x-track["cx"])/(rx-hw))**2 + ((car.y-track["cy"])/(ry-hw))**2
        if ex_i < 1:
            nx = -(car.x-track["cx"])/rx
            ny = -(car.y-track["cy"])/ry
            nl = math.hypot(nx,ny) or 1
            ux, uy = nx/nl, ny/nl
            car.x -= ux*3; car.y -= uy*3
            dot = car.vx*ux + car.vy*uy
            car.vx -= 1.6*dot*ux; car.vy -= 1.6*dot*uy
            car.vx *= 0.7; car.vy *= 0.7
    else:
        idx = nearest_cl(track, car.x, car.y, car.cl_hint)
        car.cl_hint = idx
        c = track["center"][idx]
        dx, dy = car.x-c[0], car.y-c[1]
        d = math.hypot(dx, dy)
        limit = track["halfWidth"] * 0.92
        if d > limit:
            ux, uy = dx/d, dy/d
            car.x = c[0] + ux*limit
            car.y = c[1] + uy*limit
            dot = car.vx*ux + car.vy*uy
            car.vx -= 1.7*dot*ux; car.vy -= 1.7*dot*uy
            car.vx *= 0.65; car.vy *= 0.65

    # car-car collisions
    for o in all_cars:
        if o is car: continue
        dx, dy = car.x-o.x, car.y-o.y
        d = math.hypot(dx, dy)
        if 0 < d < 38:
            ux, uy = dx/d, dy/d
            ov = (38-d)*0.5
            car.x += ux*ov; car.y += uy*ov
            o.x -= ux*ov;  o.y -= uy*ov
            rel = (car.vx-o.vx)*ux + (car.vy-o.vy)*uy
            if rel < 0:
                j = -rel * 0.9
                car.vx += ux*j*0.5; car.vy += uy*j*0.5
                o.vx -= ux*j*0.5;   o.vy -= uy*j*0.5

    # lap detection
    if track.get("isEllipse"):
        sx, sy = track["cx"], track["cy"]+track["ry"]
        top_y = track["cy"] - track["ry"]
        if math.hypot(car.x-track["cx"], car.y-top_y) < track["ry"]:
            car.crossed_half = True
    else:
        s = track["center"][0]
        sx, sy = s[0], s[1]
        half = track["center"][len(track["center"])//2]
        if math.hypot(car.x-half[0], car.y-half[1]) < track["halfWidth"]*2:
            car.crossed_half = True
    if car.crossed_half:
        if math.hypot(car.x-sx, car.y-sy) < track["halfWidth"]*1.4:
            lap_t = car.total_time - car.lap_start
            if lap_t > 1.0:
                car.lap += 1
                car.best_lap = min(car.best_lap, lap_t)
                car.lap_start = car.total_time
                car.crossed_half = False
                if car.lap >= total_laps:
                    car.finished = True
                    car.finish_time = car.total_time

# ---------------- Rendering ----------------

GRASS = (22, 41, 26)
ROAD = (42, 42, 50)
RUMBLE_R = (210, 30, 30)
RUMBLE_Y = (220, 220, 30)
WHITE = (255,255,255)
BLACK = (10,10,10)
PAD = (0, 255, 140)

def draw_dashed_polyline(surf, color, points, width=4, dash=20, gap=20, closed=True):
    pts = list(points)
    if closed: pts.append(pts[0])
    pen = 0  # 0 = drawing dash, 1 = gap
    rem = dash
    for i in range(len(pts)-1):
        x1, y1 = pts[i]; x2, y2 = pts[i+1]
        seg_len = math.hypot(x2-x1, y2-y1)
        if seg_len == 0: continue
        dx, dy = (x2-x1)/seg_len, (y2-y1)/seg_len
        cur = 0
        while cur < seg_len:
            take = min(rem, seg_len-cur)
            sx, sy = x1+dx*cur, y1+dy*cur
            ex, ey = x1+dx*(cur+take), y1+dy*(cur+take)
            if pen == 0:
                pygame.draw.line(surf, color, (sx, sy), (ex, ey), width)
            cur += take
            rem -= take
            if rem <= 0:
                pen ^= 1
                rem = dash if pen == 0 else gap

def draw_track_to_surface(track):
    """Render the entire track to an offscreen surface (cached)."""
    surf = pygame.Surface((track["width"], track["height"])).convert()
    surf.fill(GRASS)
    if track.get("isEllipse"):
        cx_, cy_ = track["cx"], track["cy"]
        rx, ry, hw = track["rx"], track["ry"], track["halfWidth"]
        # outer ellipse fill
        pygame.draw.ellipse(surf, ROAD, (cx_-rx-hw, cy_-ry-hw, 2*(rx+hw), 2*(ry+hw)))
        # cut grass hole
        pygame.draw.ellipse(surf, GRASS, (cx_-rx+hw, cy_-ry+hw, 2*(rx-hw), 2*(ry-hw)))
        # rumble strips approximated by dashed ellipse outlines
        # outer red
        for i in range(0, 360, 30):
            a0 = math.radians(i); a1 = math.radians(i+15)
            x0 = cx_ + math.cos(a0)*(rx+hw); y0 = cy_ + math.sin(a0)*(ry+hw)
            x1 = cx_ + math.cos(a1)*(rx+hw); y1 = cy_ + math.sin(a1)*(ry+hw)
            pygame.draw.line(surf, RUMBLE_R, (x0,y0),(x1,y1), 8)
        for i in range(15, 360, 30):
            a0 = math.radians(i); a1 = math.radians(i+15)
            x0 = cx_ + math.cos(a0)*(rx-hw); y0 = cy_ + math.sin(a0)*(ry-hw)
            x1 = cx_ + math.cos(a1)*(rx-hw); y1 = cy_ + math.sin(a1)*(ry-hw)
            pygame.draw.line(surf, RUMBLE_Y, (x0,y0),(x1,y1), 8)
        # start line checkers
        sx, sy = cx_, cy_+ry
        rect = pygame.Rect(sx-30, sy-hw, 60, 2*hw)
        draw_checkers(surf, rect)
    else:
        # build road polygon (outer minus inner)
        outer = track["outer"]; inner = track["inner"]
        pygame.draw.polygon(surf, ROAD, outer)
        pygame.draw.polygon(surf, GRASS, inner)
        # rumble strips
        draw_dashed_polyline(surf, RUMBLE_R, outer, width=6, dash=20, gap=20)
        draw_dashed_polyline(surf, RUMBLE_Y, inner, width=6, dash=20, gap=20)
        # center dashes
        draw_dashed_polyline(surf, (255,255,255), track["center"], width=3, dash=18, gap=18)
        # start/finish checkers, rotated
        s, n = track["center"][0], track["center"][1]
        ang = math.atan2(n[1]-s[1], n[0]-s[0])
        hw = track["halfWidth"]
        # build a small checker surface and rotate
        checker = pygame.Surface((40, hw*2), pygame.SRCALPHA)
        draw_checkers(checker, pygame.Rect(0, 0, 40, hw*2))
        rot = pygame.transform.rotate(checker, -math.degrees(ang))
        rect = rot.get_rect(center=(s[0], s[1]))
        surf.blit(rot, rect)
    return surf

def draw_checkers(surf, rect, cols=4, rows=12):
    cw, ch = rect.width / cols, rect.height / rows
    for r in range(rows):
        for c in range(cols):
            color = WHITE if (r+c) % 2 == 0 else BLACK
            pygame.draw.rect(surf, color, (rect.x+c*cw, rect.y+r*ch, math.ceil(cw), math.ceil(ch)))

def draw_jump_pads(surf, track, t, world_to_screen):
    pads = track.get("jumpPads", [])
    if not pads: return
    pulse = 0.5 + 0.5 * math.sin(t*5)
    for p in pads:
        sx, sy = world_to_screen(p["x"], p["y"])
        r = int(p["r"] * world_to_screen.scale)
        # rotated rect with chevrons
        ang = math.atan2(p["dx"], -p["dy"])
        pad_surf = pygame.Surface((int(r*1.4), int(r)), pygame.SRCALPHA)
        alpha = int(80 + 100*pulse)
        pygame.draw.rect(pad_surf, (0, 255, 140, alpha), pad_surf.get_rect())
        pygame.draw.rect(pad_surf, PAD, pad_surf.get_rect(), 3)
        for i in (-1, 0, 1):
            yy = pad_surf.get_height()//2 + i*15
            pygame.draw.line(pad_surf, WHITE, (pad_surf.get_width()*0.2, yy+8),
                             (pad_surf.get_width()*0.5, yy-8), 4)
            pygame.draw.line(pad_surf, WHITE, (pad_surf.get_width()*0.5, yy-8),
                             (pad_surf.get_width()*0.8, yy+8), 4)
        rot = pygame.transform.rotate(pad_surf, -math.degrees(ang)+90)
        rect = rot.get_rect(center=(sx, sy))
        surf.blit(rot, rect)

def draw_car(surf, car, world_to_screen):
    sx, sy = world_to_screen(car.x, car.y)
    s = world_to_screen.scale
    body_w, body_h = int(28*s), int(44*s)
    car_surf = pygame.Surface((body_w+8, body_h+8), pygame.SRCALPHA)
    if car.is_airborne:
        pygame.draw.rect(car_surf, (0,0,0,120),
                         (4, 4+8, body_w, body_h))
    pygame.draw.rect(car_surf, car.spec["color"], (4, 4, body_w, body_h))
    pygame.draw.rect(car_surf, (240,240,255), (4+int(4*s), 4+int(6*s), body_w-int(8*s), int(16*s)))
    pygame.draw.rect(car_surf, (30,30,30), (4, 4, body_w, int(4*s)))
    pygame.draw.rect(car_surf, (30,30,30), (4, 4+body_h-int(4*s), body_w, int(4*s)))
    rot = pygame.transform.rotate(car_surf, -math.degrees(car.angle))
    rect = rot.get_rect(center=(sx, sy))
    surf.blit(rot, rect)

# ---------------- Camera helper ----------------
class Camera:
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.scale = 1.0
        self.cx = 0
        self.cy = 0
        self.rot = 0.0  # chase cam rotation

    def set(self, target_x, target_y, scale, rot=0.0):
        self.cx = target_x; self.cy = target_y
        self.scale = scale
        self.rot = rot

    def __call__(self, x, y):
        # translate
        dx, dy = x - self.cx, y - self.cy
        if self.rot != 0.0:
            c = math.cos(self.rot); s = math.sin(self.rot)
            dx, dy = dx*c - dy*s, dx*s + dy*c
        return (dx*self.scale + self.sw/2, dy*self.scale + self.sh/2)

# ---------------- HUD ----------------

def draw_minimap(screen, track, cars, x, y, w, h):
    pygame.draw.rect(screen, (10,14,26), (x, y, w, h))
    pygame.draw.rect(screen, (0,200,255), (x, y, w, h), 1)
    sx, sy = w/track["width"], h/track["height"]
    if track.get("isEllipse"):
        pygame.draw.ellipse(screen, (0,200,255),
                            (x+(track["cx"]-track["rx"])*sx, y+(track["cy"]-track["ry"])*sy,
                             2*track["rx"]*sx, 2*track["ry"]*sy), 2)
        pygame.draw.ellipse(screen, (0,200,255),
                            (x+(track["cx"]-track["rx"]+track["halfWidth"])*sx,
                             y+(track["cy"]-track["ry"]+track["halfWidth"])*sy,
                             2*(track["rx"]-track["halfWidth"])*sx,
                             2*(track["ry"]-track["halfWidth"])*sy), 2)
    else:
        pts = [(x+p[0]*sx, y+p[1]*sy) for p in track["center"][::4]]
        pygame.draw.polygon(screen, (0,200,255), pts, 2)
    for p in track.get("jumpPads", []):
        pygame.draw.circle(screen, PAD, (int(x+p["x"]*sx), int(y+p["y"]*sy)), 2)
    for c in cars:
        pygame.draw.circle(screen, c.spec["color"],
                           (int(x+c.x*sx), int(y+c.y*sy)), 3 if not c.is_ai else 2)

def fmt_time(t):
    if t == float("inf"): return "—"
    m = int(t//60)
    s = t - m*60
    return f"{m}:{s:05.2f}"

# ---------------- Menu ----------------

class GameState:
    def __init__(self):
        self.mode = "single"
        self.car_pick = "blaze"
        self.car_pick2 = "apex"
        self.track_pick = "oval"
        self.total_laps = 3
        self.sensitivity = 1.0
        self.scene = "menu"  # menu / play / results
        self.cars = []
        self.track = None
        self.results = []
        self.boost_flash_until = 0
        self.chase_cam = False

def menu_loop(screen, font, big, small, gs):
    """Returns when user clicks START or quits."""
    clock = pygame.time.Clock()
    cars = CARS
    tracks = list(TRACKS.values())
    while True:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit(0)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # mode buttons
                if 200 <= my <= 240:
                    if 200 <= mx <= 590: gs.mode = "single"
                    elif 600 <= mx <= 990: gs.mode = "multi"
                # car row P1
                for i, c in enumerate(cars):
                    cx_ = 200 + i*90
                    if cx_ <= mx <= cx_+76 and 290 <= my <= 380:
                        gs.car_pick = c["id"]
                # car row P2
                if gs.mode == "multi":
                    for i, c in enumerate(cars):
                        cx_ = 200 + i*90
                        if cx_ <= mx <= cx_+76 and 410 <= my <= 500:
                            gs.car_pick2 = c["id"]
                # laps
                base_y = 540 if gs.mode == "multi" else 420
                for i, n in enumerate([1,3,5]):
                    bx = 270 + i*60
                    if bx <= mx <= bx+50 and base_y <= my <= base_y+34:
                        gs.total_laps = n
                # sensitivity slider
                sl_x, sl_y, sl_w = 540, base_y+10, 320
                if sl_x <= mx <= sl_x+sl_w and sl_y-8 <= my <= sl_y+18:
                    gs.sensitivity = 0.5 + (mx-sl_x)/sl_w * 1.5
                    gs.sensitivity = max(0.5, min(2.0, gs.sensitivity))
                # tracks
                track_y = base_y + 80
                for i, t in enumerate(tracks):
                    col = i % 2; row = i // 2
                    tx_ = 200 + col*400; ty_ = track_y + row*70
                    if tx_ <= mx <= tx_+380 and ty_ <= my <= ty_+60:
                        gs.track_pick = t["id"]
                # start button
                start_y = track_y + 170
                if 200 <= mx <= 990 and start_y <= my <= start_y+60:
                    return

        screen.fill((10, 14, 26))
        # title
        title = big.render("DRIFT RACE", True, (255, 140, 0))
        screen.blit(title, title.get_rect(center=(SCREEN_W//2, 90)))
        sub = small.render("CHAMPIONSHIP EDITION", True, (0, 200, 255))
        screen.blit(sub, sub.get_rect(center=(SCREEN_W//2, 130)))
        # mode buttons
        for i, (mid, label) in enumerate([("single","SINGLE PLAYER"), ("multi","LOCAL MULTIPLAYER")]):
            x_ = 200 + i*400
            active = gs.mode == mid
            color = (255,140,0) if active else (40,50,70)
            pygame.draw.rect(screen, color, (x_, 200, 390, 40), border_radius=8)
            t = font.render(label, True, (20,20,20) if active else (220,220,220))
            screen.blit(t, t.get_rect(center=(x_+195, 220)))
        # P1 cars
        screen.blit(small.render("YOUR CAR", True, (140,160,180)), (200, 270))
        for i, c in enumerate(cars):
            x_ = 200 + i*90
            sel = c["id"] == gs.car_pick
            pygame.draw.rect(screen, c["color"], (x_+22, 295, 32, 44), border_radius=4)
            label = small.render(c["name"], True, c["color"] if sel else (180,180,180))
            screen.blit(label, label.get_rect(center=(x_+38, 358)))
            if sel:
                pygame.draw.rect(screen, (255,140,0), (x_, 290, 76, 80), 2, border_radius=6)
        # P2 cars
        next_y = 420
        if gs.mode == "multi":
            screen.blit(small.render("PLAYER 2 CAR", True, (140,160,180)), (200, 390))
            for i, c in enumerate(cars):
                x_ = 200 + i*90
                sel = c["id"] == gs.car_pick2
                pygame.draw.rect(screen, c["color"], (x_+22, 415, 32, 44), border_radius=4)
                label = small.render(c["name"], True, c["color"] if sel else (180,180,180))
                screen.blit(label, label.get_rect(center=(x_+38, 478)))
                if sel:
                    pygame.draw.rect(screen, (255,140,0), (x_, 410, 76, 80), 2, border_radius=6)
            next_y = 540
        # laps + sensitivity
        screen.blit(small.render("LAPS", True, (140,160,180)), (270, next_y-22))
        for i, n in enumerate([1,3,5]):
            bx = 270 + i*60
            sel = gs.total_laps == n
            color = (255,140,0) if sel else (40,50,70)
            pygame.draw.rect(screen, color, (bx, next_y, 50, 34), border_radius=6)
            t = font.render(str(n), True, (20,20,20) if sel else (220,220,220))
            screen.blit(t, t.get_rect(center=(bx+25, next_y+17)))
        screen.blit(small.render(f"STEERING SENSITIVITY: {gs.sensitivity:.2f}x",
                    True, (140,160,180)), (540, next_y-22))
        sl_x, sl_y, sl_w = 540, next_y+10, 320
        pygame.draw.rect(screen, (40,50,70), (sl_x, sl_y, sl_w, 6), border_radius=3)
        knob_x = sl_x + (gs.sensitivity-0.5)/1.5 * sl_w
        pygame.draw.circle(screen, (255,140,0), (int(knob_x), sl_y+3), 8)
        # tracks
        screen.blit(small.render("TRACK", True, (140,160,180)), (200, next_y+70))
        track_y = next_y+90
        for i, t in enumerate(tracks):
            col = i % 2; row = i // 2
            tx_ = 200 + col*400; ty_ = track_y + row*70
            sel = t["id"] == gs.track_pick
            color = (255,140,0) if sel else (40,50,70)
            pygame.draw.rect(screen, color, (tx_, ty_, 380, 60), 2 if not sel else 0, border_radius=8)
            tn = font.render(t["name"], True, (20,20,20) if sel else (220,220,220))
            screen.blit(tn, (tx_+12, ty_+6))
            if t.get("boost"):
                tag = small.render("BOOST", True, (0,255,140))
                screen.blit(tag, (tx_+12+tn.get_width()+10, ty_+12))
            td = small.render(t["desc"], True, (40,40,40) if sel else (140,160,180))
            screen.blit(td, (tx_+12, ty_+34))
        # start button
        start_y = track_y + 170
        pygame.draw.rect(screen, (255,140,0), (200, start_y, 790, 60), border_radius=10)
        t = big.render("START RACE", True, (20,20,20))
        screen.blit(t, t.get_rect(center=(595, start_y+30)))

        pygame.display.flip()
        clock.tick(FPS)

def play_loop(screen, font, big, small, gs):
    track = get_track(gs.track_pick)
    gs.track = track
    p1_spec = next(c for c in CARS if c["id"] == gs.car_pick)
    cars = []
    p1 = Car("P1", p1_spec, False, track["startPositions"][0],
             dict(up=False, down=False, left=False, right=False, brake=False))
    cars.append(p1)
    if gs.mode == "multi":
        p2_spec = next(c for c in CARS if c["id"] == gs.car_pick2)
        p2 = Car("P2", p2_spec, False, track["startPositions"][1],
                 dict(up=False, down=False, left=False, right=False, brake=False))
        cars.append(p2)
    else:
        ais = [c for c in CARS if c["id"] != gs.car_pick][:2]
        for i, spec in enumerate(ais):
            cars.append(Car(f"AI{i+1}", spec, True, track["startPositions"][i+1]))
    gs.cars = cars

    track_surf = draw_track_to_surface(track)
    cam = Camera(SCREEN_W, SCREEN_H)
    clock = pygame.time.Clock()
    boost_flash_until = 0
    countdown = 3.0  # 3-second countdown
    countdown_active = True
    elapsed = 0.0
    finish_grace = None

    def trigger_flash():
        nonlocal boost_flash_until
        boost_flash_until = pygame.time.get_ticks() + 600

    while True:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                gs.scene = "menu"; return

        keys = pygame.key.get_pressed()
        # P1 inputs (also forward arrows in single)
        p1.controls["up"]    = keys[pygame.K_w] or (gs.mode=="single" and keys[pygame.K_UP])
        p1.controls["down"]  = keys[pygame.K_s] or (gs.mode=="single" and keys[pygame.K_DOWN])
        p1.controls["left"]  = keys[pygame.K_a] or (gs.mode=="single" and keys[pygame.K_LEFT])
        p1.controls["right"] = keys[pygame.K_d] or (gs.mode=="single" and keys[pygame.K_RIGHT])
        p1.controls["brake"] = keys[pygame.K_SPACE]
        gs.chase_cam = keys[pygame.K_LSHIFT]
        if gs.mode == "multi":
            p2.controls["up"]    = keys[pygame.K_UP]
            p2.controls["down"]  = keys[pygame.K_DOWN]
            p2.controls["left"]  = keys[pygame.K_LEFT]
            p2.controls["right"] = keys[pygame.K_RIGHT]
            p2.controls["brake"] = keys[pygame.K_RSHIFT]

        if countdown_active:
            countdown -= dt
            if countdown <= 0:
                countdown_active = False
        else:
            for c in cars:
                step(c, dt, track, gs.sensitivity, cars, gs.total_laps,
                     on_boost=trigger_flash if c is p1 else None)

        # render
        screen.fill((10,14,26))
        scale = min(SCREEN_W/1300, SCREEN_H/750)
        rot = -p1.angle if (gs.chase_cam and gs.mode == "single") else 0.0
        cam.set(p1.x, p1.y, scale, rot)
        # draw track via blit-rotate-scale: easier to blit scaled, no rotation, for perf
        if rot == 0.0:
            tw = int(track["width"]*scale); th = int(track["height"]*scale)
            scaled = pygame.transform.scale(track_surf, (tw, th))
            ox = SCREEN_W/2 - p1.x*scale
            oy = SCREEN_H/2 - p1.y*scale
            screen.blit(scaled, (ox, oy))
        else:
            # rotated cam: scale then rotate around p1
            tw = int(track["width"]*scale); th = int(track["height"]*scale)
            scaled = pygame.transform.scale(track_surf, (tw, th))
            rotated = pygame.transform.rotate(scaled, math.degrees(rot))
            # center the rotated image so that p1's screen position is the rotation center
            # rotation rotates around the surface's center, so adjust by computing where (p1*scale) ended up
            px = p1.x*scale - tw/2
            py = p1.y*scale - th/2
            cosr = math.cos(rot); sinr = math.sin(rot)
            rx = px*cosr - py*sinr
            ry = px*sinr + py*cosr
            new_center = (SCREEN_W/2 - rx, SCREEN_H/2 - ry)
            screen.blit(rotated, rotated.get_rect(center=new_center))

        cam.scale = scale
        draw_jump_pads(screen, track, elapsed, cam)
        for c in cars:
            draw_car(screen, c, cam)

        # HUD
        lap_text = f"LAP {min(p1.lap+1, gs.total_laps)}/{gs.total_laps}  ·  {fmt_time(p1.total_time)}"
        screen.blit(font.render(lap_text, True, WHITE), (16, 16))
        # speed
        v = int(p1.speed * 18)
        spd = big.render(str(v), True, (255,140,0))
        screen.blit(spd, (SCREEN_W-spd.get_width()-20, SCREEN_H-90))
        screen.blit(small.render("KM/H", True, (140,160,180)),
                    (SCREEN_W-50, SCREEN_H-30))
        # minimap
        draw_minimap(screen, track, cars, 16, SCREEN_H-136, 180, 120)
        # boost flash
        if pygame.time.get_ticks() < boost_flash_until or p1.is_airborne:
            t = big.render("BOOST!", True, (0,255,140))
            screen.blit(t, t.get_rect(center=(SCREEN_W//2, SCREEN_H//2)))
        # countdown
        if countdown_active:
            n = max(1, int(math.ceil(countdown)))
            text = "GO!" if countdown <= 0.5 else str(n)
            t = big.render(text, True, (255,255,255))
            screen.blit(t, t.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 60)))

        pygame.display.flip()

        if all(c.finished for c in cars):
            gs.scene = "results"; return
        if p1.finished and finish_grace is None:
            finish_grace = pygame.time.get_ticks() + 4000
        if finish_grace is not None and pygame.time.get_ticks() > finish_grace:
            gs.scene = "results"; return

def results_loop(screen, font, big, small, gs):
    sorted_cars = sorted(gs.cars, key=lambda c: (
        not c.finished, c.finish_time if c.finished else (-c.lap, c.total_time)
    ))
    clock = pygame.time.Clock()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                gs.scene = "menu"; return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                gs.scene = "menu"; return
        screen.fill((10,14,26))
        title = big.render("RACE FINISHED", True, (255,140,0))
        screen.blit(title, title.get_rect(center=(SCREEN_W//2, 100)))
        for i, c in enumerate(sorted_cars):
            t = c.finish_time if c.finished else None
            line = f"{i+1}.  {c.label:>4}    {fmt_time(t) if t else 'DNF':>8}    best {fmt_time(c.best_lap)}"
            color = (255,215,0) if i == 0 else c.spec["color"]
            txt = font.render(line, True, color)
            screen.blit(txt, txt.get_rect(center=(SCREEN_W//2, 200 + i*40)))
        prompt = small.render("Click or press ENTER to return to menu", True, (140,160,180))
        screen.blit(prompt, prompt.get_rect(center=(SCREEN_W//2, SCREEN_H-60)))
        pygame.display.flip()
        clock.tick(FPS)

# ---------------- Main ----------------

def main():
    pygame.init()
    pygame.display.set_caption("Drift Race - Championship Edition")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    font  = pygame.font.SysFont("consolas,arial", 18, bold=True)
    big   = pygame.font.SysFont("consolas,arial", 42, bold=True)
    small = pygame.font.SysFont("consolas,arial", 13, bold=True)
    gs = GameState()
    while True:
        if gs.scene == "menu":
            menu_loop(screen, font, big, small, gs)
            gs.scene = "play"
        elif gs.scene == "play":
            play_loop(screen, font, big, small, gs)
        elif gs.scene == "results":
            results_loop(screen, font, big, small, gs)

if __name__ == "__main__":
    main()
