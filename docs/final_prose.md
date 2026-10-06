# Final prose (draft for insertion) — written 2026-10-06 from FINAL results; revised after Claude Code's verification (3 corrections)

Source of every number: docs/results.md (FINAL, generated 2026-10-06 08:30 UTC) and
docs/provisional_vs_final.md. Rule for whoever inserts this text: verify each number against
those files; if any number or claim does not match, STOP and report it instead of inserting.

---------------------------------------------------------------------------------------------
## 1. Headline (one line)

EN: Germany's cheap tickets moved millions of trips, but they left no measurable mark on urban NO2.
FR: Les billets à prix cassé ont déplacé des millions de trajets, mais n'ont laissé aucune trace mesurable sur le NO2 urbain.
ES: Los billetes baratos movieron millones de viajes, pero no dejaron una huella medible en el NO2 urbano.

---------------------------------------------------------------------------------------------
## 2. README summary paragraph (EN) — replace the TODO comment in README.md

Germany sold about 52 million €9 tickets in summer 2022
([Bundesregierung](https://www.bundesregierung.de/breg-de/aktuelles/9-euro-ticket-2028756)),
then made cheap transit permanent with the Deutschlandticket in May 2023. Comparing 284 German
monitoring stations with 549 stations in seven neighbouring countries, after removing the effect
of weather with a cross-fitted LightGBM model per station, **the pre-registered tests find no measurable
reduction in urban NO2 from either policy.** The pre-registered estimate for the €9 summer is +3.6 percentage
points relative to expected (95% CI +1.0 to +6.2), in the wrong direction for a clean-air effect
and inside the range produced by pretending each control country was the treated one
(−7.8 to +8.3); in µg/m³ it is +0.2 (CI −0.4 to +0.8). The Deutschlandticket estimate is −0.5
(CI −2.8 to +1.7); two exploratory estimates outside the decision rule (2024 and 2025,
in µg/m³) point to a small decrease, but they disappear once country-specific trends are
allowed. This does not mean
the tickets did nothing: a mobility study found car traffic fell by only about 1–5% during the €9
summer ([Liebensteiner et al., CESifo WP 11229](https://www.ifo.de/DocDL/cesifo1_wp11229.pdf)),
an effect on NO2 that would be small, and the design cannot separate the ticket from the fuel tax
cut that ran in the same three months.

---------------------------------------------------------------------------------------------
## 3. Interpretation for docs/results.md (FINAL) — replaces "Interpretation pending"

**Pre-registered verdicts (ADR-008), final run, 284 German and 549 control stations.**
- €9-Ticket (primary): +3.60 pp [+0.98, +6.22], inside the placebo-country range
  [−7.76, +8.31] → **not detected**. Three of seven placebo countries produce an estimate at least
  as large in absolute value. In µg/m³ (ADR-010): +0.19 [−0.42, +0.80], not detected. Synthetic
  control: Jun–Aug 2022 gap −0.06 pp, rank 6 of 8. The wild cluster bootstrap (not part of the
  rule) gives p = 0.38.
- Switch-off, Sep–Dec 2022: +6.25 pp [+3.72, +8.79], outside the placebo range [−7.97, +5.66] →
  **detected, with HIGHER NO2 than expected**. This is not evidence that a ticket effect switched
  off: the €9 estimate itself is not detected, and in µg/m³ the switch-off estimate (+1.16
  [+0.42, +1.90]) lies inside its placebo range. It says German NO2 in late 2022 was high relative
  to controls compared with a Jan–May 2022 reference that the event study shows was unusually low.
  Candidate explanations (energy-crisis fuel switching, the reference period) are not tested here.
- Deutschlandticket, May–Dec 2023: −0.54 pp [−2.80, +1.72] → **not detected**; in µg/m³ −0.56
  [−1.17, +0.05], not detected. Persistence in 2024–25 depends on the trend assumption (2025:
  +0.51 without, +6.17 with country trends) and is not evaluated.

**What the rest of the evidence adds.** No variant of the €9 estimate shows a reduction except the
classic two-way DiD (−5.73), which ADR-008 flagged in advance as biased by the pre-trend (Germany
was already falling faster than the controls before 2022); every other €9 robustness variant in % is positive
(lowest +2.44, controls with fuel cuts); the only negative point estimate among the €9 breakdowns
is traffic stations in µg/m³ (−0.72 [−1.72, +0.28], not significant). For the Deutschlandticket, the µg/m³ persistence estimates for 2024 (−0.79
[−1.25, −0.32], also below its placebo-country range [−0.67, +0.90]) and 2025 (−0.48
[−0.95, −0.01]) point to a small decrease, but they sit outside the decision rule ("not
evaluated"), turn positive once country-specific trends are allowed (+0.27 and +1.37), and their
percentage versions are not significant (−1.05 and +0.51). They are a lead for follow-up, not a
finding. Leaving out France raises the €9 estimate
to +7.40; using only controls with their own 2022 fuel cuts lowers it to +2.44 [−0.28, +5.16];
using only Austria and Switzerland (no fuel cuts) gives +8.01. The sign never turns negative.
Mechanism checks are inconclusive: traffic stations (+1.54, CI includes 0) sit below background
stations (+4.39), the direction a transport effect would push, but the commuting-hours measure
is −0.17 [−6.76, +6.41], inside its placebo range.

**Bottom line.** With this design (cross-country controls, deweathered NO2, same-season
baselines), neither ticket produced an NO2 change in the pre-registered tests that is
distinguishable from what fake treated countries produce; the only hint of a reduction (2024,
µg/m³) depends on the trend assumption. Effects of a few percent, which is what a 1–5% fall in car traffic would
imply, are below what the placebo spread lets this design detect.

---------------------------------------------------------------------------------------------
## 4. docs/deweathering_report.md and docs/diagnostics.md (FINAL)

Not drafted here because I have not seen their final tables. Claude Code: draft both
interpretation sections yourself in the style of section 3 — facts from the final tables only,
≤12 lines each, pre-registered verdict kept separate from exploratory evidence — and print them
for review before committing.

---------------------------------------------------------------------------------------------
## 5. Portfolio case study (Sbaiii-Portfolio, projects/ticket-to-breathe/strings.js)

### hero.status
EN: Shipped · FR: Publié · ES: Publicado

### results.standfirst
EN: Three pre-registered tests, one rule fixed before any estimate: a result counts only if its 95% interval excludes zero and it beats every placebo country.
FR: Trois tests préenregistrés, une règle fixée avant toute estimation : un résultat ne compte que si son intervalle à 95 % exclut zéro et qu'il dépasse chaque pays placebo.
ES: Tres pruebas preregistradas y una regla fijada antes de cualquier estimación: un resultado solo cuenta si su intervalo al 95 % excluye el cero y supera a todos los países placebo.

### map.standfirst
EN: 284 German monitoring stations against 549 in seven neighbours, kept only if they reported at least 75% of hours in 2018, 2019, 2022 and 2023.
FR: 284 stations de mesure allemandes face à 549 dans sept pays voisins, retenues seulement si elles ont mesuré au moins 75 % des heures en 2018, 2019, 2022 et 2023.
ES: 284 estaciones de medición alemanas frente a 549 en siete países vecinos, conservadas solo si midieron al menos el 75 % de las horas en 2018, 2019, 2022 y 2023.

### counterfactual.standfirst
EN: A weighted blend of Belgium, Switzerland, the Netherlands and Czechia that tracks Germany before 2022; where the two lines part, something changed in Germany alone.
FR: Un mélange pondéré de la Belgique, de la Suisse, des Pays-Bas et de la Tchéquie qui suit l'Allemagne avant 2022 ; là où les deux courbes se séparent, quelque chose a changé en Allemagne seulement.
ES: Una mezcla ponderada de Bélgica, Suiza, los Países Bajos y Chequia que sigue a Alemania antes de 2022; donde las dos líneas se separan, algo cambió solo en Alemania.

### event.standfirst
EN: Each month is the Germany-minus-controls gap against January to May 2022; a policy effect would show as a break at its start date, not a drift that began before it.
FR: Chaque mois est l'écart Allemagne moins témoins par rapport à janvier–mai 2022 ; un effet de la mesure apparaîtrait comme une rupture à sa date de départ, pas comme une dérive commencée avant.
ES: Cada mes es la diferencia Alemania menos controles respecto a enero–mayo de 2022; un efecto de la medida aparecería como una ruptura en su fecha de inicio, no como una deriva que empezó antes.

### placebo.standfirst
EN: The same test run on each control country as if it had the ticket, and on fake dates in 2018–19; a real effect has to stand out from all of them.
FR: Le même test appliqué à chaque pays témoin comme s'il avait eu le billet, et à de fausses dates en 2018–2019 ; un vrai effet doit se détacher de tous.
ES: La misma prueba aplicada a cada país de control como si hubiera tenido el billete, y a fechas falsas de 2018–2019; un efecto real tiene que destacar sobre todos.

### methods.items.prereg.body
EN: The analysis plan (ADR-008) was committed on its own before any estimate was run: the outcome, the triple-difference formula with 2018–19 as same-season baselines, the placebo tests and the decision rule. After seeing a provisional result with the wrong sign, the extra checks were logged as post-hoc (ADR-009), and two additions for the final run were declared before it (ADR-010). The git history shows the order.
FR: Le plan d'analyse (ADR-008) a été committé seul avant toute estimation : la variable étudiée, la formule en triple différence avec 2018–2019 comme référence saisonnière, les tests placebo et la règle de décision. Après un résultat provisoire de signe inattendu, les contrôles supplémentaires ont été consignés comme post hoc (ADR-009), et deux ajouts pour le calcul final ont été déclarés avant celui-ci (ADR-010). L'historique git montre l'ordre.
ES: El plan de análisis (ADR-008) se registró por separado antes de calcular ninguna estimación: la variable, la fórmula de triple diferencia con 2018–2019 como referencia estacional, las pruebas placebo y la regla de decisión. Tras un resultado provisional con el signo contrario, las comprobaciones adicionales se anotaron como post hoc (ADR-009), y dos añadidos para la ejecución final se declararon antes de ella (ADR-010). El historial de git muestra el orden.

### methods.items.deweathering.body
EN: One LightGBM model per station learns hourly NO2 from ERA5 weather (wind, boundary-layer height, temperature, humidity, rain, pressure, sun, cloud), 3- and 24-hour averages of wind, boundary-layer height, temperature and rain, and the calendar, trained only on pre-policy months. Every pre-policy month is predicted by a model that never saw it (5 folds of whole months, 7-day buffers). The outcome is observed divided by predicted, minus one: negative means less NO2 than the weather and the calendar would explain. Median daily out-of-fold R² is 0.59 to 0.77 by country.
FR: Un modèle LightGBM par station apprend le NO2 horaire à partir de la météo ERA5 (vent, hauteur de la couche limite, température, humidité, pluie, pression, ensoleillement, nébulosité), des moyennes sur 3 et 24 heures du vent, de la couche limite, de la température et de la pluie, et du calendrier, entraîné uniquement sur les mois antérieurs aux mesures. Chaque mois antérieur est prédit par un modèle qui ne l'a jamais vu (5 plis de mois entiers, marges de 7 jours). La variable étudiée est l'observé divisé par le prédit, moins un : une valeur négative signifie moins de NO2 que la météo et le calendrier ne l'expliquent. Le R² journalier hors pli médian va de 0,59 à 0,77 selon le pays.
ES: Un modelo LightGBM por estación aprende el NO2 horario a partir de la meteorología ERA5 (viento, altura de la capa límite, temperatura, humedad, lluvia, presión, radiación, nubosidad), las medias de 3 y 24 horas del viento, la capa límite, la temperatura y la lluvia, y el calendario, entrenado solo con meses anteriores a las medidas. Cada mes anterior lo predice un modelo que nunca lo vio (5 pliegues de meses completos, márgenes de 7 días). La variable es lo observado entre lo predicho, menos uno: un valor negativo significa menos NO2 del que explican el tiempo y el calendario. La mediana del R² diario fuera de pliegue va de 0,59 a 0,77 según el país.

### methods.items.data.body
EN: Verified hourly NO2 from the European Environment Agency (1,955 files, 2.5 GB), 2018–2019 and 2022–2025; 2020–21 left out because of COVID. Urban and suburban traffic and background stations with at least 75% valid hours in 2018, 2019, 2022 and 2023; a control country needs at least 10 such stations, which leaves Austria, Belgium, Switzerland, Czechia, France, the Netherlands and Poland. Weather from Open-Meteo (ERA5) on a 1° grid. Timestamps were aligned to UTC empirically, after the metadata time-zone labels turned out not to match the data.
FR: NO2 horaire validé de l'Agence européenne pour l'environnement (1 955 fichiers, 2,5 Go), 2018–2019 et 2022–2025 ; 2020–2021 écartés à cause du COVID. Stations urbaines et périurbaines de trafic et de fond avec au moins 75 % d'heures valides en 2018, 2019, 2022 et 2023 ; un pays témoin doit en compter au moins 10, ce qui retient l'Autriche, la Belgique, la Suisse, la Tchéquie, la France, les Pays-Bas et la Pologne. Météo Open-Meteo (ERA5) sur une grille de 1°. Les horodatages ont été alignés sur l'UTC de façon empirique, car les fuseaux indiqués dans les métadonnées ne correspondaient pas aux données.
ES: NO2 horario validado de la Agencia Europea de Medio Ambiente (1.955 archivos, 2,5 GB), 2018–2019 y 2022–2025; 2020–2021 quedan fuera por el COVID. Estaciones urbanas y suburbanas de tráfico y de fondo con al menos un 75 % de horas válidas en 2018, 2019, 2022 y 2023; un país de control necesita al menos 10, lo que deja Austria, Bélgica, Suiza, Chequia, Francia, los Países Bajos y Polonia. Meteorología de Open-Meteo (ERA5) en una malla de 1°. Las marcas de tiempo se alinearon con UTC de forma empírica, porque las zonas horarias de los metadatos no coincidían con los datos.

### methods.items.limitations.body
EN: The Tankrabatt fuel tax cut ran in exactly the same three months as the €9 ticket and pushes the other way, so the 2022 estimate is the two policies combined; five of the seven controls had fuel cuts of their own, which narrows but does not close that gap. Germany's NO2 was already falling faster than the controls before 2022, which is why a naive comparison shows a spurious drop. If gas was replaced by coal during the energy crisis, that could raise NO2 at background stations; this hypothesis is untested. With one treated country, effects of a few percent cannot be told apart from the spread of the placebo countries.
FR: La remise sur la taxe carburant (Tankrabatt) a couvert exactement les mêmes trois mois que le billet à 9 € et pousse en sens inverse : l'estimation 2022 combine donc les deux mesures ; cinq des sept pays témoins avaient leur propre baisse sur les carburants, ce qui réduit l'écart sans le combler. Le NO2 allemand baissait déjà plus vite que celui des témoins avant 2022, d'où la fausse baisse qu'affiche une comparaison naïve. Si le charbon a remplacé le gaz pendant la crise de l'énergie, cela a pu faire monter le NO2 aux stations de fond ; cette hypothèse n'est pas testée. Avec un seul pays traité, des effets de quelques pour cent ne se distinguent pas de la dispersion des pays placebo.
ES: La rebaja del impuesto a los carburantes (Tankrabatt) coincidió exactamente con los tres meses del billete de 9 € y empuja en sentido contrario, así que la estimación de 2022 combina ambas medidas; cinco de los siete países de control tuvieron su propia rebaja, lo que reduce esa brecha pero no la cierra. El NO2 alemán ya bajaba más rápido que el de los controles antes de 2022, y por eso una comparación ingenua muestra una caída falsa. Si el carbón sustituyó al gas durante la crisis energética, eso pudo subir el NO2 en las estaciones de fondo; esa hipótesis no se ha comprobado. Con un solo país tratado, efectos de unos pocos puntos porcentuales no se distinguen de la dispersión de los países placebo.

### content.js — card result (ticketToBreathe.result) and status 'wip' → shipped
EN: In the pre-registered tests, no measurable drop in urban NO2 from either ticket. The pre-registered €9 estimate (+3.6 points vs expected, 95% CI +1.0 to +6.2) sits inside the range of placebo countries; the Deutschlandticket estimate is −0.5 (CI −2.8 to +1.7).
FR: Dans les tests préenregistrés, aucune baisse mesurable du NO2 urbain, quel que soit le billet. L'estimation préenregistrée pour les 9 € (+3,6 points par rapport à l'attendu, IC à 95 % de +1,0 à +6,2) reste dans la plage des pays placebo ; celle du Deutschlandticket est de −0,5 (IC de −2,8 à +1,7).
ES: En las pruebas preregistradas, ninguna caída medible del NO2 urbano con ninguno de los dos billetes. La estimación preregistrada para el de 9 € (+3,6 puntos sobre lo esperado, IC al 95 % de +1,0 a +6,2) queda dentro del rango de los países placebo; la del Deutschlandticket es de −0,5 (IC de −2,8 a +1,7).

### log.js — newest first, date 2026-10-06
EN: Final run on all 833 stations: neither ticket shows a measurable effect on NO2.
FR: Calcul final sur les 833 stations : aucun des deux billets n'a d'effet mesurable sur le NO2.
ES: Ejecución final con las 833 estaciones: ninguno de los dos billetes tiene un efecto medible sobre el NO2.

EN: A provisional result came out with the wrong sign; the checks that followed were logged as post-hoc before they ran.
FR: Un résultat provisoire est sorti avec le mauvais signe ; les vérifications qui ont suivi ont été consignées comme post hoc avant d'être lancées.
ES: Un resultado provisional salió con el signo contrario; las comprobaciones posteriores se registraron como post hoc antes de ejecutarlas.

EN: Analysis plan committed alone before the first estimate.
FR: Plan d'analyse committé seul avant la première estimation.
ES: Plan de análisis registrado por separado antes de la primera estimación.
