"""
Drift Race - Championship Edition (Python / pygame port)

Run:
    pip install pygame
    python drift_race.py

Controls:
    P1: WASD  (Space = drift brake, Left-Shift = chase cam in single player)
    P2: Arrow keys  (Right-Shift = drift brake) -- local multiplayer mode
    ESC or click MENU button: back to menu
"""

import math
import sys
import random
import pygame
from copy import deepcopy

SCREEN_W, SCREEN_H = 1280, 800
FPS = 60

# ---------------- Cars ----------------
CARS = [
    dict(id="blaze", name="Blaze",  color=(255,107,26),  trim=(255,170,100), accel=0.95, top=8.5, handling=0.95),
    dict(id="apex",  name="Apex",   color=(0,212,255),   trim=(140,235,255), accel=0.85, top=9.2, handling=0.88),
    dict(id="fury",  name="Fury",   color=(255,46,99),   trim=(255,140,170), accel=1.00, top=8.0, handling=1.00),
    dict(id="viper", name="Viper",  color=(0,255,136),   trim=(140,255,200), accel=0.88, top=8.8, handling=0.92),
    dict(id="ghost", name="Ghost",  color=(168,85,247),  trim=(220,170,255), accel=0.82, top=9.5, handling=0.86),
    dict(id="storm", name="Storm",  color=(251,191,36),  trim=(253,225,140), accel=0.92, top=8.6, handling=0.94),
]

