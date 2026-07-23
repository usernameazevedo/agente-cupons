"""Utilidades comuns do agente de cupons: config, chave da API, HTTP."""
import json
import os

RAIZ = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(RAIZ, "config.json")
CLAUDE_JSON = os.path.expanduser("~/.claude.json")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)


def carregar_config():
    """Lê config.json (fonte única de verdade das lojas e parâmetros)."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def chave_perplexity():
    """Lê a chave da API do Perplexity em runtime.

    Prioridade: variável de ambiente PERPLEXITY_API_KEY; senão o ~/.claude.json.
    Nunca hardcodar a chave no repositório.
    """
    env = os.environ.get("PERPLEXITY_API_KEY")
    if env:
        return env
    try:
        with open(CLAUDE_JSON, encoding="utf-8") as f:
            d = json.load(f)
        return d["mcpServers"]["perplexity"]["env"]["PERPLEXITY_API_KEY"]
    except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(
            "Chave do Perplexity nao encontrada (env PERPLEXITY_API_KEY nem ~/.claude.json)"
        ) from e


def caminho_resultado(data_iso):
    """Caminho do arquivo de resultado para uma data (YYYY-MM-DD)."""
    return os.path.join(RAIZ, "resultados", f"{data_iso}.json")
