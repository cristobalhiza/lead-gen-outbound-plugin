# sarava-leadgen

Plugin de Claude Code con el proceso de lead gen outbound de Saravá. Trae dos skills:

| Skill | Para qué |
|---|---|
| `lead-gen` | De un ICP o una lista de empresas a contactos verificados en HubSpot, Instantly (con email) y Prosp (sin email). |
| `email-variants` | Variantes de copy para los pasos de una campaña de Instantly, contra el fingerprinting de copy. |

## Instalar (una vez por persona)

1. **Claude Code** (terminal o app de escritorio). Las skills corren scripts en tu computador:
   no funcionan desde claude.ai en el navegador. **Python** no lo instalas tú: si falta, Claude
   lo instala la primera vez (te pide aprobar el comando y, en Windows, quizás una ventana de
   permisos).
2. **Conectores** en tu cuenta de claude.ai (Configuración → Conectores):

   | Conector | Para qué |
   |---|---|
   | Apollo | Empresas, personas y emails |
   | Clay | Segunda fuente de empresas y personas, waterfall de email |
   | HubSpot | Dedupe y carga al CRM del cliente (o token del cliente, ver abajo) |
   | n8n | Verificación de emails, subida a Instantly y Prosp, variantes de copy |

   n8n: conéctalo desde https://claude.ai/directory/n8n con la URL de la instancia de Saravá e
   inicia sesión con la cuenta compartida de n8n para autorizar (pide la URL y el acceso a
   Cristóbal por un canal privado, nunca por el chat con Claude). No necesitas la clave del
   webhook ("Lead-gen webhook"): el conector llama a los flujos sin ella.
3. **CLI de Clay**, solo si vas a armar universos grandes por ICP: pídele a Claude
   "configura Clay".
4. **El plugin** (una sola vez):

   - **Desde la app de escritorio:**
     1. Abre **Settings**.
     2. En la navegación de la izquierda, sección **Customize**, entra a **Plugins**.
     3. Botón **+ Add** → **Add marketplace**.
     4. En el modal elige **Add from a repository** y pega
        `cristobalhiza/lead-gen-outbound-plugin`
        (o `https://github.com/cristobalhiza/lead-gen-outbound-plugin`).
     5. En la lista de plugins de ese marketplace, instala **sarava-leadgen**.
   - **Desde la terminal de Claude Code:**
     ```
     /plugin install sarava-leadgen --marketplace cristobalhiza/lead-gen-outbound-plugin
     ```

   Reinicia la app o la sesión para que cargue.

Para actualizar cuando haya cambios: **Settings → Customize → Plugins** en la app, o
`claude plugin update sarava-leadgen@sarava` en la terminal.

Si no eres de perfil técnico, haz los pasos 1 a 4 en una llamada corta con alguien del equipo;
después todo es conversar con Claude.

**Las claves no pasan por el chat.** Las de Reoon, BounceBan, Instantly y Prosp viven en
credenciales de la instancia n8n de Saravá, y los flujos se llaman con el conector. Apollo,
Clay y HubSpot van por sus conectores. Si un cliente usa token de HubSpot, la skill pregunta
solo el **nombre** de la variable del `.env`, nunca el valor.

## Cómo se usa

### lead-gen

Abre Claude Code en la carpeta del cliente (ej. `~/Proyectos/<cliente>/`) y pide, por ejemplo:

> Comencemos un lead gen para Acme: proveedores de minería en México, 11+ empleados, CEO, CHRO, COO, 3 por empresa.

La skill:

1. **Clarifica** (antes de gastar nada): origen de las empresas (ICP o lista), blacklist
   opcional, cargos (ofrece ampliarlos), seniority mínimo, tope por empresa y prioridad, CRM
   (portal, idioma, reglas), IDs de Instantly y Prosp, presupuesto, meta por tanda. Todo
   queda en `campaign.yaml`.
2. **Empresas**: universo por ICP (Apollo + Clay), blacklist, normalización de nombres
   (script + revisión con Haiku), dominios, enriquecimiento, existentes en HubSpot.
3. **Personas**: Apollo + Clay, dedupe, tope por empresa.
4. **Emails**: enriquecimiento Apollo, filtro de calidad, waterfall Clay.
5. **Verificación** (n8n): Reoon y luego BounceBan solo para catch-all/unknown, con tu OK al costo.
6. **CRM** y **outreach**: HubSpot primero, después Instantly (con email) y Prosp (sin email),
   siempre en seco antes de la subida real.

Trabaja por tandas (piloto de ~40 empresas, o la meta del día si hay plazo) y deja todo en
`state.md`, así otra sesión puede retomar con "sigamos con la campaña X".

También se pueden llamar directo: `/sarava-leadgen:lead-gen` y `/sarava-leadgen:email-variants`.

### email-variants

> Créame 9 variantes además de la original para todos los pasos de https://app.instantly.ai/app/campaign/<id>/editor

Pregunta cuántas variantes por paso, conserva el original, cambia estructura y largo (no
sinónimos), no usa spintax, no inventa contenido y avisa las frases repetidas entre
versiones. Solo escribe si la campaña está en borrador y respalda antes.

## Puntos de control

Nada que gaste créditos o escriba afuera corre sin tu OK: búsquedas grandes, enriquecimiento
Apollo, BounceBan, HubSpot, Instantly y Prosp. Antes de cada escritura ves una muestra y los
conteos.

## Limitaciones conocidas

- Los scripts locales de respaldo (`verify_router.py`, `instantly_upload.py`, etc.) viven en
  otro repo y solo se usan si el conector n8n no está disponible.
- Lo propio de tu equipo (ruta de scripts locales, clientes con script de CRM o scoring
  propio, reglas fijas por cliente) va en `~/.claude/sarava-leadgen.local.md`, fuera del repo.
  La skill lo lee si existe.

## Estructura

```
.claude-plugin/        plugin.json + marketplace.json
skills/lead-gen/       SKILL.md, campaign.template.yaml, references/, scripts/
skills/email-variants/ SKILL.md, scripts/variants.py
```

Los scripts traen autopruebas que corren al importarlos (`python3 scripts/<script>.py --help`).
