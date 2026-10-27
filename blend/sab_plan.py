# Castro de Sabroso: features read off the 1930 plan ("Levantamento e desenho do autor, em 1930"), plan pixels, x→E, y→S
W_WEST=[(915,250),(840,258),(770,285),(712,325),(668,378),(637,438),(620,500),(618,560),(630,620),(648,675),(660,700)]
W_EAST_INNER=[(935,254),(990,260),(1012,278),(1028,330),(1040,410),(1047,490),(1052,580)]
W_LOWER=[(660,700),(628,730),(605,790),(593,860),(596,940),(615,990),(660,1020),(740,1050),(810,1080),(875,1122),(960,1124),(1040,1115),(1088,1092)]
W_EAST_OUTER=[(1062,565),(1120,585),(1185,625),(1240,680),(1280,740),(1298,820),(1300,900),(1292,980),(1272,1080),(1245,1180),(1212,1252)]
W_SE=[(1050,1120),(1090,1170),(1140,1215),(1172,1250)]
W_INNER=[[(1088,1010),(1090,1092)],[(1100,1010),(1102,1090)],[(945,540),(945,625)],[(945,540),(995,538)],[(965,598),(1040,600),(1048,640)],[(918,600),(940,602)],
 [(842,300),(832,325)],[(938,268),(925,320)],[(1018,437),(1034,437)],[(836,352),(860,352)],[(1030,862),(1060,860),(1062,905)],[(1045,1060),(1080,1100),(1085,1150)],
 [(1130,1100),(1165,1095),(1195,1150)],[(706,412),(746,436),(760,440)],[(680,610),(700,600)],[(940,808),(960,795)],[(880,840),(895,835)],[(760,665),(785,700),(770,705)]]
# round houses: centre x,y, radius px (≈ 4.6 px/m)
HOUSES=[(905,286,10),(930,292,9),(985,308,10),(790,368,11),(805,366,12),(850,400,10),(985,370,10),(1006,372,9),(737,413,11),(790,433,9),(675,487,10),
 (742,527,10),(764,513,11),(782,548,9),(818,540,10),(717,578,10),(778,575,9),(893,490,10),(930,542,10),(1020,615,10),(980,642,9),(940,690,13),
 (760,682,9),(778,690,9),(965,805,11),(898,857,10),(912,850,9),(1048,885,8),(1046,905,6),(1050,920,6),(1147,1110,12),(730,555,8),(790,600,8),(805,522,7)]
CISTERN=[(710,435),(965,565)]
ROCKS=[(920,420,25),(880,520,18),(885,700,30),(760,765,40),(1185,1245,14),(965,895,8),(990,352,14)]
LABELS=[("Cisterna",1012,372),("Gravuras rupestres",965,895),("Gruta",880,662),("Entrada N · 1.ª fase",928,256),("Entrada SE · 3.ª fase",1110,1165),("Entrada SO · 2.ª fase (local aprox.)",705,735)]
# visitor path: from the access track north of the hill to the north gate, then into the enclosure
PATH=[(905,60),(915,150),(925,215),(930,262),(915,330),(890,420),(870,520),(880,620),(900,720),(930,800)]

# ---------------- sources and structure catalogue ----------------
SOURCES={
 "cardozo1930":"Cardozo, M. (1930). Planta do Castro de Sabroso, levantamento e desenho do autor (Fig. 17), com o limite da zona de protecção balizada em 1929.",
 "era2021":"Painel interpretativo do Castro de Sabroso (ERA Arqueologia / Município de Guimarães, 2021), planta do estado actual.",
 "loureiro1999":"Loureiro, S. (1999). O Castro de Sabroso (Guimarães). Um estudo espacial à luz dos dados arqueológicos. Revista de Guimarães, 109, 13-50.",
 "cruz2015":"Cruz, G. & Antunes, J. (2015). Castro de Sabroso. Notícia dos trabalhos arqueológicos de 2015. Revista de Guimarães, 124-125, 237-249.",
 "pereira1938":"Páginas inéditas de Félix Alves Pereira (1938). Revista de Guimarães, 48(4), 277-282.",
 "cardozo1976":"Cardozo, M. (1976), citado em Loureiro (1999): muralha em talude com 3 a 5 m de altura e 4 m de largura.",
 "hawkes1958":"Hawkes, C. (1958; publ. 1971), citado em Loureiro (1999): fases da muralha e entradas N, SO e SE.",
 "sarmento1909":"Sarmento, F. M. (1909), citado em Loureiro (1999): 35 casas circulares, diâmetro médio 4,70 m; placas de xisto como possível cobertura.",
 "dgt":"DGT — Ortofotomapa 2021 (25 cm) e modelo de elevação; relevo exagerado 1,25×.",
}
CISTERN_HOUSE=(1006,372)   # the "1" (cisterna) of the 1930 legend sits on this circle
FILLED=[(710,435),(965,565)]  # filled circles in the 1930 plan, function not identified
