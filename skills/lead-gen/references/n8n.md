# Flujos n8n de lead gen (claves solo en n8n)

ESTADO 2026-10-21: los 4 flujos publicados (executionMode "production") y probados en vivo;
son la vía por defecto. El cache de verificación es el de n8n (el local de verify_router no se
comparte). Prosp no tiene borrado por API: un lead subido por error se saca desde la UI.

Usar solo si el conector n8n está disponible. Las claves viven en credenciales de n8n; la skill
nunca ve ni pide secretos. Los webhooks llevan Header Auth ("Lead-gen webhook"); el conector
no necesita el header.

## Cómo llamar

`execute_workflow` con `triggerNodeName: "Webhook"`, `inputs: {webhookData: {method: "POST",
body: {...}}}`, `executionMode: "production"` (publicado) o `"manual"` (borrador). Devuelve
`executionId` al instante; el resultado se lee con `get_workflow_execution` (`includeData`,
`nodeNames`). Input inválido → la ejecución queda en error con el mensaje "input inválido: ...".

**Todo `dry_run: false` (y todo `limit_bounceban > 0`) requiere OK explícito del usuario,
con el resultado del dry run a la vista.**

| Flujo | ID |
|---|---|
| verify-emails | 10S0lqLv81UxiOQp |
| bounceban-recover | maopFC6H2WlQ0z04 |
| prosp-upload | xc8iSwAhwG6QBvqN |
| campaign-hub-sync | rq6yeEwj5vDurjx7 |

Data tables (proyecto 499h0jTs4i5ljWD1): verify_cache OfbDGtm5yWSW1qIh,
verify_results 9BwOh1MPpudr8BCC, verify_runs Hm2OR6agABiToizh.

## verify-emails (asíncrono)

Body: `{run_id: [\w.:-]{1,80}, emails: [{email, score?, mx_gateway?}] (1-2000),
limit_bounceban: 0-1000 (sin él no gasta), dry_run: bool, bb_domains: [], blocked_domains: []}`.
Misma lógica que verify_router (sin IPQS). Si Reoon falla, el email queda Pending
"PENDIENTE - Reoon sin respuesta (HTTP n)" y no va a BounceBan. En seco no llama ni a Reoon y marca
"SECO - iría a BounceBan": la cola del seco está inflada (caso real: 127 en seco vs 44 reales). Para
estimar costo: corrida real con `limit_bounceban: 0` → `resumen.cola_bounceban` → segunda corrida
con el límite aprobado.

Resultado: polling de `verify_runs` (filtrar `run_id`) hasta `status = done`, después leer
`verify_results` por `run_id`: `{email, verdict: Send|Discard|Pending, motivo, score}`. Si queda
en `running` y la ejecución está en error → avisar al usuario (también le llega un DM del
flujo de errores).

## bounceban-recover

Body `{task_ids: [...]}` (1-2000). Gratis (solo `?id=`). Resumen:
`{pedidos, recuperados, por_resultado, credits_remaining, fallos}`; hace upsert en verify_cache.

## prosp-upload

Body `{list_id, campaign_id (obligatorios), dry_run (true por defecto), leads: [{linkedin_url
(linkedin.com/in/...), name, job_title, company, hs_lead_id?}]}`. Seco → nodo "¿Subir?"
(salida false): aceptados, rechazados, muestra. Real → nodo Resumen: `{subidos, total, fallos}`.
Prosp corta cerca de 50/min (429): mandar bodies de ≤40 leads con 1 min entre ejecuciones y
reintentar los `fallos` 429 tras la pausa (caso real: exec 2865 subió 50/85, reintento 2867 35/35).

## campaign-hub-sync

ESTADO 2026-11-27: **listo**. Publicado (`rq6yeEwj5vDurjx7`, carpeta Lead-gen) y probado contra
producción con `list_universes` y `get_universe`; las acciones de escritura se estrenan en la
primera tanda piloto (revisar `status` y la vista del universo). Mismo Header Auth que los otros
flujos ("Lead-gen webhook"); responde con la respuesta de Campaign Hub más `status` (código
HTTP): `execute_workflow` (`executionMode: "production"`) y leer el nodo "Respuesta".

Reenvía el body tal cual a `POST /api/webhooks/leadgen` de Campaign Hub (el token
`LEADGEN_WEBHOOK_TOKEN` vive en la credencial del flujo) y devuelve la respuesta. Body:
`{action, ...}` en `snake_case`; acciones `list_universes`, `get_universe`, `upsert_companies`
(≤2000 empresas), `start_wave`, `update_wave`, `set_request_status`. Cuándo llamar cada una:
SKILL.md, sección Campaign Hub. Contrato y ejemplos: Campaign Hub,
`docs/features/leadgen-sync.md`. Errores: 400 nombra el campo o la fila (no se escribió nada),
404 universo/tanda/solicitud inexistente, 401 token mal configurado en n8n (avisar a Cristóbal).
