import { describe, expect, it } from "vitest";
import { caminhoFicha } from "./rotas";

describe("endereços das fichas", () => {
  it.each([
    ["guimaraes-castro-de-sabroso", "Castro de Sabroso", "castros/guimaraes-castro-de-sabroso/"],
    ["guimaraes-citania-de-briteiros", "Citânia de Briteiros", "citanias/guimaraes-citania-de-briteiros/"],
    ["paredes-de-coura-cividade-de-cossourado", "Cividade de Cossourado", "cividades/paredes-de-coura-cividade-de-cossourado/"],
    ["guimaraes-museu-da-cultura-castreja", "Museu da Cultura Castreja", "museus/guimaraes-museu-da-cultura-castreja/"],
    ["x-povoado-de-y", "Povoado de Y", "sitios/x-povoado-de-y/"],
  ])("%s", (id, nome, esperado) => {
    expect(caminhoFicha({ id, nome })).toBe(esperado);
  });
});