# ---------------- Tracks ----------------
def catmull_rom(p0, p1, p2, p3, t):
    t2, t3 = t*t, t*t*t
    return (
        0.5*((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
        0.5*((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3),
    )

def build_centerline(controls, samples=512):
    n = len(controls); out = []; seg = samples // n
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
    t["bg"] = render_track_bg(t)
    _track_cache[tid] = t
    return t

def nearest_cl(track, x, y, hint=-1):
    c = track["center"]; N = len(c)
    best, bd = 0, float("inf")
    if hint >= 0:
        for k in range(-8, 9):
            i = (hint + k) % N
            dx, dy = c[i][0]-x, c[i][1]-y
            d = dx*dx + dy*dy
            if d < bd: bd = d; best = i
        if bd < (track["halfWidth"]*1.4)**2: return best
    for i in range(N):
        dx, dy = c[i][0]-x, c[i][1]-y
        d = dx*dx + dy*dy
        if d < bd: bd = d; best = i
    return best

# ---------------- Track rendering (offscreen, high-quality) ----------------
GRASS_DARK = (14, 26, 18)
GRASS_LIGHT = (29, 51, 34)
ROAD = (44, 44, 52)
KERB_R = (220, 38, 38)
KERB_W = (248, 250, 252)
WHITE = (255,255,255)
BLACK = (15,15,18)
PAD = (0, 255, 140)

def render_track_bg(track):
    surf = pygame.Surface((track["width"], track["height"])).convert()
    # Grass radial-ish
    surf.fill(GRASS_DARK)
    # vignette of lighter green near center
    for i in range(20):
        r = 200 + i*60
        alpha = 8
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (GRASS_LIGHT[0], GRASS_LIGHT[1], GRASS_LIGHT[2], alpha), (r, r), r)
        surf.blit(s, (track["width"]//2 - r, track["height"]//2 - r))
    # speckles
    rng = random.Random(42)
    for _ in range(2000):
        x = rng.randrange(track["width"]); y = rng.randrange(track["height"])
        c = (50 + rng.randrange(40), 80 + rng.randrange(40), 45 + rng.randrange(30))
        surf.set_at((x, y), c)
    if track.get("isEllipse"):
        draw_ellipse_road(surf, track)
    else:
        draw_poly_road(surf, track)
    return surf

def draw_ellipse_road(surf, t):
    cx_, cy_, rx, ry, hw = t["cx"], t["cy"], t["rx"], t["ry"], t["halfWidth"]
    # outer asphalt
    pygame.draw.ellipse(surf, ROAD, (cx_-rx-hw, cy_-ry-hw, 2*(rx+hw), 2*(ry+hw)))
    # cut grass hole
    inner_rect = (cx_-rx+hw, cy_-ry+hw, 2*(rx-hw), 2*(ry-hw))
    grass_inner = pygame.Surface((inner_rect[2], inner_rect[3]), pygame.SRCALPHA)
    pygame.draw.ellipse(grass_inner, (*GRASS_DARK, 255), (0, 0, inner_rect[2], inner_rect[3]))
    surf.blit(grass_inner, (inner_rect[0], inner_rect[1]))
    # asphalt speckle
    rng = random.Random(7)
    for _ in range(2500):
        a = rng.uniform(0, math.tau)
        rad = rng.uniform(rx-hw+5, rx+hw-5)
        rad_y = rng.uniform(ry-hw+5, ry+hw-5)
        x = cx_ + math.cos(a) * rad
        y = cy_ + math.sin(a) * rad_y
        v = 30 + rng.randrange(40)
        if 0 <= x < t["width"] and 0 <= y < t["height"]:
            surf.set_at((int(x), int(y)), (v, v, v+2))
    # center dashed lane (white)
    draw_dashed_ellipse(surf, (255,255,255,180), cx_, cy_, rx, ry, dash_deg=4, gap_deg=4, width=4)
    # KERBS — solid red/white blocks (NOT dashed lines)
    draw_ellipse_kerb(surf, cx_, cy_, rx + hw + 4, ry + hw + 4, segments=80, depth=14)
    draw_ellipse_kerb(surf, cx_, cy_, rx - hw - 4, ry - hw - 4, segments=80, depth=14, inward=True)
    # start/finish
    sx, sy = cx_, cy_+ry
    draw_checker_strip(surf, pygame.Rect(sx-50, sy-hw, 100, hw*2), 6, 8)
    pygame.draw.rect(surf, (220,220,255), (sx-58, sy-hw-8, 116, 6))

def draw_poly_road(surf, t):
    outer, inner = t["outer"], t["inner"]
    pygame.draw.polygon(surf, ROAD, outer)
    pygame.draw.polygon(surf, GRASS_DARK, inner)
    # speckle inside road only
    rng = random.Random(11)
    for _ in range(3500):
        # sample from outer bounding then keep ones within road
        x = rng.randrange(t["width"]); y = rng.randrange(t["height"])
        if point_in_polygon(x, y, outer) and not point_in_polygon(x, y, inner):
            v = 30 + rng.randrange(40)
            surf.set_at((x, y), (v, v, v+2))
    # center dashed lane
    pts = t["center"]
    draw_dashed_polyline(surf, (255,255,255,180), pts, width=4, dash=26, gap=26)
    # KERBS
    draw_poly_kerb(surf, outer, width=14, block_len=24, side=+1)
    draw_poly_kerb(surf, inner, width=14, block_len=24, side=-1)
    # start/finish (rotated)
    s, n = pts[0], pts[1]
    ang = math.atan2(n[1]-s[1], n[0]-s[0])
    hw = t["halfWidth"]
    chk = pygame.Surface((56, hw*2), pygame.SRCALPHA)
    draw_checker_strip(chk, pygame.Rect(0, 0, 56, hw*2), 4, 10)
    pygame.draw.rect(chk, (220,220,255), (0, 0, 56, 5))
    rot = pygame.transform.rotate(chk, -math.degrees(ang))
    surf.blit(rot, rot.get_rect(center=(s[0], s[1])))

def draw_dashed_ellipse(surf, color, cx_, cy_, rx, ry, dash_deg=4, gap_deg=4, width=3):
    a = 0.0
    while a < 360:
        a0 = math.radians(a); a1 = math.radians(a + dash_deg)
        steps = 6
        prev = None
        for s in range(steps+1):
            ang = a0 + (a1-a0) * s/steps
            x = cx_ + math.cos(ang)*rx
            y = cy_ + math.sin(ang)*ry
            if prev is not None:
                pygame.draw.line(surf, color, prev, (x, y), width)
            prev = (x, y)
        a += dash_deg + gap_deg

def draw_dashed_polyline(surf, color, points, width=4, dash=20, gap=20):
    pts = list(points) + [points[0]]
    pen = 0; rem = dash
    for i in range(len(pts)-1):
        x1, y1 = pts[i]; x2, y2 = pts[i+1]
        seg_len = math.hypot(x2-x1, y2-y1)
        if seg_len == 0: continue
        dx, dy = (x2-x1)/seg_len, (y2-y1)/seg_len
        cur = 0
        while cur < seg_len:
            take = min(rem, seg_len-cur)
            sx_, sy_ = x1+dx*cur, y1+dy*cur
            ex_, ey_ = x1+dx*(cur+take), y1+dy*(cur+take)
            if pen == 0:
                pygame.draw.line(surf, color, (sx_, sy_), (ex_, ey_), width)
            cur += take
            rem -= take
            if rem <= 0:
                pen ^= 1
                rem = dash if pen == 0 else gap

def draw_ellipse_kerb(surf, cx_, cy_, rx, ry, segments=60, depth=12, inward=False):
    for i in range(segments):
        a0 = (i / segments) * math.tau
        a1 = ((i+1) / segments) * math.tau
        # Build polygon for one block
        outer_pts = []
        inner_pts = []
        for s in range(9):
            a = a0 + (a1-a0) * s/8
            outer_pts.append((cx_ + math.cos(a)*rx, cy_ + math.sin(a)*ry))
            sign = +1 if not inward else -1
            inner_pts.append((cx_ + math.cos(a)*(rx - sign*depth),
                              cy_ + math.sin(a)*(ry - sign*depth)))
        poly = outer_pts + list(reversed(inner_pts))
        color = KERB_R if i % 2 == 0 else KERB_W
        pygame.draw.polygon(surf, color, poly)
        pygame.draw.polygon(surf, (0,0,0,80), poly, 1)

def draw_poly_kerb(surf, pts, width, block_len, side):
    """Draw red/white kerb blocks along a polygon, stepping along edges."""
    N = len(pts)
    block_idx = 0
    for i in range(N):
        a = pts[i]; b = pts[(i+1)%N]
        dx, dy = b[0]-a[0], b[1]-a[1]
        seg_len = math.hypot(dx, dy)
        if seg_len < 0.01: continue
        ux, uy = dx/seg_len, dy/seg_len
        # outward-ish normal (consistent with build_walls)
        nx, ny = -uy * side, ux * side
        cur = 0
        while cur < seg_len:
            L = min(block_len, seg_len-cur)
            p1 = (a[0]+ux*cur,     a[1]+uy*cur)
            p2 = (a[0]+ux*(cur+L), a[1]+uy*(cur+L))
            p3 = (p2[0]+nx*width,  p2[1]+ny*width)
            p4 = (p1[0]+nx*width,  p1[1]+ny*width)
            color = KERB_R if block_idx % 2 == 0 else KERB_W
            pygame.draw.polygon(surf, color, [p1, p2, p3, p4])
            pygame.draw.polygon(surf, (0,0,0), [p1, p2, p3, p4], 1)
            cur += L
            block_idx += 1

def draw_checker_strip(surf, rect, cols, rows):
    cw, ch = rect.width / cols, rect.height / rows
    for r in range(rows):
        for c in range(cols):
            color = WHITE if (r+c) % 2 == 0 else BLACK
            pygame.draw.rect(surf, color,
                (rect.x + c*cw, rect.y + r*ch, math.ceil(cw)+1, math.ceil(ch)+1))
    pygame.draw.rect(surf, (200,200,255), rect, 2)

def point_in_polygon(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi:
            inside = not inside
        j = i
    return inside

# ---------------- Skid marks ----------------
class SkidLayer:
    def __init__(self, w, h):
        self.surf = pygame.Surface((w, h), pygame.SRCALPHA)
    def add(self, car):
        sa, ca = math.sin(car.angle), math.cos(car.angle)
        for ox, oy in ((-9, 16), (9, 16)):
            wx = car.x + (ox*ca + oy*sa)
            wy = car.y + (ox*sa - oy*ca)
            pygame.draw.circle(self.surf, (20, 20, 25, 150), (int(wx), int(wy)), 3)

# ---------------- Cars / Physics ----------------
ACCEL_SCALE = 0.18
FRICTION = 0.985
DRIFT_FRICTION = 0.97
TURN_RATE = 0.045

class Car:
    def __init__(self, label, spec, is_ai, start, controls=None):
        self.label = label
        self.spec = spec
        self.is_ai = is_ai
        self.controls = controls or dict(up=False,down=False,left=False,right=False,brake=False)
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

def step(car, dt, track, sens, all_cars, total_laps, on_boost=None, skid=None):
    if car.finished: return
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
    car.vx += fx * a; car.vy += fy * a

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
        car.vx = car.vx/cur*cap; car.vy = car.vy/cur*cap
    car.speed = cur
    car.x += car.vx; car.y += car.vy

    if car.is_airborne:
        car.airborne_timer -= dt
        if car.airborne_timer <= 0: car.is_airborne = False
    if car.drifting and car.speed > 3 and skid is not None:
        skid.add(car)

    pads = track.get("jumpPads", [])
    for i, p in enumerate(pads):
        dx, dy = car.x-p["x"], car.y-p["y"]
        if dx*dx+dy*dy < p["r"]**2 and car.last_pad != i:
            car.is_airborne = True
            car.airborne_timer = 0.9
            boost = car.spec["top"] * 1.3
            car.vx = p["dx"] * boost; car.vy = p["dy"] * boost
            car.last_pad = i
            if not car.is_ai and on_boost: on_boost()
    near = False
    for p in pads:
        dx, dy = car.x-p["x"], car.y-p["y"]
        if dx*dx+dy*dy < (p["r"]*1.5)**2:
            near = True; break
    if not near: car.last_pad = -1

    # walls
    if track.get("isEllipse"):
        rx, ry, hw = track["rx"], track["ry"], track["halfWidth"]
        if ((car.x-track["cx"])/(rx+hw))**2 + ((car.y-track["cy"])/(ry+hw))**2 > 1:
            nx = (car.x-track["cx"])/rx; ny = (car.y-track["cy"])/ry
            nl = math.hypot(nx,ny) or 1
            ux, uy = nx/nl, ny/nl
            car.x -= ux*3; car.y -= uy*3
            dot = car.vx*ux + car.vy*uy
            car.vx -= 1.6*dot*ux; car.vy -= 1.6*dot*uy
            car.vx *= 0.7; car.vy *= 0.7
        if ((car.x-track["cx"])/(rx-hw))**2 + ((car.y-track["cy"])/(ry-hw))**2 < 1:
            nx = -(car.x-track["cx"])/rx; ny = -(car.y-track["cy"])/ry
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

    for o in all_cars:
        if o is car: continue
        dx, dy = car.x-o.x, car.y-o.y
        d = math.hypot(dx, dy)
        if 0 < d < 38:
            ux, uy = dx/d, dy/d
            ov = (38-d)*0.5
            car.x += ux*ov; car.y += uy*ov
            o.x -= ux*ov; o.y -= uy*ov
            rel = (car.vx-o.vx)*ux + (car.vy-o.vy)*uy
            if rel < 0:
                j = -rel * 0.9
                car.vx += ux*j*0.5; car.vy += uy*j*0.5
                o.vx -= ux*j*0.5;   o.vy -= uy*j*0.5

    if track.get("isEllipse"):
        sx, sy = track["cx"], track["cy"]+track["ry"]
        top_y = track["cy"] - track["ry"]
        if math.hypot(car.x-track["cx"], car.y-top_y) < track["ry"]:
            car.crossed_half = True
    else:
        s = track["center"][0]; sx, sy = s[0], s[1]
        half = track["center"][len(track["center"])//2]
        if math.hypot(car.x-half[0], car.y-half[1]) < track["halfWidth"]*2:
            car.crossed_half = True
    if car.crossed_half and math.hypot(car.x-sx, car.y-sy) < track["halfWidth"]*1.4:
        lap_t = car.total_time - car.lap_start
        if lap_t > 1.0:
            car.lap += 1
            car.best_lap = min(car.best_lap, lap_t)
            car.lap_start = car.total_time
            car.crossed_half = False
            if car.lap >= total_laps:
                car.finished = True
                car.finish_time = car.total_time

# ---------------- Drawing helpers ----------------
def shade_color(color, p):
    return tuple(max(0, min(255, int(c + 255*p))) for c in color)

def make_car_sprite(spec, scale=1.0, airborne=False):
    """Build a top-down car sprite with windshield, lights, wheels."""
    w, h = int(28*scale), int(48*scale)
    margin = 8
    surf = pygame.Surface((w+margin*2, h+margin*2), pygame.SRCALPHA)
    cx_, cy_ = surf.get_width()//2, surf.get_height()//2
    rect_x, rect_y = cx_-w//2, cy_-h//2
    # ground shadow
    shadow_offset = 8 if airborne else 2
    pygame.draw.rect(surf, (0,0,0,90),
                     (rect_x+1, rect_y+shadow_offset, w, h), border_radius=6)
    # body
    body_rect = (rect_x, rect_y, w, h)
    pygame.draw.rect(surf, spec["color"], body_rect, border_radius=6)
    # side shading - darker edges
    side_rect_l = (rect_x, rect_y, max(2, w//6), h)
    side_rect_r = (rect_x + w - max(2, w//6), rect_y, max(2, w//6), h)
    sh = shade_color(spec["color"], -0.25)
    side_l = pygame.Surface((side_rect_l[2], side_rect_l[3]), pygame.SRCALPHA)
    side_l.fill((sh[0], sh[1], sh[2], 100))
    surf.blit(side_l, (side_rect_l[0], side_rect_l[1]))
    side_r = pygame.Surface((side_rect_r[2], side_rect_r[3]), pygame.SRCALPHA)
    side_r.fill((sh[0], sh[1], sh[2], 100))
    surf.blit(side_r, (side_rect_r[0], side_rect_r[1]))
    # panel lines
    pygame.draw.line(surf, (0,0,0,90), (rect_x, rect_y+h//4), (rect_x+w, rect_y+h//4), 1)
    pygame.draw.line(surf, (0,0,0,90), (rect_x, rect_y+3*h//4), (rect_x+w, rect_y+3*h//4), 1)
    # racing stripe
    pygame.draw.rect(surf, spec["trim"], (cx_-2, rect_y+2, 4, h-4))
    # windshield (front)
    ws_w, ws_h = int(w*0.78), int(h*0.18)
    pygame.draw.rect(surf, (15, 30, 55), (cx_-ws_w//2, rect_y+h//4 + 1, ws_w, ws_h), border_radius=3)
    # rear window
    pygame.draw.rect(surf, (20, 30, 50), (cx_-ws_w//2, rect_y+3*h//4-ws_h-1, ws_w, ws_h), border_radius=3)
    # roof
    roof_w, roof_h = int(w*0.84), int(h*0.22)
    pygame.draw.rect(surf, shade_color(spec["color"], -0.15),
                     (cx_-roof_w//2, cy_-roof_h//2, roof_w, roof_h), border_radius=4)
    # headlights (front)
    pygame.draw.circle(surf, (255, 248, 200), (rect_x+4, rect_y+3), 3)
    pygame.draw.circle(surf, (255, 248, 200), (rect_x+w-4, rect_y+3), 3)
    # taillights (rear)
    pygame.draw.rect(surf, (255, 32, 32), (rect_x+2, rect_y+h-4, 6, 2))
    pygame.draw.rect(surf, (255, 32, 32), (rect_x+w-8, rect_y+h-4, 6, 2))
    # wheels
    pygame.draw.rect(surf, (26, 26, 30), (rect_x-2, rect_y+6,    4, 9), border_radius=1)
    pygame.draw.rect(surf, (26, 26, 30), (rect_x+w-2, rect_y+6,  4, 9), border_radius=1)
    pygame.draw.rect(surf, (26, 26, 30), (rect_x-2, rect_y+h-15, 4, 9), border_radius=1)
    pygame.draw.rect(surf, (26, 26, 30), (rect_x+w-2, rect_y+h-15,4, 9), border_radius=1)
    return surf

# Cache car sprites per spec id
_car_sprite_cache = {}
def get_car_sprite(spec, airborne=False):
    key = (spec["id"], airborne)
    if key not in _car_sprite_cache:
        _car_sprite_cache[key] = make_car_sprite(spec, scale=1.0, airborne=airborne)
    return _car_sprite_cache[key]

def draw_jump_pads(screen, track, t, world_to_screen):
    pads = track.get("jumpPads", [])
    if not pads: return
    pulse = 0.5 + 0.5 * math.sin(t*5)
    scale = world_to_screen.scale
    for p in pads:
        sx_, sy_ = world_to_screen(p["x"], p["y"])
        r = p["r"] * scale
        ang = math.atan2(p["dx"], -p["dy"])
        pad_w, pad_h = int(r*1.4), int(r)
        ps = pygame.Surface((pad_w+12, pad_h+12), pygame.SRCALPHA)
        # glow
        for i in range(6, 0, -1):
            alpha = int(20 * pulse + 10)
            pygame.draw.rect(ps, (0, 255, 140, alpha),
                             (6-i, 6-i, pad_w+i*2, pad_h+i*2), border_radius=8)
        # pad body
        pygame.draw.rect(ps, (0, 80, 30, 220), (6, 6, pad_w, pad_h), border_radius=6)
        # gradient overlay
        grad = pygame.Surface((pad_w, pad_h), pygame.SRCALPHA)
        for y in range(pad_h):
            a = int(40 + (1-y/pad_h) * (120 + pulse*80))
            pygame.draw.line(grad, (0, 255, 140, a), (0, y), (pad_w, y))
        ps.blit(grad, (6, 6))
        pygame.draw.rect(ps, (159, 255, 208), (6, 6, pad_w, pad_h), 3, border_radius=6)
        # chevrons
        cw = pad_w; ch = pad_h
        for i in (-1, 0, 1):
            yy = ch//2 + i*int(ch*0.35) + 6
            off_y = int((-(t*60) % 16))
            pygame.draw.line(ps, (255, 255, 255, int(180+pulse*70)),
                             (6 + cw*0.2, yy + off_y + 8),
                             (6 + cw*0.5, yy + off_y - 6), 4)
            pygame.draw.line(ps, (255, 255, 255, int(180+pulse*70)),
                             (6 + cw*0.5, yy + off_y - 6),
                             (6 + cw*0.8, yy + off_y + 8), 4)
        rot = pygame.transform.rotate(ps, -math.degrees(ang)+90)
        rect = rot.get_rect(center=(sx_, sy_))
        screen.blit(rot, rect)

# ---------------- Camera ----------------
class Camera:
    def __init__(self, sw, sh):
        self.sw, self.sh = sw, sh
        self.scale = 1.0
        self.cx = self.cy = 0
        self.rot = 0.0
    def set(self, x, y, scale, rot=0.0):
        self.cx, self.cy = x, y
        self.scale = scale
        self.rot = rot
    def __call__(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        if self.rot != 0.0:
            c = math.cos(self.rot); s = math.sin(self.rot)
            dx, dy = dx*c - dy*s, dx*s + dy*c
        return (dx*self.scale + self.sw/2, dy*self.scale + self.sh/2)

# ---------------- HUD ----------------
def draw_speedo(screen, x, y, r, speed, max_speed, fonts):
    # bg arc
    cx_, cy_ = x, y
    start_a, end_a = math.radians(135), math.radians(405)
    # Use polylines for thick arcs
    def arc_points(rad, a0, a1, n=64):
        return [(cx_ + math.cos(a0 + (a1-a0)*i/n)*rad,
                 cy_ + math.sin(a0 + (a1-a0)*i/n)*rad) for i in range(n+1)]
    # background
    pygame.draw.lines(screen, (255,255,255,40), False, arc_points(r, start_a, end_a), 14)
    # value
    ratio = max(0, min(1, speed/max_speed))
    if ratio > 0.001:
        # color shift
        if ratio < 0.5:
            color = (0, 212, 255)
        elif ratio < 0.85:
            color = (255, 140, 0)
        else:
            color = (255, 46, 99)
        pygame.draw.lines(screen, color, False,
                          arc_points(r, start_a, start_a + (end_a-start_a)*ratio), 12)
    # ticks
    for i in range(11):
        a = start_a + (end_a-start_a)*(i/10)
        x1 = cx_ + math.cos(a)*(r-22); y1 = cy_ + math.sin(a)*(r-22)
        x2 = cx_ + math.cos(a)*(r-12); y2 = cy_ + math.sin(a)*(r-12)
        pygame.draw.line(screen, (255,255,255,120), (x1,y1), (x2,y2), 2)
    # number
    val = str(int(speed * 18))
    txt = fonts["big"].render(val, True, (255, 140, 0))
    screen.blit(txt, txt.get_rect(center=(cx_, cy_-4)))
    unit = fonts["small"].render("KM/H", True, (140, 160, 180))
    screen.blit(unit, unit.get_rect(center=(cx_, cy_+24)))

def draw_minimap(screen, track, cars, x, y, w, h):
    # bg panel
    panel = pygame.Surface((w+16, h+16), pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 12, 22, 220), panel.get_rect(), border_radius=10)
    pygame.draw.rect(panel, (0, 200, 255, 90), panel.get_rect(), 1, border_radius=10)
    screen.blit(panel, (x-8, y-8))
    pad = 6
    sx = (w-pad*2)/track["width"]; sy = (h-pad*2)/track["height"]
    sc = min(sx, sy)
    ox = x + (w - track["width"]*sc)/2
    oy = y + (h - track["height"]*sc)/2
    if track.get("isEllipse"):
        pygame.draw.ellipse(screen, (40,42,52),
            (ox+(track["cx"]-track["rx"]-track["halfWidth"])*sc,
             oy+(track["cy"]-track["ry"]-track["halfWidth"])*sc,
             2*(track["rx"]+track["halfWidth"])*sc,
             2*(track["ry"]+track["halfWidth"])*sc))
        pygame.draw.ellipse(screen, (8, 12, 22),
            (ox+(track["cx"]-track["rx"]+track["halfWidth"])*sc,
             oy+(track["cy"]-track["ry"]+track["halfWidth"])*sc,
             2*(track["rx"]-track["halfWidth"])*sc,
             2*(track["ry"]-track["halfWidth"])*sc))
        pygame.draw.ellipse(screen, (0,200,255),
            (ox+(track["cx"]-track["rx"])*sc, oy+(track["cy"]-track["ry"])*sc,
             2*track["rx"]*sc, 2*track["ry"]*sc), 2)
    else:
        outer = [(ox+p[0]*sc, oy+p[1]*sc) for p in track["outer"]]
        inner = [(ox+p[0]*sc, oy+p[1]*sc) for p in track["inner"]]
        pygame.draw.polygon(screen, (40,42,52), outer)
        pygame.draw.polygon(screen, (8, 12, 22), inner)
        pygame.draw.polygon(screen, (0,200,255),
            [(ox+p[0]*sc, oy+p[1]*sc) for p in track["center"][::4]], 2)
    for p in track.get("jumpPads", []):
        pygame.draw.circle(screen, PAD, (int(ox+p["x"]*sc), int(oy+p["y"]*sc)), 3)
    for c in cars:
        pygame.draw.circle(screen, c.spec["color"],
                           (int(ox+c.x*sc), int(oy+c.y*sc)),
                           4 if not c.is_ai else 2)
        if not c.is_ai:
            pygame.draw.circle(screen, (255,255,255),
                               (int(ox+c.x*sc), int(oy+c.y*sc)), 4, 1)

def fmt_time(t):
    if t == float("inf"): return "—"
    m = int(t//60); s = t - m*60
    return f"{m}:{s:05.2f}"

# ---------------- Menu ----------------
class Button:
    def __init__(self, rect, label, kind="normal", value=None):
        self.rect = pygame.Rect(rect)
        self.label = label; self.kind = kind; self.value = value
        self.hover = False; self.active = False

    def draw(self, screen, fonts):
        if self.active:
            pygame.draw.rect(screen, (255,140,0), self.rect, border_radius=10)
            pygame.draw.rect(screen, (255,180,80), self.rect, 1, border_radius=10)
            color = (20, 12, 0)
        elif self.hover:
            pygame.draw.rect(screen, (40, 60, 90), self.rect, border_radius=10)
            pygame.draw.rect(screen, (0, 200, 255), self.rect, 1, border_radius=10)
            color = (240, 240, 250)
        else:
            pygame.draw.rect(screen, (24, 32, 48), self.rect, border_radius=10)
            pygame.draw.rect(screen, (60, 80, 110), self.rect, 1, border_radius=10)
            color = (210, 220, 235)
        font = fonts["mid"] if self.kind == "big" else fonts["small_b"]
        t = font.render(self.label, True, color)
        screen.blit(t, t.get_rect(center=self.rect.center))

class GameState:
    def __init__(self):
        self.mode = "single"
        self.car_pick = "blaze"
        self.car_pick2 = "apex"
        self.track_pick = "oval"
        self.total_laps = 3
        self.sensitivity = 1.0
        self.scene = "menu"
        self.cars = []
        self.track = None
        self.chase_cam = False

def make_fonts():
    pygame.font.init()
    return {
        "title": pygame.font.SysFont("arial,helvetica", 56, bold=True),
        "big": pygame.font.SysFont("consolas,arial", 38, bold=True),
        "mid": pygame.font.SysFont("arial,helvetica", 18, bold=True),
        "small": pygame.font.SysFont("arial,helvetica", 13),
        "small_b": pygame.font.SysFont("arial,helvetica", 13, bold=True),
        "tiny": pygame.font.SysFont("arial,helvetica", 11),
    }

def menu_loop(screen, fonts, gs):
    clock = pygame.time.Clock()
    cars = CARS
    tracks = list(TRACKS.values())

    while True:
        mx, my = pygame.mouse.get_pos()
        clicked = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit(0)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True

        # background
        screen.fill((10, 16, 28))
        # subtle radial light
        for i in range(8):
            r = 200 + i*70
            s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (30, 50, 90, 8), (r,r), r)
            screen.blit(s, (SCREEN_W//2-r, SCREEN_H//4-r))

        # panel background
        panel = pygame.Surface((860, SCREEN_H-40), pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 22, 38, 240), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, (0, 200, 255, 60), panel.get_rect(), 1, border_radius=18)
        panel_x = (SCREEN_W - 860)//2; panel_y = 20
        screen.blit(panel, (panel_x, panel_y))

        # Title
        title = fonts["title"].render("DRIFT RACE", True, (255, 140, 0))
        screen.blit(title, title.get_rect(center=(SCREEN_W//2, panel_y+50)))
        sub = fonts["small_b"].render("CHAMPIONSHIP EDITION", True, (0, 200, 255))
        screen.blit(sub, sub.get_rect(center=(SCREEN_W//2, panel_y+92)))

        # Mode buttons
        mode_y = panel_y + 120
        modes = [("single", "SINGLE PLAYER"), ("multi", "LOCAL MULTIPLAYER")]
        mode_btns = []
        for i, (mid, label) in enumerate(modes):
            r = pygame.Rect(panel_x + 30 + i*410, mode_y, 380, 44)
            b = Button(r, label, kind="big", value=mid)
            b.active = (gs.mode == mid)
            b.hover = r.collidepoint(mx, my)
            b.draw(screen, fonts)
            mode_btns.append(b)
            if clicked and b.hover: gs.mode = mid

        # Car row P1
        cy_ = mode_y + 70
        screen.blit(fonts["small_b"].render("YOUR CAR", True, (107, 138, 168)), (panel_x+40, cy_))
        for i, c in enumerate(cars):
            r = pygame.Rect(panel_x + 40 + i*125, cy_+22, 110, 80)
            sel = c["id"] == gs.car_pick
            hover = r.collidepoint(mx, my)
            bg = (40, 30, 0) if sel else ((28, 36, 56) if hover else (18, 24, 36))
            border = (255, 140, 0) if sel else ((0, 200, 255) if hover else (50, 60, 80))
            pygame.draw.rect(screen, bg, r, border_radius=10)
            pygame.draw.rect(screen, border, r, 2, border_radius=10)
            sprite = get_car_sprite(c, airborne=False)
            sm = pygame.transform.scale(sprite, (38, 64))
            screen.blit(sm, sm.get_rect(center=(r.centerx, r.centery-6)))
            nm = fonts["small_b"].render(c["name"], True, c["color"] if sel else (200,210,225))
            screen.blit(nm, nm.get_rect(center=(r.centerx, r.bottom-12)))
            if clicked and hover: gs.car_pick = c["id"]

        # Stats bars for selected P1
        p1 = next(c for c in cars if c["id"] == gs.car_pick)
        stat_y = cy_+114
        for i, (label, val) in enumerate([("ACCEL", p1["accel"]), ("TOP SPD", p1["top"]/9.5), ("HANDLING", p1["handling"])]):
            screen.blit(fonts["tiny"].render(label, True, (130,150,180)), (panel_x+40, stat_y + i*16))
            bar_x = panel_x+120; bar_y = stat_y + i*16 + 4; bar_w = 200
            pygame.draw.rect(screen, (40,50,70), (bar_x, bar_y, bar_w, 5), border_radius=2)
            pygame.draw.rect(screen, (255,140,0), (bar_x, bar_y, int(bar_w*val), 5), border_radius=2)

        next_y = stat_y + 60

        # Player 2 cars (multi)
        if gs.mode == "multi":
            screen.blit(fonts["small_b"].render("PLAYER 2 CAR", True, (107,138,168)), (panel_x+40, next_y))
            for i, c in enumerate(cars):
                r = pygame.Rect(panel_x + 40 + i*125, next_y+22, 110, 70)
                sel = c["id"] == gs.car_pick2
                hover = r.collidepoint(mx, my)
                bg = (40, 30, 0) if sel else ((28, 36, 56) if hover else (18, 24, 36))
                border = (255, 140, 0) if sel else ((0, 200, 255) if hover else (50, 60, 80))
                pygame.draw.rect(screen, bg, r, border_radius=10)
                pygame.draw.rect(screen, border, r, 2, border_radius=10)
                sprite = get_car_sprite(c)
                sm = pygame.transform.scale(sprite, (32, 54))
                screen.blit(sm, sm.get_rect(center=(r.centerx, r.centery-4)))
                nm = fonts["small_b"].render(c["name"], True, c["color"] if sel else (200,210,225))
                screen.blit(nm, nm.get_rect(center=(r.centerx, r.bottom-10)))
                if clicked and hover: gs.car_pick2 = c["id"]
            next_y += 110

        # Laps + sensitivity
        screen.blit(fonts["small_b"].render("LAPS", True, (107,138,168)), (panel_x+40, next_y))
        for i, n in enumerate([1,3,5]):
            r = pygame.Rect(panel_x + 40 + i*60, next_y+22, 50, 38)
            b = Button(r, str(n))
            b.active = gs.total_laps == n
            b.hover = r.collidepoint(mx, my)
            b.draw(screen, fonts)
            if clicked and b.hover: gs.total_laps = n

        screen.blit(fonts["small_b"].render(f"STEERING SENSITIVITY: {gs.sensitivity:.2f}x", True, (107,138,168)),
                    (panel_x + 280, next_y))
        sl_x, sl_y, sl_w = panel_x + 280, next_y + 32, 540
        pygame.draw.rect(screen, (40,50,70), (sl_x, sl_y, sl_w, 6), border_radius=3)
        prog = (gs.sensitivity - 0.5) / 1.5
        pygame.draw.rect(screen, (255,140,0), (sl_x, sl_y, int(sl_w*prog), 6), border_radius=3)
        knob_x = sl_x + int(sl_w * prog)
        pygame.draw.circle(screen, (255,140,0), (knob_x, sl_y+3), 9)
        pygame.draw.circle(screen, (255,200,140), (knob_x, sl_y+3), 9, 2)
        if pygame.mouse.get_pressed()[0]:
            if sl_x-10 <= mx <= sl_x+sl_w+10 and sl_y-12 <= my <= sl_y+18:
                gs.sensitivity = max(0.5, min(2.0, 0.5 + (mx-sl_x)/sl_w * 1.5))

        # Tracks
        track_y = next_y + 75
        screen.blit(fonts["small_b"].render("TRACK", True, (107,138,168)), (panel_x+40, track_y))
        for i, t in enumerate(tracks):
            col = i % 2; row = i // 2
            r = pygame.Rect(panel_x + 40 + col*400, track_y+22 + row*72, 380, 60)
            sel = t["id"] == gs.track_pick
            hover = r.collidepoint(mx, my)
            bg = (40, 30, 0) if sel else ((28, 36, 56) if hover else (18, 24, 36))
            border = (255, 140, 0) if sel else ((0, 200, 255) if hover else (50, 60, 80))
            pygame.draw.rect(screen, bg, r, border_radius=10)
            pygame.draw.rect(screen, border, r, 2, border_radius=10)
            tn = fonts["mid"].render(t["name"], True, (255,180,80) if sel else (220,225,235))
            screen.blit(tn, (r.x+12, r.y+8))
            if t.get("boost"):
                tag = fonts["tiny"].render("BOOST PADS", True, (4,40,20))
                tw = tag.get_width()+10
                pygame.draw.rect(screen, (0,255,140),
                                 (r.x+22+tn.get_width(), r.y+12, tw, 16), border_radius=3)
                screen.blit(tag, (r.x+27+tn.get_width(), r.y+13))
            td = fonts["tiny"].render(t["desc"], True, (140,160,180))
            screen.blit(td, (r.x+12, r.y+36))
            if clicked and hover: gs.track_pick = t["id"]

        # Start button
        start_y = track_y + 180
        start_r = pygame.Rect(panel_x+40, start_y, 780, 56)
        hover_s = start_r.collidepoint(mx, my)
        col1 = (255, 180, 80) if hover_s else (255, 160, 64)
        col2 = (255, 90, 0) if hover_s else (255, 107, 26)
        for i in range(start_r.height):
            t = i / start_r.height
            c = (int(col1[0]*(1-t)+col2[0]*t), int(col1[1]*(1-t)+col2[1]*t), int(col1[2]*(1-t)+col2[2]*t))
            pygame.draw.line(screen, c, (start_r.x, start_r.y+i), (start_r.right, start_r.y+i))
        pygame.draw.rect(screen, (255, 200, 140), start_r, 2, border_radius=12)
        pygame.draw.rect(screen, (0,0,0,0), start_r, border_radius=12)  # masked corners
        st = fonts["big"].render("START RACE", True, (20, 12, 0))
        screen.blit(st, st.get_rect(center=start_r.center))
        if clicked and hover_s:
            return

        # hint
        hint = fonts["tiny"].render(
            "P1: WASD + SPACE drift + LSHIFT chase  |  P2: Arrows + RSHIFT drift  |  ESC menu",
            True, (110, 130, 160))
        screen.blit(hint, hint.get_rect(center=(SCREEN_W//2, start_y+72)))

        pygame.display.flip()
        clock.tick(FPS)

def play_loop(screen, fonts, gs):
    track = get_track(gs.track_pick)
    gs.track = track
    p1_spec = next(c for c in CARS if c["id"] == gs.car_pick)
    cars = []
    p1 = Car("P1", p1_spec, False, track["startPositions"][0])
    cars.append(p1)
    if gs.mode == "multi":
        p2_spec = next(c for c in CARS if c["id"] == gs.car_pick2)
        p2 = Car("P2", p2_spec, False, track["startPositions"][1])
        cars.append(p2)
    else:
        ais = [c for c in CARS if c["id"] != gs.car_pick][:2]
        for i, spec in enumerate(ais):
            cars.append(Car(f"AI{i+1}", spec, True, track["startPositions"][i+1]))
    gs.cars = cars

    skid = SkidLayer(track["width"], track["height"])
    cam = Camera(SCREEN_W, SCREEN_H)
    clock = pygame.time.Clock()
    boost_flash_until = 0
    countdown = 3.5
    elapsed = 0.0
    finish_grace = None

    menu_btn = pygame.Rect(SCREEN_W-110, 18, 92, 36)

    def trigger_flash():
        nonlocal boost_flash_until
        boost_flash_until = pygame.time.get_ticks() + 700

    while True:
        dt = clock.tick(FPS) / 1000.0
        elapsed += dt
        mx, my = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                gs.scene = "menu"; return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if menu_btn.collidepoint(e.pos):
                    gs.scene = "menu"; return

        keys = pygame.key.get_pressed()
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

        if countdown > 0:
            countdown -= dt
        else:
            for c in cars:
                step(c, dt, track, gs.sensitivity, cars, gs.total_laps,
                     on_boost=trigger_flash if c is p1 else None,
                     skid=skid)

        # Render
        screen.fill((10, 16, 24))
        scale = min(SCREEN_W/1300, SCREEN_H/750) * 1.3
        rot = -p1.angle if (gs.chase_cam and gs.mode == "single") else 0.0
        cam.set(p1.x, p1.y, scale, rot)

        # draw track + skid (composited offscreen at world resolution would be slow;
        # we scale the bg directly)
        if rot == 0.0:
            tw = int(track["width"]*scale); th = int(track["height"]*scale)
            scaled_bg = pygame.transform.smoothscale(track["bg"], (tw, th))
            scaled_skid = pygame.transform.smoothscale(skid.surf, (tw, th))
            ox = SCREEN_W/2 - p1.x*scale
            oy = SCREEN_H/2 - p1.y*scale
            screen.blit(scaled_bg, (ox, oy))
            screen.blit(scaled_skid, (ox, oy))
        else:
            tw = int(track["width"]*scale); th = int(track["height"]*scale)
            combo = pygame.Surface((tw, th)).convert()
            scaled_bg = pygame.transform.smoothscale(track["bg"], (tw, th))
            combo.blit(scaled_bg, (0, 0))
            scaled_skid = pygame.transform.smoothscale(skid.surf, (tw, th))
            combo.blit(scaled_skid, (0, 0))
            rotated = pygame.transform.rotate(combo, math.degrees(rot))
            px = p1.x*scale - tw/2
            py = p1.y*scale - th/2
            cosr = math.cos(rot); sinr = math.sin(rot)
            rx = px*cosr - py*sinr
            ry = px*sinr + py*cosr
            new_center = (SCREEN_W/2 - rx, SCREEN_H/2 - ry)
            screen.blit(rotated, rotated.get_rect(center=new_center))

        # jump pads
        cam.scale = scale
        draw_jump_pads(screen, track, elapsed, cam)
        # cars
        for c in cars:
            sx_, sy_ = cam(c.x, c.y)
            sprite = get_car_sprite(c.spec, airborne=c.is_airborne)
            angle_deg = -math.degrees(c.angle + rot if rot else c.angle)
            rotated = pygame.transform.rotate(sprite, angle_deg)
            screen.blit(rotated, rotated.get_rect(center=(sx_, sy_)))
            if c.is_airborne:
                glow = pygame.Surface((70, 70), pygame.SRCALPHA)
                pygame.draw.circle(glow, (0, 220, 255, 90), (35, 35), 32)
                pygame.draw.circle(glow, (0, 255, 255, 50), (35, 35), 24)
                screen.blit(glow, glow.get_rect(center=(sx_, sy_)))

        # ----- HUD -----
        # Top bar (lap + timer)
        topbar = pygame.Surface((360, 44), pygame.SRCALPHA)
        pygame.draw.rect(topbar, (8, 12, 22, 200), topbar.get_rect(), border_radius=12)
        pygame.draw.rect(topbar, (0, 200, 255, 80), topbar.get_rect(), 1, border_radius=12)
        screen.blit(topbar, (SCREEN_W//2-180, 18))
        lap_text = f"LAP {min(p1.lap+1, gs.total_laps)}/{gs.total_laps}"
        lt = fonts["mid"].render(lap_text, True, (255, 180, 100))
        tt = fonts["mid"].render(fmt_time(p1.total_time), True, (240, 240, 250))
        screen.blit(lt, (SCREEN_W//2-160, 28))
        screen.blit(tt, (SCREEN_W//2-160 + lt.get_width() + 20, 28))

        # Controls box (top left)
        ctl = pygame.Surface((230, 110), pygame.SRCALPHA)
        pygame.draw.rect(ctl, (8, 12, 22, 180), ctl.get_rect(), border_radius=10)
        pygame.draw.rect(ctl, (255,255,255,30), ctl.get_rect(), 1, border_radius=10)
        screen.blit(ctl, (18, 18))
        if gs.mode == "multi":
            lines = ["P1: WASD + SPACE drift", "P2: Arrows + RSHIFT drift", "ESC / button: menu"]
        else:
            lines = ["WASD - drive", "SPACE - drift brake", "L-SHIFT - chase cam", "ESC / button: menu"]
        for i, ln in enumerate(lines):
            screen.blit(fonts["small"].render(ln, True, (160, 180, 210)), (32, 30 + i*20))

        # Menu button (top right)
        hover_mb = menu_btn.collidepoint(mx, my)
        col = (255, 80, 80) if hover_mb else (40, 50, 80)
        pygame.draw.rect(screen, (8, 12, 22), menu_btn, border_radius=8)
        pygame.draw.rect(screen, col, menu_btn, 2, border_radius=8)
        mb_t = fonts["small_b"].render("◀ MENU", True, (255,255,255) if hover_mb else (200,210,225))
        screen.blit(mb_t, mb_t.get_rect(center=menu_btn.center))

        # Speedometer
        draw_speedo(screen, SCREEN_W-110, SCREEN_H-110, 78, p1.speed, p1.spec["top"]*1.5, fonts)

        # Minimap
        draw_minimap(screen, track, cars, 32, SCREEN_H-180, 220, 150)

        # Standings
        ranked = sorted(cars, key=lambda c: (
            not c.finished,
            c.finish_time if c.finished else (-c.lap, c.total_time)
        ))
        stand_w = 180
        stand_h = 36 + len(ranked)*22
        stand_x = SCREEN_W - stand_w - 18
        stand_y = 70
        sp = pygame.Surface((stand_w, stand_h), pygame.SRCALPHA)
        pygame.draw.rect(sp, (8, 12, 22, 200), sp.get_rect(), border_radius=10)
        pygame.draw.rect(sp, (255,255,255,30), sp.get_rect(), 1, border_radius=10)
        screen.blit(sp, (stand_x, stand_y))
        screen.blit(fonts["small_b"].render("STANDINGS", True, (255,180,100)), (stand_x+12, stand_y+8))
        for i, c in enumerate(ranked):
            yy = stand_y + 30 + i*22
            screen.blit(fonts["small_b"].render(f"{i+1}.", True, (255,200,120)), (stand_x+12, yy))
            pygame.draw.circle(screen, c.spec["color"], (stand_x+38, yy+8), 5)
            screen.blit(fonts["small"].render(f"{c.label}  L{c.lap+1}", True,
                        (255,255,255) if not c.is_ai else (180,200,220)),
                        (stand_x+50, yy))

        # Boost text
        if pygame.time.get_ticks() < boost_flash_until or p1.is_airborne:
            for blur in range(3, 0, -1):
                t = fonts["title"].render("BOOST!", True, (0, 255, 140))
                t.set_alpha(60)
                screen.blit(t, t.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 100)).inflate(blur*2, blur*2))
            t = fonts["title"].render("BOOST!", True, (200, 255, 220))
            screen.blit(t, t.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 100)))

        # Countdown
        if countdown > 0:
            txt = "GO!" if countdown < 0.5 else str(int(math.ceil(countdown - 0.5)))
            big_font = pygame.font.SysFont("arial,helvetica", 200, bold=True)
            t = big_font.render(txt, True, (255, 200, 80))
            t_shadow = big_font.render(txt, True, (50, 30, 0))
            screen.blit(t_shadow, t_shadow.get_rect(center=(SCREEN_W//2+4, SCREEN_H//2+4)))
            screen.blit(t, t.get_rect(center=(SCREEN_W//2, SCREEN_H//2)))

        pygame.display.flip()

        if all(c.finished for c in cars):
            gs.scene = "results"; return
        if p1.finished and finish_grace is None:
            finish_grace = pygame.time.get_ticks() + 4000
        if finish_grace is not None and pygame.time.get_ticks() > finish_grace:
            gs.scene = "results"; return

def results_loop(screen, fonts, gs):
    sorted_cars = sorted(gs.cars, key=lambda c: (
        not c.finished, c.finish_time if c.finished else (-c.lap, c.total_time)
    ))
    clock = pygame.time.Clock()
    while True:
        mx, my = pygame.mouse.get_pos()
        clicked = False
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit(0)
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                gs.scene = "menu"; return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                clicked = True

        screen.fill((10, 16, 28))

        panel_w, panel_h = 620, min(SCREEN_H-60, 480)
        px = (SCREEN_W-panel_w)//2; py = (SCREEN_H-panel_h)//2
        ps = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(ps, (15, 22, 38, 240), ps.get_rect(), border_radius=18)
        pygame.draw.rect(ps, (0, 200, 255, 60), ps.get_rect(), 1, border_radius=18)
        screen.blit(ps, (px, py))

        title = fonts["title"].render("RACE FINISHED", True, (255, 140, 0))
        screen.blit(title, title.get_rect(center=(SCREEN_W//2, py+48)))

        for i, c in enumerate(sorted_cars):
            r = pygame.Rect(px+30, py+110 + i*48, panel_w-60, 40)
            bg = (60, 50, 0, 80) if i == 0 else (255,255,255,8)
            sp = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            sp.fill(bg)
            screen.blit(sp, r.topleft)
            if i == 0:
                pygame.draw.rect(screen, (255, 215, 0), (r.x, r.y, 4, r.h))
            pos = fonts["mid"].render(f"#{i+1}", True, (255,180,100))
            screen.blit(pos, (r.x+10, r.y+10))
            nm = fonts["mid"].render(f"{c.label}  ({c.spec['name']})", True, c.spec["color"])
            screen.blit(nm, (r.x+50, r.y+10))
            t = fmt_time(c.finish_time) if c.finished else "DNF"
            tt = fonts["mid"].render(t, True, (240,240,250))
            screen.blit(tt, (r.x+r.w-200, r.y+10))
            bl = fonts["small"].render(f"best {fmt_time(c.best_lap)}", True, (140,160,180))
            screen.blit(bl, (r.x+r.w-100, r.y+14))

        # Back to menu button
        bm_r = pygame.Rect(px+30, py+panel_h-70, panel_w-60, 50)
        hover = bm_r.collidepoint(mx, my)
        col1 = (255, 180, 80) if hover else (255, 160, 64)
        col2 = (255, 90, 0) if hover else (255, 107, 26)
        for i in range(bm_r.height):
            tt = i / bm_r.height
            c = (int(col1[0]*(1-tt)+col2[0]*tt), int(col1[1]*(1-tt)+col2[1]*tt), int(col1[2]*(1-tt)+col2[2]*tt))
            pygame.draw.line(screen, c, (bm_r.x, bm_r.y+i), (bm_r.right, bm_r.y+i))
        pygame.draw.rect(screen, (255, 200, 140), bm_r, 2, border_radius=12)
        bt = fonts["big"].render("BACK TO MENU", True, (20, 12, 0))
        screen.blit(bt, bt.get_rect(center=bm_r.center))
        if clicked and hover:
            gs.scene = "menu"; return

        pygame.display.flip()
        clock.tick(FPS)

def main():
    pygame.init()
    pygame.display.set_caption("Drift Race - Championship Edition")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    fonts = make_fonts()
    gs = GameState()
    while True:
        if gs.scene == "menu":
            menu_loop(screen, fonts, gs)
            gs.scene = "play"
        elif gs.scene == "play":
            play_loop(screen, fonts, gs)
        elif gs.scene == "results":
            results_loop(screen, fonts, gs)

if __name__ == "__main__":
    main()
