import sys, math, time
sys.path.insert(0, '.')
from scene import *

CH = (38, 42, 46); SILV = (176, 180, 184); WHT = (226, 228, 229); NAVY = (34, 52, 84); RED = (96, 30, 36); BLK = (22, 24, 26); TAUPE = (120, 112, 100)
Z = ZC

def lamp_e(x): return ('lamp', x)

ENT = {}
# ---------------------------------------------------------------- VIA 01
ENT[1] = dict(
    birds=[(0.38, 0.35, 0.5), (0.43, 0.15, 0.42), (0.47, 0.5, 0.38), (0.53, 0.25, 0.46), (0.57, 0.62, 0.34), (0.62, 0.12, 0.4), (0.33, 0.7, 0.32)],
    elev=[('lamp', 2.05), ('lamp', 27.95),
          ('shrub', 13.95, 0.9, 0.85, 3), ('shrub', 16.05, 0.8, 0.7, 4), ('tuft', 14.6, 0.55, 0.45, 1), ('tuft', 15.5, 0.5, 0.4, 2),
          ('tree', 15.0, 2.9, 4.25, 1.3, 7),
          ('sedan', 4.6, True, CH), ('sedan', 8.45, True, SILV), ('moto', 11.75), ('sedan', 18.25, False, NAVY), ('van', 21.55),
          ('person', 0.8, 1, 0.25, False, False, 1), ('person', 29.1, -1, 2.9, False, True, 2)],
    stall_bounds=([Z - 9, Z - 3, Z + 3, Z + 9], [Z - 6, Z, Z + 6, Z + 12]),
    arrow_z=[Z + 4.9],
    plan=[('car', 4.6, Z, -1, CH, 1), ('car', 4.6, Z - 6, -1, WHT, 2), ('car', 4.6, Z + 6, -1, RED, 3),
          ('car', 25.4, Z - 3, 1, TAUPE, 4), ('car', 25.4, Z + 3, 1, BLK, 5),
          ('car', 8.45, Z, -1, SILV, 6), ('moto', 11.75, Z, -1), ('car', 18.25, Z, 1, NAVY, 7), ('van', 21.55, Z - 0.3, 1),
          ('bush', 13.95, Z, 0.9, 1), ('bush', 16.05, Z, 0.85, 2), ('bush', 15.0, Z - 3.25, 1.2, 3), ('bush', 15.0, Z + 3.25, 1.2, 4), ('bush', 14.1, Z + 6.5, 0.9, 5), ('bush', 15.9, Z - 6.5, 0.9, 6),
          ('person', 0.8, Z, 0.0, 1), ('person', 1.1, Z + 3.4, math.pi, 2), ('person', 29.1, Z, math.pi, 3), ('person', 28.7, Z - 3.1, 0.0, 4),
          ('lamp', 2.05, Z + 3.8), ('lamp', 27.95, Z - 3.6),
          ('tree', 15.0, Z, 2.9, 11), ('tree', 15.0, Z - 6.5, 2.9, 12), ('tree', 15.0, Z + 6.5, 2.9, 13)])
# ---------------------------------------------------------------- VIA 02
ENT[2] = dict(
    birds=[(0.36, 0.3, 0.5), (0.42, 0.12, 0.42), (0.46, 0.55, 0.36), (0.55, 0.22, 0.46), (0.6, 0.6, 0.34), (0.64, 0.1, 0.4)],
    elev=[('lamp', 2.05), ('lamp', 22.95),
          ('tree', 12.5, 2.4, 4.4, 2.2, 21),
          ('sedan', 3.9, True, CH), ('moto', 7.05), ('sedan', 10.35, True, NAVY), ('sedan', 14.65, False, SILV), ('sedan', 21.1, False, WHT),
          ('person', 1.54, 1, 0.3, True, False, 3), ('person', 23.3, -1, 2.8, False, False, 4), ('person', 24.4, -1, 0.5, True, False, 5)],
    stall_bounds=([Z - 9, Z - 3, Z + 3, Z + 9], [Z - 9, Z - 3, Z + 3, Z + 9]),
    arrow_z=[Z + 4.9],
    plan=[('car', 3.9, Z, -1, CH, 1), ('car', 3.9, Z - 6, -1, WHT, 2), ('car', 3.9, Z + 6, -1, TAUPE, 3),
          ('car', 21.1, Z, 1, WHT, 4), ('car', 21.1, Z - 6, 1, BLK, 5), ('car', 21.1, Z + 6, 1, SILV, 6),
          ('moto', 7.05, Z, -1), ('car', 10.35, Z, -1, NAVY, 7), ('car', 14.65, Z, 1, SILV, 8),
          ('bush', 12.5, Z - 3.25, 0.7, 1), ('bush', 12.5, Z + 3.25, 0.7, 2),
          ('person', 1.54, Z, 0.0, 1), ('person', 1.0, Z + 3.5, math.pi, 2), ('person', 23.3, Z, math.pi, 3), ('person', 24.4, Z + 0.4, math.pi, 4),
          ('lamp', 2.05, Z + 3.8), ('lamp', 22.95, Z - 3.6),
          ('tree', 12.5, Z, 2.4, 21), ('tree', 12.5, Z - 6.5, 2.4, 22), ('tree', 12.5, Z + 6.5, 2.4, 23)])
