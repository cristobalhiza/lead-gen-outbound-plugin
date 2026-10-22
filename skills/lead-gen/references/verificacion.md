# Verificación de emails y waterfall

## Router (fuente de verdad)

**Vía por defecto: flujo n8n `verify-emails`** (ver `n8n.md`): misma lógica, claves y cache
compartido en n8n. El script local de abajo es el respaldo cuando no hay conector n8n; lo que
verifique queda solo en el cache local.

`verify_router.py` (ruta en el archivo local `~/.claude/sarava-leadgen.local.md`). NO reimplementar ni usar las
fórmulas de Clay (la versión vieja mandó 22% de bounces: el umbral catch-all `< 75` nunca se
cumple porque Reoon puntúa catch_all con 75 fijo, y `null < N` es `true` en JS).

Orden de decisión por email:
1. Rebote real en cache → Discard (le gana a todo).
2. Dominio en `BLOQUEADOS` → Discard.
3. Cisco IronPort (`iphmx` en MX) → Discard: gateway ciego, 77% rebote, BounceBan no sirve.
4. Reoon (modo power): sintaxis/MX/spamtrap/desechable/role/invalid → Discard.
5. `is_safe_to_send` = true → Send. Es veto duro; ningún score lo anula.
5b. Reoon sin respuesta (clave mala, 401, timeout) → Pending, nunca a BounceBan.
6. Todo unknown/catch_all → **BounceBan** (`deliverable` → Send, resto → Discard).
7. `--bb-domain <dominio>` fuerza BounceBan aunque Reoon diga safe (dominios con historial).

Respaldo sin n8n: `verify_router.py --csv 06_emails.csv --out 07_verified` con `--dry-run`,
después `--limit N` (sin `--limit` no gasta; columna `Email_Final`). Los 408 →
`bounceban_recover.py` (gratis por Task ID).

## Waterfall de email con Clay (MCP)

Para: sin email de Apollo **y** descartados por el router.

1. `search-contacts-by-name` con `{contactName, companyIdentifier: <dominio confirmado>}`
   (o reusar el taskId de la búsqueda de personas de Clay si el lead salió de ahí).
2. `add-contact-data-points` con `[{type: "Email"}]` sobre esos entityIds.
3. Poll `get-task-context` hasta `completed` (1-3 min, algunos más).
4. Merge por **URL de LinkedIn**, nunca por nombre (homónimos en la misma empresa).

Reglas del resultado:
- Mismo email que el que ya se descartó → descartar, no re-verificar.
- Email de Clay es **candidato**: nunca pisa un Apollo `verified` + no catch-all.
- **Dominio calcado**: si el dominio del email ≠ dominio confirmado de la empresa,
  `dig +short MX <dominio>`; si el proveedor de MX no coincide → descartar aunque diga deliverable
  (casos reales: `perpetua.com`, `sibanyestillwater.co`).
- Todo candidato vuelve a pasar por el router.
- El MCP deja el resultado en una task, no en una tabla de Clay. Si el usuario lo quiere en la
  UI de Clay, entregar CSV para importar.

Costo de referencia (Apollo, 2026-09-30): waterfall a sin-email ≈ 2 créditos/persona; a
descartados con email ≈ 18/persona con casi nada recuperado. Por eso el waterfall de
descartados va por Clay, no por Apollo.

## Gateways (MX)

`dig +short MX <dominio>`: `pphosted.com` Proofpoint, `mimecast.com` Mimecast,
`iphmx.com` Cisco (ciego → descartar), `barracudanetworks.com` Barracuda. El tech stack de
Apollo a veces viene vacío; el MX manda. Guardar en columna `MX_Gateway`.
