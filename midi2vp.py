#!/usr/bin/env python3
"""Convierte un archivo MIDI a la notación de teclas de Virtual Piano (61 teclas, C2–C7).

Uso: python3 midi2vp.py archivo.mid [--grid 8] [--tracks 1,2] [--transpose 0] [--info]
  --grid N      subdivisión del pulso para cuantizar (8 = corcheas de tresillo no, 4 = semicorcheas). Por defecto 4.
  --tracks      índices de pistas a incluir (por defecto todas las que tengan notas, menos batería canal 10).
  --transpose   semitonos (+/-) antes de mapear.
  --info        solo muestra las pistas y sus rangos.
Salida: texto en notación VP ([acordes], espacio = pausa corta, - = pausa larga, salto cada compás par)."""
import sys, struct, argparse

WHITE = "1234567890qwertyuiopasdfghjklzxcvbnm"
SHIFT = {"1":"!","2":"@","3":"#","4":"$","5":"%","6":"^","7":"&","8":"*","9":"(","0":")"}
KEY = {}
midi = 36
for i, ch in enumerate(WHITE):
    step = i % 7
    KEY[midi] = ch
    if step not in (2, 6) and i < len(WHITE) - 1:
        KEY[midi + 1] = SHIFT.get(ch, ch.upper()); midi += 2
    else:
        midi += 1
LO, HI = 36, 96

def read_vlq(d, p):
    v = 0
    while True:
        b = d[p]; p += 1; v = (v << 7) | (b & 0x7f)
        if not b & 0x80: return v, p

def parse(path):
    d = open(path, "rb").read()
    assert d[:4] == b"MThd"
    fmt, ntr, div = struct.unpack(">HHH", d[8:14])
    p = 14; tracks = []
    for _ in range(ntr):
        assert d[p:p+4] == b"MTrk"; ln = struct.unpack(">I", d[p+4:p+8])[0]; q = p + 8; end = q + ln
        t = 0; run = None; notes = []; name = ""; on = {}; tempos = []
        while q < end:
            dt, q = read_vlq(d, q); t += dt; st = d[q]
            if st & 0x80: q += 1; run = st
            else: st = run
            if st == 0xFF:
                ty = d[q]; q += 1; ln2, q = read_vlq(d, q); data = d[q:q+ln2]; q += ln2
                if ty == 3: name = data.decode("latin1", "ignore")
                if ty == 0x51: tempos.append((t, int.from_bytes(data, "big")))
            elif st in (0xF0, 0xF7):
                ln2, q = read_vlq(d, q); q += ln2
            else:
                hi = st & 0xF0; chn = st & 0x0F
                n = 2 if hi in (0x80, 0x90, 0xA0, 0xB0, 0xE0) else 1
                a = d[q]; b = d[q+1] if n == 2 else 0; q += n
                if hi == 0x90 and b > 0: on.setdefault(a, []).append((t, chn))
                elif hi == 0x80 or (hi == 0x90 and b == 0):
                    if on.get(a):
                        t0, c0 = on[a].pop(0); notes.append((t0, t - t0, a, c0))
        tracks.append({"name": name, "notes": notes, "tempos": tempos})
        p = end
    return div, tracks

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mid"); ap.add_argument("--grid", default="auto", help="subdivisión del pulso (2,3,4,6,8,12) o auto")
    ap.add_argument("--tracks", default=""); ap.add_argument("--channels", default="", help="canales MIDI a incluir (para archivos formato 0 de una sola pista)"); ap.add_argument("--transpose", type=int, default=0); ap.add_argument("--info", action="store_true")
    ap.add_argument("--beats-per-line", type=int, default=8)
    ap.add_argument("--auto", action="store_true", help="elige la transposición (-6..+6) con menos teclas negras y menos acordes mixtos Shift/no Shift")
    a = ap.parse_args()
    div, tracks = parse(a.mid)
    tempo = next((tp for tr in tracks for _, tp in tr["tempos"]), 500000)
    if a.info or True:
        print(f"# división {div} ticks/negra · tempo {60e6/tempo:.0f} bpm · {len(tracks)} pistas", file=sys.stderr)
        for i, tr in enumerate(tracks):
            ns = [n for _, _, n, _ in tr["notes"]]
            chs = sorted({c for *_, c in tr["notes"]})
            if ns: print(f"#  pista {i}: '{tr['name']}' {len(ns)} notas, rango {min(ns)}-{max(ns)}, canales {chs}", file=sys.stderr)
            else: print(f"#  pista {i}: '{tr['name']}' sin notas", file=sys.stderr)
        if a.info: return
    sel = [int(x) for x in a.tracks.split(",") if x] or [i for i, tr in enumerate(tracks) if tr["notes"]]
    ev = []
    for i in sel:
        for t0, dur, n, c in tracks[i]["notes"]:
            if c == 9: continue  # batería
            if a.channels and str(c) not in a.channels.split(","): continue
            ev.append((t0, n + a.transpose))
    BLACK = {1, 3, 6, 8, 10}
    if a.auto:
        best = None
        for tr in range(-6, 7):
            blacks = sum(1 for _, n in ev if (n + tr) % 12 in BLACK)
            score = (blacks, abs(tr))
            if best is None or score < best[0]: best = (score, tr)
        a.transpose += best[1]
        ev = [(t0, n + best[1]) for t0, n in ev]
        print(f"# transposición automática: {best[1]:+d} semitonos ({best[0][0]} notas en teclas negras)", file=sys.stderr)
    if a.grid == "auto":
        best = None
        for g in (2, 3, 4, 6, 8, 12):
            st = div / g
            err = sum(abs(t0 / st - round(t0 / st)) for t0, _ in ev) / max(1, len(ev))
            score = (round(err, 3), g)
            if best is None or score < best: best = score
        a.grid = best[1]
        print(f"# rejilla automática: {a.grid} por pulso (error medio {best[0]})", file=sys.stderr)
    else: a.grid = int(a.grid)
    step = div / a.grid
    slots = {}
    for t0, n in ev:
        while n < LO: n += 12
        while n > HI: n -= 12
        s = round(t0 / step); slots.setdefault(s, set()).add(n)
    if not slots: print("sin notas", file=sys.stderr); return
    out = []; last = -1; per_line = a.beats_per_line * a.grid
    for s in sorted(slots):
        if last >= 0:
            gap = s - last - 1
            if gap > 0:
                # pausas exactas para el reproductor: nota = 1 celda, " " = 1 celda, "-" = 2 celdas
                out.append("-" * (gap // 2) + ("." if gap % 2 else ""))
            if last // per_line != s // per_line: out.append("\n")
        ks = "".join(KEY[n] for n in sorted(slots[s]) if n in KEY)
        out.append(f"[{ks}]" if len(ks) > 1 else ks)
        last = s
    txt = "".join(out)
    import re
    txt = txt.strip()
    print(f"# tempo del reproductor: {60e6/tempo*a.grid/2:.0f} bpm (cada celda = 1/{a.grid} de pulso = media pulsación del reproductor)", file=sys.stderr)
    print(txt)

if __name__ == "__main__": main()