# ---------------------------------------------------------------- VIA 03
ENT[3] = dict(
    birds=[(0.4, 0.3, 0.5), (0.45, 0.12, 0.42), (0.5, 0.5, 0.36), (0.57, 0.2, 0.46), (0.6, 0.6, 0.34)],
    elev=[('lamp', 1.65), ('lamp', 14.35),
          ('tree', 2.3, 2.0, 2.75, 1.0, 31), ('tree', 13.7, 3.2, 4.25, 1.5, 32),
          ('moto', 3.8), ('sedan', 6.5, True, SILV), ('sedan', 9.5, False, NAVY),
          ('person', 1.0, 1, 0.3, False, True, 6), ('person', 15.2, -1, 2.8, True, False, 7)],
    stall_bounds=([Z - 6.5, Z - 2.0, Z + 2.0, Z + 6.5], [Z - 9, Z - 3, Z + 3, Z + 9]),
    arrow_z=[Z + 4.9],
    plan=[('moto', 3.8, Z, -1), ('car', 3.8, Z - 4.4, -1, CH, 1), ('car', 3.8, Z + 4.4, -1, WHT, 2),
          ('car', 12.2, Z - 3, 1, TAUPE, 3), ('car', 12.2, Z + 3, 1, BLK, 4),
          ('car', 6.5, Z, -1, SILV, 5), ('car', 9.5, Z, 1, NAVY, 6),
          ('person', 0.8, Z + 0.9, 0.0, 1), ('person', 0.9, Z + 3.9, math.pi, 2), ('person', 15.5, Z + 1.6, math.pi, 3), ('person', 15.2, Z - 2.4, 0.0, 4),
          ('lamp', 1.65, Z + 3.4), ('lamp', 14.35, Z - 3.4),
          ('tree', 2.3, Z, 2.0, 31), ('tree', 2.3, Z - 6.5, 2.0, 33), ('tree', 2.3, Z + 6.5, 2.0, 34),
          ('tree', 13.7, Z, 3.2, 32), ('tree', 13.7, Z - 6.5, 3.2, 35), ('tree', 13.7, Z + 6.5, 3.2, 36)])


# ---------------------------------------------------------------- textos / cotas
def spaced(d, xy, text, fnt, fill, sp=0.0, anchor='m'):
    w = sum(d.textlength(c, font=fnt) for c in text) + sp * (len(text) - 1)
    x, y = xy
    if anchor == 'm':
        x -= w / 2
    elif anchor == 'r':
        x -= w
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill, anchor='ls')
        x += d.textlength(c, font=fnt) + sp
    return w


def draw_band(img, v, vid):
    d = ImageDraw.Draw(img, 'RGBA')
    d.rectangle([X0, BAND_TOP, X0 + PW, BAND_TOP + BAND_H], fill=(233, 235, 235))
    yc = BAND_TOP + 105
    f_val, f_lab, f_tot = font(30, semi=True), font(23), font(36, bold=True)
    ink = (58, 62, 66)
    xs = v['xs']
    # guias tenues desde el corte
    for xm in xs:
        d.line([(SX(v, xm), BAND_TOP), (SX(v, xm), yc - 18)], fill=(200, 203, 203), width=2)
    d.line([(SX(v, 0), yc), (SX(v, v['L']), yc)], fill=ink, width=3)
    for xm in xs:
        x = SX(v, xm)
        d.line([(x, yc - 20), (x, yc + 20)], fill=ink, width=3)
        d.line([(x - 9, yc + 9), (x + 9, yc - 9)], fill=ink, width=4)
    for i, (nm, w, z0, z1) in enumerate(v['segs']):
        cx = (SX(v, xs[i]) + SX(v, xs[i + 1])) / 2
        if w < 0.9:   # tramos muy angostos: valor escalonado hacia arriba con guia
            d.text((cx, yc - 58), f'{w:.2f}', font=f_val, fill=ink, anchor='ms')
            d.line([(cx, yc - 50), (cx, yc - 20)], fill=(120, 124, 128), width=2)
        else:
            d.text((cx, yc - 14), f'{w:.2f}', font=f_val, fill=ink, anchor='ms')
        for k, line in enumerate(v['labels'][i].split('\n')):
            spaced(d, (cx, yc + 52 + k * 31), line, f_lab, (84, 88, 92), 1.6)
    yt = BAND_TOP + 268
    d.line([(SX(v, 0), yt), (SX(v, v['L']), yt)], fill=ink, width=3)
    for xm in (0, v['L']):
        x = SX(v, xm)
        d.line([(x, yt - 24), (x, yt + 24)], fill=ink, width=3)
        d.line([(x - 9, yt + 9), (x + 9, yt - 9)], fill=ink, width=4)
    d.text(((SX(v, 0) + SX(v, v['L'])) / 2, yt - 14), f"{v['L']:.2f}", font=f_tot, fill=ink, anchor='ms')


