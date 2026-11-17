// Tipologias e regiões do atlas. As chaves são usadas nos ficheiros de cada sítio (campo `kind` de data.json).
// `forma` escolhe o símbolo castrejo do mapa e do índice (components/ui/Icones.tsx e components/atlas/Marcadores.tsx).
export const TIPOLOGIAS = {
  castro: { nome: "Castro", plural: "Castros", forma: "casa" },
  citania: { nome: "Citânia", plural: "Citânias", forma: "citania" },
  cividade: { nome: "Cividade", plural: "Cividades", forma: "citania" },
  povoado: { nome: "Povoado fortificado", plural: "Povoados fortificados", forma: "casa" },
  balneario: { nome: "Balneário castrejo", plural: "Balneários castrejos", forma: "pedra-formosa" },
  museu: { nome: "Espaço museológico", plural: "Espaços museológicos", forma: "triskele" },
  outro: { nome: "Outro sítio", plural: "Outros sítios", forma: "casa" },
} as const;

export type Tipologia = keyof typeof TIPOLOGIAS;

export const REGIOES = {
  norte: "Norte",
  centro: "Centro",
  "lisboa-vale-tejo": "Lisboa e Vale do Tejo",
  alentejo: "Alentejo",
  algarve: "Algarve",
  acores: "Açores",
  madeira: "Madeira",
} as const;

export type Regiao = keyof typeof REGIOES;
