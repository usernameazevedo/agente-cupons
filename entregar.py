"""Formatacao da mensagem e enfileiramento no outbox do bot de WhatsApp."""
import json
import os

SELO = {"alta": "🟢 alta", "media": "🟡 media"}


def formatar_mensagem(config, resultados, data_iso):
    """Monta o texto unico enviado ao grupo, so com cupons >= min_score_entrega."""
    minimo = config.get("min_score_entrega", 40)
    maxpl = config.get("max_cupons_por_loja", 5)
    linhas = [f"🎟️ *Cupons da semana* · {data_iso}", ""]
    por_id = {l["id"]: l for l in config["lojas"]}
    algum = False
    for loja_id, cupons in resultados.items():
        loja = por_id.get(loja_id, {"nome": loja_id, "link_ofertas": ""})
        validos = [c for c in cupons if c["score"] >= minimo][:maxpl]
        if not validos:
            continue
        algum = True
        linhas.append(f"*{loja['nome']}*")
        for c in validos:
            desc = f" · {c['desconto']}" if c["desconto"] else ""
            val = f" · vence {c['validade']}" if c["validade"] else ""
            linhas.append(f"  `{c['codigo']}`{desc} ({SELO.get(c['tier'], c['tier'])}{val})")
        if loja.get("link_ofertas"):
            linhas.append(f"  🔗 {loja['link_ofertas']}")
        linhas.append("")
    if not algum:
        return None
    linhas.append("_Selo = confianca estimada (recencia da verificacao + corroboracao "
                  "entre fontes), nao garantia. Teste no carrinho antes de finalizar._")
    return "\n".join(linhas).strip()


def enfileirar(outbox_path, grupo, texto):
    """Adiciona a mensagem ao outbox.json que o bot consome."""
    fila = []
    if os.path.exists(outbox_path):
        try:
            with open(outbox_path, encoding="utf-8") as f:
                fila = json.load(f)
        except (json.JSONDecodeError, OSError):
            fila = []
    fila.append({"grupo": grupo, "texto": texto})
    with open(outbox_path, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=1)
