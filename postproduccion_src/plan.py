"""Sprites en vista superior (planta). Luz desde arriba-izquierda; z+ = arriba de la lamina."""
import numpy as np, cv2, math
from spr import *
from nature import _crown, _gcol, GREENS

PPM = 300


def _profile(half, d):
    L, R = [], []
    for z, w in half:
        L.append((-w, z * d)); R.append((w, z * d))
    pts = L + R[::-1]
    return spline(pts, True, 8)


def car_top(body=(38, 42, 46), d=1, length=4.6, width=1.8, seed=0):
    """d=+1 frente hacia arriba, d=-1 frente hacia abajo."""
    pad = 0.9
    s = Spr(width + 2 * pad, length + 2 * pad, (width + 2 * pad) / 2, (length + 2 * pad) / 2, PPM)
    hw = width / 2
    k = hw / 0.90
    half = [(-2.30, 0.58 * k), (-2.20, 0.74 * k), (-1.95, 0.85 * k), (-1.30, 0.90 * k), (0.2, 0.91 * k), (1.1, 0.89 * k), (1.75, 0.84 * k), (2.12, 0.74 * k), (2.30, 0.54 * k)]
    half = [(z * length / 4.6, w) for z, w in half]
    Z = lambda z: z * d * length / 4.6
    sil = _profile([(z / (length / 4.6) * (length / 4.6), w) for z, w in half], d)
    # sombra
    msil = s.mask(sil)
    s.blur_shadow(msil, 0.07, alpha=0.42, dx=0.14, dz=-0.14)
    # ruedas
    for zz in (-1.45, 1.45):
        for sx in (-1, 1):
            a, b = sorted((sx * (hw - 0.07), sx * (hw + 0.04)))
            s.poly(rrect_pts(a, Z(zz) - 0.33, b, Z(zz) + 0.33, 0.05), (14, 14, 16))
    top, bot = shade(body, 0.20), shade(body, -0.28)
    s.comp(msil, s.vgrad(bot, top, -2.3, 2.3))
    s.comp(msil, s.hgrad((255, 255, 255), (0, 0, 0), -hw, hw), 0.0)
    # sombreado lateral (derecha mas oscura)
    s.comp(msil, s.hgrad((0, 0, 0), (0, 0, 0), -hw, hw), 0.0)
    shr = s.mask(rrect_pts(hw * 0.35, -2.2, hw + 0.2, 2.2, 0.2))
    s.comp(shr, (0, 0, 0), 0.18, clip=msil)
    # capot y maletero
    hood = spline([(-0.62 * k, Z(1.05)), (0.62 * k, Z(1.05)), (0.58 * k, Z(2.0)), (0.0, Z(2.12)), (-0.58 * k, Z(2.0))], True, 8)
    s.poly(hood, shade(body, 0.28), 0.35, clip=msil)
    s.line(hood, shade(body, -0.55), 0.012, closed=True, alpha=0.55, clip=msil)
    trunk = spline([(-0.56 * k, Z(-1.2)), (0.56 * k, Z(-1.2)), (0.52 * k, Z(-2.08)), (-0.52 * k, Z(-2.08))], True, 6)
    s.poly(trunk, shade(body, 0.2), 0.30, clip=msil)
    s.line(trunk, shade(body, -0.55), 0.012, closed=True, alpha=0.5, clip=msil)
    # cabina: parabrisas, luneta, techo, ventanas laterales
    ws = spline([(-0.66 * k, Z(0.55)), (0.66 * k, Z(0.55)), (0.60 * k, Z(1.08)), (-0.60 * k, Z(1.08))], True, 6)
    mw = s.mask(ws)
    s.comp(mw, s.vgrad((24, 32, 42), (92, 112, 128), -2.3, 2.3) if d > 0 else s.vgrad((92, 112, 128), (24, 32, 42), -2.3, 2.3))
    s.poly([(-0.5 * k, Z(0.62)), (-0.25 * k, Z(0.62)), (-0.15 * k, Z(1.04)), (-0.42 * k, Z(1.04))], (255, 255, 255), 0.16, clip=mw)
    rw = spline([(-0.60 * k, Z(-0.85)), (0.60 * k, Z(-0.85)), (0.55 * k, Z(-1.28)), (-0.55 * k, Z(-1.28))], True, 6)
    mr = s.mask(rw)
    s.comp(mr, (28, 36, 46))
    s.poly([(0.1 * k, Z(-0.9)), (0.35 * k, Z(-0.9)), (0.28 * k, Z(-1.24)), (0.06 * k, Z(-1.24))], (255, 255, 255), 0.10, clip=mr)
    # vidrios laterales
    for sx in (-1, 1):
        s.poly([(sx * 0.62 * k, Z(0.5)), (sx * 0.74 * k, Z(0.5)), (sx * 0.74 * k, Z(-0.85)), (sx * 0.62 * k, Z(-0.85))], (26, 34, 44), 0.9)
    roof = rrect_pts(-0.62 * k, min(Z(-0.85), Z(0.55)), 0.62 * k, max(Z(-0.85), Z(0.55)), 0.10)
    mroof = s.mask(roof)
    s.comp(mroof, s.hgrad(shade(body, 0.34), shade(body, -0.06), -0.62 * k, 0.62 * k))
    s.line(roof, shade(body, -0.6), 0.010, closed=True, alpha=0.55)
    # espejos
    for sx in (-1, 1):
        a, b = sorted((sx * (hw - 0.02), sx * (hw + 0.14)))
        s.poly(rrect_pts(a, Z(0.62) - 0.07, b, Z(0.62) + 0.07, 0.04), shade(body, -0.1))
    # luces
    for sx in (-1, 1):
        s.poly(spline([(sx * 0.42 * k, Z(2.10)), (sx * 0.76 * k, Z(1.95)), (sx * 0.80 * k, Z(1.80)), (sx * 0.52 * k, Z(2.02))], True, 6), (236, 238, 232), 0.95, clip=msil)
        s.poly(spline([(sx * 0.46 * k, Z(-2.20)), (sx * 0.80 * k, Z(-2.08)), (sx * 0.80 * k, Z(-1.92)), (sx * 0.54 * k, Z(-2.10))], True, 6), (190, 28, 34), 0.95, clip=msil)
    s.line(sil, shade(body, -0.75), 0.012, closed=True, alpha=0.6)
    return s


