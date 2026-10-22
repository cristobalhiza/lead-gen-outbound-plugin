#!/usr/bin/env python3
"""Saca del universo las empresas de la blacklist del cliente (por dominio, y por nombre
normalizado solo si a la empresa le falta dominio).

Uso:  python3 blacklist.py universo.csv blacklist.csv [--dom-col Domain] [--name-col Company]
                           [--bl-dom-col Domain] [--bl-name-col Company] --out 00_companies.csv
Escribe --out (las que siguen) y 00_blacklisted.csv al lado (las descartadas + Blacklist_Match).
"""
import argparse, csv, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalize_company import normalize


def dominio(v):
    """'https://www.Foo.com.mx/contacto' -> 'foo.com.mx'"""
    v = (v or "").strip().lower()
    v = re.sub(r"^[a-z]+://", "", v)
    v = re.split(r"[/?#:\s]", v)[0].strip(".")
    return re.sub(r"^www\d?\.", "", v)


def nombre(v):
    """'Grupo Foo, S.A. de C.V.' -> 'grupo foo' (sin forma legal, tildes ni signos)"""
    v = unicodedata.normalize("NFKD", normalize(v or "")[0]).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", v.lower()).split())


def match(dom, nom, bl_doms, bl_noms):
    """-> motivo o "". Un subdominio cuenta (mx.foo.com matchea foo.com)."""
    if dom:
        partes = dom.split(".")
        for i in range(len(partes) - 1):
            if ".".join(partes[i:]) in bl_doms:
                return "dominio " + ".".join(partes[i:])
        return ""                          # con dominio, el nombre no se usa (homonimos)
    return "nombre " + nom if nom and nom in bl_noms else ""


def demo():
    assert dominio("https://www.Foo.com.mx/contacto?x=1") == "foo.com.mx"
    assert dominio("http://www2.bar.cl:8080") == "bar.cl" and dominio(" baz.com. ") == "baz.com"
    assert nombre("Grupo Foo, S.A. de C.V.") == nombre("GRUPO FOO SA DE CV") == "grupo foo"
    assert nombre("Compañía Minera Ñandú") == "compania minera nandu"
    d, n = {"foo.com"}, {"grupo bar"}
    assert match("mx.foo.com", "", d, n) == "dominio foo.com"
    assert match("notfoo.com", "", d, n) == ""
    assert match("", "grupo bar", d, n) == "nombre grupo bar"
    assert match("otro.com", "grupo bar", d, n) == ""


demo()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("universo"); p.add_argument("blacklist"); p.add_argument("--out", required=True)
    p.add_argument("--dom-col", default="Domain"); p.add_argument("--name-col", default="Company")
    p.add_argument("--bl-dom-col", default="Domain"); p.add_argument("--bl-name-col", default="Company")
    a = p.parse_args()
    bl = list(csv.DictReader(open(a.blacklist, encoding="utf-8-sig")))
    bl_doms = {dominio(r.get(a.bl_dom_col)) for r in bl} - {""}
    bl_noms = {nombre(r.get(a.bl_name_col)) for r in bl} - {""}
    r = csv.DictReader(open(a.universo, encoding="utf-8-sig"))
    campos = r.fieldnames
    sigue, fuera = [], []
    for row in r:
        m = match(dominio(row.get(a.dom_col)), nombre(row.get(a.name_col)), bl_doms, bl_noms)
        (fuera if m else sigue).append({**row, "Blacklist_Match": m} if m else row)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos); w.writeheader(); w.writerows(sigue)
    out_bl = os.path.join(os.path.dirname(os.path.abspath(a.out)), "00_blacklisted.csv")
    with open(out_bl, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos + ["Blacklist_Match"]); w.writeheader(); w.writerows(fuera)
    print(f"blacklist: {len(bl)} filas ({len(bl_doms)} dominios) | universo: {len(sigue) + len(fuera)}"
          f" | siguen {len(sigue)} | descartadas {len(fuera)} -> {out_bl}")
