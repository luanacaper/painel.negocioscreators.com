"""Monta negocioscreators.com (host=site) ou painel.negocioscreators.com (host=painel)
a partir dos repositórios de cada cliente, sem tirar nada deles do lugar.

Uso:
  python build.py site            # monta em ./out
  python build.py painel --check  # só diz se algum repositório mudou desde o último deploy
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CFG = json.loads((AQUI / "sites.json").read_text(encoding="utf-8"))
HOST = sys.argv[1] if len(sys.argv) > 1 else "site"
CHECK = "--check" in sys.argv
DOMINIO = CFG["dominio"] if HOST == "site" else CFG["painel"]
OUT = AQUI / "out"
IGNORAR = shutil.ignore_patterns(".git", ".github", "*.md", "*.gs", "*.sql", "CNAME")
TEXTO = {".html", ".htm", ".js", ".mjs", ".css", ".json", ".xml", ".txt", ".webmanifest", ".svg"}

meus = [s for s in CFG["sites"] if s["host"] == HOST]


def sha(repo):
    r = subprocess.run(["git", "ls-remote", f"https://github.com/{repo}.git", "HEAD"], capture_output=True, text=True, check=True)
    return r.stdout.split()[0]


def destino(s):
    base = CFG["dominio"] if s["host"] == "site" else CFG["painel"]
    return f"https://{base}/{s['path']}".rstrip("/")


def saida(nome, valor):
    f = os.environ.get("GITHUB_OUTPUT")
    if f:
        with open(f, "a", encoding="utf-8") as h:
            h.write(f"{nome}={valor}\n")
    print(f"{nome}={valor}")


shas = {s["repo"]: sha(s["repo"]) for s in meus}

if CHECK:
    try:
        with urllib.request.urlopen(f"https://{DOMINIO}/_build.json", timeout=20) as r:
            antes = json.load(r).get("shas", {})
    except Exception as e:  # domínio ainda sem DNS/HTTPS: compara com o último build feito aqui
        print("domínio não respondeu:", e)
        local = AQUI / ".ultimo-build.json"
        antes = json.loads(local.read_text(encoding="utf-8")).get("shas", {}) if local.exists() else {}
    saida("changed", "true" if antes != shas else "false")
    sys.exit(0)

# Mapa de reescrita: endereço antigo no github.io -> endereço novo no domínio
mapa = []
for s in CFG["sites"]:
    dono, repo = s["repo"].split("/")
    mapa.append((f"{dono}.github.io/{repo}", destino(s)))
for a in CFG["aliases"]:
    alvo = next(s for s in CFG["sites"] if s["path"] == a["para"])
    mapa.append((a["de"], destino(alvo)))
mapa.sort(key=lambda x: -len(x[0]))
padroes = [(re.compile(r"(?:https?://)?" + re.escape(de) + r"(?![A-Za-z0-9_.-])"), para) for de, para in mapa]

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

with tempfile.TemporaryDirectory() as tmp:
    for s in sorted(meus, key=lambda s: len(s["path"])):  # raiz primeiro, subpastas depois
        src = Path(tmp) / s["repo"].replace("/", "__")
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"https://github.com/{s['repo']}.git", str(src)], check=True)
        alvo = OUT / s["path"] if s["path"] else OUT
        shutil.copytree(src, alvo, ignore=IGNORAR, dirs_exist_ok=True)
        print(f"ok  /{s['path']:<32} <- {s['repo']}")

for arq in OUT.rglob("*"):
    if arq.is_file() and arq.suffix.lower() in TEXTO:
        t = arq.read_text(encoding="utf-8", errors="surrogateescape")
        n = t
        for p, para in padroes:
            n = p.sub(para, n)
        if n != t:
            arq.write_text(n, encoding="utf-8", errors="surrogateescape")

if HOST == "painel":
    (OUT / "index.html").write_text((AQUI / "painel-index.html").read_text(encoding="utf-8").replace(
        "<!--LISTA-->", "\n".join(
            f'<a class="app" href="/{s["path"]}/"><span class="av">{s["nome"][0]}</span><span><b>{s["nome"]}</b><small>painel.negocioscreators.com/{s["path"]}</small></span></a>'
            for s in meus)), encoding="utf-8")

(OUT / "404.html").write_text((AQUI / "404.html").read_text(encoding="utf-8"), encoding="utf-8")
(OUT / "CNAME").write_text(DOMINIO + "\n", encoding="utf-8")
(OUT / ".nojekyll").write_text("", encoding="utf-8")
(OUT / "_build.json").write_text(json.dumps({"shas": shas}, indent=1), encoding="utf-8")
print("pronto:", DOMINIO)
