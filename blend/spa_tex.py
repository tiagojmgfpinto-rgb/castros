# Castro de São Paio: textures for blend/dio_spa.py (numpy only, no Blender), so they can be tested on their own.
# ground(): the orthophoto (0.25 m) is used as a map of surface classes and as the low-frequency colour; the fine detail at the
# texture's 5 cm is procedural per class (grass, succulent/heather scrub, dry grass/earth, sand, granite, pavement), so the
# ground stays sharp close up and no car, parasol or building shadow of the satellite image is painted on it.
# Tiles: granite (rock faces, triplanar UVs), ashlar (chapel walls), roof tiles, weathered boardwalk planks, gravel, dark planks.
import numpy as np
from scipy.ndimage import gaussian_filter, median_filter, binary_dilation, binary_opening, binary_closing, zoom, map_coordinates


def _noise(shape, sigma, rng):
    n = gaussian_filter(rng.normal(0, 1, shape), sigma, mode='wrap'); return n / (n.std() + 1e-9)


def fbm(shape, sigmas, amps, rng):
    return sum(a * _noise(shape, s, rng) for s, a in zip(sigmas, amps))


def lowpass(img, sigma):
    return np.stack([gaussian_filter(img[..., k], sigma) for k in range(img.shape[-1])], -1)


def classify(O, H, sea, relief):
    """O: orthophoto RGB float (0.25 m grid), H: ground height, relief: H - smoothed H. Returns a dict of boolean masks."""
    mx = O.max(2); mn = O.min(2); sat = (mx - mn) / (mx + 1); r, g, b = O[..., 0], O[..., 1], O[..., 2]
    lum = O.mean(2)
    SEA = H < sea + .05
    SAND = (mx > 160) & (sat < .32) & (r >= b) & (H < 8) & ~SEA
    rough = gaussian_filter(np.abs(H - gaussian_filter(H, 2)), 2)          # beach sand is smooth; surf foam lies on rough rock
    FOAM = (mx > 175) & (sat < .25) & (H < 7) & (rough > .1) & ~SEA
    FOAM = binary_dilation(binary_opening(FOAM, iterations=1), iterations=2) & ~SEA
    SAND = SAND & ~FOAM
    SAND = binary_closing(binary_opening(SAND, iterations=2), iterations=3) & ~SEA & ~FOAM
    ROCK = (((relief > .35) & (H < 12)) | ((sat < .17) & (mx < 155) & (H < 9))) & (H > sea + .1) & ~SAND
    ROCK = binary_opening(ROCK, iterations=1) | (FOAM & (H > sea + .1))
    PAVED = (sat < .1) & (mx > 170) & (H > 3) & ~SAND & ~FOAM
    PAVED = binary_closing(binary_opening(PAVED, iterations=2), iterations=4)
    from scipy.ndimage import label as _lab
    lb, nl = _lab(~PAVED); sz = np.bincount(lb.ravel()); small = (sz < 480); small[0] = False
    PAVED |= small[lb] & (H > 3)                    # cars and their shadows inside the car parks and on the roads
    WATER = SEA | ((H < 1.3) & ((b > r + 6) | ((mx > 185) & (sat < .2))))   # waves and foam the LiDAR puts just above the sea
    WATER = binary_closing(WATER, iterations=2) & (H < 1.6)
    # surf: the LiDAR also caught the breaking waves up to 2-3 m above the sea; white, smooth, next to the water
    from scipy.ndimage import distance_transform_edt as _edt
    _d = _edt(~WATER) * .25; _rgh = gaussian_filter(np.abs(H - gaussian_filter(H, 2)), 2)
    SURF = (mx > 165) & (sat < .14) & (_d < 10) & (H < 3) & (_rgh < .06)
    from scipy.ndimage import label as _lb2
    _l, _n = _lb2(WATER | SURF); _keep = np.zeros(_n + 1, bool); _keep[np.unique(_l[WATER])] = True; _keep[0] = False
    SURF = SURF & _keep[_l] & (_d < 6) & (H < 2.5)        # only surf joined to the water (white lichen or flat rock tops stay rock)
    WATER = binary_closing(WATER | SURF, iterations=2) & (H < 2.5)
    SEA = SEA | WATER
    SAND &= ~SEA; ROCK &= ~SEA; PAVED &= ~SEA; FOAM &= ~SEA
    GREEN = (g > r + 4) & (g > b + 4) & ~(SEA | SAND | ROCK | PAVED)
    VIOLET = (b > g + 2) & (r > g - 6) & ~(SEA | SAND | ROCK | PAVED | GREEN)
    EARTH = ~(SEA | SAND | ROCK | PAVED | GREEN | VIOLET)
    return dict(FOAM=FOAM, WATER=WATER, SEA=SEA, SAND=SAND, ROCK=ROCK, PAVED=PAVED, GREEN=GREEN, VIOLET=VIOLET, EARTH=EARTH, lum=lum)


