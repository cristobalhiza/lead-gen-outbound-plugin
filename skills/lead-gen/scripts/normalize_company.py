#!/usr/bin/env python3
"""Normaliza nombres de empresa para CRM: quita forma legal, "A - B" -> A,
TODO MAYUSCULA -> Title Case. Marca para revision lo que no es obvio.

Uso:  python3 normalize_company.py entrada.csv --col Empresa > salida.csv
Agrega columnas Company_Normalized y Normalize_Flag (vacio = sin dudas).
"""
import argparse, csv, re, sys

# Orden importa: las largas primero ("S.A. de C.V." antes que "S.A.").
# Una sola lista para todos los paises (no chocan entre si). Pais nuevo -> agregar aca + assert.
_S, _CV = r"s\.?\s*", r"(?:\s+de?\s+c\.?\s*v\.?)?"     # MX: "de C.V." opcional al final
LEGAL = [_S + r"a\.?\s*p\.?\s*i\.?" + _CV, _S + r"a\.?\s*b\.?" + _CV,      # MX: SAPI, SAB
         _S + r"de?\s+r\.?\s*l\.?" + _CV, _S + r"a\.?\s+de\s+c\.?\s*v\.?",   # MX: S. de R.L., S.A. de C.V.
         r"s\.?\s?a\.?\s?s\.?", r"s\.?\s?a\.?\s?u\.?", r"s\.?\s?l\.?\s?u\.?",  # CO SAS, AR SAU, ES SLU
         r"s/a", r"eireli",                                                   # BR
         r"s\.?\s?a\.?\s?c\.?", r"s\.?\s?a\.?\s?a\.?", r"s\.?\s?c\.?", r"a\.?\s?c\.?",  # PE; MX S.C., A.C.
         r"s\.?\s?p\.?\s?a\.?", r"s\.?\s?r\.?\s?l\.?", r"e\.?\s?i\.?\s?r\.?\s?l\.?",
         r"s\.?\s?a\.?", r"s\.?\s?l\.?", r"ltda\.?", r"limitada", r"y\s+c[ií]a\.?",
         r"&\s*c[ií]a\.?", r"c[ií]a\.?", r"inc\.?", r"llc", r"l\.?l\.?c\.?", r"corp\.?",
         r"corporation", r"ltd\.?", r"limited", r"gmbh", r"plc", r"co\.?"]
LEGAL_RE = re.compile(r"[\s,]+(?:%s)\s*$" % "|".join(LEGAL), re.I)
# "X, S.A. de C.V. (SIGLA)": forma legal antes de un parentesis final
LEGAL_PAREN_RE = re.compile(r"[\s,]+(?:%s)\s*(?=\([^)]*\)\s*$)" % "|".join(LEGAL), re.I)
OFFICIAL_RE = re.compile(r"\s*\((?:official(?: account)?|oficial|cuenta oficial)\)\s*$", re.I)
MINUS = {"de", "del", "la", "las", "los", "y", "e", "el", "en", "para", "por", "a", "of",
         "and", "the", "for", "to"}


# Primeras palabras de 2-3 letras que son palabra, no sigla.
COMUNES = {"san", "sur", "gas", "eco", "geo", "oro", "mar", "sol", "red", "pro", "top", "big",
           "one", "air", "oil", "bio", "max", "new", "tec", "mas", "uno", "mix", "art", "all",
           "el", "la", "los", "las", "del", "mi", "my", "go", "rio", "luz", "fe", "via"}


INICIOS = {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "tr", "ch", "ll",
           "sh", "th", "st", "sp", "sc", "sk", "sl", "sm", "sn", "sw", "ph", "wh", "kr", "kl",
           "xp", "ps", "qu"}


