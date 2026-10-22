---
name: email-variants
description: Crea variantes de copy para los pasos de una campaña de Instantly (cold email) contra el fingerprinting de copy - conserva siempre el original, distinto largo/estructura/cantidad de palabras, sin spintax, sin inventar contenido. Usar solo cuando el usuario pida variantes o versiones del copy de una campaña de Instantly ("variantes", "versiones del copy", "variaciones para la campaña") o pase un link app.instantly.ai/app/campaign/<id>/editor pidiendo variantes. No es para buscar leads ni armar una campaña de prospección (eso es lead-gen).
---

# Variantes de copy (Instantly)

Por qué (Deliverability Updates, 18 sep 2026): Google y Microsoft marcan frases repetidas cada
vez más rápido. El spintax se detecta a nivel de frase, y una sola frase marcada (a menudo el
CTA, la firma, el cargo o el teléfono) envenena toda la secuencia. Lo que funciona hoy es
**rotar estructuras, no sinónimos**, con muchas variantes de distinto largo, estructura y
cantidad de palabras, y probar copy cada semana.

## Python (antes del primer script)

Los scripts usan solo la biblioteca estándar (sin `pip`). Antes de correr uno, buscar el
intérprete: `python3 --version`, después `python --version`, después `py -3 --version`
(Windows). Usar el primero que responda **Python 3.8+**; en los comandos de esta skill,
`python3` significa ese. Ojo: en Windows `python3`/`python` pueden abrir la Microsoft Store en
vez de responder: eso cuenta como "no hay".

Si no hay: decirle al usuario en una línea qué se va a instalar y por qué, y con su OK:
- Windows: `winget install -e --id Python.Python.3.12` (puede aparecer una ventana de permisos
  de Windows que el usuario acepta); después usar `py -3`.
- Mac: `brew install python` si hay Homebrew; si no, `xcode-select --install` (el usuario
  acepta la ventana de Apple) y usar `python3`.
- Linux: el gestor de paquetes (`sudo apt install python3`).

Verificar con `--version` y anotar en `state.md` qué comando quedó. El usuario nunca tiene que
instalar nada a mano.

## 1. Preguntar (AskUserQuestion, lo que no esté explícito)

- **Campaña(s)**: el ID sale del link (`/campaign/<id>/editor`). Nunca adivinarlo (workspace
  compartido entre clientes).
- **Cuántas variantes por paso**, además del original. Referencia: el informe pide 15-20
  variantes por campaña como mínimo; con 4 pasos, 4-5 por paso ya cumple y 9 por paso
  (10 con el original) es lo que se ha usado en Saravá.
- **Qué pasos**: todos por defecto.
- **Asuntos**: si se varían (por defecto sí, salvo los pasos sin asunto, que van en el mismo
  hilo y siguen sin asunto).
- Si la campaña ya tiene variantes: ¿se reemplazan (se conserva el original) o se agregan?

## 2. Leer y respaldar

Leer la campaña con el flujo n8n **instantly-sequences** (paso 5) con `action: "get"` y
guardar la respuesta en `<carpeta>/raw/campaign_<id8>.json`. Después
`python3 <skill>/scripts/variants.py <id> --campaign-json raw/campaign_<id8>.json`, desde la carpeta de la campaña:
sin archivo de variantes todavía, deja los originales en `copy_originales_<id8>.md` para
escribir a partir de ellos. **Avisar antes de escribir** si el
original tiene algo raro: asunto que parece etiqueta interna ("Follow-up o derivación"),
variables mezcladas (`{{first_name}}` y `{{firstName}}` en la misma campaña), caracteres
invisibles. No corregirlos sin OK.

## 3. Escribir las variantes

En `<carpeta>/variantes/c<id8>.py` (formato en el docstring del script). Reglas:

- **El original no se toca**: queda en la posición 0 tal cual.
- **Mismo mensaje, nada inventado**: mismas afirmaciones, cifras, nombres de producto y
  llamados a la acción del original. Nada de datos, beneficios o casos nuevos.
- **Rotar estructura, no sinónimos**: cada variante con otro largo (de 2-3 líneas a la versión
  larga), otra forma (párrafo corto, viñetas, lista numerada, empezar por la pregunta, empezar
  por el problema) y otra cantidad de palabras. Cambiar palabras sueltas sobre la misma
  estructura no sirve.
- **Sin spintax** en ningún lado (`{a|b}`, `{{RANDOM|...}}`): el script lo rechaza.
- **Ninguna frase repetida entre versiones**, sobre todo el CTA y la frase de apertura:
  reformular el llamado a la acción en cada variante manteniendo lo que pide (ej. "15 minutos
  esta semana o la próxima"). El script avisa las frases repetidas.
- **Solo las variables del original** de ese paso (el script rechaza otras).
- **Firma**: no va en el cuerpo; el script copia la del original (elemento estático).
- Idioma y trato (tú/usted) del original.

## 4. Validar y mostrar

`python3 scripts/variants.py <id> --campaign-json raw/campaign_<id8>.json` →
`copy_variantes_<id8>.md` con cada versión, su conteo de palabras, el rango por paso y las
frases repetidas, y `raw/sequences_update_<id8>.json` (lo que se manda a n8n). Corregir los avisos
de frases repetidas. Mostrar al usuario el rango de palabras por paso y el link al `.md`;
pedir OK.

## 5. Escribir en Instantly

Flujo n8n **instantly-sequences** (`execute_workflow`, workflowId `201TuEKiJgIdUy67`,
`triggerNodeName: "Webhook"`, `executionMode: "production"`,
`inputs: {webhookData: {method: "POST", body}}`; el resultado sale del nodo "Respuesta",
leído con `get_workflow_execution`):

1. `{action: "update", campaign_id, sequences: <raw/sequences_update_<id8>.json>, dry_run: true}`
   → `variantes_por_paso`, `asuntos` y `backup_id` (el respaldo se guarda igual). Mostrarlo y
   pedir OK.
2. Igual con `dry_run: false` → comprobar `ok: true` y `original_intacto: true`.
3. Si algo salió mal: `{action: "restore", campaign_id, backup_id, dry_run: false}` (con OK;
   restore también es seco por defecto).

El flujo rechaza sin escribir si la campaña no está en borrador, si cambió algún original o
la cantidad de pasos. Anotar el `backup_id` en `state.md`. La clave de Instantly vive solo en
n8n.

Flujo publicado y probado en vivo (2026-10-22). Solo si el conector n8n no está disponible:
respaldo local `variants.py <id>` (sin `--campaign-json` lee la API) y `--apply` (solo
borrador, respalda en `raw/`), que lee la clave del `.env` por nombre (`--key-env`) sin
mostrarla; anotarlo en `state.md`.

## 6. Cierre

- Anotar en `state.md` de la campaña (si existe): fecha, cuántas variantes por paso, respaldo.
- Recordar al usuario: probar el copy cada semana, juzgar por **respuestas humanas** (los
  tests de placement de Outlook dan falsos positivos) y no cambiar originales sin respaldo.
