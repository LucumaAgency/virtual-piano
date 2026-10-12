# Piano Virtual (MVP)

Clon funcional de la mecánica de virtualpiano.net en un solo archivo `index.html` (sin dependencias ni build).

- 61 teclas (C2–C7) con el mismo mapeo QWERTY: `1234567890qwertyuiopasdfghjklzxcvbnm` = blancas; Shift (`!@$%^*(` y mayúsculas) = negras.
- Partituras en notación de letras: `[abc]` acorde, espacio pausa, `-` pausa larga, `|` compás.
- Reproducción automática con tempo, resaltado de la partitura y de las teclas, 2 líneas de anticipación.
- Modo práctica: avanza solo al tocar la tecla correcta.
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

Ejemplo: "A Moment of Relief" (Code Veronica, video Synthesia de 88 teclas, 80 bpm) → `video2midi.py video.mp4 songs/re-code-veronica-video.mid --hue 30-130 --intro 0 --bpm 80 --kb 585-650 --minframes 2` (262 notas; azul = mano derecha, verde = izquierda; el teclado ocupa y 570-715 así que la calibración automática falla y se pasa `--kb`) → `midi2vp.py ... --grid auto`. Los videos fuente (mp4) no van en el repo.

## Publicación
Está publicado en Lucuma Previews como `lucuma/piano-virtual`. Subir una versión nueva:
`node ../previews/push.js lucuma piano-virtual . --nota "..."` (push.js ignora README, .py y .mid).
