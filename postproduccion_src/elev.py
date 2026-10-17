"""Sprites en elevacion (vista frontal/posterior) para el corte vial."""
import numpy as np, cv2, math
from spr import *

PPM = 400
GLASS_T, GLASS_B = (74, 92, 106), (22, 30, 38)


def sedan(front=True, body=(38, 42, 46), seed=0):
    """Sedan 1.80 x 1.43 m visto de frente o de atras. Origen: centro, suelo."""
    s = Spr(2.3, 1.7, 1.15, 0.12, PPM)
    top, bot = shade(body, 0.30), shade(body, -0.35)
    # sombra de contacto
    sh = s.mask(ellipse_pts(0, -0.02, 0.95, 0.07))
    s.blur_shadow(sh, 0.04, alpha=0.55)
    # neumaticos
    for sx in (-1, 1):
        s.poly(rrect_pts(sx * 0.62 if sx > 0 else -0.87, 0.0, 0.87 if sx > 0 else -0.62, 0.52, 0.07), (18, 18, 20))
        s.poly(rrect_pts(sx * 0.70 if sx > 0 else -0.80, 0.0, 0.80 if sx > 0 else -0.70, 0.30, 0.03), (40, 40, 44), 0.5)
    # silueta carroceria
    sil = spline([(-0.86, 0.19), (-0.90, 0.40), (-0.91, 0.72), (-0.87, 0.90), (-0.76, 0.97), (-0.70, 1.03), (-0.62, 1.27),
                  (-0.50, 1.40), (0.0, 1.43), (0.50, 1.40), (0.62, 1.27), (0.70, 1.03), (0.76, 0.97), (0.87, 0.90),
                  (0.91, 0.72), (0.90, 0.40), (0.86, 0.19), (0.0, 0.15)], True, 12)
    msil = s.mask(sil)
    s.comp(msil, s.vgrad(bot, top, 0.15, 1.40))
    # reflejo de cielo en capot/techo
    s.comp(s.mask(spline([(-0.80, 0.86), (-0.7, 0.95), (0.7, 0.95), (0.80, 0.86), (0.0, 0.83)], True, 8)), (255, 255, 255), 0.16, clip=msil)
    # parabrisas / luneta
    if front:
        g = spline([(-0.60, 1.00), (-0.50, 1.29), (0.50, 1.29), (0.60, 1.00), (0.0, 0.985)], True, 8)
    else:
        g = spline([(-0.56, 1.03), (-0.46, 1.27), (0.46, 1.27), (0.56, 1.03), (0.0, 1.015)], True, 8)
    mg = s.mask(g)
    s.comp(mg, s.vgrad(GLASS_B, GLASS_T, 1.0, 1.29))
    s.comp(s.mask([(-0.45, 1.27), (-0.18, 1.27), (-0.38, 1.02), (-0.57, 1.02)]), (255, 255, 255), 0.13, clip=mg)
    s.comp(s.mask([(0.05, 1.27), (0.12, 1.27), (-0.08, 1.02), (-0.15, 1.02)]), (255, 255, 255), 0.07, clip=mg)
    # montantes + techo
    s.line(g, shade(body, -0.5), 0.025, closed=True, alpha=0.7)
    # espejos
    for sx in (-1, 1):
        s.poly(rrect_pts(0.84 * sx - (0.0 if sx > 0 else 0.15), 0.98, 0.84 * sx + (0.15 if sx > 0 else 0.0), 1.09, 0.04), shade(body, -0.15))
        s.poly(rrect_pts(0.88 * sx - (0.0 if sx > 0 else 0.10), 1.0, 0.88 * sx + (0.10 if sx > 0 else 0.0), 1.07, 0.03), (28, 34, 40), 0.7)
    if front:
        # faros
        for sx in (-1, 1):
            hp = spline([(0.44 * sx, 0.67), (0.84 * sx, 0.73), (0.86 * sx, 0.79), (0.62 * sx, 0.815), (0.44 * sx, 0.765)], True, 8)
            mh = s.mask(hp)
            s.comp(mh, s.vgrad((118, 124, 130), (206, 211, 214), 0.66, 0.82))
            s.line(hp, (20, 22, 25), 0.016, closed=True, alpha=0.95)
            s.poly(ellipse_pts(0.64 * sx, 0.735, 0.042, 0.034), (22, 25, 30))
            s.poly(ellipse_pts(0.64 * sx, 0.735, 0.018, 0.014), (150, 160, 170))
            s.poly(rrect_pts(0.76 * sx - 0.03, 0.685, 0.76 * sx + 0.03, 0.70, 0.01), (225, 170, 70), 0.85)
            # antiniebla
            s.poly(ellipse_pts(0.62 * sx, 0.36, 0.085, 0.045), (22, 24, 28))
            s.poly(ellipse_pts(0.62 * sx, 0.36, 0.045, 0.022), (190, 196, 200), 0.8)
        # parrilla
        gr = [(-0.40, 0.61), (0.40, 0.61), (0.36, 0.76), (-0.36, 0.76)]
        s.poly(gr, (14, 15, 17))
        for zz in np.linspace(0.63, 0.74, 4):
            s.line([(-0.37, zz), (0.37, zz)], (70, 74, 80), 0.008, alpha=0.8)
        s.line([(-0.37, 0.775), (0.37, 0.775)], (200, 204, 208), 0.022, alpha=0.95)
        s.poly(ellipse_pts(0, 0.69, 0.045, 0.04), (190, 195, 200))
        # toma inferior
        s.poly(spline([(-0.60, 0.27), (0.60, 0.27), (0.52, 0.47), (-0.52, 0.47)], True, 6), (12, 13, 15), 0.95)
        s.line([(-0.50, 0.45), (0.50, 0.45)], (80, 84, 90), 0.01, alpha=0.7)
        # placa
        s.poly(rrect_pts(-0.26, 0.31, 0.26, 0.43, 0.012), (232, 232, 224))
        s.line([(-0.22, 0.37), (0.22, 0.37)], (60, 60, 70), 0.035, alpha=0.7)
    else:
        # luces traseras
        for sx in (-1, 1):
            tp = spline([(0.42 * sx, 0.70), (0.85 * sx, 0.74), (0.88 * sx, 0.90), (0.60 * sx, 0.88), (0.44 * sx, 0.82)], True, 8)
            mt = s.mask(tp)
            s.comp(mt, s.vgrad((120, 12, 18), (205, 35, 38), 0.66, 0.90))
            s.line(tp, (50, 8, 10), 0.012, closed=True, alpha=0.9)
            s.poly(rrect_pts(min(0.5 * sx, 0.7 * sx), 0.72, max(0.5 * sx, 0.7 * sx), 0.755, 0.01), (235, 235, 235), 0.7)
        # maletero / junta
        s.line([(-0.44, 0.69), (0.44, 0.69)], shade(body, -0.55), 0.012, alpha=0.8)
        s.poly(rrect_pts(-0.30, 0.52, 0.30, 0.64, 0.012), shade(body, -0.5), 0.35)
        s.poly(rrect_pts(-0.26, 0.54, 0.26, 0.64, 0.012), (232, 232, 224))
        s.line([(-0.22, 0.59), (0.22, 0.59)], (60, 60, 70), 0.035, alpha=0.7)
        # parachoques
        s.poly(spline([(-0.62, 0.22), (0.62, 0.22), (0.58, 0.34), (-0.58, 0.34)], True, 6), (16, 17, 19), 0.9)
        for sx in (-1, 1):
            s.poly(ellipse_pts(0.68 * sx, 0.40, 0.04, 0.025), (190, 40, 40), 0.8)
        s.poly(rrect_pts(-0.12, 0.20, 0.12, 0.26, 0.02), (60, 62, 66))
    # linea de cintura / brillo lateral
    s.line([(-0.86, 0.60), (-0.88, 0.40)], (255, 255, 255), 0.02, alpha=0.18)
    s.line([(0.86, 0.60), (0.88, 0.40)], (0, 0, 0), 0.02, alpha=0.20)
    # oclusion en parte baja
    s.comp(s.mask([(-0.95, 0.0), (0.95, 0.0), (0.95, 0.24), (-0.95, 0.24)]), s.vgrad((0, 0, 0), (0, 0, 0), 0, 1), 0.28, clip=msil)
    # contorno
    s.line(sil, shade(body, -0.7), 0.012, closed=True, alpha=0.55)
    return s