def van_top(body=(228, 230, 231), d=1):
    length, width = 5.3, 2.0
    pad = 0.9
    s = Spr(width + 2 * pad, length + 2 * pad, (width + 2 * pad) / 2, (length + 2 * pad) / 2, PPM)
    hw = width / 2
    Z = lambda z: z * d
    sil = rrect_pts(-hw, -length / 2, hw, length / 2, 0.30, 10)
    sil = np.array([(x, Z(z)) for x, z in sil])
    m = s.mask(sil)
    s.blur_shadow(m, 0.08, alpha=0.42, dx=0.16, dz=-0.16)
    for zz in (-1.75, 1.6):
        for sx in (-1, 1):
            a, b = sorted((sx * (hw - 0.08), sx * (hw + 0.04)))
            s.poly(rrect_pts(a, Z(zz) - 0.36, b, Z(zz) + 0.36, 0.05), (14, 14, 16))
    s.comp(m, s.vgrad(shade(body, -0.12), shade(body, 0.08), -2.7, 2.7))
    s.comp(s.mask(rrect_pts(hw * 0.4, -3, hw + 0.2, 3, 0.2)), (0, 0, 0), 0.14, clip=m)
    # parabrisas
    ws = [(-0.88, Z(1.55)), (0.88, Z(1.55)), (0.80, Z(2.30)), (-0.80, Z(2.30))]
    mw = s.mask(ws)
    s.comp(mw, (36, 46, 58))
    s.poly([(-0.6, Z(1.6)), (-0.25, Z(1.6)), (-0.16, Z(2.25)), (-0.5, Z(2.25))], (255, 255, 255), 0.14, clip=mw)
    # nervaduras de techo
    for zz in np.linspace(-2.3, 1.3, 6):
        s.line([(-0.82, Z(zz)), (0.82, Z(zz))], shade(body, -0.28), 0.02, alpha=0.55, clip=m)
    s.line([(0, Z(-2.5)), (0, Z(1.4))], shade(body, -0.3), 0.012, alpha=0.5, clip=m)
    for sx in (-1, 1):
        a, b = sorted((sx * (hw - 0.02), sx * (hw + 0.17)))
        s.poly(rrect_pts(a, Z(1.62) - 0.08, b, Z(1.62) + 0.08, 0.04), shade(body, -0.3))
    s.poly(spline([(-0.8, Z(2.62)), (-0.45, Z(2.66)), (-0.5, Z(2.55))], True, 4), (236, 238, 232), 0.9, clip=m)
    s.poly(spline([(0.8, Z(2.62)), (0.45, Z(2.66)), (0.5, Z(2.55))], True, 4), (236, 238, 232), 0.9, clip=m)
    s.line(sil, shade(body, -0.65), 0.012, closed=True, alpha=0.55)
    return s


