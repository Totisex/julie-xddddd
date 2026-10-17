"""Arboles, arbustos, personas, luminarias, aves (elevacion)."""
import numpy as np, cv2, math
from spr import *

PPM = 300
GREENS = [(36, 66, 38), (52, 88, 46), (72, 112, 56), (98, 138, 70), (128, 160, 88)]


def _gcol(t):
    """t en 0..1 -> verde interpolado."""
    t = float(np.clip(t, 0, 0.999)) * (len(GREENS) - 1)
    i = int(t)
    return mix(GREENS[i], GREENS[i + 1], t - i)


def _crown(s, cx, cz, rx, rz, rng, n=140, rmin=0.10, rmax=0.24, light=(-0.55, 0.75)):
    """Copa: nube de cumulos, luz desde arriba-izquierda, sin huecos."""
    env = s.mask(ellipse_pts(cx, cz, rx, rz, 60))
    s.comp(env, GREENS[0], 1.0)
    sc = (rx / 1.5 + 0.35)

    def bright(nx, nz, jit):
        return 0.42 + 0.42 * (light[0] * nx + light[1] * nz) + rng.uniform(-jit, jit)

    def clump(x, z, rr, nx, nz, clipm):
        t = bright(nx, nz, 0.14)
        base = _gcol(t)
        s.poly(ellipse_pts(x, z, rr, rr * 0.84, 18), shade(base, -0.30), 1.0, clip=clipm)
        s.poly(ellipse_pts(x - rr * 0.12, z + rr * 0.16, rr * 0.84, rr * 0.68, 18), base, 1.0, clip=clipm)
        s.poly(ellipse_pts(x - rr * 0.30, z + rr * 0.34, rr * 0.40, rr * 0.28, 14), shade(base, 0.20), 0.75, clip=clipm)

    # pasada 1: cumulos grandes de relleno (interior + borde)
    pts = []
    for _ in range(int(n * 1.3)):
        ang = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0.05, 1.0))
        pts.append((cx + rx * 0.95 * r * math.cos(ang), cz + rz * 0.95 * r * math.sin(ang)))
    pts.sort(key=lambda p: p[1])
    for (x, z) in pts:
        nx, nz = (x - cx) / rx, (z - cz) / rz
        clump(x, z, rng.uniform(rmin, rmax) * sc * 0.95, nx, nz, env)
    # pasada 2: luces pequenas en la mitad superior-izquierda
    for _ in range(int(n * 0.9)):
        ang = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0, 1))
        nx, nz = r * math.cos(ang), r * math.sin(ang)
        if nx * light[0] + nz * light[1] < -0.05:
            continue
        clump(cx + rx * 0.92 * nx, cz + rz * 0.92 * nz, rng.uniform(rmin * 0.5, rmax * 0.65) * sc, nx, nz, env)
    # contorno irregular
    for _ in range(int(n * 0.55)):
        ang = rng.uniform(0, 2 * math.pi)
        nx, nz = math.cos(ang), math.sin(ang)
        clump(cx + rx * 0.99 * nx, cz + rz * 0.99 * nz, rng.uniform(rmin * 0.6, rmax * 0.85) * sc, nx, nz, None)
    # sombra interior propia (parte baja-derecha)
    sh = s.mask(ellipse_pts(cx + rx * 0.35, cz - rz * 0.45, rx * 0.7, rz * 0.55, 40))
    sh = cv2.GaussianBlur(sh, (0, 0), 0.18 * s.ppm)
    s.comp(sh * (s.a > 0.5), (18, 36, 22), 0.30)
    # moteado fino (poco)
    for _ in range(260):
        ang = rng.uniform(0, 2 * math.pi); r = math.sqrt(rng.uniform(0, 1))
        nx, nz = r * math.cos(ang), r * math.sin(ang)
        d = rng.uniform(0.012, 0.026)
        t = bright(nx, nz, 0.2)
        s.poly(ellipse_pts(cx + rx * nx, cz + rz * nz, d, d, 8), shade(_gcol(t), rng.choice([-0.32, 0.22])), 0.55, clip=env)


