# Facts

Every number and claim in `script.md` is here, checked 2026-10-31.

| # | Claim | Source |
| --- | --- | --- |
| 1 | Typical soda-lime glass is about 70% silica, 15% soda, 9% lime | [Soda-lime glass](https://www.doc.surf/wiki/soda-lime-glass) |
| 2 | Silica melts at about 1,713 °C, and is too viscous there to work easily | [Glenn Lockwood, glass compositions](https://www.glennklockwood.com/materials-science/glass-compositions.html) |
| 3 | Soda reduces the melting temperature dramatically, but makes the glass water-soluble | Same as 2 |
| 4 | Lime (CaO, usually from limestone) is added to counter that | Same as 1 |
| 5 | Each 10% of cullet cuts furnace energy by about 2.5 to 3% | [CTCN](https://www.ctc-n.org/technologies/glass-recycling), [GMIC](https://gmic.org/?p=2100) |
| 6 | Batch is weighed and mixed by an electronically controlled plant, and proportions are "absolutely critical" | [Beatson Clark](https://www.beatsonclark.co.uk/glass-process) |
| 7 | Container furnaces run around the clock all year | [Wikipedia, Glass melting furnace](https://en.wikipedia.org/wiki/Glass_melting_furnace) |
| 8 | Average container furnace campaigns are 8 to 10 years | [SORG, glassonweb](https://glassonweb.com/news/sorg-15-years-and-16m-tons-even-more-records) |
| 9 | The furnace must reach about 1,600 °C. Another source says up to about 1,575 °C | Beatson Clark, [Wikipedia, Glass production](https://en.wikipedia.org/wiki/Glass_production) |
| 10 | Gas bubbles form during melting, and fining agents such as sodium sulfate release gases that help clear them | Fining patents ([US 11,697,608](https://patents.justia.com/patent/11697608)) |
| 11 | The forehearth conditions glass to about 1,100 °C | Beatson Clark |
| 12 | Glass is sheared into gobs of set weight, which fall by gravity through troughs and chutes | Wikipedia, Glass production |
| 13 | IS machines have 5 to 20 sections, each making 1 to 4 containers at once | Same as 12 |
| 14 | 12-section machines ran at about 470 bottles a minute, 13 cycles a minute | [Glass Online, IVC](https://www.glassonline.com/emhart-machines-for-ivc/) |
| 15 | In press-and-blow the plunger rises to press the gob, forming the neck and blank | Beatson Clark |
| 16 | The part-made container is inverted through 180° and moved to the blow mould | Beatson Clark |
| 17 | The neck ring arm holds the parison by its finish and swings it across. The blow mould closes around it | Wikipedia, Glass production |
| 18 | Heatproof plunger materials allowed plungers thin enough for narrow necks | [Eurotherm](https://www.eurotherm.com/?p=84959) |
| 19 | Press-and-blow gives more uniform walls, allowing lighter narrow-neck bottles | [US 4,411,681](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/4411681) |
| 20 | After moulding, glass can drop from 1,100 °C to 600 °C in about 10 s. Outside cools fast, inside stays hotter, which locks in thermal stress | [Daxin, thermal stress and annealing](https://www.daxinglassbottle.com/news/glass-bottles-and-jars-thermal-stress-and-annealing) |
| 21 | Unremoved stress lowers strength, and can make glass crack on its own | Same as 20 |
| 22 | Hot-end coating is applied seconds after forming at about 400–600 °C, as a vapour through a hood | [Glassrock](https://glassrock.com/?p=11036) |
| 23 | It's a very thin tin oxide layer, applied just before annealing, and helps the cold-end coating adhere | Wikipedia, Glass production |
| 24 | The lehr heats containers to about 580 °C, then cools them over 20 to 60 minutes, depending on thickness | Same as 23 |
| 25 | Cold-end coating is a polyethylene wax that makes the surface slippery and scratch-resistant | Same as 23 |
| 26 | Every container is inspected, for checks (small cracks), stones, blisters and thin walls | Same as 23 |
| 27 | Mould numbers on containers trace defects back to a mould | Same as 23 |

**Deliberately left out:** that rejects are crushed into cullet (no direct source), and "never loses quality" (too strong for the sources).

## Stage cards

```
STAGE: Melt
INPUT: dry granular batch
PRINCIPLE: flux lowers melting temperature; gas escapes during melting
PARAMETERS: up to about 1,600 °C, continuous
OUTPUT: clear melt
MUST SHOW: yellow-white glow, closed tank seen through a port, rising bubbles
MUST NOT SHOW: stove door, loose flames, red or brown liquid

STAGE: Forehearth and shear
INPUT: clear melt
PRINCIPLE: cooling raises viscosity
PARAMETERS: about 1,100 °C
OUTPUT: gob of set weight
MUST SHOW: yellow-orange stream falling straight down, blades, cylinder-shaped gob
MUST NOT SHOW: sideways flow, sparks, bubbles in the gob

STAGE: Blank side (press)
INPUT: gob at about 1,100 °C
PRINCIPLE: pressing into a metal mould; skin stiffens on contact
ORDER: gob lands, mould sealed from above, plunger rises
OUTPUT: hollow parison, neck already formed, neck pointing DOWN
MUST SHOW: neck ring at bottom, plunger rising from below
MUST NOT SHOW: plunger from above, finished bottle shape

STAGE: Invert
INPUT: parison, skin stiff, core soft
PRINCIPLE: 180° swing on the neck ring arm
OUTPUT: parison right way up in the open blow mould
MUST SHOW: held by the neck only, orange glow
MUST NOT SHOW: gripped by the body

STAGE: Final blow
INPUT: parison in closed blow mould
PRINCIPLE: compressed air expands soft glass to the mould wall
OUTPUT: bottle, cooling fast
MUST SHOW: closed mould (cutaway), air entering at the neck
MUST NOT SHOW: glass ballooning outside the mould

STAGE: Hot-end coating
INPUT: bottle at about 400–600 °C
PRINCIPLE: vapour reacts on hot glass to leave tin oxide
OUTPUT: invisible film
MUST SHOW: a hood over the conveyor, faint haze, near-black dull glow
MUST NOT SHOW: liquid jet, bright orange bottle

STAGE: Lehr
INPUT: bottle with locked-in stress
PRINCIPLE: reheat so stress relaxes, then cool slowly
PARAMETERS: about 580 °C, 20–60 min
OUTPUT: stress-free bottle
MUST SHOW: steel mesh belt, glow fading along the direction of travel
MUST NOT SHOW: wooden belt, glow growing as bottles travel
```
