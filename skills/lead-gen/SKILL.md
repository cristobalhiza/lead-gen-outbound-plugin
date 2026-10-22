---
name: lead-gen
description: Lead gen / generación de leads / prospección B2B de Saravá para cualquier cliente - desde un ICP o lista de empresas hasta contactos verificados en HubSpot + Instantly (con email) y Prosp (sin email). Usar SIEMPRE que el usuario quiera hacer, armar, comenzar o retomar un lead gen, buscar leads, prospectos o contactos de empresas, o armar una lista de prospección ("quiero hacer un lead gen", "necesito leads de...", "busca contactos en estas cuentas", "sigamos con la campaña X", "otra tanda"). No es para redactar copy de correos (eso es email-variants). Campaña nueva: empieza SIEMPRE con una fase de clarificación que fija los criterios en campaign.yaml. Campaña existente: retoma desde state.md.
---

# Lead gen

Principio: **nada se asume, todo lo que gasta créditos o escribe afuera tiene un punto de
control.** Cada etapa escribe `NN_etapa.csv` en la carpeta de la campaña, así se puede
retomar desde cualquier etapa sin repetir gasto.

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

## Estado de la campaña (`<carpeta>/state.md`) - obligatorio

Es lo que permite retomar en otra sesión. Dos partes:

1. **Foto actual** (arriba, se reescribe): fecha, tanda y etapa en curso, **próximo paso
   exacto** (comando o llamada), decisiones pendientes del usuario, archivo vigente de cada
   etapa, IDs abiertos (Clay taskId, BounceBan Task IDs 408, n8n run_id/executionId),
   acumulados por destino (HubSpot, Instantly, Prosp), empresas procesadas / restantes,
   créditos gastados (Apollo, BounceBan, Clay).
2. **Historial** (abajo, solo se agrega): una entrada por etapa o tanda cerrada, con fecha,
   conteos, créditos y decisiones del usuario (textuales si cambian criterios).

Se actualiza **al cerrar cada etapa, antes de cada punto de control, al topar un límite de
Apollo y antes de terminar la sesión**, aunque la etapa haya quedado a medias (marcar qué
filas quedaron pendientes). Lo que cambie criterios va además al `campaign.yaml`.

**Al empezar**: si el usuario nombra una campaña o hay un `campaign.yaml` en la carpeta (o en
una subcarpeta), leer `campaign.yaml` + `state.md`, resumir dónde quedó y el próximo paso, y
confirmar antes de seguir. No reconstruir el estado desde los CSV si `state.md` existe; si no
coinciden, avisar.

Herramientas:
- **Flujos n8n** (vía por defecto, claves solo en n8n, cache de verificación compartido):
  `references/n8n.md`. Su ESTADO dice qué flujo está listo; lo que no esté listo va por script.
- **Archivo local** `~/.claude/sarava-leadgen.local.md` (opcional, fuera del repo): leerlo al empezar si existe. Trae
  lo propio de cada equipo: ruta de los scripts locales de respaldo, y carpeta, scripts de CRM,
  scoring y reglas fijas por cliente. Lo que diga para un cliente manda sobre lo genérico.
- **Sin conector n8n**: scripts locales de respaldo (`verify_router.py`, `bounceban_recover.py`,
  `instantly_upload.py`, `prosp_upload.py`) en la ruta del archivo local; uso en
  `references/verificacion.md` y en su `--help`. Anotarlo en `state.md`. Si no hay, avisar.
- De esta skill: `scripts/normalize_company.py` (nombres) y `scripts/blacklist.py` (exclusiones).
- **Apollo, Clay y HubSpot por sus conectores** (MCP; Clay también por CLI). **Nunca leer
  claves del `.env` en código propio** ni llamar las APIs REST directo, aunque la carpeta tenga
  scripts viejos que lo hacen o un `.env` con claves: eso es de antes de los conectores. Si el
  conector no alcanza para el volumen, avisar al usuario en vez de pasarse a REST.

