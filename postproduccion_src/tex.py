"""Texturas de materiales (float32 RGB)."""
import numpy as np, cv2
from scipy.spatial import Voronoi
from spr import noise

STONE = [(178, 175, 168), (162, 160, 154), (192, 188, 178), (150, 148, 144), (170, 164, 150), (184, 182, 176)]
JOINT = (92, 92, 90)


def _grain(h, w, rng, amp, scale=2):
    return (rng.random((h, w)).astype(np.float32) - 0.5) * 2 * amp


def stone(h, w, seed=0, cell=48):
    """laja irregular (celdas de Voronoi)"""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.float32)
    img[:] = JOINT
    pts = []
    ny, nx = h // cell + 4, w // cell + 4
    for j in range(-2, ny):
        for i in range(-2, nx):
            pts.append((i * cell + rng.uniform(-0.38, 0.38) * cell + cell / 2, j * cell + rng.uniform(-0.38, 0.38) * cell + cell / 2))
    pts = np.array(pts)
    vor = Voronoi(pts)
    for pi, ri in enumerate(vor.point_region):
        reg = vor.regions[ri]
        if -1 in reg or len(reg) < 3:
            continue
        poly = vor.vertices[reg]
        c = poly.mean(0)
        # contraer para dejar junta
        poly = c + (poly - c) * (1 - 2.0 / cell * 1.6)
        if poly[:, 0].max() < 0 or poly[:, 0].min() > w or poly[:, 1].max() < 0 or poly[:, 1].min() > h:
            continue
        base = np.array(STONE[rng.integers(0, len(STONE))], np.float32) * rng.uniform(0.93, 1.06)
        cv2.fillConvexPoly(img, np.round(poly * 8).astype(np.int32), tuple(float(v) for v in base), lineType=cv2.LINE_AA, shift=3)
    n1 = noise(h, w, 22, rng, 3)
    n2 = noise(h, w, 5, rng, 2)
    img *= (0.93 + 0.12 * n1 + 0.06 * n2)[..., None]
    img += _grain(h, w, rng, 4)[..., None]
    return img


def asphalt(h, w, seed=1, tracks=None, ppm=100):
    rng = np.random.default_rng(seed)
    base = np.array((74, 76, 78), np.float32)
    n1 = noise(h, w, 60, rng, 3)
    n2 = noise(h, w, 6, rng, 2)
    g = (rng.random((h, w)).astype(np.float32) - 0.5)
    img = base[None, None, :] * (0.92 + 0.14 * n1 + 0.07 * n2)[..., None] + (g * 16)[..., None]
    return img


def concrete(h, w, seed=2, base=(203, 204, 201)):
    rng = np.random.default_rng(seed)
    n1 = noise(h, w, 90, rng, 3)
    n2 = noise(h, w, 8, rng, 2)
    g = (rng.random((h, w)).astype(np.float32) - 0.5)
    return np.array(base, np.float32)[None, None, :] * (0.95 + 0.08 * n1 + 0.03 * n2)[..., None] + (g * 7)[..., None]


def grass(h, w, seed=3, base=(88, 128, 64)):
    rng = np.random.default_rng(seed)
    n1 = noise(h, w, 40, rng, 3)
    n2 = noise(h, w, 7, rng, 3)
    g = (rng.random((h, w)).astype(np.float32) - 0.5)
    img = np.array(base, np.float32)[None, None, :] * (0.82 + 0.28 * n1 + 0.12 * n2)[..., None]
    img[..., 0] += g * 14; img[..., 1] += g * 22; img[..., 2] += g * 8
    return img


def building(h, w, seed=4):
    rng = np.random.default_rng(seed)
    n1 = noise(h, w, 260, rng, 3)
    n2 = noise(h, w, 14, rng, 3)
    g = (rng.random((h, w)).astype(np.float32) - 0.5)
    base = np.array((196, 198, 196), np.float32)
    img = base[None, None, :] * (0.955 + 0.07 * n1 + 0.035 * n2)[..., None] + (g * 7)[..., None]
    return img
