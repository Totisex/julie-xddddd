import sys, math, time
sys.path.insert(0, '.')
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import spr, tex, elev, nature, plan
from spr import noise, shade

# ----------------------------------------------------------------- layout
S = 100                      # px por metro (escala unica para corte y planta)
SW, SH = 5000, 3550          # lamina
X0, PW = 200, 4600           # panel: ancho 46 m
SEC_TOP = 270
SKY = 11.8                   # m sobre calzada visibles
BELOW = 3.9                  # m de subrasante (medido del PDF)
BLD_H = 9.1                  # altura edificaciones colindantes (medido del PDF)
Y_LANE = SEC_TOP + int(SKY * S)
SEC_BOT = Y_LANE + int(BELOW * S)
BAND_TOP = SEC_BOT + 15
BAND_H = 315
PLAN_TOP = BAND_TOP + BAND_H + 20
PLAN_LEN = 12.5
PLAN_BOT = PLAN_TOP + int(PLAN_LEN * S)
ZC = 5.5                     # posicion longitudinal del corte dentro del tramo de planta

FONT_DIR = '/usr/share/fonts/opentype/inter/'
def font(sz, bold=False, semi=False):
    n = 'Inter-Bold.otf' if bold else ('Inter-SemiBold.otf' if semi else 'Inter-Regular.otf')
    return ImageFont.truetype(FONT_DIR + n, sz)

# ----------------------------------------------------------------- datos de las 3 vias (medidos del PDF)
# (tipo, ancho_m, z_ini, z_fin)  z = nivel sobre la calzada (m)
VIAS = {
    1: dict(L=30.0, segs=[('vereda', 2.4, .20, .20), ('parking', 4.4, .20, 0), ('lane', 3.3, 0, 0), ('lane', 3.3, 0, 0), ('berma', 3.2, .15, .15),
                          ('lane', 3.3, 0, 0), ('lane', 3.3, 0, 0), ('parking', 4.4, 0, .20), ('vereda', 2.4, .20, .20)],
            labels=['VEREDA', 'ESTACIONAMIENTO\nPARALELO', 'CARRIL\nVEHICULAR', 'CARRIL\nVEHICULAR', 'BERMA\nCENTRAL', 'CARRIL\nVEHICULAR', 'CARRIL\nVEHICULAR', 'ESTACIONAMIENTO\nPARALELO', 'VEREDA'],
            sub='Ancho total 30.00 m   ·   4 carriles (2 por sentido)   ·   berma central   ·   estacionamiento paralelo   ·   veredas laterales'),
    2: dict(L=25.0, segs=[('vereda', 2.4, .20, .20), ('parking', 3.0, .20, 0), ('lane', 3.3, 0, 0), ('lane', 3.3, 0, 0), ('berma', 1.0, .20, .20),
                          ('lane', 3.3, 0, 0), ('lane', 3.3, 0, 0), ('parking', 3.0, 0, .20), ('vereda', 2.4, .20, .20)],
            labels=['VEREDA', 'ESTACIONAMIENTO\nPARALELO', 'CARRIL\nVEHICULAR', 'CARRIL\nVEHICULAR', 'BERMA\nCENTRAL', 'CARRIL\nVEHICULAR', 'CARRIL\nVEHICULAR', 'ESTACIONAMIENTO\nPARALELO', 'VEREDA'],
            sub='Ancho total 25.00 m   ·   4 carriles (2 por sentido)   ·   berma central   ·   estacionamiento paralelo   ·   veredas laterales'),
    3: dict(L=16.0, segs=[('vereda', 2.0, .12, .12), ('berma', .6, .20, .20), ('parking', 2.4, .20, 0), ('lane', 3.0, 0, 0), ('lane', 3.0, 0, 0),
                          ('parking', 2.4, 0, .20), ('berma', .6, .20, .20), ('vereda', 2.0, .12, .12)],
            labels=['VEREDA', 'BERMA', 'EST.\nPARALELO', 'CARRIL\nVEHICULAR', 'CARRIL\nVEHICULAR', 'EST.\nPARALELO', 'BERMA', 'VEREDA'],
            sub='Ancho total 16.00 m   ·   2 carriles (1 por sentido)   ·   bermas laterales   ·   estacionamiento paralelo   ·   veredas laterales'),
}
for v in VIAS.values():
    xs = np.cumsum([0] + [s_[1] for s_ in v['segs']])
    assert abs(xs[-1] - v['L']) < 1e-6, (xs[-1], v['L'])
    v['xs'] = xs
    v['side'] = (46 - v['L']) / 2

