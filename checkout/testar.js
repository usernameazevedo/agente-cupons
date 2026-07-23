// Teste de checkout REAL de cupons via Bright Data Scraping Browser.
//
// As lojas de tenis (Nike, Adidas, Centauro) bloqueiam automacao no edge (Akamai).
// O Scraping Browser do Bright Data e um navegador remoto que fura essa protecao;
// conectamos nele via Playwright CDP. Sem credencial, o script sai avisando.
//
// Uso: node testar.js <loja> CODE1 CODE2 ...
//   ex: node testar.js centauro MAIS15 BEMVINDO10
// Saida (stdout, ultima linha): RESULTADO_JSON {...}
//
// Credencial (nunca hardcodada): env BRIGHTDATA_BROWSER_WSS ou checkout/.env
//   BRIGHTDATA_BROWSER_WSS=wss://brd-customer-XXXX-zone-YYYY:PASSWORD@brd.superproxy.io:9222
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

// ---- credencial ------------------------------------------------------------
function endpoint() {
  if (process.env.BRIGHTDATA_BROWSER_WSS) return process.env.BRIGHTDATA_BROWSER_WSS.trim();
  const envFile = path.join(__dirname, ".env");
  if (fs.existsSync(envFile)) {
    for (const linha of fs.readFileSync(envFile, "utf8").split("\n")) {
      const m = linha.match(/^\s*BRIGHTDATA_BROWSER_WSS\s*=\s*(.+?)\s*$/);
      if (m) return m[1].replace(/^["']|["']$/g, "");
    }
  }
  return null;
}

// ---- adaptadores por loja --------------------------------------------------
// Cada loja: como abrir um produto elegivel, adicionar a sacola e achar o campo de cupom.
const LOJAS = {
  centauro: {
    produto: "https://www.centauro.com.br/tenis-de-corrida-unissex-olympikus-corre-5-9974A7.html",
    carrinho: "https://www.centauro.com.br/checkouts/carrinho?newcheckout=true",
    async preparar(page) {
      try { await page.getByRole("button", { name: /Rejeitar/i }).click({ timeout: 6000 }); } catch {}
      for (const loc of [
        page.getByRole("option", { name: /tamanho 42/i }),
        page.getByRole("button", { name: /tamanho 42/i }),
        page.locator('[aria-label*="tamanho 42"]'),
      ]) { try { await loc.first().click({ timeout: 5000 }); break; } catch {} }
      for (const loc of [
        page.getByRole("button", { name: /Adicionar ao carrinho/i }),
        page.getByRole("button", { name: /Comprar agora/i }),
      ]) { try { await loc.first().click({ timeout: 6000 }); break; } catch {} }
    },
    campo: (page) => page.getByPlaceholder(/Digite o cupom/i).or(page.getByRole("textbox", { name: /Cupom/i })),
    aplicar: (page) => page.getByRole("button", { name: /^Adicionar$/ }),
  },
  // Nike e Adidas: mapeados quando o Bright Data destravar o acesso (mesmo padrao).
};

const log = (...a) => console.error("[testar]", ...a);
const totalDe = async (page) => {
  const t = await page.evaluate(() => document.body.innerText);
  const m = t.match(/Total a pagar:\s*R\$\s*([\d.,]+)/i) || t.match(/Total\s*R\$\s*([\d.,]+)/i);
  return m ? m[1] : null;
};
const mensagemDe = async (page) => {
  const t = await page.evaluate(() => document.body.innerText);
  for (const re of [/Cupom não encontrado[^\n]*/i, /Ocorreu um erro ao aplicar cupom[^\n]*/i,
                    /cupom[^\n]*aplicado[^\n]*/i, /desconto[^\n]*aplicado[^\n]*/i]) {
    const m = t.match(re); if (m) return m[0].trim();
  }
  return "";
};
function classificar(msg, antes, depois) {
  if (/não encontrado/i.test(msg)) return "fantasma";       // codigo nao existe -> descartar
  if (/erro ao aplicar/i.test(msg)) return "existe_restrito"; // real, mas nao p/ este produto
  if (depois && antes && depois !== antes) return "aplicou";  // desconto confirmado
  return "indefinido";
}

(async () => {
  const [lojaId, ...codes] = process.argv.slice(2);
  const loja = LOJAS[lojaId];
  if (!loja) { console.log("RESULTADO_JSON " + JSON.stringify({ erro: `loja '${lojaId}' sem adaptador` })); return; }
  if (!codes.length) { console.log("RESULTADO_JSON " + JSON.stringify({ erro: "sem codigos" })); return; }

  const wss = endpoint();
  if (!wss) {
    console.log("RESULTADO_JSON " + JSON.stringify({
      erro: "credencial ausente",
      detalhe: "defina BRIGHTDATA_BROWSER_WSS (env ou checkout/.env) com o endpoint do Scraping Browser",
    }));
    return;
  }

  log("conectando ao Scraping Browser...");
  const browser = await chromium.connectOverCDP(wss);
  const ctx = await browser.newContext({ locale: "pt-BR", viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  const resultados = [];
  try {
    log("abrindo produto:", loja.produto);
    await page.goto(loja.produto, { waitUntil: "domcontentloaded", timeout: 60000 });
    await loja.preparar(page);
    await page.goto(loja.carrinho, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(4000);
    const antes = await totalDe(page);
    log("total base:", antes);

    for (const code of codes) {
      try {
        await loja.campo(page).first().fill("");
        await loja.campo(page).first().fill(code);
        await loja.aplicar(page).first().click({ timeout: 8000 });
        await page.waitForTimeout(3500);
        const msg = await mensagemDe(page);
        const depois = await totalDe(page);
        const status = classificar(msg, antes, depois);
        log(`  ${code}: ${status} (${msg || "sem msg"})`);
        resultados.push({ code, status, msg, totalDepois: depois });
      } catch (e) {
        resultados.push({ code, status: "erro_fluxo", msg: e.message.slice(0, 120) });
      }
    }
    console.log("RESULTADO_JSON " + JSON.stringify({ loja: lojaId, totalAntes: antes, resultados }));
  } catch (e) {
    console.log("RESULTADO_JSON " + JSON.stringify({ erro: e.message.slice(0, 200), resultados }));
  } finally {
    await browser.close();
  }
})();
