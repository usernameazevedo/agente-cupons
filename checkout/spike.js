// Spike: valida se o Playwright headless passa pelo checkout da Centauro e
// classifica cupons (fantasma vs restrito vs aplicou). Uso: node spike.js CODE1 CODE2 ...
const { chromium } = require("playwright");

const PRODUTO = "https://www.centauro.com.br/tenis-de-corrida-unissex-olympikus-corre-5-9974A7.html";
const CARRINHO = "https://www.centauro.com.br/checkouts/carrinho?newcheckout=true";
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

const log = (...a) => console.log("[spike]", ...a);

async function lerTotal(page) {
  const txt = await page.evaluate(() => document.body.innerText);
  const m = txt.match(/Total a pagar:\s*R\$\s*([\d.,]+)/i) || txt.match(/Total\s*R\$\s*([\d.,]+)/i);
  return m ? m[1] : null;
}

async function lerMensagem(page) {
  const txt = await page.evaluate(() => document.body.innerText);
  for (const re of [/Cupom não encontrado[^\n]*/i, /Ocorreu um erro ao aplicar cupom[^\n]*/i,
                    /cupom[^\n]*aplicado[^\n]*/i, /desconto[^\n]*aplicado[^\n]*/i]) {
    const m = txt.match(re);
    if (m) return m[0].trim();
  }
  return "";
}

function classificar(msg, totalAntes, totalDepois) {
  if (/não encontrado/i.test(msg)) return "fantasma";
  if (/erro ao aplicar/i.test(msg)) return "existe_restrito";
  if (totalDepois && totalAntes && totalDepois !== totalAntes) return "aplicou";
  return "indefinido";
}

(async () => {
  const codes = process.argv.slice(2);
  if (!codes.length) { log("passe códigos: node spike.js MAIS15 BEMVINDO10"); process.exit(1); }

  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
  });
  const ctx = await browser.newContext({
    userAgent: UA, locale: "pt-BR", viewport: { width: 1280, height: 800 },
  });
  // esconde navigator.webdriver
  await ctx.addInitScript(() => Object.defineProperty(navigator, "webdriver", { get: () => undefined }));
  const page = await ctx.newPage();

  try {
    log("abrindo produto...");
    await page.goto(PRODUTO, { waitUntil: "domcontentloaded", timeout: 45000 });
    // cookies
    try { await page.getByRole("button", { name: /Rejeitar/i }).click({ timeout: 6000 }); log("cookies rejeitados"); }
    catch { log("sem banner de cookies"); }

    // seleciona tamanho 42 (tenta varios seletores)
    let ok = false;
    for (const loc of [
      page.getByRole("option", { name: /tamanho 42/i }),
      page.getByRole("button", { name: /tamanho 42/i }),
      page.locator('[aria-label*="tamanho 42"]'),
      page.locator("text=/^42$/"),
    ]) {
      try { await loc.first().click({ timeout: 5000 }); ok = true; log("tamanho 42 selecionado"); break; } catch {}
    }
    if (!ok) log("!! não achei o tamanho — seguindo mesmo assim");

    // adicionar ao carrinho
    for (const loc of [
      page.getByRole("button", { name: /Adicionar ao carrinho/i }),
      page.getByRole("button", { name: /Comprar agora/i }),
    ]) {
      try { await loc.first().click({ timeout: 6000 }); log("adicionado ao carrinho"); break; } catch {}
    }

    log("indo ao carrinho...");
    await page.goto(CARRINHO, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(4000);
    const totalAntes = await lerTotal(page);
    log("total base:", totalAntes);

    const campo = page.getByPlaceholder(/Digite o cupom/i).or(page.getByRole("textbox", { name: /Cupom/i }));
    const aplicar = page.getByRole("button", { name: /^Adicionar$/ });

    const resultados = [];
    for (const code of codes) {
      try {
        await campo.first().fill("");
        await campo.first().fill(code);
        await aplicar.first().click({ timeout: 8000 });
        await page.waitForTimeout(3500);
        const msg = await lerMensagem(page);
        const totalDepois = await lerTotal(page);
        const status = classificar(msg, totalAntes, totalDepois);
        log(`  ${code}: ${status} | msg="${msg}" | total=${totalDepois}`);
        resultados.push({ code, status, msg, totalDepois });
      } catch (e) {
        log(`  ${code}: ERRO_FLUXO ${e.message}`);
        resultados.push({ code, status: "erro_fluxo", msg: e.message });
      }
    }
    console.log("RESULTADO_JSON " + JSON.stringify({ totalAntes, resultados }));
  } catch (e) {
    log("FALHA GERAL:", e.message);
    console.log("RESULTADO_JSON " + JSON.stringify({ erro: e.message }));
  } finally {
    await browser.close();
  }
})();