# ----------------------------------------------------------------- utilidades de lienzo
def blend(cv, x0, y0, rgb, mask=None, alpha=1.0, clip=None):
    h, w = rgb.shape[:2]
    cx0, cy0, cx1, cy1 = clip if clip else (0, 0, cv.shape[1], cv.shape[0])
    ax0, ay0 = max(x0, cx0), max(y0, cy0)
    ax1, ay1 = min(x0 + w, cx1), min(y0 + h, cy1)
    if ax1 <= ax0 or ay1 <= ay0:
        return
    sub = rgb[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
    if mask is None:
        m = np.full(sub.shape[:2], alpha, np.float32)
    else:
        m = mask[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] * alpha
    dst = cv[ay0:ay1, ax0:ax1]
    cv[ay0:ay1, ax0:ax1] = sub * m[..., None] + dst * (1 - m[..., None])


def poly_mask(pts, W=None):
    """pts en px absolutos -> (x0,y0,mask)"""
    p = np.asarray(pts, float)
    x0, y0 = int(math.floor(p[:, 0].min())) - 2, int(math.floor(p[:, 1].min())) - 2
    x1, y1 = int(math.ceil(p[:, 0].max())) + 2, int(math.ceil(p[:, 1].max())) + 2
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    q = np.round((p - [x0, y0]) * 16).astype(np.int32)
    cv2.fillPoly(m, [q], 255, lineType=cv2.LINE_AA, shift=4)
    return x0, y0, m.astype(np.float32) / 255.0


def fill_tex(cv, pts, texfn, clip=None, alpha=1.0):
    x0, y0, m = poly_mask(pts)
    t = texfn(m.shape[0], m.shape[1])
    blend(cv, x0, y0, t, m, alpha, clip)


def fill_color(cv, pts, col, alpha=1.0, clip=None):
    x0, y0, m = poly_mask(pts)
    blend(cv, x0, y0, np.broadcast_to(np.array(col, np.float32), m.shape + (3,)), m, alpha, clip)


def line_px(cv, pts, col, w, alpha=1.0, closed=False, clip=None):
    p = np.asarray(pts, float)
    pad = int(w) + 3
    x0, y0 = int(p[:, 0].min()) - pad, int(p[:, 1].min()) - pad
    x1, y1 = int(p[:, 0].max()) + pad, int(p[:, 1].max()) + pad
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    q = np.round((p - [x0, y0]) * 16).astype(np.int32)
    cv2.polylines(m, [q], closed, 255, max(1, int(round(w))), lineType=cv2.LINE_AA, shift=4)
    blend(cv, x0, y0, np.broadcast_to(np.array(col, np.float32), m.shape + (3,)), m.astype(np.float32) / 255.0, alpha, clip)


_cache = {}
def paste(cv, sp, px, py, rot=0.0, clip=None, key=None):
    k = key or id(sp)
    if k not in _cache:
        _cache[k] = sp.rgba_small(S)
    rgb, a = _cache[k]
    oxp, oyp = sp.ox * S, rgb.shape[0] - sp.oz * S
    if rot:
        M = cv2.getRotationMatrix2D((oxp, oyp), rot, 1.0)
        rgb = cv2.warpAffine(rgb, M, (rgb.shape[1], rgb.shape[0]), flags=cv2.INTER_LINEAR)
        a = cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR)
    x0, y0 = int(round(px - oxp)), int(round(py - oyp))
    h, w = a.shape
    cx0, cy0, cx1, cy1 = clip if clip else (0, 0, cv.shape[1], cv.shape[0])
    ax0, ay0 = max(x0, cx0), max(y0, cy0)
    ax1, ay1 = min(x0 + w, cx1), min(y0 + h, cy1)
    if ax1 <= ax0 or ay1 <= ay0:
        return
    r = rgb[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
    aa = a[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
    cv[ay0:ay1, ax0:ax1] = r + cv[ay0:ay1, ax0:ax1] * (1 - aa[..., None])


def vgrad_rect(cv, x0, y0, x1, y1, c0, c1):
    h = y1 - y0
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    cv[y0:y1, x0:x1] = g
CLR = None

# ----------------------------------------------------------------- geometria transversal
def seg_range(v, i):
    return v['xs'][i], v['xs'][i + 1]

def surf_z(v, xm):
    for i, (nm, w, z0, z1) in enumerate(v['segs']):
        a, b = seg_range(v, i)
        if a - 1e-9 <= xm <= b + 1e-9:
            return z0 + (z1 - z0) * (xm - a) / (b - a)
    return 0.0

def SX(v, xm):
    return X0 + (xm + v['side']) * S

def SY(z):
    return Y_LANE - z * S

def lane_dir(v, i):
    a, b = seg_range(v, i)
    return -1 if (a + b) / 2 < v['L'] / 2 else 1   # -1 = hacia abajo (flecha ↓), +1 = hacia arriba (flecha ↑)

# ----------------------------------------------------------------- CORTE
def draw_section(cv, v, ent):
    L = v['L']
    # cielo
    top = SEC_TOP
    vgrad_rect(cv, X0, top, X0 + PW, Y_LANE, (196, 216, 228), (240, 245, 246))
    rng = np.random.default_rng(11)
    h, w = Y_LANE - top, PW
    n = noise(h, w, 420, rng, 4)
    cl = np.clip((n - 0.52) / 0.22, 0, 1) ** 1.5 * np.clip(1.15 - np.linspace(0, 1, h)[:, None] * 0.8, 0, 1)
    sky = cv[top:Y_LANE, X0:X0 + PW]
    cv[top:Y_LANE, X0:X0 + PW] = sky * (1 - 0.42 * cl[..., None]) + np.array((252, 253, 253), np.float32) * 0.42 * cl[..., None]
    # aves
    for (bx, bz, sz) in ent['birds']:
        paste(cv, nature.bird(sz, 0.5 + 0.4 * ((bx * 7) % 1)), X0 + bx * PW, SEC_TOP + bz * S * 3.0, key=('bird', bx))
    # edificaciones colindantes ("propiedad de terceros")
    xl, xr = SX(v, 0), SX(v, L)
    ytop = SY(BLD_H)
    for (a, b, sd) in ((X0, int(xl), 4), (int(xr), X0 + PW, 5)):
        t = tex.building(SEC_BOT - int(ytop), b - a, sd)
        gx = np.linspace(0, 1, b - a, dtype=np.float32)[None, :, None]
        if sd == 4:
            t = t * (1 - 0.14 * np.clip((gx - 0.82) / 0.18, 0, 1))
        else:
            t = t * (1 - 0.14 * np.clip((0.18 - gx) / 0.18, 0, 1))
        gy = np.linspace(1.03, 0.94, t.shape[0], dtype=np.float32)[:, None, None]
        cv[int(ytop):SEC_BOT, a:b] = t * gy
        cv[int(ytop) - 3:int(ytop) + 3, a:b] = (222, 223, 221)
    # terreno por elementos
    ybot = SEC_BOT
    segs = v['segs']
    for i, (nm, wd, z0, z1) in enumerate(segs):
        a, b = seg_range(v, i)
        pts = [(SX(v, a), SY(z0)), (SX(v, b), SY(z1)), (SX(v, b), ybot), (SX(v, a), ybot)]
        sd = 20 + i
        if nm == 'vereda':
            fn = lambda hh, ww, sd=sd: tex.stone(hh, ww, sd, 44)
        elif nm == 'parking':
            fn = lambda hh, ww, sd=sd: tex.concrete(hh, ww, sd, (203, 204, 201))
        elif nm == 'lane':
            fn = lambda hh, ww, sd=sd: tex.asphalt(hh, ww, sd)
        else:
            fn = lambda hh, ww, sd=sd: tex.grass(hh, ww, sd, (92, 124, 70))
        fill_tex(cv, pts, fn)
        # profundidad: oscurece suavemente hacia abajo
        x0_, y0_, m = poly_mask(pts)
        gy = np.linspace(0, 1, m.shape[0], dtype=np.float32)[:, None, None]
        blend(cv, x0_, y0_, np.zeros(m.shape + (3,), np.float32), m * (0.05 + 0.20 * gy[..., 0]))
    # carpeta superior (0.10 m)
    for i, (nm, wd, z0, z1) in enumerate(segs):
        a, b = seg_range(v, i)
        top_c = {'vereda': (146, 144, 138), 'parking': (176, 177, 174), 'lane': (96, 98, 100), 'berma': (70, 104, 52)}[nm]
        pts = [(SX(v, a), SY(z0)), (SX(v, b), SY(z1)), (SX(v, b), SY(z1) + 8), (SX(v, a), SY(z0) + 8)]
        fill_color(cv, pts, top_c, 0.55)
    # linea de rasante
    prof = []
    for i, (nm, wd, z0, z1) in enumerate(segs):
        a, b = seg_range(v, i)
        prof += [(SX(v, a), SY(z0)), (SX(v, b), SY(z1))]
    line_px(cv, prof, (45, 47, 48), 3, 0.65)
    # juntas verticales entre elementos
    for i in range(len(segs) + 1):
        xm = v['xs'][i]
        zt = max(surf_z(v, xm - 1e-6) if i > 0 else -9, surf_z(v, xm + 1e-6) if i < len(segs) else -9)
        line_px(cv, [(SX(v, xm), SY(zt)), (SX(v, xm), SEC_BOT)], (52, 54, 55), 2.5, 0.55)
    # bordillos
    for i in range(1, len(segs)):
        n0, n1 = segs[i - 1][0], segs[i][0]
        if {n0, n1} <= {'lane', 'parking'}:
            continue
        if n0 == n1:
            continue
        xm = v['xs'][i]
        zt = max(surf_z(v, xm - 1e-6), surf_z(v, xm + 1e-6))
        cw = 0.15 if v is not VIAS[3] else 0.10
        # berma contra veredas/estac.: el bordillo queda dentro de la berma
        if 'berma' in (n0, n1) and 'vereda' not in (n0, n1) and v is VIAS[3]:
            cx0 = xm if n1 != 'berma' else xm
        pts = [(SX(v, xm - cw / 2), SY(zt)), (SX(v, xm + cw / 2), SY(zt)), (SX(v, xm + cw / 2), SY(-0.38)), (SX(v, xm - cw / 2), SY(-0.38))]
        fill_color(cv, pts, (198, 198, 194), 1.0)
        line_px(cv, pts + [pts[0]], (110, 110, 108), 1.6, 0.8, closed=True)
    # hierba en berma (flecos)
    rng = np.random.default_rng(5)
    for i, (nm, wd, z0, z1) in enumerate(segs):
        if nm != 'berma':
            continue
        a, b = seg_range(v, i)
        xa, xb = SX(v, a) + 8, SX(v, b) - 8
        for _ in range(int((xb - xa) * 0.9)):
            x = rng.uniform(xa, xb); y = SY(z0) - 2
            hh = rng.uniform(6, 15); lean = rng.uniform(-5, 5)
            c = nature._gcol(rng.uniform(0.35, 0.9))
            line_px(cv, [(x, y + 2), (x + lean * 0.4, y - hh * 0.55), (x + lean, y - hh)], c, 1.6, 0.95)
    # flechas de sentido en carriles (en el bloque seccionado, como el PDF)
    for i, (nm, wd, z0, z1) in enumerate(segs):
        if nm != 'lane':
            continue
        a, b = seg_range(v, i)
        d = lane_dir(v, i)
        cxp, cyp = SX(v, (a + b) / 2), SY(-2.3)
        ar = np.array([(0, 0.85), (0.46, 0.18), (0.17, 0.18), (0.17, -0.85), (-0.17, -0.85), (-0.17, 0.18), (-0.46, 0.18)])
        pts = [(cxp + x * S, cyp - z * S * (1 if d > 0 else -1)) for x, z in ar]
        fill_color(cv, pts, (240, 241, 238), 0.92)
    # ------------------------------------------------ entourage
    for (kind, xm, *args) in ent['elev']:
        zs = surf_z(v, xm)
        px, py = SX(v, xm), SY(zs)
        if kind == 'lamp':
            paste(cv, nature.lamp(7.1, 1.7), px, py, key=('lamp',))
    for (kind, xm, *args) in ent['elev']:
        zs = surf_z(v, xm)
        px, py = SX(v, xm), SY(zs)
        if kind == 'tree':
            cw, th, trh, seed = args
            paste(cv, nature.tree(cw, th, trh, seed=seed), px, py, key=('tree', cw, th, seed))
        elif kind == 'shrub':
            w_, h_, seed = args
            paste(cv, nature.shrub(w_, h_, seed), px, py, key=('shrub', w_, h_, seed))
        elif kind == 'tuft':
            w_, h_, seed = args
            paste(cv, nature.grass_tuft(h_, w_, seed), px, py, key=('tuft', w_, h_, seed))
    for (kind, xm, *args) in ent['elev']:
        zs = surf_z(v, xm)
        px, py = SX(v, xm), SY(zs)
        slope = (surf_z(v, xm + 0.3) - surf_z(v, xm - 0.3)) / 0.6
        rot = math.degrees(math.atan(slope)) * 1.0   # +: cae hacia la derecha -> rotacion horaria
        if kind == 'sedan':
            front, col = args
            paste(cv, elev.sedan(front, col), px, py, rot=rot, key=('sedan', front, col))
        elif kind == 'van':
            paste(cv, elev.van_rear(), px, py, rot=rot, key=('van',))
        elif kind == 'moto':
            paste(cv, elev.moto_front(), px, py, rot=rot, key=('moto',))
    for (kind, xm, *args) in ent['elev']:
        zs = surf_z(v, xm)
        px, py = SX(v, xm), SY(zs)
        if kind == 'person':
            face, phase, fem, bag, seed = args
            paste(cv, nature.person(phase=phase, female=fem, facing=face, bag=bag), px, py, key=('person', face, phase, fem, bag))

# ----------------------------------------------------------------- PLANTA
def PX(v, xm): return X0 + (xm + v['side']) * S
def PY(zz): return PLAN_TOP + zz * S

def draw_plan(cv, v, ent):
    L = v['L']
    clip = (X0, PLAN_TOP, X0 + PW, PLAN_BOT)
    xl, xr = int(PX(v, 0)), int(PX(v, L))
    hgt = PLAN_BOT - PLAN_TOP
    # edificaciones
    for (a, b, sd) in ((X0, xl, 14), (xr, X0 + PW, 15)):
        t = tex.building(hgt, b - a, sd) * 0.97
        gx = np.linspace(0, 1, b - a, dtype=np.float32)[None, :, None]
        if sd == 14:
            t = t * (1 - 0.16 * np.clip((gx - 0.88) / 0.12, 0, 1))
        else:
            t = t * (1 - 0.16 * np.clip((0.12 - gx) / 0.12, 0, 1))
        cv[PLAN_TOP:PLAN_BOT, a:b] = t
    segs = v['segs']
    for i, (nm, wd, z0, z1) in enumerate(segs):
        a, b = seg_range(v, i)
        xa, xb = int(round(PX(v, a))), int(round(PX(v, b)))
        sd = 40 + i
        if nm == 'vereda':
            t = tex.stone(hgt, xb - xa, sd, 46)
            # oclusion junto a la edificacion
            gx = np.linspace(0, 1, xb - xa, dtype=np.float32)[None, :, None]
            if i == 0:
                t = t * (1 - 0.20 * np.clip((0.18 - gx) / 0.18, 0, 1))
            else:
                t = t * (1 - 0.20 * np.clip((gx - 0.82) / 0.18, 0, 1))
        elif nm == 'parking':
            t = tex.concrete(hgt, xb - xa, sd, (204, 205, 202))
        elif nm == 'lane':
            t = tex.asphalt(hgt, xb - xa, sd)
            # huellas de neumaticos (sutiles)
            cxl = (xb - xa) / 2
            for off in (-0.85, 0.85):
                xx = int(cxl + off * S)
                if 0 < xx < xb - xa:
                    gx = np.exp(-((np.arange(xb - xa) - xx) / (0.28 * S)) ** 2)[None, :, None].astype(np.float32)
                    t = t * (1 - 0.10 * gx)
        else:
            t = tex.grass(hgt, xb - xa, sd, (92, 124, 70))
        cv[PLAN_TOP:PLAN_BOT, xa:xb] = t
    # juntas de dilatacion en concreto de estacionamiento
    for i, (nm, wd, z0, z1) in enumerate(segs):
        if nm != 'parking':
            continue
        a, b = seg_range(v, i)
        for zj in np.arange(ZC - 3.0 - 6 * 3, PLAN_LEN + 6, 3.0):
            if 0 <= zj <= PLAN_LEN:
                line_px(cv, [(PX(v, a), PY(zj)), (PX(v, b), PY(zj))], (150, 150, 146), 1.6, 0.55, clip=clip)
    # bordillos
    for i in range(1, len(segs)):
        n0, n1 = segs[i - 1][0], segs[i][0]
        if n0 == n1 or {n0, n1} <= {'lane', 'parking'}:
            continue
        xm = v['xs'][i]
        cw = 0.15 if v is not VIAS[3] else 0.10
        pts = [(PX(v, xm - cw / 2), PLAN_TOP), (PX(v, xm + cw / 2), PLAN_TOP), (PX(v, xm + cw / 2), PLAN_BOT), (PX(v, xm - cw / 2), PLAN_BOT)]
        fill_color(cv, pts, (200, 200, 196), 1.0, clip)
        line_px(cv, [(PX(v, xm - cw / 2), PLAN_TOP), (PX(v, xm - cw / 2), PLAN_BOT)], (120, 120, 118), 1.5, 0.8, clip=clip)
        line_px(cv, [(PX(v, xm + cw / 2), PLAN_TOP), (PX(v, xm + cw / 2), PLAN_BOT)], (120, 120, 118), 1.5, 0.8, clip=clip)
    # marcas viales
    W_ = (238, 239, 236); Y_ = (226, 188, 64)
    lanes = [i for i, s_ in enumerate(segs) if s_[0] == 'lane']
    for i in lanes:
        a, b = seg_range(v, i)
        # borde continuo junto a estacionamiento / berma
        for j, sgn in ((i - 1, a), (i + 1, b)):
            if 0 <= j < len(segs) and segs[j][0] in ('parking', 'berma'):
                off = 0.12 if segs[j][0] == 'parking' else 0.25
                xx = sgn + (off if sgn == a else -off)
                line_px(cv, [(PX(v, xx), PLAN_TOP), (PX(v, xx), PLAN_BOT)], W_, 0.11 * S, 0.92, clip=clip)
    # separacion entre carriles del mismo sentido (discontinua) / sentido opuesto (amarilla doble)
    for i in lanes:
        j = i + 1
        if j < len(segs) and segs[j][0] == 'lane':
            xm = v['xs'][j]
            if lane_dir(v, i) == lane_dir(v, j):
                z = ZC - 6.0 * 3
                while z < PLAN_LEN + 6:
                    z0_, z1_ = z, z + 3.0
                    if z1_ > 0 and z0_ < PLAN_LEN:
                        line_px(cv, [(PX(v, xm), PY(max(z0_, 0))), (PX(v, xm), PY(min(z1_, PLAN_LEN)))], W_, 0.10 * S, 0.92, clip=clip)
                    z += 6.0
            else:
                for off in (-0.09, 0.09):
                    line_px(cv, [(PX(v, xm + off), PLAN_TOP), (PX(v, xm + off), PLAN_BOT)], Y_, 0.09 * S, 0.95, clip=clip)
    # marcas de plaza de estacionamiento paralelo (T en extremos)
    for i, (nm, wd, z0, z1) in enumerate(segs):
        if nm != 'parking':
            continue
        a, b = seg_range(v, i)
        side_left = (a + b) / 2 < v['L'] / 2
        for zb in ent['stall_bounds'][0 if side_left else 1]:
            line_px(cv, [(PX(v, a + 0.18), PY(zb)), (PX(v, a + 0.18 + 0.7), PY(zb))], W_, 0.09 * S, 0.9, clip=clip)
            line_px(cv, [(PX(v, b - 0.18 - 0.7), PY(zb)), (PX(v, b - 0.18), PY(zb))], W_, 0.09 * S, 0.9, clip=clip)
    # flechas de sentido sobre el pavimento
    for i in lanes:
        a, b = seg_range(v, i)
        d = lane_dir(v, i)
        ar = np.array([(0, 0.85), (0.46, 0.18), (0.17, 0.18), (0.17, -0.85), (-0.17, -0.85), (-0.17, 0.18), (-0.46, 0.18)])
        for zz in ent['arrow_z']:
            pts = [(PX(v, (a + b) / 2) + x * S, PY(zz) - z * S * (1 if d > 0 else -1)) for x, z in ar]
            fill_color(cv, pts, W_, 0.9, clip)
    # ---------------- entourage
    for (kind, xm, zz, *args) in ent['plan']:
        px, py = PX(v, xm), PY(zz)
        if kind == 'bush':
            D, seed = args
            paste(cv, plan.bush_top(D, seed), px, py, clip=clip, key=('bush', D, seed))
        elif kind == 'tuftp':
            D, seed = args
            paste(cv, plan.bush_top(D, seed), px, py, clip=clip, key=('tuftp', D, seed))
    for (kind, xm, zz, *args) in ent['plan']:
        px, py = PX(v, xm), PY(zz)
        if kind == 'car':
            d, col, seed = args
            paste(cv, plan.car_top(col, d, seed=seed), px, py, clip=clip, key=('car', d, col))
        elif kind == 'van':
            paste(cv, plan.van_top(d=args[0]), px, py, clip=clip, key=('vant', args[0]))
        elif kind == 'moto':
            paste(cv, plan.moto_top(d=args[0]), px, py, clip=clip, key=('motot', args[0]))
    for (kind, xm, zz, *args) in ent['plan']:
        px, py = PX(v, xm), PY(zz)
        if kind == 'person':
            ang, seed = args
            paste(cv, plan.person_top(ang, seed), px, py, clip=clip, key=('pers', ang))
    for (kind, xm, zz, *args) in ent['plan']:
        px, py = PX(v, xm), PY(zz)
        if kind == 'tree':
            D, seed = args
            paste(cv, plan.tree_top(D, seed), px, py, clip=clip, key=('treet', D, seed))
    for (kind, xm, zz, *args) in ent['plan']:
        px, py = PX(v, xm), PY(zz)
        if kind == 'lamp':
            paste(cv, plan.lamp_top(1.7), px, py, clip=clip, key=('lampt',))
