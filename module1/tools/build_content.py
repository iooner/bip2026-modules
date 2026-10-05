"""Régénère content.js depuis le tableau Excel.
Usage : pip install openpyxl ; python3 tools/build_content.py [chemin.xlsx]
"""
import json, re, sys, pathlib
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
XLSX = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tools" / "BIP2026_testpersonnalite.xlsx"

# Corrections connues du tableau (clé : (langue, question, réponse) -> champ: texte)
FIXES = {
    # EN 3c : la cellule contient par erreur une phrase "œuvre" (Paula Muhr). Traduit depuis le FR.
    ("en", 3, "c"): {"result": "You hate authority, and yet you dream of being told what to do. "
                     "Your contradictions overwhelm you so much that you get lost in them. "
                     "Don't worry: no one holds it against you for being more complex than an amoeba."},
}

def clean(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = re.sub(r"\s+([.,])", r"\1", s)
    return s[:1].upper() + s[1:] if s else s

def sheet(ws, lang):
    questions, artworks, cur = [], [], None
    for row in ws.iter_rows(values_only=True):
        a, b, c, d, e = (list(row) + [None] * 5)[:5]
        if not c or str(c).strip() in ("Proposition",):
            continue
        if a and re.match(r"\d", str(a)):
            cur = {"q": clean(b), "answers": []}
            questions.append(cur)
        letter = "abcd"[len(cur["answers"])]
        ans = {"label": clean(re.sub(r"^[a-d]\.\s*", "", str(c).strip())), "result": clean(d)}
        ans.update(FIXES.get((lang, len(questions), letter), {}))
        cur["answers"].append(ans)
        if e:
            artworks.append(clean(e))
    assert len(questions) == 8 and all(len(q["answers"]) == 4 for q in questions), lang
    return {"questions": questions, "artworks": artworks}

wb = openpyxl.load_workbook(XLSX)
data = {"fr": sheet(wb["FR"], "fr"), "en": sheet(wb["EN"], "en")}
data["en"]["artworks"] = [s.replace("Paula Murh", "Paula Muhr") for s in data["en"]["artworks"]]
# « Dans Archives/ Présents, » remplacé par la formule commune (demande du 05/10).
data["fr"]["artworks"] = [re.sub(r"^Dans Archives?\s*/\s*Présents,", "Dans la suite de l'exposition (****),", s) for s in data["fr"]["artworks"]]
data["en"]["questions"][0]["q"] = data["en"]["questions"][0]["q"].replace("firt", "first")
out = ROOT / "content.js"
out.write_text("// Généré par tools/build_content.py, ne pas éditer à la main.\nwindow.CONTENT = "
               + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
print("OK ->", out, {k: (len(v["questions"]), len(v["artworks"])) for k, v in data.items()})
