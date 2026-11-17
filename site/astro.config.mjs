import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";
import { readdirSync, readFileSync } from "node:fs";

// BASE_PATH permite publicar num subcaminho (por exemplo GitHub Pages: /castros/).
const base = process.env.BASE_PATH || "/";

// Endereços do site antigo (/castro/<id>/ e /creditos/) continuam a funcionar: reencaminham para as fichas novas,
// que seguem as secções de lib/rotas.ts (castros, citânias, cividades, museus, sítios).
const seccao = (nome) =>
  /^castro\b/i.test(nome) ? "castros" : /^cit[âa]nia\b/i.test(nome) ? "citanias" : /^cividade\b/i.test(nome) ? "cividades" : /^(museu|n[úu]cleo|centro|espa[çc]o)\b/i.test(nome) ? "museus" : "sitios";
const redirects = Object.fromEntries(
  readdirSync("./src/content/monumentos")
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const id = f.slice(0, -3);
      const nome = JSON.parse(readFileSync(`./src/content/monumentos/${f}`, "utf8").match(/^nome: (.*)$/m)[1]);
      return [`/castro/${id}/`, `${base}${seccao(nome)}/${id}/`];
    }),
);

export default defineConfig({
  site: process.env.SITE_URL || "https://tiagojmgfpinto-rgb.github.io",
  base,
  trailingSlash: "always",
  redirects,
  integrations: [react(), sitemap()],
  vite: {
    ssr: { noExternal: ["three"] },
  },
});
