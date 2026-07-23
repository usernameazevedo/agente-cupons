# Agente de Cupons

Descobre, pontua por confiança e entrega no WhatsApp os cupons de desconto em
funcionamento das grandes lojas (Nike, Adidas, Centauro, Renner por padrão), com
o link direto para as ofertas. Roda sozinho toda semana via LaunchAgent.

## Como funciona

```
Descobrir            Pontuar                     Entregar
(Perplexity)   ->    (confiança 0-100)     ->    (WhatsApp, grupo "Cupons")
 sonar+search        recência + corroboração      só cupons >= score mínimo
```

1. **Descobrir** (`descobrir.py`): pergunta ao modelo `sonar` do Perplexity os cupons
   válidos de cada loja em JSON (código, desconto, regras, validade, quão recente foi
   verificado) e baixa o texto bruto da busca para corroboração.
2. **Pontuar** (`pontuar.py`): dá um score de confiança a cada cupom com base em
   recência da verificação, se o código também aparece no texto bruto das fontes
   (**guarda anti-alucinação**: código só do modelo fica no máximo 🟡 média),
   amplitude de fontes e validade. Descarta código vencido ou em formato inválido.
3. **Entregar** (`entregar.py`): monta uma mensagem única e enfileira em
   `agenda-whatsapp/outbox.json`, que o bot de WhatsApp envia ao grupo.

O selo (🟢 alta / 🟡 média) é **confiança estimada, não garantia**. A mensagem
sempre lembra de testar no carrinho antes de finalizar.

## Uso manual

```bash
python3 rodar.py --dry              # roda tudo, mostra a prévia, NÃO envia
python3 rodar.py --dry --loja nike  # só uma loja (repetível: --loja nike --loja adidas)
python3 rodar.py                    # roda e ENFILEIRA no WhatsApp
```

Relatórios brutos de cada dia ficam em `resultados/YYYY-MM-DD.json`.

## Agendamento (semanal)

LaunchAgent `~/Library/LaunchAgents/com.luisazvedo.agente-cupons.plist` roda
`rodar-semanal.sh` toda **segunda às 9h**. Log em `agente-cupons.log`.

```bash
launchctl unload ~/Library/LaunchAgents/com.luisazvedo.agente-cupons.plist
launchctl load   ~/Library/LaunchAgents/com.luisazvedo.agente-cupons.plist
```

## Pré-requisitos

- Grupo de WhatsApp chamado **Cupons** com o número do bot (agenda-whatsapp) dentro.
  O nome é configurável em `config.json` (`grupo_whatsapp`).
- Chave da API do Perplexity — lida em runtime de `PERPLEXITY_API_KEY` ou de
  `~/.claude.json` (`mcpServers.perplexity.env.PERPLEXITY_API_KEY`). Nunca hardcodada.
- Python 3 com `requests` (`pip3 install -r requirements.txt`).

## Adicionar/editar lojas

Edite `config.json`. Cada loja precisa de: `id`, `nome`, `dominio`, `link_ofertas`
e (opcional) `queries`. Parâmetros globais: `grupo_whatsapp`, `min_score_entrega`,
`max_cupons_por_loja`.

## Roadmap — validação por checkout real (opcional)

A v1 valida por confiança (recência + corroboração). O passo seguinte, ligado loja a
loja, é abrir o carrinho e aplicar o código de verdade para confirmar o desconto.
É a parte frágil (cada loja tem fluxo próprio; algumas têm anti-bot/CAPTCHA no
checkout) e por isso fica como módulo separado a habilitar gradualmente.