def van_rear(body=(228, 230, 231)):
    s = Spr(2.6, 2.9, 1.3, 0.12, PPM)
    sh = s.mask(ellipse_pts(0, -0.02, 1.0, 0.08)); s.blur_shadow(sh, 0.045, alpha=0.55)
    for sx in (-1, 1):
        a, b = (0.62, 0.90) if sx > 0 else (-0.90, -0.62)
        s.poly(rrect_pts(a, 0, b, 0.62, 0.07), (18, 18, 20))
        s.poly(rrect_pts((a + b) / 2 - 0.05, 0, (a + b) / 2 + 0.05, 0.30, 0.03), (42, 42, 46), 0.5)
    sil = spline([(-0.90, 0.32), (-0.96, 0.60), (-0.97, 1.40), (-0.95, 2.05), (-0.90, 2.38), (-0.78, 2.52), (0, 2.55),
                  (0.78, 2.52), (0.90, 2.38), (0.95, 2.05), (0.97, 1.40), (0.96, 0.60), (0.90, 0.32), (0, 0.28)], True, 12)
    ms = s.mask(sil)
    s.comp(ms, s.hgrad(shade(body, -0.18), shade(body, 0.04), -0.97, 0.97))
    s.comp(ms, s.vgrad((60, 70, 85), (255, 255, 255), 0.3, 2.55), 0.0)
    s.comp(s.mask([(-0.9, 2.3), (0.9, 2.3), (0.78, 2.52), (-0.78, 2.52)]), (255, 255, 255), 0.22, clip=ms)
    # ventanas puertas traseras
    for sx in (-1, 1):
        a, b = (0.05, 0.80) if sx > 0 else (-0.80, -0.05)
        w = rrect_pts(a, 1.40, b, 2.12, 0.07)
        mw = s.mask(w)
        s.comp(mw, s.vgrad(GLASS_B, GLASS_T, 1.4, 2.12))
        s.comp(s.mask([(a + 0.05, 2.1), (a + 0.28, 2.1), (a + 0.12, 1.45), (a - 0.02, 1.45)]), (255, 255, 255), 0.12, clip=mw)
        s.line(w, (40, 44, 48), 0.014, closed=True, alpha=0.7)
    # junta de puertas y manijas
    s.line([(0, 0.62), (0, 2.5)], shade(body, -0.5), 0.014, alpha=0.8)
    s.poly(rrect_pts(0.08, 1.15, 0.22, 1.20, 0.01), (60, 62, 66)); s.poly(rrect_pts(-0.22, 1.15, -0.08, 1.20, 0.01), (60, 62, 66))
    # luces
    for sx in (-1, 1):
        a, b = (0.80, 0.95) if sx > 0 else (-0.95, -0.80)
        s.poly(rrect_pts(a, 0.78, b, 1.50, 0.04), s.vgrad((130, 14, 20), (210, 38, 40), 0.78, 1.5))
    # parachoques + placa
    s.poly(rrect_pts(-0.96, 0.28, 0.96, 0.66, 0.07), (46, 48, 52))
    s.comp(s.mask(rrect_pts(-0.96, 0.50, 0.96, 0.66, 0.05)), (255, 255, 255), 0.12, clip=ms)
    s.poly(rrect_pts(-0.27, 0.70, 0.27, 0.83, 0.012), (232, 232, 224))
    s.line([(-0.22, 0.765), (0.22, 0.765)], (60, 60, 70), 0.04, alpha=0.7)
    # espejos
    for sx in (-1, 1):
        a, b = (0.98, 1.20) if sx > 0 else (-1.20, -0.98)
        s.poly(rrect_pts(a, 1.45, b, 1.95, 0.07), shade(body, -0.3))
        s.poly(rrect_pts(a + 0.03 * (1 if sx > 0 else -1), 1.52, b - 0.03 * (1 if sx > 0 else -1), 1.88, 0.05), (30, 36, 42), 0.8)
    s.comp(s.mask([(-1, 0), (1, 0), (1, 0.4), (-1, 0.4)]), (0, 0, 0), 0.2, clip=ms)
    s.line(sil, shade(body, -0.6), 0.012, closed=True, alpha=0.5)
    return s