## Fase 0 - Clarify (obligatoria, antes de gastar nada)

Leer el input, contar empresas/columnas, y con eso llenar `campaign.template.yaml` →
`<carpeta>/campaign.yaml`. Si existe un `campaign.yaml`, leerlo y confirmar solo lo que falte.
Preguntar con AskUserQuestion (agrupado, máx. 4 por vez) todo lo que no esté explícito:

0. **Origen de las empresas**: por defecto **ICP** (industria, país, tamaños, otros filtros),
   y el universo se arma en la Fase 1, paso 0. Solo es lista si el usuario adjunta un archivo
   y lo avisa. **Blacklist (opcional)**: preguntar si hay empresas a excluir (clientes
   actuales, competidores, cuentas en curso): CSV con nombre y dominio. Si no hay, se omite.
1. **Carpeta y cliente.** La que diga el archivo local para ese cliente; si no, carpeta del
   cliente (ej. `~/Proyectos/sarava-clientes/<cliente>/...`).
2. **Job titles**: ofrecer siempre ampliarlos (aunque no se pida), siguiendo
   `references/job_titles.md`: biblioteca previa, reglas de seniority/área/siglas, y
   aprobación con los excluidos y dudosos a la vista.
   **Seniority mínimo**: derivarlo de los cargos entregados (el cargo más bajo de la lista
   manda, ej. si hay "Gerente de X" el mínimo es Manager) y **confirmarlo**. Si los cargos y
   el seniority pedido chocan (ej. "mínimo VP" + cargos Manager), mostrar el choque y preguntar.
3. **Tope por empresa** y **criterios de prioridad** para elegir cuáles quedan: seniority,
   relevancia del área (cuál primero), tiene email verificado, antigüedad en el cargo,
   ubicación, otro. Guardar el orden en `priority_order`.
4. **Ubicación** (país/región).
5. **CRM**: cómo se sube. Si hay conector de HubSpot disponible, ver a qué portal está
   conectado (`get_organization_details`: nombre + portal ID) y preguntar si se sube por ahí
   (sin token). Si el portal no es el del cliente, o el usuario prefiere token: el **nombre** de
   la variable del `.env` (nunca pedir que se pegue el valor en el chat; si no existe, que el
   usuario la agregue él al `.env`). Además, **idioma de los valores**
   (en/es), owner, si crea Leads además de Contacts, etiqueta de batch, lista estática,
   propiedades custom, y reglas propias (asociación sitio→matriz, país, `hs_timezone`,
   `target_persona`, etc.). No aplicar reglas de un cliente a otro.
6. **Outreach**: `instantly_campaign_id` y `prosp_list_id` + `prosp_campaign_id` son
   obligatorios para subir (cuenta Saravá salvo que se indique otra). ¿Teléfonos?
7. **Scoring**: ninguno, el modelo del cliente si el archivo local lo define, u otro.
8. **Presupuesto**: tope de créditos BounceBan/Apollo por corrida.
9. **Volumen y ritmo**: cuántos leads se piden por tanda (lo usual: 150-200 por semana, no la
   campaña entera de una vez), si hay una meta con plazo (ej. "160 hoy") y el tamaño del
   piloto (por defecto 40 empresas).

Mostrar el `campaign.yaml` final y pedir OK antes de la Fase 1.

## Tandas (batches)

El universo de empresas (Fase 1, paso 0) se arma una vez. Todo lo que gasta créditos
(Fase 1, pasos 1-5, y Fases 2-6) se corre **por tanda de empresas**, nunca sobre el universo
completo:

1. **Piloto**: las primeras `pilot_companies` (40 por defecto), ordenadas por el criterio que
   diga el usuario (tamaño, prioridad, al azar). Se corre hasta la Fase 4 (verificación).
2. **Medir**: leads por empresa, enviables por empresa (Send), sin email (Prosp), empresas con
   0 leads, créditos por lead enviable. Proyectar cuántas empresas hacen falta para la meta de
   la tanda (`target_leads_per_wave`).
