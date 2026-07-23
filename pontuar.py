"""Pontuacao de confianca dos cupons descobertos.

Entrada: saida de descobrir.descobrir_loja -> {cupons, corpus, fontes}.
Cada cupom vem do modelo (codigo, desconto, regras, validade, verificado).

O score estima CONFIANCA (nao garantia) a partir de:
  - recencia da verificacao (parseada do campo 'verificado');
  - corroboracao: o codigo tambem aparece no texto bruto da busca (anti-alucinacao);
  - amplitude de fontes; validade futura conhecida.
Cupom com validade vencida ou codigo em formato invalido e descartado.
"""
import datetime as dt
import re

RE_CODIGO_OK = re.compile(r"^[A-Z][A-Z0-9]{2,15}$")
RE_DATA = re.compile(r"(\d{2}/\d{2}/\d{4})")


def _recencia(verificado, hoje):
    t = (verificado or "").lower()
    if "hoje" in t or "today" in t:
        return 45, "verificado hoje"
    if "ontem" in t or "yesterday" in t:
        return 32, "verificado ontem"
    m = RE_DATA.search(verificado or "")
    if m:
        try:
            d = dt.datetime.strptime(m.group(1), "%d/%m/%Y").date()
            dias = (hoje - d).days
            if dias <= 3:
                return 30, f"verificado {m.group(1)}"
            if dias <= 14:
                return 18, f"verificado {m.group(1)}"
            return 8, f"verificado {m.group(1)}"
        except ValueError:
            pass
    m = re.search(r"(\d+)\s*dias?", t)
    if m:
        return (18 if int(m.group(1)) <= 14 else 8), f"{m.group(1)} dias atras"
    return 6, "recencia incerta"


def _validade_ok(validade, hoje):
    """(valida?, texto). Descarta so se a data existir e ja passou."""
    m = RE_DATA.search(validade or "")
    if not m:
        return True, ""
    try:
        d = dt.datetime.strptime(m.group(1), "%d/%m/%Y").date()
        return d >= hoje, m.group(1)
    except ValueError:
        return True, ""


def pontuar_loja(dados, hoje):
    """Pontua todos os cupons de uma loja. Devolve lista ordenada por score desc."""
    corpus_up = (dados.get("corpus") or "").upper()
    n_fontes = len(dados.get("fontes", []))
    saida = []
    for c in dados.get("cupons", []):
        cod = str(c.get("codigo", "")).strip().upper()
        if not RE_CODIGO_OK.match(cod) or cod.isdigit():
            continue
        val_ok, val_txt = _validade_ok(c.get("validade", ""), hoje)
        if not val_ok:
            continue

        rec_score, rec_txt = _recencia(c.get("verificado", ""), hoje)
        corroborado = cod in corpus_up
        score = rec_score
        score += 12 if corroborado else 0  # bonus (nao portao): sobe a confianca
        score += min(n_fontes, 6) * 3      # amplitude de fontes que embasaram a busca
        score += 6 if val_txt else 0
        score = max(0, min(100, score))

        saida.append(
            {
                "codigo": cod,
                "desconto": (c.get("desconto") or "").strip(),
                "regras": (c.get("regras") or "").strip(),
                "validade": val_txt,
                "recencia": rec_txt,
                "corroborado": corroborado,
                "score": score,
                "tier": "alta" if score >= 65 else "media" if score >= 40 else "baixa",
            }
        )
    return sorted(saida, key=lambda x: x["score"], reverse=True)
