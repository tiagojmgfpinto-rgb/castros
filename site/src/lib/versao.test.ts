import { describe, expect, it } from "vitest";
import { comVersao } from "./versao";

describe("comVersao", () => {
  it("acrescenta um hash do conteúdo aos ficheiros de public/", () => {
    const u = comVersao("maquetas/guimaraes-castro-de-sabroso/guimaraes-castro-de-sabroso.glb");
    expect(u).toMatch(/^maquetas\/guimaraes-castro-de-sabroso\/guimaraes-castro-de-sabroso\.glb\?v=[0-9a-f]{10}$/);
    expect(comVersao("maquetas/guimaraes-castro-de-sabroso/guimaraes-castro-de-sabroso.glb")).toBe(u);
  });
  it("deixa como está um ficheiro em falta, um endereço já versionado ou nada", () => {
    expect(comVersao("maquetas/nao-existe.glb")).toBe("maquetas/nao-existe.glb");
    expect(comVersao("a.glb?v=1")).toBe("a.glb?v=1");
    expect(comVersao(undefined)).toBeUndefined();
  });
});
