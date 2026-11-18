// Endereços permanentes das fichas, agrupados pela designação do sítio:
// /castros/sabroso…, /citanias/…, /cividades/…, /museus/…, /sitios/…
export const SECCOES = {
  castros: "Castros",
  citanias: "Citânias",
  cividades: "Cividades",
  museus: "Museus",
  sitios: "Sítios",
} as const;

export type Seccao = keyof typeof SECCOES;

export function seccaoDe(nome: string): Seccao {
  if (/^castro\b/i.test(nome)) return "castros";
  if (/^cit[âa]nia\b/i.test(nome)) return "citanias";
  if (/^cividade\b/i.test(nome)) return "cividades";
  if (/^(museu|n[úu]cleo|centro|espa[çc]o)\b/i.test(nome)) return "museus";
  return "sitios";
}

/** Caminho da ficha, relativo à base do site, com barra final. */
export function caminhoFicha(m: { id: string; nome: string }) {
  return `${seccaoDe(m.nome)}/${m.id}/`;
}