def moto_front(body=(34, 36, 40)):
    s = Spr(1.5, 1.5, 0.75, 0.05, PPM)
    sh = s.mask(ellipse_pts(0, -0.01, 0.35, 0.04)); s.blur_shadow(sh, 0.025, alpha=0.55)
    dark = (20, 21, 23)
    # neumatico delantero
    s.poly(rrect_pts(-0.065, 0.0, 0.065, 0.64, 0.05), (14, 14, 16))
    s.line([(-0.03, 0.02), (-0.03, 0.6)], (60, 60, 64), 0.01, alpha=0.6)
    # tenedores
    for sx in (-1, 1):
        s.capsule((0.11 * sx, 0.22), (0.12 * sx, 0.98), 0.018, 0.022, (150, 155, 160))
        s.capsule((0.11 * sx, 0.22), (0.115 * sx, 0.60), 0.026, 0.028, (92, 96, 102))
    # guardabarros
    s.poly(spline([(-0.12, 0.58), (-0.10, 0.70), (0.10, 0.70), (0.12, 0.58), (0, 0.55)], True, 8), (50, 52, 58))
    # motor/cilindros
    for sx in (-1, 1):
        s.poly(rrect_pts(0.17 * sx - (0.0 if sx > 0 else 0.20), 0.30, 0.17 * sx + (0.20 if sx > 0 else 0.0), 0.62, 0.05), (88, 92, 98))
        for zz in np.linspace(0.35, 0.58, 5):
            s.line([(0.17 * sx, zz), (0.37 * sx, zz)], (40, 42, 46), 0.01, alpha=0.7)
    s.poly(rrect_pts(-0.16, 0.20, 0.16, 0.52, 0.04), (30, 32, 36))
    # tanque
    tk = spline([(-0.22, 0.86), (-0.28, 0.98), (-0.20, 1.10), (0.20, 1.10), (0.28, 0.98), (0.22, 0.86), (0, 0.80)], True, 8)
    mt = s.mask(tk)
    s.comp(mt, s.vgrad(shade(body, -0.35), shade(body, 0.35), 0.80, 1.10))
    s.comp(s.mask([(-0.12, 1.08), (-0.04, 1.08), (-0.10, 0.90), (-0.18, 0.92)]), (255, 255, 255), 0.22, clip=mt)
    # faro
    s.poly(ellipse_pts(0, 0.88, 0.115, 0.115), (70, 74, 80))
    s.poly(ellipse_pts(0, 0.88, 0.095, 0.095), (210, 216, 220))
    s.poly(ellipse_pts(-0.02, 0.90, 0.045, 0.045), (255, 255, 255), 0.7)
    s.line(ellipse_pts(0, 0.88, 0.115, 0.115), (30, 32, 36), 0.012, closed=True)
    # manillar + espejos
    s.line([(-0.40, 1.12), (-0.10, 1.10), (0.10, 1.10), (0.40, 1.12)], (30, 32, 36), 0.028)
    for sx in (-1, 1):
        s.capsule((0.40 * sx, 1.12), (0.46 * sx, 1.12), 0.024, 0.024, (14, 14, 16))
        s.line([(0.33 * sx, 1.13), (0.40 * sx, 1.36)], (150, 155, 160), 0.012)
        s.poly(ellipse_pts(0.41 * sx, 1.39, 0.06, 0.035), (60, 64, 70))
        s.poly(ellipse_pts(0.41 * sx, 1.39, 0.045, 0.022), (170, 190, 205), 0.8)
        s.poly(rrect_pts(0.30 * sx - 0.03, 0.74, 0.30 * sx + 0.03, 0.98, 0.02), (24, 26, 30)) if False else None
    # intermitentes
    for sx in (-1, 1):
        s.poly(ellipse_pts(0.22 * sx, 0.84, 0.03, 0.03), (230, 160, 60), 0.9)
    return s