def clean_ortho(O, dark_near):
    """Paint over the dark building shadows (dark_near: boolean mask of shadow candidates) with the surrounding colour."""
    import cv2
    m = (dark_near & (O.mean(2) < 85)).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    out = cv2.inpaint(np.clip(O, 0, 255).astype(np.uint8), m, 5, cv2.INPAINT_TELEA)
    return out.astype(float)


def ground(sample, TS, R, classes_at, rng, sea_col=(38, 66, 72), hgt=None, sea=.3):
    """sample(x, y) -> orthophoto RGB at disc coordinates; classes_at(x, y) -> dict of class weights (0..1) on the texture grid.
    hgt(x, y) -> ground altitude (m): crevices, ridges and the tide zone of the shore rocks.
    Returns the TS×TS RGB texture of the disc (row 0 = north)."""
    mpp = 2 * R / TS
    jj, ii = np.mgrid[0:TS, 0:TS]; GX = (ii + .5) * mpp - R; GY = R - (jj + .5) * mpp
    W = classes_at(GX, GY)                       # soft masks, already upsampled
    base = sample(GX, GY)                        # bilinear orthophoto colour
    lo = lowpass(base, .6 / mpp)                 # 0.6 m: removes the 25 cm pixels and the jpeg blocks
    lo2 = lowpass(base, 2.2 / mpp)               # 2 m: sand and pavement (no parasols, people or cars)
    sh = (TS, TS)
    n_f = _noise(sh, .6, rng); n_m = _noise(sh, 2.5, rng); n_c = _noise(sh, 7, rng); n_p = _noise(sh, 14, rng)
    out = np.zeros((TS, TS, 3))
    # grass (fields, lawns): ortho tone + blade speckle (5-15 cm) + mown/tussock patches
    gr = lo * (1 + .10 * n_f[..., None] + .06 * n_m[..., None] + .05 * n_c[..., None])
    gr += (np.clip(n_f - 1.6, 0, None) * 18)[..., None] * np.array([.6, 1, .3])
    # succulent / heather scrub (the violet of the orthophoto: Carpobrotus in flower, heather): toned to green and red-brown, clumps
    v = lo.copy(); g_ = v.mean(-1, keepdims=True)
    v = g_ + (v - g_) * .45                                                          # halve the saturation of the violet
    clump = np.clip(n_c * .8 + n_m * .4, -2, 2)
    green_s = np.array([86, 112, 58]); red_s = np.array([122, 88, 72]); dry = np.array([150, 132, 104])
    mixc = np.where(clump[..., None] > .3, green_s, np.where(clump[..., None] < -.6, red_s, dry))
    v = v * .55 + mixc * .45
    v *= (1 + .12 * n_f[..., None] + .08 * n_m[..., None])
    # dry grass / bare earth / paths: ortho tone + grain + straw streaks
    e = lo * (1 + .08 * n_f[..., None] + .05 * n_m[..., None] + .04 * n_c[..., None])
    st = gaussian_filter(rng.normal(0, 1, sh), (.4, 2.5)); st /= st.std(); e += (np.clip(st - 1.4, 0, None) * 14)[..., None]
    # sand: very smooth, light ripples
    s = lo2 * (1 + .03 * n_f[..., None] + .02 * n_m[..., None])
    # granite: ortho tone desaturated, black and white mica speckle, lichen patches
    gk = lo.mean(-1, keepdims=True); rk = (gk * .88 + lo * .12) * np.array([1.02, 1.0, .95])
    rk *= (1 + .07 * n_m[..., None] + .06 * n_c[..., None])
    sp = rng.random(sh); rk[sp > .99] *= 1.2; rk[sp < .008] *= .8
    lich = np.clip(n_c - 1.1, 0, None)[..., None]; rk = rk * (1 - .25 * lich) + np.array([150, 150, 120]) * .25 * lich
    if hgt is not None:
        # shore granite as it looks on the photographs: grey-ochre rock (half the orthophoto tone, half granite grey), dark joints and
        # crevices, light rounded tops; black-brown wet rock and seaweed in the tide zone; orange and grey-green lichen on the tops
        Hg = hgt(GX, GY)
        cav = Hg - gaussian_filter(Hg, .35 / mpp); cav2 = Hg - gaussian_filter(Hg, 1.2 / mpp)
        rk = (gk * .5 + lo * .5) * .5 + np.array([150, 146, 136]) * .5
        rk *= (1 + .07 * n_m[..., None] + .06 * n_c[..., None])
        sp = rng.random(sh); rk[sp > .985] *= 1.22; rk[sp < .012] *= .72
        crev = np.clip(-cav * 5 - .1, 0, 1) + .6 * np.clip(-cav2 * 1.5 - .15, 0, 1)
        rk *= (1 - .55 * np.clip(crev, 0, 1))[..., None]
        rk *= (1 + .14 * np.clip(cav * 4, 0, 1) + .08 * np.clip(cav2 * 1.5, 0, 1))[..., None]
        wet = np.clip((sea + 1.8 - Hg) / 1.3, 0, 1)[..., None]
        rk = rk * (1 - .5 * wet) + np.array([58, 58, 50]) * .5 * wet
        weed = (np.clip((sea + .8 - Hg) / .5, 0, 1) * np.clip(.6 + .5 * n_m, 0, 1))[..., None]
        rk = rk * (1 - .7 * weed) + np.array([56, 60, 34]) * .7 * weed
        top = np.clip((Hg - sea - 2.5) / 1.5, 0, 1) * np.clip(cav2 * 2 + .3, 0, 1)
        lo_ = (np.clip(n_c * .7 + n_f * .5 - 1.0, 0, 1) * top)[..., None]
        rk = rk * (1 - .55 * lo_) + np.array([200, 150, 64]) * .55 * lo_
        lg_ = (np.clip(n_p * .8 + n_m * .4 - .9, 0, 1) * top)[..., None]
        rk = rk * (1 - .35 * lg_) + np.array([168, 172, 150]) * .35 * lg_
        # sand: darker and wet below the tide line
        s = s * (1 - .35 * wet) + np.array([120, 110, 92]) * .35 * wet
    # pavement: 2 m colour (no cars), fine aggregate
    pv = lo2.mean(-1, keepdims=True) * .6 + lo2 * .4
    pv = np.clip(pv, 150, 225) * (1 + .03 * n_f[..., None])
    # sea floor under the water: one colour, darker with depth (the foam of the photo is not painted)
    sf = np.array(sea_col, float) * (1 + .05 * n_c[..., None])
    if hgt is not None:
        sf = sf * (1 + .25 * np.clip(Hg - sea + .6, -1, .4)[..., None]) * (1 + .08 * n_m[..., None])   # darker with depth
    for k, t in (('GREEN', gr), ('VIOLET', v), ('EARTH', e), ('SAND', s), ('ROCK', rk), ('PAVED', pv), ('SEA', sf)):
        out += W[k][..., None] * t
    return np.clip(out, 0, 255), GX, GY