3. **Punto de control**: mostrar la proyección y proponer el tamaño de la siguiente tanda.
   Si el rendimiento es bajo (ej. <1 enviable por empresa), revisar cargos/seniority/ICP con el
   usuario antes de seguir gastando.
4. **Siguientes tandas**: del tamaño aprobado, hasta llegar a la meta de leads de la semana.
   Parar ahí aunque queden empresas: la próxima tanda se corre cuando el usuario la pida.

**Meta con plazo** (ej. "subir 160 hoy"): no hay tiempo para el piloto. La primera tanda se
dimensiona para la meta con un rendimiento conservador (si no hay historial: ~2 leads y ~1
enviable por empresa, más 20% de holgura), se avisa al usuario que reemplaza al piloto y se
anota en `state.md`. Las métricas de esa tanda sirven de piloto para las siguientes.

Columna `Wave` en `00_companies.csv` (vacío = sin procesar). Archivos por tanda:
`NN_etapa_w<K>.csv`. `state.md` lleva el acumulado por tanda y el universo restante.

## Límites de velocidad de Apollo

Apollo limita por minuto, hora y día según el endpoint, también vía MCP. Por eso:
- Preferir los endpoints bulk (`organizations_bulk_enrich`, `people_bulk_match` de 10) a las
  llamadas una por una, y no lanzar muchas llamadas en paralelo.
- Ante un 429 o un error de límite, esperar (con Monitor, no con `sleep`) y reintentar con espera
  creciente. No saltarse las empresas en silencio: deben quedar marcadas como pendientes.
- Anotar en `state.md` qué endpoint cortó y a qué volumen, para dimensionar las tandas siguientes.

## Fase 1 - Empresas

0. **Solo con ICP**: `apollo_mixed_companies_search` con industria, país y rangos de
   empleados de la config (paginar hasta agotar), y Clay con los mismos criterios como segunda
   fuente. Clay por **CLI** (`clay searches`, 500 por página, a archivo) cuando el ICP pasa de
   ~100 empresas: el MCP `search-companies` pagina de a 20 y llena el contexto.
   Unir por dominio. Mostrar conteo por tamaño, una muestra de 20 y las que parezcan fuera del
   ICP (proveedores vs. operadoras, matrices extranjeras sin operación en el país); el usuario
   aprueba el universo → `00_companies.csv`.
   **Blacklist** (si hay `blacklist_file`, con ICP o lista), antes de mostrar el universo:
   `python3 scripts/blacklist.py <universo.csv> <blacklist.csv> --out 00_companies.csv`
   (ver `--help`). Las que recuperen dominio en el paso 3 se vuelven a pasar.
1. **Normalizar nombres**:
   `python3 scripts/normalize_company.py <input.csv> --col <col> > 01_companies.csv`
   Quita forma legal de cualquier país, "A - B" → A, y decide las mayúsculas con una regla fija
   (`es_sigla`: MGA, CMPC, TMAZ, MPPI en mayúscula; Icsa, Garco como palabra). Las filas con
   `Normalize_Flag` las revisa un subagente Haiku con el prompt de
   `references/normalizacion.md` (guiones, siglas conocidas; no toca mayúsculas).
   **Mostrar al usuario los cambios del subagente y sus dudas**; aplicar correcciones antes de
   seguir. (xlsx → convertir a CSV primero.)
2. **Dominios genéricos**: toda empresa cuyo dominio (de Apollo, Clay o el input) sea una
   plataforma y no la empresa → dominio en blanco y se busca en el paso 3. Lista: `google.com`,
   `linkedin.com`, `facebook.com`, `instagram.com`, `youtube.com`, `twitter.com`, `x.com`,
   `wixsite.com`, `wix.com`, `blogspot.com`, `wordpress.com`, `godaddysites.com`,
   `business.site`, `sites.google.com`, `gmail.com`, `hotmail.com`, `outlook.com`,
   `yahoo.com` (y sus subdominios). Si no, Clay trae a los empleados de esa plataforma (caso real:
   62 de Google y LinkedIn). En la Fase 2, toda persona cuya empresa tenga uno de esos dominios
   se descarta.