def tree(crown_w, total_h, trunk_h, seed=0, lean=0.0, trunk_col=(92, 74, 58)):
    """Arbol de calle en elevacion. Origen: base del tronco."""
    rng = np.random.default_rng(seed)
    W = crown_w + 0.8
    s = Spr(W, total_h + 0.7, W / 2, 0.1, PPM)
    ch = total_h - trunk_h
    cx, cz = lean, trunk_h + ch / 2
    # tronco con ramas
    tw0, tw1 = 0.075 + crown_w * 0.012, 0.045
    tr = np.array([(-tw0, 0), (tw0, 0), (tw1 + lean * 0.05, trunk_h + ch * 0.45), (-tw1 + lean * 0.05, trunk_h + ch * 0.45)])
    mt = s.mask(tr)
    s.comp(mt, s.hgrad(shade(trunk_col, 0.18), shade(trunk_col, -0.35), -tw0, tw0))
    s.line([(0, trunk_h * 0.75), (-crown_w * 0.18, trunk_h + ch * 0.55)], shade(trunk_col, -0.1), 0.035)
    s.line([(0, trunk_h * 0.8), (crown_w * 0.2, trunk_h + ch * 0.6)], shade(trunk_col, -0.2), 0.03)
    _crown(s, cx, cz, crown_w / 2, ch / 2, rng, n=int(110 * crown_w + 60))
    # sombra del follaje sobre el tronco
    return s


def shrub(w, h, seed=0, tint=0):
    rng = np.random.default_rng(seed)
    s = Spr(w + 0.4, h + 0.4, (w + 0.4) / 2, 0.05, PPM)
    _crown(s, 0, h / 2, w / 2, h / 2, rng, n=int(40 * w * 3 + 20), rmin=0.07, rmax=0.16)
    return s


def grass_tuft(h=0.5, w=0.5, seed=0):
    rng = np.random.default_rng(seed)
    s = Spr(w + 0.1, h + 0.1, (w + 0.1) / 2, 0.02, PPM)
    for _ in range(int(60 * w + 18)):
        x0 = rng.uniform(-w / 2, w / 2) * 0.7
        top = (x0 + rng.uniform(-0.18, 0.18) * w, rng.uniform(0.5, 1.0) * h)
        mid = (x0 + (top[0] - x0) * 0.4 + rng.uniform(-0.05, 0.05), top[1] * 0.55)
        c = GREENS[rng.integers(1, 5)]
        s.line(spline([(x0, 0), mid, top], False, 8), c, rng.uniform(0.012, 0.022), alpha=0.95)
    return s


def person(h=1.72, phase=0.0, female=False, facing=1, col=(34, 37, 40), bag=False, seed=0):
    """Silueta peatonal en perfil caminando. Origen: pie base."""
    s = Spr(1.2, h + 0.2, 0.6, 0.05, PPM)
    f = facing
    k = h / 1.72
    hip, sh = (0.0, 0.94 * k), (0.02 * f, 1.46 * k)
    # piernas (fase de zancada)
    st = 0.17 * k * math.cos(phase)
    def leg(sg, back):
        knee = (hip[0] + sg * 0.5 * st * f + (0.02 * f if sg > 0 else 0), 0.52 * k)
        foot = (hip[0] + sg * st * f, 0.04 * k)
        s.capsule(hip, knee, 0.075 * k, 0.055 * k, shade(col, -0.2 if back else 0))
        s.capsule(knee, foot, 0.055 * k, 0.04 * k, shade(col, -0.2 if back else 0))
        s.capsule(foot, (foot[0] + 0.12 * f, foot[1] - 0.005), 0.035 * k, 0.03 * k, shade(col, -0.2 if back else 0))
    leg(-1, True)
    # torso
    if female:
        s.poly(np.array([(-0.13, 1.47), (0.15, 1.47), (0.21, 0.72), (-0.19, 0.72), (-0.11, 1.0)]) * np.array([1, k]) * np.array([f, 1]) + np.array([0.02 * f, 0]), col)
    else:
        torso = [(-0.14, 1.46), (0.16, 1.46), (0.15, 1.2), (0.13, 0.93), (-0.12, 0.93), (-0.15, 1.2)]
        s.poly(spline(np.array(torso) * np.array([f, k]), True, 6), col)
    leg(1, False)
    # brazos
    sw = 0.13 * k * math.cos(phase)
    s.capsule(sh, (sh[0] - sw * f * 0.5 - 0.02 * f, 1.18 * k), 0.052 * k, 0.045 * k, shade(col, -0.18))
    s.capsule((sh[0] - sw * f * 0.5 - 0.02 * f, 1.18 * k), (sh[0] - sw * f - 0.02 * f, 0.93 * k), 0.045 * k, 0.04 * k, shade(col, -0.18))
    s.capsule(sh, (sh[0] + sw * f * 0.5, 1.18 * k), 0.055 * k, 0.047 * k, col)
    s.capsule((sh[0] + sw * f * 0.5, 1.18 * k), (sh[0] + sw * f, 0.94 * k), 0.047 * k, 0.04 * k, col)
    # cuello + cabeza
    s.capsule((0.03 * f, 1.48 * k), (0.04 * f, 1.55 * k), 0.04 * k, 0.04 * k, col)
    s.poly(ellipse_pts(0.045 * f, 1.62 * k, 0.095 * k, 0.11 * k, 24), col)
    if female:
        s.poly(spline(np.array([(-0.06, 1.70), (0.08, 1.72), (0.03, 1.50), (-0.1, 1.5)]) * np.array([f, k]) + np.array([0.0, 0]), True, 6), shade(col, 0.05))
    if bag:
        s.poly(rrect_pts(-0.05 * f - 0.09, 0.84 * k, -0.05 * f + 0.09, 1.04 * k, 0.03), shade(col, 0.15))
    # gradiente suave para volumen
    m = (s.a > 0.5).astype(np.float32)
    s.comp(m * 1.0, s.vgrad((0, 0, 0), (255, 255, 255), 0.0, h), 0.10)
    return s