def draw_text(img, v, vid):
    d = ImageDraw.Draw(img, 'RGBA')
    ink = (30, 34, 38)
    spaced(d, (X0, 150), f'CORTE VIAL {vid:02d}  /  VISTA EN PLANTA', font(82, bold=True), ink, 1.5, 'l')
    d.text((X0, 215), v['sub'], font=font(33), fill=(104, 108, 112), anchor='ls')
    spaced(d, (X0 + PW, 150), 'PROPUESTA', font(76, bold=True), (66, 122, 98), 3.0, 'r')
    # propiedad de terceros
    ft = font(46)
    for (xa, xb) in ((X0, SX(v, 0)), (SX(v, v['L']), X0 + PW)):
        cx = (xa + xb) / 2
        for ycen in ((SY(BLD_H) + SY(0)) / 2 - 30, (PLAN_TOP + PLAN_BOT) / 2):
            d.text((cx, ycen), 'Propiedad', font=ft, fill=(128, 131, 129), anchor='ms')
            d.text((cx, ycen + 56), 'de terceros', font=ft, fill=(128, 131, 129), anchor='ms')
    # rotulos de area
    fl = font(26, semi=True)
    spaced(d, (X0 + 30, SEC_TOP + 54), 'CORTE', fl, (255, 255, 255, 235), 4, 'l') if False else None
    # pie de planta
    yb = PLAN_BOT + 58
    d.text((X0, yb), 'VISTA EN PLANTA  ·  tramo ilustrativo: el PDF original no define la longitud de la vía, por lo que no se asignan cotas longitudinales',
           font=font(28), fill=(110, 114, 118), anchor='ls')
    # escala grafica (exacta: 100 px = 1 m)
    sx0 = X0 + PW - 1000
    for k in range(2):
        d.rectangle([sx0 + k * 500, yb - 22, sx0 + (k + 1) * 500, yb - 8], fill=(50, 54, 58) if k == 0 else (255, 255, 255), outline=(50, 54, 58), width=2)
    for k, t in enumerate(['0', '5', '10 m']):
        d.text((sx0 + k * 500, yb + 26), t, font=font(24), fill=(80, 84, 88), anchor='ms')
    d.text((sx0 - 24, yb - 8), 'ESCALA', font=font(22), fill=(110, 114, 118), anchor='rs')
    # marco fino de paneles
    d.rectangle([X0, SEC_TOP, X0 + PW, SEC_BOT], outline=(205, 208, 208), width=2)
    d.rectangle([X0, PLAN_TOP, X0 + PW, PLAN_BOT], outline=(205, 208, 208), width=2)


def build(vid, out):
    t = time.time()
    v = VIAS[vid]; ent = ENT[vid]
    cv = np.full((SH, SW, 3), 255, np.float32)
    # birds: convertir a coordenadas
    ent = dict(ent)
    ent['birds'] = [(fx, fy * 0.65, sz) for fx, fy, sz in ent['birds']]
    draw_section(cv, v, ent)
    draw_plan(cv, v, ent)
    img = Image.fromarray(np.clip(cv, 0, 255).astype(np.uint8))
    draw_band(img, v, vid)
    draw_text(img, v, vid)
    img.save(out, dpi=(300, 300), optimize=True)
    print(out, img.size, round(time.time() - t, 1), 's')


if __name__ == '__main__':
    ids = [int(a) for a in sys.argv[1:]] or [1, 2, 3]
    for i in ids:
        build(i, f'out_via{i}.png')