3. **Dominios faltantes** con WebSearch. Por cada uno: confirmar que la web es de esa empresa
   (no de un homónimo, distribuidor o matriz extranjera) y `dig +short MX <dominio>`
   (sin MX = sospechoso; guardar proveedor en `MX_Gateway`). Columna `Domain_Confidence`
   (high/medium/low). Las `low` se muestran al usuario.
4. **Enriquecer empresas en Apollo** (`apollo_organizations_bulk_enrich` por dominio):
   `organization_id`, LinkedIn de empresa, industria, empleados, país/ciudad. Las que no
   matchean se listan.
5. **Ya existentes en HubSpot**: buscar por dominio/nombre (HubSpot MCP o API con el token
   de la config). Marcar `HS_Company_ID`; no se duplican. → `03_companies_enriched.csv`

## Fase 2 - Personas (Apollo + Clay)

1. **Apollo** `apollo_mixed_people_api_search`: `organization_ids` + `person_titles` +
   `person_seniorities` (de la config) + `person_locations`. Paginado hasta agotar.
2. **Clay** `search-contacts` por las mismas empresas (dominio o LinkedIn de empresa, hasta 10
   por llamada), mismos cargos/seniority/ubicación en DSL, con
   `limit <tope> by clay_company_id`. Se corre siempre como segunda fuente salvo que la config
   diga lo contrario. Guardar el `taskId` (sirve después para el email).
3. **Unir y deduplicar** en dos pasos. Antes del match, Apollo search no trae LinkedIn ni el
   apellido completo: deduplicar por empresa + nombre + inicial del apellido. Después del
   `bulk_match` (Fase 3), de nuevo por URL de LinkedIn normalizada (minúsculas, sin
   `http(s)://www.`, sin `/` final, decodificada). Columna `Source` = apollo | clay | both.
4. **Aplicar tope por empresa** con el `priority_order` de la config. Guardar los que quedaron
   fuera en `04_overflow.csv` (no se pierden). → `04_people.csv`
5. **Punto de control**: conteo por empresa, empresas con 0 leads, costo estimado del
   enriquecimiento. OK del usuario.

## Fase 3 - Enriquecer y emails

1. **Apollo `apollo_people_bulk_match`** (10 por llamada) de los que tienen Apollo ID o
   LinkedIn: email + status, LinkedIn, ciudad, headline, fecha de inicio del cargo, todo lo
   que pide el CRM, en **una sola pasada** (no re-enriquecer al final). Informar el bloque
   `mcp_credits`.
2. **Deduplicar por LinkedIn** (segundo paso de la Fase 2.3): si Apollo y Clay traen a la
   misma persona, queda una fila (gana la que tiene email verificado).
3. **Filtro de calidad, antes de verificar y de HubSpot** (lo que se crea en el CRM y no sale
   a outreach queda sucio). Marcar `Excluir` con motivo y mostrar la lista al usuario:
   - Cargo que nombra otra empresa ("Fundador de X", "Partner at Y" ≠ empresa del lead):
     Clay mezcla experiencias.
   - Perfil que no es persona (nombre = empresa o "RH/RRHH <empresa>", nombre y apellido
     iguales).
   - Área real del cargo: "Gerente General de Calidad/Marketing/Comercial" es de esa área, no
     C-level; "Consultor … Founder" no es ejecutivo de la empresa.
   - LinkedIn cuyo slug no corresponde al nombre del lead.
   - Email cuyo dominio ≠ dominio de la empresa: `dig MX` de ambos; si el proveedor no
     coincide, revisar (variantes `.com`/`.com.mx` con el mismo MX están bien).
