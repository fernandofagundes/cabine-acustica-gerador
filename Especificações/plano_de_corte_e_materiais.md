# Plano de Corte e Lista de Materiais — Cabine Acústica do Gerador Toyama TG8000CXER

Complementa `projeto_cabine_acustica_gerador_toyama_tg8000cxer.md`. A ordem de montagem e as regras de fixação estão em `guia_de_montagem.md`. As medidas saem do modelo 3D (`casa_gerador.py`), cabine de 2.000 × 1.600 × 2.120 mm. Todas as medidas em milímetros.

Desenho das chapas: `plano_de_corte.png` (ou `plano_de_corte.svg`). O desenho é gerado e conferido por `plano_de_corte.py`, que acusa erro se alguma peça não couber ou encostar em outra.

---

## 1. Resumo

- **São 9 chapas de 2.200 × 1.600 mm**, e não 5 a 6 como estimado no documento do projeto. Só as peças somam 28,0 m², e cada chapa tem 3,52 m².
- O número não baixa com encaixe melhor: há 9 peças grandes (base, teto, tampa, traseira inferior, 2 laterais, divisória e 2 folhas de porta) e nenhuma delas divide chapa com outra.
- Sobra cerca de um quarto de chapa na 7, na 8 e na 9. Serve de reserva para erro de corte e para o defletor de ar frio, se for adotado.
- Além do compensado, a estrutura usa **sarrafos 40 × 40 e longarinas 45 × 70 de madeira maciça**. As medidas de cada um estão em `lista_de_pecas.md`.

## 2. Soluções construtivas já aplicadas ao modelo 3D

1. **Parede traseira em duas peças**, porque 1.666 de altura não cabe na chapa de 1.600:
   - traseira inferior de 2.000 × 1.560, do piso até 1.658 de altura;
   - traseira superior de 2.000 × 444, de 1.658 até 2.102, que cobre o topo da câmara e faz a parede de trás do capuz;
   - régua de emenda de compensado de 18 × 100 por dentro, com cola PU e parafusos.
2. **Teto da câmara com 2.000 × 1.582**, encostando por dentro na traseira superior.
3. **Folhas de porta com 936 × 1.658**, com 4 mm de folga em cima e embaixo, e batentes de 60 mm.
4. **Tampa do capuz com a chapa inteira (2.200 × 1.600)**, que dá 100 mm de beiral sobre cada veneziana lateral.
5. **Sarrafos 40 × 40 em todas as quinas internas**, dentro da espessura do revestimento. As chapas são coladas e parafusadas neles.
6. **Apoio em 3 longarinas 45 × 70 sobre 9 calços de borracha de 10 mm**, no lugar dos 6 pés de borracha de 80 mm. A altura do piso não muda.
7. **Quadro de compensado 18 × 50** em volta da lã de cada folha de porta.

## 3. Lista de peças (compensado naval 18 mm)

Os desenhos cotados de cada peça, com os furos, estão em `desenhos/desenhos_tecnicos.pdf`. A coluna "Folha" é o código do desenho.