def es_sigla(w, i):
    """Regla fija de mayusculas (no la decide el LLM): 2-3 letras al inicio (MGA, OTI, UAN),
    sin vocales (CMPC, 3L, WD/360), hasta 5 letras que empiezan con dos consonantes que no
    abren silaba (TMAZ, XMIN) o 4 letras con 3 consonantes seguidas (MPPI, MSHA, EQMS).
    El resto va como palabra (Icsa, Imsa, Amsu, Garco)."""
    letras = re.sub(r"[^a-zñ]", "", w.lower())
    if not letras:
        return False
    if not re.search(r"[aeiouyáéíóú]", letras):
        return True
    if i == 0 and 2 <= len(letras) <= 3 and letras not in COMUNES and re.fullmatch(r"[\w&./]+", w.strip("()")):
        return True
    if len(letras) <= 5 and letras[:2] not in INICIOS and not re.match(r"[aeiouyáéíóú]", letras) \
            and not re.match(r".[aeiouyáéíóú]", letras):
        return True                        # TMAZ, XMIN: dos consonantes que no abren silaba
    return len(letras) == 4 and bool(re.search(r"[^aeiouyáéíóú]{3}", letras))


def normalize(name):
    """-> (normalizado, flag). flag != "" significa revisar a mano."""
    orig = name.strip()
    flags = []
    s = orig
    # "A - B" -> A (solo guion con espacios; "Coca-Cola" queda igual)
    if re.search(r"\s[-–—]\s", s):
        s = re.split(r"\s[-–—]\s", s)[0]
        flags.append("guion: se dejo la primera parte")
    s = OFFICIAL_RE.sub("", s)
    s = re.sub(r"(?:\s+|\.)mx\.?$", "", s, flags=re.I)   # sufijo de pais: "Promas MX", "ESJ.MX"
    s = LEGAL_PAREN_RE.sub(" ", s)
    s = re.sub(r"\s*\([^)]*\b(?:s\.?\s*a\.?\s*p\.?\s*i|s\.?\s*a\.?\s*de\s+c\.?\s*v)\b[^)]*\)\s*$", "", s, flags=re.I)  # "(Arsenal SAPI de CV)"
    prev = None
    while prev != s:                       # "Foo S.A. y Cia. Ltda." trae varias
        prev, s = s, LEGAL_RE.sub("", s).strip(" ,.")
    todo = s.isupper() or s.islower()      # mezclado: solo se tocan las palabras en MAYUSCULA
    if todo and s.isupper():
        first = re.sub(r"\W", "", s.split()[0]) if s.split() else ""
        if 2 <= len(first) <= (4 if len(s.split()) > 1 else 5):
            flags.append("primera palabra corta: posible sigla")
    words = []
    for i, w in enumerate(s.split()):
        if not todo and not (w.isupper() and len(re.sub(r"[^A-ZÑÁÉÍÓÚ]", "", w)) >= 2):
            words.append(w)
        elif es_sigla(w, i):
            words.append(w.upper())        # sigla: CMPC, MGA, MPPI, 3L
        elif i and w.lower() in MINUS:
            words.append(w.lower())
        else:
            words.append("-".join(re.sub(r"\w", lambda m: m.group().upper(), p.lower(), count=1) for p in w.split("-")))
    s = " ".join(words)
    if any(len(re.sub(r"\W", "", w)) <= 4 and w.isupper() for w in words):
        flags.append("posible sigla")
    s = re.sub(r"(?<=\s)(Y|De|Del)(?=\s)", lambda m: m.group().lower(), s)  # "Cribas Y Equipos", "Nacional De Cobre"
    if not s:
        return orig, "quedo vacio: revisar"
    return s, "; ".join(flags)


