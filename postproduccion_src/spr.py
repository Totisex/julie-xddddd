"""Mini motor de sprites RGBA (supersampling) para la postproduccion de cortes viales."""
import numpy as np, cv2, math

SHIFT = 4  # sub-pixel bits for cv2 AA polygons


def spline(pts, closed=True, n=14):
    """Catmull-Rom a traves de pts -> polilinea densa."""
    P = np.array(pts, float)
    m = len(P)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = P[(i - 1) % m] if (closed or i > 0) else P[i]
        p1 = P[i]
        p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if (closed or i + 2 < m) else P[(i + 1) % m]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return np.array(out)


def rrect_pts(x0, z0, x1, z1, r, n=8):
    r = min(r, (x1 - x0) / 2, (z1 - z0) / 2)
    pts = []
    for cx, cz, a0 in ((x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180), (x1 - r, z0 + r, 270)):
        for a in np.linspace(a0, a0 + 90, n):
            pts.append((cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a))))
    return np.array(pts)


def ellipse_pts(cx, cz, rx, rz, n=48):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([cx + rx * np.cos(a), cz + rz * np.sin(a)], 1)


def mix(c0, c1, t):
    return tuple(c0[i] * (1 - t) + c1[i] * t for i in range(3))


def shade(c, k):
    """k>0 aclara, k<0 oscurece."""
    c = np.array(c, float)
    if k >= 0:
        return tuple(c + (255 - c) * k)
    return tuple(c * (1 + k))


