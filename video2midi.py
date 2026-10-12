#!/usr/bin/env python3
"""Extrae un MIDI de un video tipo Synthesia (barras que caen sobre un teclado de 88 teclas a todo lo ancho).
Uso: python3 video2midi.py video.mp4 salida.mid [--y0 100 --y1 140] [--step 2] [--bpm auto|75]

1. Calibra el teclado: mediana de 40 fotogramas de la franja del teclado (sin manos), detecta las 36 negras
   y ajusta x0 + ancho de blanca por mínimos cuadrados (el teclado puede salirse unos px del cuadro).
2. En cada fotograma lee una franja alta (lejos de partículas), binariza por matiz y busca BARRAS = tramos
   contiguos de columnas llenas. Cada barra se clasifica por su ancho: estrecha = negra (centro más cercano),
   ancha = blanca (tecla cuyo centro cae dentro). Así una barra blanca no dispara las negras vecinas.
3. Escribe un MIDI con tiempos reales al bpm indicado (auto = estima por autocorrelación de ataques)."""
import sys, argparse, struct, cv2, numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--y0", type=int, default=100); ap.add_argument("--y1", type=int, default=140)
ap.add_argument("--step", type=int, default=2); ap.add_argument("--solid", type=float, default=0.9)
ap.add_argument("--minframes", type=int, default=3)
ap.add_argument("--sat", type=int, default=90); ap.add_argument("--val", type=int, default=50)
ap.add_argument("--hue", default="95-175", help="rango de matiz OpenCV (0-180) de las barras; magenta=130-175, azul=95-130; por defecto 95-175 cubre las dos manos (azul+magenta)")
ap.add_argument("--maxbars", type=int, default=12)
ap.add_argument("--kb", default="auto", help="franja del teclado ya0-ya1 (p.ej. 630-710) o auto")
ap.add_argument("--bpm", default="auto")
ap.add_argument("--intro", type=float, default=5.0, help="segundos iniciales en que se completa con una franja baja (y 300-340), por si un destello de intro tapa la franja alta")
ap.add_argument("--thr", type=float, default=0, help="umbral de ancho de barra (px) negra/blanca; 0 = (ancho negra + ancho blanca)/2 del teclado. OJO: Synthesia dibuja las barras más estrechas que las teclas (blanca ≈16px, negra ≈14px con teclas de 23/15px): mide los anchos reales de las barras y pásalo a mano")
ap.add_argument("--debug", action="store_true")
a = ap.parse_args()

cap = cv2.VideoCapture(a.video); fps = cap.get(cv2.CAP_PROP_FPS)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# ---------- 1. calibración ----------
bands = []
for k in range(40):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(N * (k + 0.5) / 40)); ok, f = cap.read()
    if ok: bands.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
med = np.median(np.stack(bands), axis=0).astype(np.uint8)
if a.kb == "auto":
    # fila más brillante = borde superior del teclado (línea luminosa); negras justo debajo
    rows = (med > 140).mean(axis=1); ytop = int(np.argmax(rows > 0.8)); ya0, ya1 = ytop + 30, ytop + 110
else:
    ya0, ya1 = [int(v) for v in a.kb.split("-")]
prof = (med[ya0:ya1, :] < 60).mean(axis=0) > 0.8
segs = []; s = None
for x, v in enumerate(prof):
    if v and s is None: s = x
    if not v and s is not None: segs.append((s, x)); s = None
if s is not None: segs.append((s, W))
segs = [(p, q) for p, q in segs if 8 < q - p < 45]
blacks = [(p + q) / 2 for p, q in segs]
if len(blacks) != 36:
    sys.exit(f"calibración: se detectaron {len(blacks)} negras (esperaba 36) en y={ya0}-{ya1}; usa --kb")
NAMES = "ABCDEFG"
# índice de blanca a cuya derecha está cada negra, con desplazamiento nominal de un piano real
OFF = {"A": 0.0, "C": -0.25, "D": 0.25, "F": -0.25, "G": 0.0}
bidx = []
for i in range(52):
    if NAMES[i % 7] in OFF and i < 51: bidx.append(i + 1 + OFF[NAMES[i % 7]])
