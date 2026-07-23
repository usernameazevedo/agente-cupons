#!/usr/bin/env python3
"""Orquestrador do agente de cupons.

Fluxo: descobrir -> extrair+pontuar -> salvar relatorio -> (opcional) entregar no WhatsApp.

Uso:
  python3 rodar.py               # roda tudo e ENFILEIRA a mensagem no WhatsApp
  python3 rodar.py --dry         # roda tudo, salva relatorio, mas NAO envia (imprime a previa)
  python3 rodar.py --loja nike   # so uma loja (aceita repetir)
"""
import argparse
import datetime as dt
import json
import sys

from descobrir import descobrir_loja
from entregar import enfileirar, formatar_mensagem
from lib import carregar_config, caminho_resultado, chave_perplexity
from pontuar import pontuar_loja


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="nao envia ao WhatsApp; imprime previa")
    ap.add_argument("--loja", action="append", help="filtra por id de loja (repetivel)")
    args = ap.parse_args()

    config = carregar_config()
    lojas = config["lojas"]
    if args.loja:
        alvo = set(args.loja)
        lojas = [l for l in lojas if l["id"] in alvo]
        if not lojas:
            print(f"nenhuma loja casa com {args.loja}", file=sys.stderr)
            return 1

    try:
        key = chave_perplexity()
    except RuntimeError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

    hoje = dt.date.today()
    data_iso = hoje.isoformat()
    resultados = {}
    for loja in lojas:
        dados = descobrir_loja(loja, key, data_iso)
        cupons = pontuar_loja(dados, hoje)
        resultados[loja["id"]] = cupons
        n_alta = sum(1 for c in cupons if c["tier"] == "alta")
        n_media = sum(1 for c in cupons if c["tier"] == "media")
        print(f"{loja['nome']:10} {len(cupons):3} cupons  ({n_alta} alta, {n_media} media)")

    # persiste relatorio bruto do dia
    with open(caminho_resultado(data_iso), "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    msg = formatar_mensagem(config, resultados, data_iso)
    if not msg:
        print("\nNenhum cupom acima do score minimo; nada a enviar.")
        return 0

    if args.dry:
        print("\n--- PREVIA (dry-run, nao enviado) ---\n")
        print(msg)
    else:
        enfileirar(config["outbox"], config["grupo_whatsapp"], msg)
        print(f"\nEnfileirado no WhatsApp (grupo '{config['grupo_whatsapp']}').")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