def moto_top(body=(34, 36, 40), d=1):
    length, width = 2.1, 0.85
    pad = 0.6
    s = Spr(width + 2 * pad, length + 2 * pad, (width + 2 * pad) / 2, (length + 2 * pad) / 2, PPM)
    Z = lambda z: z * d
    def blur_obj(draw):
        pass
    # sombra aproximada
    sh = s.mask(spline([(-0.12, Z(-1.0)), (0.12, Z(-1.0)), (0.30, Z(0.1)), (0.12, Z(1.0)), (-0.12, Z(1.0)), (-0.30, Z(0.1))], True, 6))
    s.blur_shadow(sh, 0.05, alpha=0.4, dx=0.10, dz=-0.10)
    # ruedas
    for zz in (-0.72, 0.78):
        s.poly(rrect_pts(-0.06, Z(zz) - 0.36, 0.06, Z(zz) + 0.36, 0.05), (14, 14, 16))
    # guardabarros
    s.poly(rrect_pts(-0.10, Z(0.55), 0.10, Z(1.0), 0.08), (60, 62, 68))
    # cuerpo
    for pts, col in ((spline([(-0.18, Z(0.6)), (0.18, Z(0.6)), (0.22, Z(0.1)), (0.14, Z(-0.2)), (-0.14, Z(-0.2)), (-0.22, Z(0.1))], True, 8), shade(body, 0.1)),
                     (spline([(-0.15, Z(-0.2)), (0.15, Z(-0.2)), (0.12, Z(-0.8)), (-0.12, Z(-0.8))], True, 8), shade(body, -0.25))):
        m = s.mask(pts)
        s.comp(m, s.hgrad(shade(col, 0.30), shade(col, -0.25), -0.2, 0.2))
    s.poly(spline([(-0.07, Z(0.5)), (-0.02, Z(0.5)), (-0.05, Z(0.15))], True, 4), (255, 255, 255), 0.25)
    # manillar y espejos
    s.line([(-0.40, Z(0.72)), (-0.10, Z(0.66)), (0.10, Z(0.66)), (0.40, Z(0.72))], (22, 24, 28), 0.04)
    for sx in (-1, 1):
        s.poly(ellipse_pts(sx * 0.38, Z(0.92), 0.05, 0.03), (60, 64, 70))
        s.line([(sx * 0.34, Z(0.70)), (sx * 0.38, Z(0.90))], (140, 145, 150), 0.012)
    s.poly(ellipse_pts(0, Z(0.95), 0.09, 0.07), (220, 224, 226))
    return s


def tree_top(D, seed=0, shadow=True):
    rng = np.random.default_rng(seed)
    pad = 1.9
    s = Spr(D + 2 * pad, D + 2 * pad, (D + 2 * pad) / 2, (D + 2 * pad) / 2, PPM)
    env = s.mask(ellipse_pts(0, 0, D / 2, D / 2, 60))
    if shadow:
        s.blur_shadow(env, 0.30, alpha=0.30, dx=0.85, dz=-0.85)
    _crown(s, 0, 0, D / 2, D / 2, rng, n=int(85 * D + 40), rmin=0.11, rmax=0.26, light=(-0.55, 0.75))
    # tono de copa en vista cenital: algo mas claro al centro
    c = s.mask(ellipse_pts(-0.15 * D / 2, 0.15 * D / 2, D * 0.28, D * 0.28, 40))
    c = cv2.GaussianBlur(c, (0, 0), D * 0.1 * s.ppm)
    s.comp(c, (150, 178, 100), 0.20, clip=env)
    return s