def lamp(h=7.2, arm=1.7, col=(92, 98, 104)):
    """Luminaria de doble brazo (elevacion). Origen: base del poste."""
    s = Spr(2 * arm + 1.0, h + 0.8, arm + 0.5, 0.05, PPM)
    top = h
    pole = [(-0.085, 0), (0.085, 0), (0.05, top), (-0.05, top)]
    mp = s.mask(pole)
    s.comp(mp, s.hgrad(shade(col, 0.28), shade(col, -0.30), -0.085, 0.085))
    s.poly(rrect_pts(-0.14, 0, 0.14, 0.30, 0.03), shade(col, -0.1))
    s.poly(rrect_pts(-0.11, 0.30, 0.11, 0.42, 0.03), shade(col, -0.05))
    for sg in (-1, 1):
        curve = spline([(0, top - 0.25), (0.22 * sg, top + 0.28), (0.85 * sg, top + 0.36), (arm * sg - 0.30 * sg, top + 0.20)], False, 10)
        s.line(curve, shade(col, -0.05), 0.07)
        head = spline([(arm * sg - 0.55 * sg, top + 0.26), (arm * sg + 0.20 * sg, top + 0.25), (arm * sg + 0.34 * sg, top + 0.14),
                       (arm * sg + 0.10 * sg, top + 0.06), (arm * sg - 0.55 * sg, top + 0.14)], True, 6)
        mh = s.mask(head)
        s.comp(mh, s.vgrad(shade(col, -0.35), shade(col, 0.15), top + 0.06, top + 0.27))
        s.poly([(arm * sg - 0.50 * sg, top + 0.14), (arm * sg + 0.06 * sg, top + 0.14), (arm * sg + 0.1 * sg, top + 0.07), (arm * sg - 0.45 * sg, top + 0.07)], (235, 238, 225), 0.85, clip=mh)
    return s


def bird(sz=0.45, wing=0.5, col=(70, 76, 82)):
    s = Spr(sz * 2.2, sz * 1.0, sz * 1.1, sz * 0.5, 300)
    p = spline([(-sz, 0.0), (-sz * 0.55, sz * 0.32 * wing * 2), (-sz * 0.12, sz * 0.08), (0, 0), (sz * 0.12, sz * 0.08), (sz * 0.55, sz * 0.32 * wing * 2), (sz, 0.0)], False, 8)
    s.line(p, col, sz * 0.09, alpha=0.9)
    s.poly(ellipse_pts(0, 0.0, sz * 0.07, sz * 0.05, 10), col)
    return s
