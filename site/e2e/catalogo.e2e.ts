import { expect, test } from "@playwright/test";
import { errosDaPagina } from "./ajuda";

test("catálogo: pesquisa, filtros e endereço", async ({ page }) => {
  const erros = errosDaPagina(page);
  await page.goto("castros/");
  const cartoes = page.locator("[data-cartao]:not([hidden])");
  const total = await page.locator("[data-cartao]").count();
  expect(total).toBeGreaterThan(40);
  await expect(page.locator(".catalogo-filtros")).toBeVisible();
  await expect(cartoes).toHaveCount(total);

  // Guimarães tem vários sítios: cada palavra tem de aparecer, sem acentos
  await page.fill("input[name=q]", "guimaraes");
  expect(await cartoes.count()).toBeGreaterThan(2);
  await page.fill("input[name=q]", "citania guimaraes");
  await expect(cartoes).toHaveCount(1);
  await expect(cartoes.first()).toContainText("Briteiros");
  expect(page.url()).toContain("q=citania+guimaraes");

  await page.fill("input[name=q]", "");
  await page.check("input[name=maqueta]");
  const nMaqueta = await page.locator('[data-cartao][data-maqueta="1"]').count();
  expect(nMaqueta).toBeGreaterThan(0);
  await expect(cartoes).toHaveCount(nMaqueta);
  await expect(page.locator(".catalogo-conta")).toHaveText(`${nMaqueta} de ${total} sítios`);

  await page.click("button[type=reset]");
  await expect(cartoes).toHaveCount(total);

  // o endereço repõe os filtros e as regiões vazias escondem-se
  await page.goto("castros/?maqueta=1&regiao=centro");
  await expect(page.locator("select[name=regiao]")).toHaveValue("centro");
  await expect(page.locator(".catalogo-vazio, [data-seccao='centro'] [data-cartao]:not([hidden])").first()).toBeVisible();

  // cada cartão leva a uma ficha que existe
  await page.goto("castros/");
  const href = await page.locator("[data-cartao] a").first().getAttribute("href");
  const r = await page.request.get(href!);
  expect(r.status()).toBe(200);
  expect(erros).toEqual([]);
});