4. Quitar contactos que **ya existen en HubSpot** (por email y por LinkedIn) → se marcan, no se
   recrean; preguntar si se actualizan.
5. Columnas estándar (las piden los scripts): `First_Name, Last_Name, Title, Parent_Company,
   Email_Final, Email_Source, LinkedIn, Apollo_ID, MX_Gateway, Final_Score` (vacío si no hay
   scoring). → `05_enriched.csv`
6. **Waterfall Clay** para los sin email (ver `references/verificacion.md`). → `06_emails.csv`
   Si `email.clay_waterfall: true`, se corre o se pregunta con el costo a la vista; **nunca se
   salta en silencio** (ni por apuro con la meta). Si el usuario lo posterga, anotarlo en
   `state.md` como decisión pendiente y los sin email siguen a Prosp.

## Fase 4 - Verificación

Flujo n8n `verify-emails` (`references/n8n.md`; reglas en `references/verificacion.md`), en
dos corridas reales (el `dry_run` no llama a Reoon y manda casi todo a la cola: no sirve para
estimar el costo):
1. `dry_run: false`, `limit_bounceban: 0`: pasa todo por Reoon, no gasta BounceBan.
2. Leer `resumen.cola_bounceban` en `verify_runs` (los unknown/catch_all reales), mostrar
   cola y costo, pedir OK y correr con `limit_bounceban` = cola (o lo que apruebe el usuario)
   y el mismo set de emails (el cache evita re-pagar Reoon).

Resultado → `07_verified_{Send,Discard,Pending}.csv` con `Verify_Verdict` = motivo; `run_id`
a `state.md`; los 408 → `bounceban-recover`.

**Segunda ronda**: los `_Discard` con motivo recuperable (invalid, BounceBan undeliverable)
→ waterfall Clay, descartando si devuelve el mismo email → de vuelta al router. Los descartes
por dominio bloqueado/Cisco/spamtrap no se reintentan.

## Fase 5 - CRM

1. Revisar que **todo valor que sube esté en el idioma de la config** (generar la etiqueta en
   ese idioma en el origen, no traducir después).
2. Cliente con script de CRM propio en el archivo local → ese script, en seco primero.
   Resto → por la vía elegida en la Fase 0 (`crm.via`): conector (antes de escribir,
   confirmar de nuevo que el portal ID coincide con `crm.portal_id`) o API con el token de la
   config. Aplicar solo las reglas de su `crm.rules`.
   Siempre: muestra de 3 registros + conteos crear/actualizar → OK → escribir.
3. Verificar después: conteo en HubSpot = conteo esperado; lista/batch creada.

## Fase 6 - Outreach

Siempre en seco primero, después la subida real con OK explícito: flujos n8n
`instantly-upload` / `prosp-upload` (`dry_run: true`, después `false`).

Instantly: solo `_Send`; sube de menor a mayor score (canario). Prosp: los que no tienen email
enviable y sí LinkedIn. El workspace es compartido entre clientes: el id nunca se adivina.

**Límite de Prosp (~50 leads/min, responde 429):** subir en tandas de ≤40 con 1 min entre
tandas. Los que vuelvan con 429 se reintentan solos después de la pausa (no son rechazo). El
total de Prosp se cuenta por los resúmenes de n8n, porque Prosp no se puede contar por API.

## Cierre

Al cerrar cada tanda: contrastar `campaign.yaml` con las reglas que de verdad se aplicaron
(regla BounceBan, Cisco, cargos rescatados, exclusiones) y corregir el yaml si cambió algo en
la sesión; borrar archivos de estado viejos (`RUN.md`, etc.) si `state.md` ya los cubre.

Resumen en `state.md` y al usuario: empresas, descartadas por blacklist (lista de
`00_blacklisted.csv` con su match), leads por fuente, emails por fuente, Send/Discard/
Pending, créditos gastados (Apollo, BounceBan, Clay), creados/actualizados en HubSpot,
subidos a Instantly/Prosp, y pendientes.