A = np.array([[1.0, b] for b in bidx]); x0, ww = np.linalg.lstsq(A, np.array(blacks), rcond=None)[0]
print(f"# teclado: x0={x0:.1f} ancho blanca={ww:.2f} (negras en y {ya0}-{ya1})", file=sys.stderr)
whites = [(21 + [0, 2, 3, 5, 7, 8, 10][i % 7] + 12 * (i // 7), x0 + (i + 0.5) * ww) for i in range(52)]
# midi de las negras: la blanca de índice i tiene nombre NAMES[i%7]; negra = midi blanca + 1
bmidi = []
for i in range(52):
    if NAMES[i % 7] in OFF and i < 51: bmidi.append(whites[i][0] + 1)
blacks = list(zip(bmidi, blacks))
bw = np.median([q - p for p, q in segs]); THR = a.thr or (bw + ww) / 2   # umbral de ancho negra/blanca
print(f"# ancho negra {bw:.0f}px, umbral {THR:.0f}px", file=sys.stderr)

def classify(p, q):
    w = q - p; c = (p + q) / 2
    if w < THR:
        m, bx = min(blacks, key=lambda b: abs(b[1] - c))
        return m if abs(bx - c) < ww * 0.6 else None
    i = int((c - x0) // ww)
    return whites[i][0] if 0 <= i < 52 else None

# ---------- 2. lectura ----------
h0, h1 = [int(x) for x in a.hue.split("-")]
def read_strip(y0, y1):
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    state = {}; notes = []; fi = 0; t = 0.0
    while True:
        ok = cap.grab()
        if not ok: break
        if fi % a.step == 0:
            ok, f = cap.retrieve(); hsv = cv2.cvtColor(f[y0:y1, :, :], cv2.COLOR_BGR2HSV)
            colored = (hsv[:, :, 0] >= h0) & (hsv[:, :, 0] <= h1) & (hsv[:, :, 1] >= a.sat) & (hsv[:, :, 2] >= a.val)
            solid = colored.mean(axis=0) >= a.solid
            t = fi / fps
            runs = []; s = None
            for x, v in enumerate(solid):
                if v and s is None: s = x
                if not v and s is not None: runs.append((s, x)); s = None
            if s is not None: runs.append((s, W))
            runs = [r for r in runs if r[1] - r[0] >= 6]
            ons = set()
            if len(runs) <= a.maxbars:
                for p, q in runs:
                    m = classify(p, q)
                    if m: ons.add(m)
            for m in list(state):
                if m not in ons:
                    t0, n = state.pop(m)
                    if n >= a.minframes: notes.append((t0, t - t0, m))
            for m in ons:
                state[m] = (state[m][0], state[m][1] + 1) if m in state else (t, 1)
        fi += 1
    for m, (t0, n) in state.items():
        if n >= a.minframes: notes.append((t0, t - t0, m))
    return sorted(notes), t

notes, t = read_strip(a.y0, a.y1)
if a.intro > 0:
    low, _ = read_strip(300, 340)
    # desfase temporal entre franjas: mediana de (t_baja - t_alta) para notas de la misma altura
    offs = []
    for t0, d, m in notes:
        c = [l for l in low if l[2] == m and 0 < l[0] - t0 < 1.5]
        if c: offs.append(c[0][0] - t0)
    off = float(np.median(offs)) if offs else 0.45
    # en la ventana del intro manda la franja baja (la alta puede estar tapada o retrasada por el destello)
    extra = [(t0 - off, d, m) for t0, d, m in low if t0 - off <= a.intro and d >= 0.15]
    notes = [n for n in notes if n[0] > a.intro]
    print(f"# franja baja: desfase {off:.2f}s, {len(extra)} notas tomadas en los primeros {a.intro:g}s", file=sys.stderr)
    notes = sorted(notes + extra)
print(f"# {len(notes)} notas, duración video {t:.1f}s, rango {min(n[2] for n in notes)}-{max(n[2] for n in notes)}", file=sys.stderr)

# ---------- 3. tempo ----------
if a.bpm == "auto":
    # pulso = moda de los intervalos entre ataques (robusto al rubato); se toma como corchea
    on = np.array(sorted(set(round(n[0], 2) for n in notes))); ioi = np.diff(on); ioi = ioi[ioi > 0.08]
    h, e = np.histogram(ioi, bins=np.arange(0.1, 1.5, 0.025)); k = int(np.argmax(h))
    pulse = float(np.median(ioi[(ioi >= e[k] - 0.025) & (ioi < e[k + 1] + 0.025)]))
    bpm = int(round(30 / pulse)); print(f"# pulso {pulse:.3f}s => {bpm} bpm (pulso = corchea); fija --bpm si prefieres otro", file=sys.stderr)
else: bpm = float(a.bpm)
tps = 480 * bpm / 60   # ticks por segundo

def vlq(n):
    out = [n & 0x7f]; n >>= 7
    while n: out.append((n & 0x7f) | 0x80); n >>= 7
    return bytes(reversed(out))
ev = []
for t0, d, m in notes:
    ev.append((int(round(t0 * tps)), 1, m)); ev.append((int(round((t0 + d) * tps)), 0, m))
ev.sort(key=lambda e: (e[0], e[1]))
trk = b"\x00\xff\x51\x03" + int(60e6 / bpm).to_bytes(3, "big"); last = 0
for tk, on, m in ev:
    trk += vlq(tk - last) + bytes([0x90 if on else 0x80, m, 80 if on else 0]); last = tk
trk += b"\x00\xff\x2f\x00"
with open(a.out, "wb") as fh:
    fh.write(b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480) + b"MTrk" + struct.pack(">I", len(trk)) + trk)
print(f"# escrito {a.out}", file=sys.stderr)
