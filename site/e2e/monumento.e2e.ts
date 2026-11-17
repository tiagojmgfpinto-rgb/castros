import { expect, test } from "@playwright/test";
import { errosDaPagina, paginasComMaqueta, transbordos } from "./ajuda";

test("página do castro: a maqueta 3D carrega, com lightbox", async ({ page }) => {
  const erros = errosDaPagina(page);
  const [pagina] = (await paginasComMaqueta(page)).filter((p) => p.includes("briteiros"));
  expect(pagina).toBeTruthy();
  const glb = page.waitForRequest(/\.glb/, { timeout: 60_000 });
  await page.goto(pagina);
  await page.locator(".maqueta").scrollIntoViewIfNeeded();
  // a ilha client:visible tem de hidratar e pedir o GLB (falhou assim no PR #46)
  await glb;
  await expect(page.locator(".maqueta-carregar")).toHaveCount(0, { timeout: 150_000 });

  // (ainda nenhuma maqueta dos castros tem épocas com fonte: o seletor não aparece)
  await expect(page.locator(".maqueta-epocas-botoes")).toHaveCount(0);

  // lightbox da galeria
  const fig = page.locator(".ficha-imagens figure > a").nth(1);
  await fig.scrollIntoViewIfNeeded();
  await fig.click();
  const dialogo = page.locator("dialog.lightbox");
  await expect(dialogo).toHaveJSProperty("open", true);
  const antes = await page.locator(".lightbox-conta").textContent();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".lightbox-conta")).not.toHaveText(antes ?? "");
  await page.keyboard.press("Escape");
  await expect(dialogo).toHaveJSProperty("open", false);
  expect(erros).toEqual([]);
});

for (const [nome, viewport] of [["computador", { width: 1280, height: 860 }], ["telemóvel", { width: 375, height: 667 }]] as const) {
  test(`visor 3D: nenhum texto sai das caixas (${nome})`, async ({ page }) => {
    await page.setViewportSize(viewport);
    const paginas = await paginasComMaqueta(page);
    expect(paginas.length).toBeGreaterThanOrEqual(5); // as cinco maquetas publicadas
    // o GLB fica pendente: chega a interface do visor, que é o que se mede, sem esperar pelo desenho
    await page.route(/\.glb/, () => undefined);
    const problemas: string[] = [];
    for (const p of paginas) {
      await page.goto(p);
      await page.locator(".maqueta").scrollIntoViewIfNeeded();
      await expect(page.locator(".maqueta-botoes")).toBeVisible();
      const medir = async () => (await page.evaluate(transbordos)).forEach((x) => problemas.push(`${p}: ${x}`));
      await medir();
      const placas = page.locator(".maqueta-placa-cartao");
      for (let i = 0; i < (await placas.count()); i++) {
        await placas.nth(i).evaluate((e) => (e as HTMLElement).click());
        await medir();
      }
      const epocas = page.locator(".maqueta-epocas-botoes button");
      for (let i = 0; i < (await epocas.count()); i++) {
        await epocas.nth(i).click();
        await medir();
      }
    }
    expect([...new Set(problemas)]).toEqual([]);
  });
}

test("visor 3D: teclado, enquadramento centrado e ecrã grande com a altura toda", async ({ page }) => {
  test.setTimeout(300_000);
  const erros = errosDaPagina(page);
  await page.setViewportSize({ width: 1280, height: 860 });
  await page.emulateMedia({ reducedMotion: "reduce" }); // sem giro: a câmara só se mexe com o teclado
  const [pagina] = (await paginasComMaqueta(page)).filter((p) => p.includes("sabroso"));
  await page.goto(pagina);
  await page.locator(".maqueta").scrollIntoViewIfNeeded();
  await expect(page.locator(".maqueta-carregar")).toHaveCount(0, { timeout: 150_000 });
  type Visor = { camera: { position: { x: number; y: number; z: number }; updateMatrixWorld(): void; matrixWorldInverse: unknown; projectionMatrix: unknown }; controlos: { current: { target: { x: number; y: number; z: number } } } };
  const camara = () => page.evaluate(() => {
    const m = (window as unknown as { __maqueta: Visor }).__maqueta;
    const p = m.camera.position, t = m.controlos.current.target;
    return { p: [p.x, p.y, p.z], t: [t.x, t.y, t.z], d: Math.hypot(p.x - t.x, p.y - t.y, p.z - t.z) };
  });
  const antes = await camara();

  // + aproxima, setas deslocam, Q roda
  await page.locator(".maqueta-palco canvas").click({ position: { x: 20, y: 300 } });
  // o swiftshader do CI desenha cerca de um fotograma por segundo (as maquetas dos castros têm floresta à volta):
  // a tecla fica em baixo até a câmara se mexer (no máximo 30 s), com a repetição de um teclado verdadeiro
  type Cam = Awaited<ReturnType<typeof camara>>;
  const segurar = async (tecla: string, mexeu: (c: Cam) => number) => {
    await page.keyboard.down(tecla);
    await page.waitForTimeout(2000);
    await expect.poll(async () => {
      await page.keyboard.down(tecla); // repetição automática (keydown com repeat)
      return mexeu(await camara());
    }, { timeout: 30_000 }).toBeGreaterThan(0.5);
    await page.keyboard.up(tecla);
    return camara();
  };
  const perto = await segurar("Equal", (c) => antes.d - c.d - 0.5);
  expect(perto.d).toBeLessThan(antes.d - 1);
  const lado = await segurar("ArrowRight", (c) => Math.hypot(c.t[0] - perto.t[0], c.t[2] - perto.t[2]));
  expect(Math.hypot(lado.t[0] - perto.t[0], lado.t[2] - perto.t[2])).toBeGreaterThan(0.5);
  const rodada = await segurar("KeyQ", (c) => Math.hypot(c.p[0] - lado.p[0], c.p[2] - lado.p[2]));
  expect(Math.hypot(rodada.p[0] - lado.p[0], rodada.p[2] - lado.p[2])).toBeGreaterThan(0.5);

  // Enquadrar volta a pôr o monumento no centro; Ampliar usa a altura toda da janela
  await page.locator(".maqueta-botoes button", { hasText: "Enquadrar" }).click();
  await page.waitForTimeout(2500);
  await page.locator(".maqueta-botoes button", { hasText: "Ampliar" }).click();
  // o primeiro fotograma em ecrã grande (sombra e oclusão ao novo tamanho) leva dezenas de segundos no swiftshader
  await expect.poll(async () => (await page.locator(".maqueta-palco").boundingBox())?.height ?? 0, { timeout: 90_000 }).toBeGreaterThan(860 * 0.75);
  expect(erros).toEqual([]);
});
