# Citânia de Briteiros: features read off the site's interpretive panel (Sociedade Martins Sarmento), panel photo pixels (1600x1200), x→right, y→down.
# The panel is schematic: rampart 1 and 2, gates and main ways are drawn clearly; ramparts 3–5 and the trenches are drawn as lines and are approximate.
R1=[(928,668),(916,628),(920,590),(940,555),(972,530),(1010,508),(1050,490),(1088,470),(1130,462),(1175,458),(1215,462),(1248,480),(1262,505),(1252,540),(1232,575),(1205,605),(1185,640),(1168,685),(1148,720),(1120,748),(1082,768),(1035,782),(990,785),(955,770),(938,735),(930,700)]
R2=[(815,800),(800,760),(820,690),(850,610),(885,535),(930,470),(985,428),(1062,398),(1120,384),(1180,378),(1235,388),(1272,410),(1300,445),(1312,490),(1308,545),(1292,610),(1272,690),(1252,770),(1235,840),(1215,905),(1195,950),(1150,975),(1100,965),(1040,925),(980,890),(920,865),(860,835)]
R3=[(1300,300),(1250,262),(1180,240),(1110,232),(1062,250),(1025,290),(1000,330),(950,370),(880,420),(800,480),(720,550),(640,620),(570,700),(530,780),(510,850),(525,905)]
R3E=[(1300,300),(1335,350),(1345,420),(1340,480),(1370,560),(1385,650),(1370,740),(1330,830),(1280,910),(1230,965),(1170,990),(1100,985)]
TRENCH=[[(1245,195),(1335,300)],[(1265,190),(1345,290)],[(1300,190),(1540,300)],[(1310,170),(1535,285)]]
R5=[(1330,55),(1440,110),(1530,160),(1580,250),(1565,290),(1520,280),(1450,250),(1400,235),(1355,270),(1320,300)]
GATES=[("Porta norte (muralha 3)",1080,222),("Porta nascente (muralha 3)",1306,318),("Porta noroeste (muralha 2)",1062,397),("Porta nordeste (muralha 2)",1254,410),
       ("Porta norte (muralha 1)",1090,468),("Porta nascente (muralha 1)",1205,604),("Porta sul (muralha 2)",1098,958)]
WAYS=[[(1030,470),(1026,540),(1021,610),(1018,690),(1025,775)],[(1140,465),(1135,540),(1126,620),(1115,690),(1105,745)],[(1030,778),(960,782),(900,788),(860,792)]]
COUNCIL=(940,640,11)     # "Casa do Conselho" (8)
BATH=(1322,462)          # balneário (9)
YOU=(1045,815)           # "Você está aqui": entrance
SCALE_PX_PER_M=65/50     # scale bar 0–25–50 m
NORTH_DEG=30             # north arrow, clockwise from panel-up (approximate)

# ---- features measured on the DGT 2021 orthophoto (25 cm), pixels of app/t3/<id>-c.jpg (4 px/m, site point at 1024,1024)
ORTHO_HOUSES=[(750,330,12),(807,400,10),(693,457,12),(840,470,10),(857,567,12),(773,785,12),(733,800,10),(777,830,12),(752,823,10),(717,850,12),
 (813,815,10),(840,870,13),(880,830,11),(910,850,10),(760,930,9),(953,907,12),(1123,770,12),(1160,827,10),(983,1107,12)]
RECON_HOUSES=[(743,670,15),(713,722,15)]        # the two round houses rebuilt by Martins Sarmento (conical roofs visible)
CHAPEL=(612,700,26,45)                          # Capela de São Romão: centre, side (px), rotation (deg)
RECEPTION=[(990,1262,68,46,-22,4.2),(1028,1292,34,40,-22,3.2)]   # reception centre (tickets) by the entrance: centre, length, width (px), rotation, height (m)
SOURCES={
 "painel":"Painel interpretativo «Citânia de Briteiros. Um povoado proto-histórico» (Sociedade Martins Sarmento), no sítio: muralhas 1 a 4, fossos, portas, ruas principais, Casa do Conselho e balneários.",
 "cardoso1938":"Cardoso, M. (1938). Citânia de Briteiros. Alguns aspectos etnográficos e sociais da nossa proto-história. Revista de Guimarães, 48.",
 "cardoso1935":"Cardoso, M. (1935). Possível identificação do primitivo local da «Pedra Formosa», na Citânia de Briteiros. Revista de Guimarães, 45.",
 "cruz2011":"Cruz, G. & Antunes, J. (2010-2011). Citânia de Briteiros, notícia dos trabalhos arqueológicos (2007-2010). Revista de Guimarães, 120-121.",
 "osm":"OpenStreetMap (contribuidores): traçado das muralhas 1 e 2 e da estrada, ODbL.",
 "dgt":"DGT — Ortofotomapa 2021 (25 cm).",
 "plan":"Unidade de Arqueologia da Universidade do Minho — Citânia de Briteiros, levantamento geral e sectores de intervenção (planta), georreferenciado sobre as casas reconstruídas e a capela.",
 "lidar":"DGT — LiDAR 2025: modelo digital do terreno (MDT) e de superfície (MDS) a 50 cm, folhas 184507 e 185507; relevo exagerado 1,15×.",
}
LABELS=[("Primeira muralha",1010,505),("Segunda muralha",1180,380),("Terceira muralha",1100,236),("Casa do Conselho",940,640),("Balneário nascente",1322,462)]
ENTRANCE=(1045,815)
