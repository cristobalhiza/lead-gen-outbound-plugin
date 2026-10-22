#!/usr/bin/env python3
"""Variantes de copy para una campaña de Instantly: original intacto (posición 0) + N variantes por paso.

Los textos los escribe el agente en <carpeta>/variantes/c<id8>.py:
    V = {1: [("", None), ("asunto", \"\"\"cuerpo sin firma\"\"\"), ...], 2: [...]}
posición 0 = original (se toma de Instantly, no se escribe); cuerpo en texto plano, la firma
se copia del original.

    python3 variants.py <campaign_id> --campaign-json raw/campaign_<id8>.json [--dir .]
        valida + copy_variantes_<id8>.md para revisar + raw/sequences_update_<id8>.json
        (el `sequences` que va al flujo n8n instantly-sequences, action update)
La campaña se lee con el flujo n8n instantly-sequences (action get) y se guarda en --campaign-json.
Respaldo sin n8n: sin --campaign-json lee la API y --apply escribe (solo borrador), con la clave
del .env por NOMBRE (--key-env instantly_api_key; el valor no se imprime).
--replace: la campaña ya tiene variantes; conserva la 0 y reemplaza el resto.
"""
import argparse, html, importlib.util, json, os, re, sys, time, urllib.request

VARS = re.compile(r"\{\{\s*(\w+)\s*\}\}")
SPINTAX = re.compile(r"\{\{\s*random\b|\{[^{}|]*\|[^{}]*\}", re.I)   # {{RANDOM|a|b}} o {a|b}


def to_text(h):
    h = re.sub(r"<li>", "• ", h)
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"</(div|li|ul|p)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", "", h)).replace("​", "")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(l.rstrip() for l in t.split("\n"))).strip()


def signature(orig_html):
    """Firma del original: el último párrafo que contiene la variable de firma ("Saludos,\\n{{accountSignature}}")."""
    paras = to_text(orig_html).split("\n\n")
    hits = [p for p in paras if re.search(r"\{\{\s*\w*signature\w*\s*\}\}", p, re.I)]
    return hits[-1] if hits else ""


def to_html(t, sig):
    full = t.strip() + ("\n\n" + sig if sig else "")
    return "".join("<div>%s</div>" % (html.escape(l, quote=False) if l else "<br />") for l in full.split("\n"))


def frases(t):
    return {f.strip().lower() for f in re.split(r"(?<=[.?!])\s+|\n+", t) if len(f.strip()) > 30}


def check(V, steps):
    """Errores duros (assert) + avisos de huella de copy (frases repetidas entre versiones)."""
    assert sorted(V) == list(range(1, len(steps) + 1)), "pasos: variantes %s vs campaña %d" % (sorted(V), len(steps))
    n = {len(v) for v in V.values()}
    assert len(n) == 1, "todos los pasos deben tener la misma cantidad de versiones: %s" % n
    avisos = []
    for i, s in enumerate(steps, 1):
        o = s["variants"][0]
        allowed = set(VARS.findall(o["subject"] + o["body"]))
        sig = signature(o["body"])
        vistas = {f: "original" for f in frases(to_text(o["body"]).replace(sig, ""))}
        for j, (subj, body) in enumerate(V[i][1:], 1):
            assert body and body.strip(), "paso %d variante %d vacía" % (i, j)
            used = set(VARS.findall(subj + body))
            assert used <= allowed, "paso %d v%d usa variables que no están en el original: %s" % (i, j, used - allowed)
            assert (subj == "") == (o["subject"].strip() == ""), "paso %d v%d: asunto vacío (mismo hilo) debe coincidir con el original" % (i, j)
            assert not SPINTAX.search(subj + body), "paso %d v%d tiene spintax" % (i, j)
            assert not (sig and sig.split("\n")[-1] in body), "paso %d v%d: la firma la agrega el script, no va en el cuerpo" % (i, j)
            for f in frases(body):
                if f in vistas:
                    avisos.append("paso %d v%d repite una frase de %s: \"%s\"" % (i, j, vistas[f], f[:70]))
                vistas.setdefault(f, "v%d" % j)
    return avisos


def _check():
    assert to_text("<div>Hola<br /><br /></div><ul><li><strong>A:</strong> b</li></ul><div>{{x}}</div>") == "Hola\n\n• A: b\n\n{{x}}"
    assert signature("<div>Hola</div><div><br /></div><div>Saludos,</div><div>{{accountSignature}}</div>") == "Saludos,\n{{accountSignature}}"
    assert to_text(to_html("Hola\n\nX", "Saludos,\n{{s}}")) == "Hola\n\nX\n\nSaludos,\n{{s}}"
    assert SPINTAX.search("{Hola|Buenas} Ana") and SPINTAX.search("{{RANDOM | a | b}}") and not SPINTAX.search("{{firstName}}")
    o = {"subject": "Hola {{firstName}}", "body": "<div>Texto uno bastante largo para contar como frase.</div><div><br /></div><div>Saludos,</div><div>{{sig}}</div>"}
    assert check({1: [("", None), ("Otro {{firstName}}", "Texto uno bastante largo para contar como frase.")]}, [{"variants": [o]}])
    try:
        check({1: [("", None), ("x", "{Hola|Buenas} {{firstName}}")]}, [{"variants": [o]}]); raise SystemExit("spintax no detectado")
    except AssertionError:
        pass