| Folha | Peça | Qtd | Medida | Recortes | Chapa |
|---|---|---|---|---|---|
| P01 | Base (piso) | 1 | 2.000 × 1.600 | 2 furos de dreno Ø10 no duto de entrada | 1 |
| P02 | Teto da câmara | 1 | 2.000 × 1.582 | 2 furos Ø300 para os exaustores | 2 |
| P03 | Tampa do capuz | 1 | 2.200 × 1.600 | — | 3 |
| P04 | Traseira inferior | 1 | 2.000 × 1.560 | — | 4 |
| P05 | Traseira superior | 1 | 2.000 × 444 | — | 8 |
| P06 | Lateral da entrada de ar frio | 1 | 1.564 × 1.666 | abertura 1.100 × 400 para a veneziana | 5 |
| P07 | Lateral do escapamento | 1 | 1.564 × 1.666 | furo Ø150 para a flange térmica | 6 |
| P08 | Divisória do labirinto de entrada | 1 | 1.514 × 1.402 | — | 7 |
| P09 | Capuz: frente | 1 | 2.000 × 320 | — | 9 |
| P10 | Capuz: lateral da saída quente | 1 | 1.564 × 320 | abertura 1.300 × 220 para a veneziana | 5 |
| P11 | Capuz: lateral fechada | 1 | 1.564 × 320 | — | 6 |
| P12 | Chicana 1 do capuz (presa à tampa) | 1 | 1.464 × 182 | — | 1 |
| P13 | Chicana 2 do capuz (presa ao piso do capuz) | 1 | 1.464 × 198 | — | 5 |
| P14 e P15 | Folha de porta | 2 | 936 × 1.658 | — | 8 e 9 |
| P16 e P17 | Guarnição lateral das portas | 2 | 60 × 1.666 | — | 9 |
| P18 e P19 | Batente inferior e superior | 2 | 1.964 × 60 | — | 8 |
| P20 e P21 | Batente lateral | 2 | 80 × 1.546 | — | 2 |
| — | Mata-junta central | 1 | 60 × 1.542 | — | 7 |
| — | Régua de emenda da traseira | 1 | 1.884 × 100 | — | 7 |
| — | Quadro da lã das portas, vertical | 4 | 50 × 1.542 | — | 4 e 6 |
| — | Quadro da lã das portas, horizontal | 4 | 828 × 50 | — | 6 e 7 |

Posição dos recortes, medida a partir do piso acabado (face de cima da base) e da face interna da parede traseira:

- **Veneziana de entrada** (P06): de 232 a 1.332 no sentido da profundidade; de 52 a 452 de altura.
- **Furo da flange** (P07): centro a 542 da traseira e a 352 de altura. Confirmar com o bocal real do silencioso antes de furar.
- **Veneziana de saída** (P10): de 132 a 1.432 no sentido da profundidade; de 48 a 268 de altura da peça.
- **Furos dos exaustores** (P02): centros a 850 da lateral do escapamento; a 482 e a 1.082 da borda traseira da peça.

O recorte da veneziana de saída deixa só 48 a 52 mm de madeira em cima e embaixo. Os sarrafos do capuz ficam exatamente atrás dessas duas faixas e as reforçam.

## 4. Lista de materiais

### 4.1. Madeira e proteção

| Item | Quantidade | Observação |
|---|---|---|
| Compensado naval 18 mm, 2.200 × 1.600 | 9 chapas | cola fenólica WBP |
| Verniz marítimo PU ou resina epóxi | ~8 L | 3 demãos em ~23 m² de face externa, mais todos os topos |
| Tinta asfáltica ou emborrachada | ~2 L | face de baixo do piso (3,2 m²), 2 demãos |
| Cobertura: telha galvanizada ou manta aluminizada | ~2,3 × 1,8 m | sobre a tampa, com caimento de 3 a 5% |
| Selante PU40 | 6 tubos | juntas internas e cantoneiras |
| Cola PU para madeira | 2 kg | todas as juntas estruturais |
| Sarrafo 40 × 40 de madeira seca tratada | 17 barras de 3 m | 40,8 m de peças; cantos e apoios das chapas |
| Longarina 45 × 70 de madeira tratada | 3 de 2 m | apoio sob a base |
| Ripa ou compensado de 12 × 40 | 2 de 1.666 | calço entre guarnição e batente |
| Parafusos inox 4,5 × 40 | 400 | chapa no sarrafo |
| Parafusos inox 4,5 × 50 | 100 | base, teto e tampa nos sarrafos |
| Parafusos inox 5,0 × 80 | 50 | sarrafo + chapa até o sarrafo ou a longarina |
| Parafusos inox 5,0 × 70 | 50 | guarnições e dobradiças |
| Parafusos inox 5,0 × 50 com arruela de EPDM | 30 | tampa do capuz |
| Parafusos inox 4,0 × 30 | 30 | régua de emenda |
| Parafusos inox 4,0 × 30 com arruela larga | ~300 | fixação da tela sobre a lã |
| Cantoneira "L" 25 × 25 | ~8,5 m | 4 quinas verticais de 2,04 m |