# ---------- tiles (seamless) ----------
def granite_tile(N=512, seed=4):
    rng = np.random.default_rng(seed); sh = (N, N)
    c = np.array([128, 124, 114], float) * (1 + .10 * fbm(sh, (2, 8, 30), (.4, .4, .5), rng))[..., None]
    sp = rng.random(sh); c[sp > .975] *= 1.3; c[sp < .03] *= .5
    lich = np.clip(_noise(sh, 18, rng) - 1, 0, None)[..., None]; c = c * (1 - .3 * lich) + np.array([170, 168, 130]) * .3 * lich
    cr = np.abs(_noise(sh, 10, rng)) < .05; c[cr] *= .45
    cr2 = np.abs(_noise(sh, 30, rng)) < .03; c[cr2] *= .5
    return np.clip(c, 0, 255).astype(np.uint8)


def ashlar_tile(N=1024, m=4.0, course=.45, seed=5, base=(184, 182, 174)):
    """Granite ashlar in regular courses (course height m): blocks 0.6-1.3 m long, joints lighter grey, each block its own tone.
    The tile covers m × m metres."""
    rng = np.random.default_rng(seed); px = N / m
    img = np.zeros((N, N, 3)); rows = int(round(m / course)); ch = N / rows
    nz = fbm((N, N), (1.5, 6), (.5, .5), rng)
    for rI in range(rows):
        y0, y1 = int(rI * ch), int((rI + 1) * ch); x = -rng.random() * 1.0 * px
        while x < N:
            L = (.6 + .7 * rng.random()) * px; x0, x1 = int(max(0, x)), int(min(N, x + L))
            tone = np.array(base) * (.86 + .22 * rng.random()) + rng.normal(0, 3, 3)
            img[y0:y1, x0:x1] = tone; x += L
            if x1 >= N: break
    img *= (1 + .06 * nz[..., None])
    sp = rng.random((N, N)); img[sp > .985] *= 1.25; img[sp < .02] *= .6
    j = 3
    for rI in range(rows + 1): img[max(0, int(rI * ch) - j // 2):int(rI * ch) + j // 2 + 1] = [128, 126, 118]
    # vertical joints: redraw by detecting tone changes along x
    dif = np.abs(np.diff(img[..., 0], axis=1)) > 6; dif = np.pad(dif, ((0, 0), (0, 1)))
    img[binary_dilation(dif, np.ones((1, 3)))] = [128, 126, 118]
    return np.clip(img, 0, 255).astype(np.uint8)


def roof_tile(N=512, m=2.0, seed=6):
    """Portuguese/Roman roof tiles (telha de canudo/marselha seen from above): rows every 0.4 m, channels every 0.2 m."""
    rng = np.random.default_rng(seed); px = N / m
    yy, xx = np.mgrid[0:N, 0:N] / px
    ch = .5 + .5 * np.cos(xx / .2 * 2 * np.pi)                     # channel shading
    row = (yy % .4) / .4; lip = np.clip((row - .85) / .15, 0, 1)
    base = np.array([196, 104, 62], float)
    tone = 1 + .08 * fbm((N, N), (3, 20), (.5, .5), rng)
    c = base * (.78 + .3 * ch)[..., None] * (1 - .35 * lip)[..., None] * tone[..., None]
    moss = np.clip(_noise((N, N), 25, rng) - 1.3, 0, None)[..., None]; c = c * (1 - .4 * moss) + np.array([110, 110, 80]) * .4 * moss
    return np.clip(c, 0, 255).astype(np.uint8)


def planks(N=512, m=2.0, w=.14, base=(140, 128, 110), seed=7, gap=(70, 62, 52)):
    """Boardwalk deck: boards w wide across the tile's v axis, weathered grey-brown, dark gaps."""
    rng = np.random.default_rng(seed); px = N / m
    yy, xx = np.mgrid[0:N, 0:N] / px
    k = (yy // w).astype(int); tones = .85 + .25 * rng.random(int(m / w) + 2)
    grain = gaussian_filter(rng.normal(0, 1, (N, N)), (.6, 12), mode='wrap'); grain /= grain.std()
    c = np.array(base, float) * tones[k][..., None] * (1 + .06 * grain[..., None])
    c[(yy % w) < .012] = gap
    return np.clip(c, 0, 255).astype(np.uint8)


def gravel(N=512, m=2.0, seed=8):
    rng = np.random.default_rng(seed); sh = (N, N)
    c = np.array([182, 176, 164], float) * (1 + .1 * _noise(sh, .8, rng) + .05 * _noise(sh, 6, rng))[..., None]
    sp = rng.random(sh); c[sp > .97] *= 1.18; c[sp < .04] *= .7
    return np.clip(c, 0, 255).astype(np.uint8)


def drystone(N=512, m=2.0, seed=9):
    """Dry-stone walling of small granite and schist stones (the low walls of the excavations): irregular stones 15-40 cm."""
    rng = np.random.default_rng(seed); px = N / m
    pts = rng.random((int(m * m / .05), 2)) * N
    from scipy.spatial import cKDTree
    yy, xx = np.mgrid[0:N, 0:N]
    P = np.c_[xx.ravel(), yy.ravel()]
    allp = np.vstack([pts + [dx, dy] for dx in (-N, 0, N) for dy in (-N, 0, N)])
    d, i = cKDTree(allp).query(P, k=2); i0 = i[:, 0] % len(pts); edge = (d[:, 1] - d[:, 0]) < 2.2
    tone = .75 + .4 * rng.random(len(pts)); hue = rng.random(len(pts))
    col = np.where(hue[:, None] < .3, np.array([120, 116, 104]), np.array([150, 146, 136])) * tone[:, None]
    c = col[i0].reshape(N, N, 3) * (1 + .05 * _noise((N, N), 1, rng))[..., None]
    c[edge.reshape(N, N)] = [60, 56, 48]
    return np.clip(c, 0, 255).astype(np.uint8)