_check()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("campaign_id"); p.add_argument("--dir", default=".")
    p.add_argument("--apply", action="store_true"); p.add_argument("--replace", action="store_true")
    p.add_argument("--campaign-json"); p.add_argument("--key-env", default="instantly_api_key")
    a = p.parse_args()
    tag = a.campaign_id[:8]
    os.makedirs(os.path.join(a.dir, "raw"), exist_ok=True)

    def api(method, path, body=None):
        env = next((d for d in (a.dir, os.path.join(a.dir, ".."), os.path.join(a.dir, "..", "..")) if os.path.exists(os.path.join(d, ".env"))), None)
        assert env, "no hay .env con %s" % a.key_env
        k = next(l.split("=", 1)[1].strip() for l in open(os.path.join(env, ".env")) if l.startswith(a.key_env + "="))
        req = urllib.request.Request("https://api.instantly.ai/api/v2/" + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + k, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        return json.load(urllib.request.urlopen(req, timeout=60))

    camp = json.load(open(a.campaign_json)) if a.campaign_json else api("GET", "campaigns/" + a.campaign_id)
    steps = camp["sequences"][0]["steps"]
    vf = os.path.join(a.dir, "variantes", "c%s.py" % tag)
    if not os.path.exists(vf):                 # primera lectura: respaldo + originales para leer
        json.dump(camp, open(os.path.join(a.dir, "raw", "campaign_%s_original.json" % tag), "w"), ensure_ascii=False, indent=1)
        open(os.path.join(a.dir, "copy_originales_%s.md" % tag), "w").write("# %s\n" % camp["name"] + "".join(
            "\n## Paso %d (espera %s días) · %d variante(s) hoy\n**Asunto:** %s\n\n```\n%s\n```\n" % (
                i, s["delay"], len(s["variants"]), s["variants"][0]["subject"].replace("\u200b", "") or "(mismo hilo)",
                to_text(s["variants"][0]["body"])) for i, s in enumerate(steps, 1)))
        sys.exit("sin %s todavía: originales en copy_originales_%s.md, respaldo en raw/" % (vf, tag))
    spec = importlib.util.spec_from_file_location("v", vf)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if any(len(s["variants"]) > 1 for s in steps) and not a.replace:
        sys.exit("la campaña ya tiene variantes: confirmar con el usuario y usar --replace (conserva la 0)")
    orig = [dict(s, variants=s["variants"][:1]) for s in steps]
    avisos = check(mod.V, orig)
    out, md = [], ["# Variantes · %s\n\nOriginal + %d por paso. Palabras = cuerpo sin firma.\n" % (camp["name"], len(mod.V[1]) - 1)]
    for i, s in enumerate(orig, 1):
        o = s["variants"][0]; sig = signature(o["body"])
        vs = [dict(o)] + [{"subject": subj, "body": to_html(b, sig)} for subj, b in mod.V[i][1:]]
        out.append(dict(s, variants=vs))
        largos = [len(to_text(v["body"]).replace(sig, "").split()) for v in vs]
        md.append("\n## Paso %d (espera %s días) · %d-%d palabras\n" % (i, s["delay"], min(largos), max(largos)))
        for j, v in enumerate(vs):
            md.append("\n### %s · %d palabras\n**Asunto:** %s\n\n```\n%s\n```\n" % (
                "Original" if j == 0 else "Variante %d" % j, largos[j],
                v["subject"].replace("​", "") or "(mismo hilo)", to_text(v["body"])))
    if avisos:
        md.insert(1, "\n**Frases repetidas (huella de copy, revisar):**\n" + "".join("- %s\n" % x for x in avisos))
    open(os.path.join(a.dir, "copy_variantes_%s.md" % tag), "w").write("".join(md))
    payload = os.path.join(a.dir, "raw", "sequences_update_%s.json" % tag)
    json.dump([dict(camp["sequences"][0], steps=out)], open(payload, "w"), ensure_ascii=False)
    print("copy_variantes_%s.md listo · %d avisos de frases repetidas · payload n8n: %s" % (tag, len(avisos), payload))
    if a.apply:
        assert not a.campaign_json, "--apply necesita leer la campaña en vivo"
        assert camp["status"] == 0, "la campaña no está en borrador: no se escribe"
        bk = os.path.join(a.dir, "raw", "campaign_backup_%s_%s.json" % (tag, time.strftime("%Y%m%d-%H%M%S")))
        json.dump(camp, open(bk, "w"), ensure_ascii=False, indent=1)
        api("PATCH", "campaigns/" + a.campaign_id, {"sequences": [dict(camp["sequences"][0], steps=out)]})
        chk = api("GET", "campaigns/" + a.campaign_id)["sequences"][0]["steps"]
        assert all(c["variants"][0] == s["variants"][0] for c, s in zip(chk, steps)), "¡el original cambió! restaurar desde " + bk
        print("respaldo:", bk, "| variantes por paso en Instantly:", [len(c["variants"]) for c in chk])