def demo():
    assert normalize("EMPRESAS CMPC S.A.") == ("Empresas CMPC", "posible sigla")
    assert normalize("Codelco - División El Teniente")[0] == "Codelco"
    assert normalize("Sodimac S.A.")[0] == "Sodimac"
    assert normalize("Inversiones Foo SpA") == ("Inversiones Foo", "")
    assert normalize("Bar y Cía. Ltda.")[0] == "Bar"
    assert normalize("COCA-COLA EMBONOR S.A.")[0] == "Coca-Cola Embonor"
    assert normalize("BANCO DE CHILE")[0] == "Banco de Chile"
    assert normalize("Grupo Saesa")[0] == "Grupo Saesa"   # mixed case: no se toca
    assert normalize("Grupo IRON de México")[0] == "Grupo Iron de México"
    assert normalize("Grupo SMM")[0] == "Grupo SMM" and normalize("iPhone Store")[0] == "iPhone Store"
    assert normalize("Arauco S.A. - Planta Nueva Aldea")[0] == "Arauco"
    # MX
    assert normalize("UAN SOLUTIONS S. DE R.L. DE C.V.") == ("UAN Solutions", "primera palabra corta: posible sigla; posible sigla")
    assert normalize("Sagitta Rock Tools S de RL de CV")[0] == "Sagitta Rock Tools"
    assert normalize("CRIBAS Y EQUIPOS INDUSTRIALES SA DE CV")[0] == "Cribas y Equipos Industriales"
    assert normalize("Cribas Y Equipos Industriales")[0] == "Cribas y Equipos Industriales"
    assert normalize("Grupo Foo, S.A.P.I. de C.V.")[0] == "Grupo Foo"
    assert normalize("Arsenal SAPI de CV")[0] == "Arsenal"
    assert normalize("Grupo Bar S.A.B. de C.V.")[0] == "Grupo Bar"
    assert normalize("Siima S.C")[0] == "Siima"
    assert normalize("Camara Minera A.C.")[0] == "Camara Minera"
    assert normalize("Baz S. A. de C. V.")[0] == "Baz"
    # otros paises
    assert normalize("Qux S.A.S.")[0] == "Qux" and normalize("Quux S.A.U.")[0] == "Quux"
    assert normalize("Vale S/A")[0] == "Vale" and normalize("Corge S.L.U.")[0] == "Corge"
    assert normalize("Fundidora de Cananea, S.A. de C.V. (FUCASA)")[0] == "Fundidora de Cananea (Fucasa)"
    assert normalize("Xanor de México S.A. de C.V. (Official)")[0] == "Xanor de México"
    assert normalize("Arsenal Tire Performance Tech (Arsenal SAPI de CV)")[0] == "Arsenal Tire Performance Tech"
    assert normalize("Inductotherm Heating & Welding Mexico S d RL d CV")[0] == "Inductotherm Heating & Welding Mexico"
    assert normalize("EQUIPOS Y EXPLOSIVOS DEL NORESTE (EYENESA)")[0] == "Equipos y Explosivos del Noreste (Eyenesa)"
    assert normalize("AMSU") == ("Amsu", "primera palabra corta: posible sigla")
    for orig, esperado in [("MGA CONTRATISTA MINERA", "MGA Contratista Minera"), ("OTI INGENIERÍA", "OTI Ingeniería"),
                           ("ICSA INDUSTRIAS CAMPUZANO", "Icsa Industrias Campuzano"), ("IMSA", "Imsa"),
                           ("MPPI SOLUTIONS", "MPPI Solutions"), ("MSHA", "MSHA"), ("EQMS", "EQMS"),
                           ("3L GLOBAL COMPANY SUPPLY", "3L Global Company Supply"), ("WD/360", "WD/360"),
                           ("AAA WELDING & GAS", "AAA Welding & Gas"), ("ECO DRILLING MEXICO", "Eco Drilling Mexico"),
                           ("SAN LUIS RASSINI", "San Luis Rassini"), ("GARCO", "Garco"), ("TREE CORP", "Tree"),
                           ("SANY MEXICO", "Sany Mexico"), ("IG TYRES", "IG Tyres"), ("UM MINING", "UM Mining"),
                           ("TMAZ", "TMAZ"), ("XPLOR", "Xplor"), ("TECLUBIN", "Teclubin"), ("GRUPO SMM", "Grupo SMM"),
                           ("PROMAS", "Promas"), ("TREN", "Tren"), ("STAR", "Star")]:
        assert normalize(orig)[0] == esperado, (orig, normalize(orig)[0])
    assert normalize("Nacional De Cobre, S.A. De C.V.")[0] == "Nacional de Cobre"
    assert normalize("ESJ.MX")[0] == "ESJ" and normalize("Critical To Quality")[0] == "Critical To Quality"
    assert normalize("PROMAS MX")[0] == "Promas" and normalize("Gammaco Mx")[0] == "Gammaco"
    assert normalize("Power V")[0] == "Power V" and normalize("Coca-Cola")[0] == "Coca-Cola"


demo()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--col", required=True)
    a = p.parse_args()
    r = csv.DictReader(open(a.csv, encoding="utf-8-sig"))
    w = csv.DictWriter(sys.stdout, fieldnames=r.fieldnames + ["Company_Normalized", "Normalize_Flag"])
    w.writeheader()
    for row in r:
        row["Company_Normalized"], row["Normalize_Flag"] = normalize(row[a.col])
        w.writerow(row)
