"""Descoberta de cupons por loja via Perplexity.

Estrategia em duas camadas:
  1. chat/completions (modelo sonar) -> JSON estruturado de cupons (codigo, desconto,
     regras, validade, quao recente foi verificado). Alta precisao de extracao.
  2. search -> texto bruto das fontes, usado em pontuar.py como CORROBORACAO
     (um codigo so vira confianca "alta" se tambem aparece no texto bruto, nao apenas
     na sintese do modelo -> guarda anti-alucinacao).
"""
import json
import re
import time

import requests

from lib import chave_perplexity  # noqa: F401 (reexport util)

TIMEOUT = 60

PROMPT = (
    "Liste os cupons de desconto ATUALMENTE validos da loja {nome} ({dominio}) no Brasil, "
    "hoje ({hoje}). Para cada cupom devolva: codigo exato, desconto, regras/restricoes, "
    "validade (se houver) e quao recentemente foi verificado. "
    'Responda APENAS um JSON valido: {{"cupons":[{{"codigo":"","desconto":"","regras":"",'
    '"validade":"","verificado":""}}]}}. So inclua cupons com CODIGO real (nao inclua '
    "descontos automaticos sem codigo). Se nao houver, devolva lista vazia."
)


def _extrair_json(texto):
    """Extrai o primeiro objeto JSON do conteudo do modelo (tolerante a cercas/ruido)."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.M).strip()
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return {"cupons": []}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"cupons": []}


def _chat(nome, dominio, hoje, key):
    """Chama o modelo e devolve (lista_cupons, fontes_urls)."""
    prompt = PROMPT.format(nome=nome, dominio=dominio, hoje=hoje)
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "sonar", "messages": [{"role": "user", "content": prompt}], "temperature": 0},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        j = r.json()
    except (requests.RequestException, ValueError):
        return [], []
    conteudo = j["choices"][0]["message"]["content"]
    cupons = _extrair_json(conteudo).get("cupons", [])
    fontes = [s.get("url", "") for s in j.get("search_results", []) if s.get("url")]
    return cupons, fontes


def _corpus(query, key):
    """Texto bruto concatenado da Search API (para corroboracao de codigos)."""
    try:
        r = requests.post(
            "https://api.perplexity.ai/search",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"query": query, "max_results": 10, "country": "BR", "max_tokens_per_page": 2048},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        res = r.json().get("results", [])
    except (requests.RequestException, ValueError):
        return ""
    return " ".join((x.get("snippet") or "") + " " + (x.get("title") or "") for x in res)


def descobrir_loja(loja, key, hoje):
    """Descobre cupons de uma loja. Devolve dict {cupons, corpus, fontes}."""
    dominio = loja.get("dominio") or loja.get("link_ofertas", "")
    cupons_brutos = {}
    fontes = set()
    for q in loja.get("queries", [""])[:1] or [""]:  # uma sintese por loja basta
        cs, fs = _chat(loja["nome"], dominio, hoje, key)
        fontes.update(fs)
        for c in cs:
            cod = str(c.get("codigo", "")).strip().upper()
            if cod:
                cupons_brutos.setdefault(cod, c)  # primeira ocorrencia vence
        time.sleep(1)
    corpus = _corpus(f"cupom desconto {loja['nome']} codigo {hoje}", key)
    return {"cupons": list(cupons_brutos.values()), "corpus": corpus, "fontes": sorted(fontes)}