class Spr:
    """Lienzo RGBA premultiplicado. Coordenadas en metros: x derecha, z arriba, origen en (ox,oz) metros desde la esquina inferior izquierda."""

    def __init__(self, w, h, ox, oz, ppm=400):
        self.ppm, self.ox, self.oz = ppm, ox, oz
        self.W, self.H = int(round(w * ppm)), int(round(h * ppm))
        self.rgb = np.zeros((self.H, self.W, 3), np.float32)
        self.a = np.zeros((self.H, self.W), np.float32)

    def px(self, pts):
        p = np.asarray(pts, float)
        X = (p[:, 0] + self.ox) * self.ppm
        Y = self.H - (p[:, 1] + self.oz) * self.ppm
        return np.stack([X, Y], 1)

    def _roi(self, q, pad=2):
        x0 = max(0, int(q[:, 0].min()) - pad); x1 = min(self.W, int(q[:, 0].max()) + pad + 2)
        y0 = max(0, int(q[:, 1].min()) - pad); y1 = min(self.H, int(q[:, 1].max()) + pad + 2)
        return x0, y0, x1, y1

    def mask(self, pts):
        """mascara completa (gradientes / recortes)."""
        m = np.zeros((self.H, self.W), np.uint8)
        q = np.round(self.px(pts) * (1 << SHIFT)).astype(np.int32)
        cv2.fillPoly(m, [q], 255, lineType=cv2.LINE_AA, shift=SHIFT)
        return m.astype(np.float32) / 255.0

    def vgrad(self, c0, c1, z0, z1):
        ys = np.arange(self.H, dtype=np.float32)
        z = (self.H - ys) / self.ppm - self.oz
        t = np.clip((z - z0) / (z1 - z0), 0, 1)[:, None, None]
        return (np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t) * np.ones((1, self.W, 1), np.float32)

    def hgrad(self, c0, c1, x0, x1):
        xs = np.arange(self.W, dtype=np.float32)
        x = xs / self.ppm - self.ox
        t = np.clip((x - x0) / (x1 - x0), 0, 1)[None, :, None]
        return (np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t) * np.ones((self.H, 1, 1), np.float32)

    def _comp_roi(self, roi, m, col, alpha, clip):
        x0, y0, x1, y1 = roi
        if clip is not None:
            m = m * clip[y0:y1, x0:x1]
        m = (m * alpha).astype(np.float32)
        col = np.asarray(col, np.float32)
        if col.ndim == 3:
            col = col[y0:y1, x0:x1]
        else:
            col = col[None, None, :]
        r = self.rgb[y0:y1, x0:x1]
        self.rgb[y0:y1, x0:x1] = col * m[..., None] + r * (1 - m[..., None])
        a = self.a[y0:y1, x0:x1]
        self.a[y0:y1, x0:x1] = m + a * (1 - m)

    def comp(self, m, col, alpha=1.0, clip=None):
        self._comp_roi((0, 0, self.W, self.H), m, col, alpha, clip)

    def poly(self, pts, col, alpha=1.0, clip=None):
        q = self.px(pts)
        x0, y0, x1, y1 = self._roi(q)
        if x1 <= x0 or y1 <= y0:
            return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        qq = np.round((q - np.array([x0, y0])) * (1 << SHIFT)).astype(np.int32)
        cv2.fillPoly(m, [qq], 255, lineType=cv2.LINE_AA, shift=SHIFT)
        self._comp_roi((x0, y0, x1, y1), m.astype(np.float32) / 255.0, col, alpha, clip)

    def line(self, pts, col, w, alpha=1.0, closed=False, clip=None):
        q = self.px(pts)
        pad = int(w * self.ppm) + 3
        x0, y0, x1, y1 = self._roi(q, pad)
        if x1 <= x0 or y1 <= y0:
            return
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        qq = np.round((q - np.array([x0, y0])) * (1 << SHIFT)).astype(np.int32)
        cv2.polylines(m, [qq], closed, 255, max(1, int(round(w * self.ppm))), lineType=cv2.LINE_AA, shift=SHIFT)
        self._comp_roi((x0, y0, x1, y1), m.astype(np.float32) / 255.0, col, alpha, clip)

    def capsule(self, p0, p1, r0, r1, col, alpha=1.0, clip=None):
        a, b = np.array(p0, float), np.array(p1, float)
        d = b - a
        L = np.hypot(*d)
        if L < 1e-9:
            self.poly(ellipse_pts(a[0], a[1], r0, r0), col, alpha, clip)
            return
        pts = []
        ang = math.atan2(d[1], d[0])
        for t in np.linspace(ang + math.pi / 2, ang + 3 * math.pi / 2, 14):
            pts.append(a + r0 * np.array([math.cos(t), math.sin(t)]))
        for t in np.linspace(ang - math.pi / 2, ang + math.pi / 2, 14):
            pts.append(b + r1 * np.array([math.cos(t), math.sin(t)]))
        self.poly(np.array(pts), col, alpha, clip)

    def blur_shadow(self, m, sigma_m, col=(0, 0, 0), alpha=0.4, dx=0, dz=0):
        s = max(1.0, sigma_m * self.ppm)
        mm = cv2.GaussianBlur(m, (0, 0), s)
        M = np.float32([[1, 0, dx * self.ppm], [0, 1, -dz * self.ppm]])
        mm = cv2.warpAffine(mm, M, (self.W, self.H))
        self.comp(mm, col, alpha)

    def rgba_small(self, scale_to_ppm):
        """devuelve (rgb, a) reducidos a scale_to_ppm px/m (no premultiplicado -> premult)."""
        f = scale_to_ppm / self.ppm
        w, h = max(1, int(round(self.W * f))), max(1, int(round(self.H * f)))
        rgb = cv2.resize(self.rgb, (w, h), interpolation=cv2.INTER_AREA)
        a = cv2.resize(self.a, (w, h), interpolation=cv2.INTER_AREA)
        return rgb, a  # rgb premultiplicado por alpha local (ver comp)


def noise(h, w, scale, rng, octaves=3):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(1, int(scale / (2 ** o)))
        small = rng.random((h // s + 2, w // s + 2)).astype(np.float32)
        big = cv2.resize(small, (w + s, h + s), interpolation=cv2.INTER_CUBIC)[:h, :w]
        out += big * amp
        tot += amp
        amp *= 0.5
    return out / tot