def bush_top(D, seed=0):
    rng = np.random.default_rng(seed)
    pad = 0.7
    s = Spr(D + 2 * pad, D + 2 * pad, (D + 2 * pad) / 2, (D + 2 * pad) / 2, PPM)
    env = s.mask(ellipse_pts(0, 0, D / 2, D / 2, 40))
    s.blur_shadow(env, 0.10, alpha=0.30, dx=0.20, dz=-0.20)
    _crown(s, 0, 0, D / 2, D / 2, rng, n=int(40 * D + 10), rmin=0.08, rmax=0.17)
    return s


def rot(pts, ang):
    c, sn = math.cos(ang), math.sin(ang)
    P = np.asarray(pts, float)
    return np.stack([P[:, 0] * c - P[:, 1] * sn, P[:, 0] * sn + P[:, 1] * c], 1)


def person_top(ang=0.0, seed=0, col=(30, 33, 36), k=1.25):
    """Peaton visto desde arriba; ang=0 camina hacia +z."""
    s = Spr(1.8, 1.8, 0.9, 0.9, PPM)
    R = lambda pts: rot(np.asarray(pts, float) * k, ang)
    sh = s.mask(R(ellipse_pts(0, 0, 0.30, 0.17, 28)))
    s.blur_shadow(sh, 0.05, alpha=0.42, dx=0.14, dz=-0.14)
    for sx, zz in ((-0.10, 0.17), (0.10, -0.15)):
        s.poly(R(rrect_pts(sx - 0.055, zz - 0.15, sx + 0.055, zz + 0.15, 0.045)), shade(col, -0.25))
    for sx, zz in ((-1, -0.10), (1, 0.12)):
        s.capsule(tuple(R([(sx * 0.215, 0.0)])[0]), tuple(R([(sx * 0.27, zz)])[0]), 0.050 * k, 0.042 * k, shade(col, 0.10))
    m = s.mask(R(rrect_pts(-0.25, -0.125, 0.25, 0.125, 0.11, 8)))
    s.comp(m, s.hgrad(shade(col, 0.28), shade(col, -0.10), -0.3 * k, 0.3 * k))
    s.line(R(rrect_pts(-0.25, -0.125, 0.25, 0.125, 0.11, 8)), shade(col, 0.55), 0.012, closed=True, alpha=0.5)
    s.poly(R(ellipse_pts(0, 0.015, 0.105, 0.115, 20)), (58, 50, 46))
    s.poly(R(ellipse_pts(-0.025, 0.04, 0.05, 0.05, 14)), (104, 94, 88), 0.55)
    return s


def lamp_top(arm=1.7, col=(92, 98, 104)):
    """Luminaria doble brazo en planta (brazos en x)."""
    pad = 0.6
    s = Spr(2 * arm + 2 * pad + 1.0, 1.6, arm + pad + 0.5, 0.8, PPM)
    # sombra del poste/brazos (larga, hacia abajo-derecha)
    s.line([(0, 0), (4.2, -4.2)], (0, 0, 0), 0.12, alpha=0.10)
    s.line([(-arm, 0), (arm, 0)], (0, 0, 0), 0.09, alpha=0.0)
    s.line([(-arm, 0.0), (arm, 0.0)], shade(col, -0.1), 0.07)
    for sg in (-1, 1):
        s.poly(rrect_pts(arm * sg - 0.33 if sg > 0 else arm * sg * 1.0 - 0.33, -0.15, (arm * sg + 0.33) if sg > 0 else (arm * sg + 0.33), 0.15, 0.08)
               if sg > 0 else rrect_pts(-arm - 0.33, -0.15, -arm + 0.33, 0.15, 0.08), shade(col, 0.1))
        s.poly(rrect_pts(arm * sg - 0.20, -0.09, arm * sg + 0.20, 0.09, 0.05), (236, 240, 226), 0.9)
    s.poly(ellipse_pts(0, 0, 0.14, 0.14, 20), shade(col, 0.25))
    s.poly(ellipse_pts(-0.03, 0.03, 0.06, 0.06, 12), shade(col, 0.55), 0.8)
    return s
