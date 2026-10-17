# Piano Virtual (MVP)

Clon funcional de la mecánica de virtualpiano.net en un solo archivo `index.html` (sin dependencias ni build).

- 61 teclas (C2–C7) con el mismo mapeo QWERTY: `1234567890qwertyuiopasdfghjklzxcvbnm` = blancas; Shift (`!@$%^*(` y mayúsculas) = negras.
- Partituras en notación de letras: `[abc]` acorde, espacio o `.` = pausa de media pulsación, `-` = pausa de una pulsación, `|` compás (solo visual). Cada nota dura media pulsación del reproductor (no hay duraciones).
- Reproducción automática con tempo, resaltado de la partitura y de las teclas, 2 líneas de anticipación.
- Modo práctica: avanza solo al tocar la tecla correcta. Acordes mixtos (negras + blancas, p. ej. `[qsH]`): se aceptan con Shift mantenido en todas, sin Shift en ninguna, y en cualquier orden de teclas. Bloq Mayús vale como Shift sostenido también para los números (1-0 → !@#$%^&*()).
- Partitura bloqueada; botón "Editar partitura" para pegar otra. Si se pega el HTML `#song-pattern` de virtualpiano.net se convierte solo.

Servir por http (los samples no cargan con `file://`): `python3 -m http.server` y abrir `http://localhost:8000`, o publicar en cualquier hosting estático.

## Sonido
Por defecto usa muestras reales del Salamander Grand Piano (CC-BY, carpeta `samples/`, 21 mp3 cada tercera menor C2–C7, ~1.4 MB) con pitch-shift al semitono más cercano. Si no cargan, cae a síntesis. Hay 9 timbres sintéticos adicionales en el selector.

## Canciones
Las partituras viven en `songs/<slug>.txt`; cada una necesita su `<option value="slug">` en el `<select id="song">` del index. Repertorio actual: 19 canciones (Coldplay, Radiohead, Resident Evil, Here to Stay), varias en versión "piano" y "completo". Los `.mid` de origen se guardan al lado.

### Desde MIDI
`python3 midi2vp.py archivo.mid [--grid 4|auto] [--tracks 1,2] [--transpose n] [--auto] [--info]` convierte un MIDI a la notación del teclado. `--grid auto` detecta la subdivisión (tresillos incluidos); `--auto` transpone a la tonalidad con menos teclas negras para evitar acordes mixtos Shift/no Shift; cuantiza, agrupa acordes, transpone octavas fuera de C2–C7 y omite batería. Sin dependencias externas. Ejemplo: `songs/o-fly-on.txt` (MIDI gratuito de midisfree.com, 65 bpm, 2 manos). Fuentes de MIDI gratuitos: midisfree.com, BitMidi.

### Desde video (Synthesia)
`python3 video2midi.py video.mp4 songs/<slug>.mid [--hue 95-175] [--y0 100 --y1 140] [--intro 5] [--bpm auto]` saca un MIDI de un video de barras que caen sobre un teclado de 88 teclas a todo lo ancho. Requiere OpenCV (`pip install opencv-python numpy`).

- Calibra solo el teclado: mediana de 40 fotogramas, detecta las 36 negras y ajusta origen/ancho.
- Lee una franja alta del cuadro, lejos de las partículas, y clasifica cada barra por su ancho (estrecha = negra, ancha = blanca) para que una blanca no dispare las negras vecinas.
- En los primeros `--intro` segundos usa una franja baja con desfase temporal automático, porque el destello del intro tapa la franja alta.
- Las dos manos pueden ir en colores distintos (`--hue 95-175` cubre azul y magenta).
- Tempo por la moda de los intervalos entre ataques (tomado como corchea). Como el video es una interpretación con rubato, convertir luego con `midi2vp.py <mid> --grid 2` (sin `--auto`, para conservar las notas del video). Las alturas son absolutas; si se prefiere una octava arriba, `--transpose 12`.
- Escribe imágenes de depuración en `video-work/` (ignorada por git).

Daydreaming (Radiohead, Synthesia 1080p con letras dentro de las barras y partículas) se leyó el 2026-10-12 con `--kb 840-960 --merge 30 --bycenter --y0 100 --y1 106 --minframes 2 --bpm 91.5` y `midi2vp.py --grid 6` (1887 notas; la letra parte cada barra en dos tramos, por eso `--merge`; las barras van centradas en la tecla, por eso `--bycenter` en vez del ancho; franja de 6 px para que la letra no la cruce). Tras leer unos 20 s hay que comprobar las primeras notas contra un fotograma antes de procesar todo. Lección aprendida (2026-10-12): el umbral de ancho negra/blanca se calcula del teclado, pero Synthesia dibuja las barras más estrechas que las teclas (blanca ≈16 px, negra ≈14 px frente a teclas de 23/15 px), así que todas las blancas se clasificaban como la negra vecina. Medir los anchos reales de las barras y pasar `--thr`. Para "A Moment of Relief" (Code Veronica) se usó directamente el MIDI oficial del video: `songs/re-code-veronica-synthesia.mid` → `midi2vp.py ... --grid auto` (273 notas, 80 bpm, rejilla de semicorchea exacta). Desde 2026-10-12 el conversor escribe las pausas exactas (`.` = 1 celda, `-` = 2 celdas; nota = 1 celda) y avisa del tempo que hay que poner en el reproductor (bpm × rejilla / 2); antes redondeaba los huecos y el ritmo salía distinto en algunos pasajes.

## Publicación
Está publicado en Lucuma Previews como `lucuma/piano-virtual` (v20 el 2026-10-14). Subir una versión nueva:
`node ../previews/push.js lucuma piano-virtual . --nota "..."` (push.js ignora README, .py y .mid).

## Bitácora

### 2026-10-11 · MVP
Reproductor en un solo `index.html` (61 teclas, mapeo QWERTY de virtualpiano.net, autoplay, práctica, samples Salamander + 9 timbres). `midi2vp.py` (MIDI → letras) y primera versión de `video2midi.py` (video de barras → MIDI). 19 canciones (Coldplay, Radiohead, Resident Evil, Here to Stay). Publicado en Lucuma Previews.

### 2026-10-12 · repo, Code Veronica y Daydreaming
- Repo `LucumaAgency/virtual-piano`; mp4 y carpetas de trabajo fuera del proyecto (`../piano-virtual-media/`), `.gitignore` para videos, `video-work/`, `trabajo/`.
- Save Room de Code Veronica: la transcripción del video original estaba mal. Se leyó el video Synthesia "A Moment of Relief" (ritmo correcto, pero todas las blancas salían como la negra vecina: Synthesia dibuja barras más estrechas que las teclas → `--thr`). Al final se usó el MIDI oficial del video: `songs/re-code-veronica-synthesia.*`. Las otras dos versiones (Save Room piano/completo, de MIDI antiguo) se retiraron a `piano-virtual-media/descartadas/`.
- `midi2vp.py`: pausas exactas (`.` = 1 celda, `-` = 2 celdas; antes redondeaba los huecos y el ritmo salía distinto en algunos pasajes) y aviso del tempo que hay que poner en el reproductor (bpm × rejilla / 2). Verificación de ida y vuelta partitura ↔ MIDI.
- Daydreaming: retranscrito desde video Synthesia 1080p (letras dentro de las barras, partículas). `video2midi.py` gana `--merge`, `--bycenter`, `--end` y `--thr`. 1887 notas, rejilla 6, reproducir a 275 bpm (deslizador de tempo ampliado a 300). La versión "completo" (MIDI antiguo) se mantiene.
- Enlace para compartir: `node ../previews/push.js acceso lucuma` genera un enlace de cliente sin contraseña (renovable con `--renew`).

### 2026-10-14 · modo práctica
- Acordes mixtos sin Shift: `[yraO]` se acepta tocando `y r a o` (y se oye la negra correcta). Antes solo valía mantener Shift en todas.
- Bloq Mayús: convierte también 1-0 en sus negras (el navegador no cambia los dígitos con Bloq Mayús, por eso `8 9 0` no sonaban como `* ( )`).
- Orden de teclas: si la primera tecla del acorde era la que lleva Shift (`h` antes que `q s` en `[qsH]`) se trababa; ahora se compara siempre contra el acorde del cursor. Probado en Chromium con Playwright: `q s h`, `h s q`, `s h q`, con y sin Shift, y el pasaje `[$Og] [*PG] [qsH] [@S] g H [$J]` de corrido sin Shift.

## Pendiente: Daydreaming, pasajes con C#/F# (2026-10-12)
El usuario oye mal las líneas 23, 25, 27, 29, 42, 44, 46, 48, 50, 52, 54, 56, 58 y 60 de `songs/daydreaming.txt` (las que llevan `T`, `I`, `E`, `^` y guiones, p. ej. `p-Tu-Iu-.p-Iy.T.u-.`) y espera ahí el patrón blanco `p.t.y.i.u.t.p.i.y.t.u.i.` (o `[6p].t.y.[6i].u.t.[6p].i.y.[6t].u.i.`).
Verificado: la lectura es fiel al video. Las barras llevan etiqueta "Db"/"F#" en esos compases y el audio del mp4 (extraído con el ffmpeg de imageio, energía en fundamentales) confirma C#4/F#4 dominantes y C4/F4 casi ausentes (línea 23: C#4 74,9 vs C4 2,0; F#4 54,3 vs F4 3,2), al revés que en los pasajes buenos. El pianista cambia la figura (A sostenida, F# de adorno, D, C#, E).
Decisión pendiente: (1) dejar fiel al video (estado actual, Previews v17) o (2) uniformar esas líneas con el patrón blanco a mano; para las líneas tipo `p.r.y-Iu.r` (con B3) y la 56 (bajo D2/E2) falta definir el patrón. Nota: el reproductor no tiene duraciones, cada nota suena un instante, así que las notas sostenidas con pausas detrás se oyen entrecortadas.
