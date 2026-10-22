# Ampliación de job titles

Se ofrece SIEMPRE en la Fase 0, aunque el usuario no lo pida: "¿Amplío estos cargos
(variantes EN/ES, sinónimos, niveles superiores)?". Si dice que no, se usan tal cual.

## Insumos (preguntar lo que falte)

- Cargos semilla del usuario.
- Área(s): marketing, operaciones, RRHH/personas, etc. Si la semilla mezcla áreas, confirmar.
- Seniority mínimo (el confirmado en la Fase 0).
- Idiomas: por defecto EN + ES.
- Máximo de cargos: por defecto 99.

## Biblioteca reutilizable

Antes de generar, revisar `references/titulos/<area>_<seniority_min>.txt`. Si existe,
partir de esa lista ya aprobada y solo agregar lo que la semilla traiga de nuevo. Después
de la aprobación, guardar/actualizar ese archivo (un cargo por línea) para la próxima campaña.

## Reglas de generación

1. **Seniority**: solo del mínimo hacia arriba (C-level, VP/Vicepresidente, Head, Director,
   Gerente/Manager si el mínimo es Manager). Los cargos de la semilla que queden bajo el mínimo
   (Coordinador, Especialista, Asociado, Analista, Jefe de...) **no se borran en silencio**: se
   listan en "excluidos por seniority" y se pregunta. "Jefe de" en Chile puede ser Manager según
   la empresa: preguntar.
2. **Área**: solo cargos cuyo trabajo principal es el área. Fuera del área o ambiguos van a
   "dudosos" con el motivo (ej. Account Director = ventas/agencia, Chief Revenue Officer = ventas,
   Creative Director = agencia/diseño).
3. **Siglas**: nunca solas. "Chief Marketing Officer" y "CMO" juntas; marcar siglas ambiguas
   (CRO = Revenue/Risk, CPO = People/Product/Procurement, CBO = Brand/Business).
4. **Pares EN/ES** cuando existan ambos en el mercado (Marketing Director / Director de
   Marketing). No inventar traducciones que nadie usa.
5. Variantes regionales cuando apliquen al país (Chile: Gerente, Subgerente si el mínimo lo
   permite, Jefe; México: Director; España: Responsable).
6. Sin duplicados (mayúsculas, tildes, "VP de" vs "VP of" cuentan como distintos solo si los
   dos se usan de verdad).

## Presentación al usuario

Agrupado por nivel (C-level / VP / Head / Director / Manager), con conteo total, más dos
bloques aparte: **excluidos por seniority** y **dudosos (área/sigla)**. El usuario aprueba,
quita o rescata. La lista aprobada va a `people_search.job_titles` y lo descartado a
`people_search.job_titles_excluded` del `campaign.yaml`.

## Uso en las búsquedas

- Apollo: `person_titles` = lista aprobada completa (además del filtro `person_seniorities`).
- Clay: la lista aprobada en `job_title in (...)` o `is_similar_to` con los cargos núcleo;
  `is_similar_to` ya expande por significado, así que revisar que no traiga los dudosos.
