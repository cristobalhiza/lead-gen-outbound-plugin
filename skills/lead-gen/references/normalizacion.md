# Normalización de nombres de empresa

Dos capas:
1. **Script** (`scripts/normalize_company.py`): formas legales de todos los países en una sola
   lista (CL, PE, MX, CO, AR, BR, ES, EE.UU./UK/DE), "A - B" → A, Title Case de nombres en
   mayúsculas y "y" en minúscula. Es determinista y rápido, y deja `Normalize_Flag` donde no
   está seguro: siglas, guiones, nombres de una palabra corta. Las **mayúsculas** las decide
   el script con una regla fija (`es_sigla`): 2-3 letras al inicio (MGA, OTI), sin vocales
   (CMPC, 3L), dos consonantes iniciales que no abren sílaba (TMAZ, XMIN) o 3 consonantes
   seguidas en 4 letras (MPPI, MSHA); el resto como palabra (Icsa, Imsa, Garco). Así el
   resultado no depende de la corrida del LLM.
   País nuevo con formas que no salen → agregarlas a `LEGAL` y un `assert` en `demo()`.
2. **Revisión de las filas con flag** por un subagente Haiku (`Agent`, `model: "haiku"`). Le
   llegan solo las filas con flag, nunca el universo entero. Si son menos de ~30, las revisa
   el agente principal sin subagente.

En una campaña real (829 empresas, México): 118 con flag en la primera versión (175 desde que el script también revisa palabras en MAYÚSCULA de nombres mixtos); todas las diferencias con la versión final hecha a
mano salieron con flag, menos una (donde el script tenía razón).

## Prompt para el subagente

Pasarle la ruta de un CSV con `Company` (original), `Company_Normalized`, `Normalize_Flag`,
y si hay `Domain`, `Country` y la `short_description` de Apollo/Clay.

```
Revisa nombres de empresa para un CRM B2B de <país>. Por cada fila de <csv>, decide el nombre
final y escribe <csv_salida> con: Company, Propuesto, Cambio (si/no), Motivo (corto).
Reglas:
- Sin forma legal (S.A., S. de R.L. de C.V., SpA, Ltda., SAS, Inc., ...).
- **Mayúsculas: las decide el script, no las cambies.** Respeta mayúsculas/minúsculas de
  `Company_Normalized` palabra por palabra. Única excepción: una sigla que todo el mundo
  conoce (COPEC, COLUN, ENEL, SANY) va en mayúscula aunque el script la haya dejado como
  palabra.
- "A - B" (con guion; el script dejó solo A en `Company_Normalized`):
  - Si el script dejó A en MAYÚSCULA (TMAZ, CTQ, AEM, BMS), A es sigla: queda el nombre largo
    B ("TMAZ - Terminal Marítima Mazatlán" → "Terminal Marítima Mazatlán"), en Title Case con
    conectores en minúscula, salvo que A sea una sigla conocida (COPEC...).
  - Si el script dejó A como palabra (Teclubin, Xplor, Seijo), A es la marca: queda A.
  - Si B es solo una descripción o categoría ("MINERIA", "Ductile & Gray Iron Castings"),
    queda A.
- La descripción sirve para saber qué es la empresa, nunca para decidir mayúsculas.
- Sin sufijo de país "MX" ("Promas MX" → "Promas").
- No reordenar: se respeta el orden y los paréntesis del original.
- Respetar tildes del original; si el original no las tiene, no inventarlas.
- Conectores en minúscula (de, del, y, la, of, and, to), salvo la primera palabra.
- No agregar ni quitar palabras de marca. Ante la duda, Cambio=no y Motivo="duda: ...".
Solo escribe el CSV y responde con el conteo de cambios y las filas con "duda".
```

El agente principal aplica `Propuesto`, muestra al usuario los cambios y las dudas (Fase 1,
paso 1) y anota en `state.md` cuántas filas cambió el subagente.