### 4.2. Isolamento

| Item | Quantidade | Observação |
|---|---|---|
| Lã de rocha 50 mm, 64 kg/m³ | ~25 m² | área revestida de ~22 m² mais 10% de perda |
| Tela perfurada ou eletrossoldada galvanizada | ~25 m² | mesma área da lã |
| Tapete de borracha | 1.100 × 1.250 | o modelo usa 20 mm de espessura; o projeto cita 10 a 15 mm |
| Calços de borracha 120 × 60 × 10 | 9 | 3 sob cada longarina |

A lã de rocha ficou acima dos 16 a 18 m² estimados no projeto. Distribuição aproximada: câmara 17 m² (teto, duas laterais, traseira, duas faces da divisória e portas) e capuz 5 m². O piso da câmara e o piso do capuz não levam lã no modelo.

### 4.3. Ventilação e escapamento

| Item | Quantidade | Observação |
|---|---|---|
| Exaustor axial 300 mm, 220 V | 2 | escolher pela curva de pressão, não pela vazão livre |
| Veneziana de entrada 1.100 × 400 | 1 | aletas a 45° para baixo, com tela anti-insetos |
| Veneziana de saída 1.300 × 220 | 1 | idem |
| Tubo flexível corrugado inox | 1 m | diâmetro conforme o bocal do silencioso (38 a 50 mm) |
| Abraçadeiras para o tubo | 2 | |
| Chapa de aço 250 × 250, 1,5 a 2 mm | 2 | flange térmica, uma por dentro e uma por fora |
| Manta de fibra cerâmica | ~0,1 m² | miolo da flange |
| Silicone de alta temperatura | 1 tubo | vedação externa da flange |

### 4.4. Portas e ferragens

| Item | Quantidade |
|---|---|
| Borracha EPDM perfil "D" ou "P" 12 × 10 | 10 m |
| Dobradiça reforçada 4", inox ou galvanizada | 6 |
| Ferrolho vertical | 2 |
| Fecho rápido de pressão ajustável | 3 |
| Puxador tipo alça | 2 |
| Pingadeira em "L" | 1,92 m |

### 4.5. Elétrica

| Item | Quantidade |
|---|---|
| Fita de LED 12 V IP65, 1 m | 1 |
| Interruptor e porta-fusível com fusível de 5 A | 1 de cada |
| Cabo 2 × 0,75 mm² para o LED | ~5 m |
| Prensa-cabo IP68 para a saída de força | 1 a 2 |
| Cabo e proteção para os 2 exaustores (220 V) | conforme instalação |

## 5. Diferenças entre o documento do projeto e o modelo 3D

Vale decidir qual versão prevalece antes de comprar:

| Assunto | Documento do projeto | Modelo 3D |
|---|---|---|
| Chapas de compensado | 5 a 6 | 9 |
| Apoio no chão | 6 pés de borracha de 80 a 100 mm | 3 longarinas 45 × 70 sobre 9 calços de borracha de 10 mm |
| Lã de rocha | 16 a 18 m², nos 6 lados da câmara | ~22 m², sem lã no piso |
| Teto | inclinado, com caimento | tampa plana |
| Tapete | ~1.100 × 900, 10 a 15 mm | 1.100 × 1.250, 20 mm |
| Flange térmica | chapas quadradas 250 × 250 | discos de Ø160 |
| Veneziana de entrada | aletas a 45° | aletas a 35° |
| Folga lateral do gerador | ~380 mm | 430 mm do lado da entrada, 250 mm do lado do escapamento |

## 6. Pontos de projeto ainda em aberto

Não entram nesta lista de corte, mas afetam a compra:

- **Segundo silencioso** na linha externa do escapamento. Sem ele, o ruído de escape não passa pelo tratamento acústico da cabine.
- **Defletor de ar frio** para levar o ar até a altura da ventoinha do motor. Seria mais uma peça de compensado de cerca de 1.464 × 1.200, que cabe na sobra da chapa 7.
- **Termostato ou alarme de temperatura** e temporizador para os exaustores seguirem ligados alguns minutos após o desligamento.
