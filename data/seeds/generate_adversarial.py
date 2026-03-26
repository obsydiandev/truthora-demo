#!/usr/bin/env python3
"""Generate adversarial (tabloid/social-media) claim variants for golden pairs.

Adds a `claim_adversarial` field to each golden pair. These variants use
sensationalist language, clickbait phrasing, slang, and indirect references
that differ lexically from the indexed fact-check text while preserving
the same semantic meaning.

This makes the benchmark harder and more realistic — real users don't
type "COVID-19 vaccine causes infertility"; they paste
"SHOCKING: Women who took the jab CAN'T GET PREGNANT anymore!!!"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent.parent / "benchmark"

# ── English adversarial rewrites ──────────────────────────────────────────────
# Each adversarial claim MUST be about the SAME topic as the original claim,
# just in tabloid/social-media style.

EN_ADVERSARIAL: dict[str, str] = {
    # Microchip / tracking
    "en_01": "SHOCKING: Women who took the jab CAN'T GET PREGNANT anymore!!!",
    "en_02": "They put a TRACKING CHIP inside the covid shot - your phone is proof!",
    "en_03": "EXPOSED: Bill Gates' plan to chip everyone through the needle 💉",
    "en_04": "lmaooo did Bill Gates really tweet about running out of microchips for vaxxes 😂",
    "en_05": "WATCH: Magnets STICK to people's arms after getting vaxxed 🧲 PROOF of chips!",
    "en_06": "People are becoming MAGNETIC after the shot - tracking devices confirmed???",
    "en_07": "LEAKED video shows microchip pulled from Pfizer vial!! They can't hide this",
    "en_08": "Bill Gates + ID2020 = mass chipping through covid jabs. Wake up people!",
    "en_09": "Gates' ENDGAME: use covid needles to microchip the entire world!! 😱",
    "en_10": "Soros and Gates secretly chipping people during covid testing - Dems involved",
    "en_11": "Woman scanned with PET MICROCHIP READER and it beeped ON HER ARM after the jab!! 🐶📡",
    "en_12": "NEW TECH: They made microchips small enough to fit INSIDE vaccine needles now!!",
    "en_13": "60 MINUTES exposed government tracking chip hidden in vaccines!! Why is nobody talking about this?!",
    "en_14": "Refuse the shot? They'll FORCE a microchip in you anyway!! This is the plan!!",
    # Fertility
    "en_15": "THE JAB DESTROYS FERTILITY - women losing babies after getting vaccinated!!",
    "en_16": "FORCING young girls to take the vax = sterilizing an entire generation!! WAKE UP!!",
    "en_17": "European Medicines Agency CAUGHT hiding data about vaccines causing INFERTILITY!!",
    "en_18": "ALL vaccinated men are now STERILE!! The science is clear but they BURY IT!!",
    "en_19": "Pfizer's OWN HEAD OF RESEARCH admitted the jab sterilizes women!! It's on video!!",
    "en_20": "EXPOSED: Covid vax wrecks male fertility - sperm count CRASHING in vaxxed men!!",
    "en_21": "The shot ATTACKS the placenta!! Babies dying in the womb from vax spike protein!!",
    "en_22": "Pfizer jab has syncytin-1 that makes your body ATTACK your own placenta!! Infertility by design!!",
    # Vaccine safety / side effects
    "en_23": "They KNEW about mRNA dangers and HID IT from us!! Safety data DELIBERATELY buried!!",
    "en_24": "HUNDREDS OF MILLIONS used as guinea pigs!! Now the truth is coming out and it's HORRIFYING!!",
    "en_25": "Study of 100 MILLION vaxxed people proves covid shots are EXTREMELY DANGEROUS!! 📊",
    "en_26": "Post-Vaccine Syndrome is OFFICIALLY REAL now - they finally admitted it!!",
    "en_27": "CDC official went on record: THE JAB causes debilitating chronic illness!! 😱",
    "en_28": "Kids had ZERO risk from covid!! Why did they jab millions of children?! CRIMINAL!!",
    "en_29": "Ohio doctor got the jab and DIED shortly after!! His family is DEVASTATED!! RIP 🙏",
    "en_30": "New review CONFIRMS: mRNA shoots CAUSE CANCER!! Turbo cancers exploding!! 📈",
    "en_31": "Pfizer CEO said something in 2018 that PROVES they planned covid vaxx IN ADVANCE!! Coincidence?!",
    "en_32": "COURT FORCED Pfizer to release SECRET list of vax side effects - it's 9 PAGES long!! 😱",
    "en_33": "Moderna PATENT proves their covid shot has programmable NANOTECH inside!! Read for yourself!!",
    "en_34": "COVID VACCINES contain Marburg virus!! 5G signal will ACTIVATE it!! Not a drill!!",
    "en_35": "New Kraken COVID variant is LINKED TO 5G SIGNALS!! They're connected!! Open your eyes!!",
    "en_36": "COVID was BACTERIAL all along, NOT a virus!! They lied so they could sell vaccines!!",
    # Ivermectin
    "en_37": "IVERMECTIN CURES COVID and they're hiding it!! Nobel prize winning drug BLOCKED by big pharma!!",
    "en_38": "Even the NIH website ADMITS ivermectin works against covid!! Why can't we use it?!",
    "en_39": "Ivermectin cures BOTH covid AND cancer!! Cheap miracle drug Big Pharma HATES!!",
    "en_40": "Pfizer's new covid pill is literally just REPACKAGED IVERMECTIN 💊🤡 same molecule!!",
    "en_41": "Indonesia OFFICIALLY approved ivermectin for covid treatment!! Why won't our countries do the same?!",
    "en_42": "NIH quietly ADDED ivermectin to their covid treatment list!! Media BLACKOUT on this!!",
    # Flat Earth
    "en_43": "US NAVY officially admitted the Earth is FLAT!! Classified docs leaked!! 🌍➡️📋",
    "en_44": "NASA's OWN DOCUMENTS contain proof Earth is FLAT!! They forgot to redact page 47!!",
    "en_45": "Photographic and observational PROOF the Earth is flat!! Globe believers can't explain THIS!!",
    "en_46": "Shooting stars ALWAYS fly UPWARD!! How is that possible on a spinning globe?! Checkmate!!",
    "en_47": "Coriolis effect DOESN'T AFFECT PLANES!! If earth was spinning pilots would need to compensate!! FLAT!!",
    "en_48": "Flight paths from New Zealand to Argentina make NO SENSE on a globe but PERFECT sense on flat map!!",
    "en_49": "Antarctica's perimeter is BIGGER than Earth's circumference!! Only makes sense if FLAT!! 🗺️",
    "en_50": "Operation Highjump: military expedition sent to find what's BEYOND Antarctica's ice wall!!",
    "en_51": "LEAKED FOOTAGE: Antarctica is just a massive ICE WALL surrounding our flat Earth!! 🧊",
    "en_52": "Ancient navigators used FLAT EARTH maps!! They KNEW - if Earth was round celestial navigation is impossible!!",
    # Moon landing
    "en_53": "NASA ADMITTED the moon landings were FAKED!! Internal memo leaked!! 🌙🎬",
    "en_54": "Buzz Aldrin literally CONFESSED on camera: we never went to the Moon!! Video keeps getting deleted!!",
    "en_55": "The Moon is TOO BRIGHT for humans to land on!! The light would have BLINDED them!! Science proves it!!",
    "en_56": "Video analysis PROVES moon landing was staged in a studio!! Wires visible in slow-mo!! 🎥",
    "en_57": "Former RUSSIAN SPACE CHIEF: America has NO PROOF they landed on the Moon!! Even Russia doubts it!!",
    "en_58": "Astronaut boot DOESN'T MATCH the footprint on the Moon!! Dead giveaway it was FAKED!!",
    "en_59": "The lunar rover couldn't FIT inside the Apollo capsule!! Do the math - it's OBVIOUS fraud!! 🚗🌙",
    "en_60": "Photo of Nixon at his desk with Moon footage playing BEFORE the landing happened!! Time travel? Or FAKE!",
    "en_61": "We called the MOON in 1969 but can't talk to a submarine underwater in 2024?? Come on people 🤡",
    "en_62": "Newspapers published Moon landing photos THE SAME DAY!! No internet back then - HOW?! Staged!!",
    # Trump / elections
    "en_63": "Trump facing 187 YEARS in prison!! The deep state will stop at nothing!! POLITICAL PERSECUTION!!",
    "en_64": "187 years behind bars for Trump after 34 felony counts!! The LEFT destroyed justice!!",
    "en_65": "HUGE W: ALL Trump convictions OVERTURNED!! Court awarded him $500 MILLION in damages!!",
    "en_66": "ALL CHARGES DROPPED in Trump hush money case!! Total witch hunt EXPOSED!! 🎉",
    "en_67": "Counting ballots AFTER election day?! That's literally HOW THEY STEAL ELECTIONS!! Common sense!!",
    "en_68": "Mail-in ballots = MASSIVE voter fraud!! Everyone knows you can print fake ones at home!!",
    "en_69": "Caught on camera!! TRUCK FULL OF BALLOTS delivered to Detroit at 3AM!! Who sent them?!",
    "en_70": "Federal election agency CONFIRMED fraud in 2020!! Why is no one arresting people?!",
    "en_71": "Georgia ADMITTED 3600 ballots were illegally counted!! Just in ONE county!! How many more?!",
    "en_72": "Tucker's expert proved with DATA: 20% of mail-in ballots in 2024 are FRAUDULENT!! 📊",
    "en_73": "Judge Merchan REFUSED to let Trump's lawyers present evidence!! Kangaroo court!! ⚖️🦘",
    "en_74": "Trump's NY case will be AUTOMATICALLY DISMISSED now that he's president!! It's the LAW!!",
    # Ukraine / NATO / geopolitics
    "en_75": "MSM won't tell you this: the war in Ukraine is ALREADY OVER!! Russia won MONTHS ago!!",
    "en_76": "NATO PROMISED Russia in 1990 they would NEVER expand eastward!! Documents PROVE IT!!",
    "en_77": "NATO VIOLATED every agreement by expanding into former Soviet states!! PROVOCATION!!",
    "en_78": "Western nations SIGNED A TREATY guaranteeing NATO would never expand east!! They BROKE it!!",
    "en_79": "Former NATO CHIEF admitted EU expansion PROVOKED Putin!! They started this!! 🤯",
    "en_80": "Russia has ALWAYS recognized Ukraine's borders!! Check the treaties!! They respected every one!!",
    "en_81": "Iran DENIES sending missiles to Russia!! Where's the PROOF?! Western propaganda!!",
    "en_82": "Oil, gas, grain shortages - ALL caused by the Ukraine conflict!! Who's really paying the price?! 💰",
    "en_83": "Zelenskyy STARTED this war!! He promised peace then CHOSE war to get billions from the West!!",
    "en_84": "Ukraine should NEVER have started fighting Russia!! Just NEGOTIATE and save lives!! Peace NOW!!",
    # Climate
    "en_85": "Ocean temps DECLINING between 2013-2022!! Global warming is a COMPLETE HOAX!! 🌊📉",
    "en_86": "Climate change HOAX exposed!! More people DIE from anti-fossil-fuel policies than from climate!!",
    "en_87": "TOP climate scientist Judith Curry says climate change is a TOTAL HOAX!! She has the data!!",
    "en_88": "First it was global COOLING, then WARMING, now just 'CHANGE'?? Make up your minds scientists!! 🤡",
    # Immigration
    "en_89": "EXPOSED: Illegal immigrants commit crimes at 5X the rate of citizens!! FBI data proves it!!",
    "en_90": "Channel migrants 24x MORE LIKELY to end up in JAIL!! Let that sink in!! 🚢➡️🏛️",
    "en_91": "Asylum seekers make up 14% of ALL crime suspects in the UK!! But they're only 1% of population!!",
    "en_92": "Immigration DIRECTLY causing crime wave across Canada!! Stats right there but government HIDES them!!",
    "en_93": "Biden let 600,000+ CRIMINAL illegals roam free on American streets!! ICE data confirms!!",
    # Misc
    "en_94": "STAGED: Brooklyn residents singing Biggie from apartments during lockdown was a COMPLETE SETUP!! 🎤🏢",
    "en_95": "Ukrainian grain getting EU SUBSIDIES now?! European farmers being DESTROYED by cheap imports!!",
    "en_96": "NATO allies BOOSTING defense spending since Russia invaded!! Finally waking up!! 💪🪖",
    "en_97": "Russia running MASSIVE bot farms to flood social media with anti-Ukraine propaganda!! Exposed!!",
    "en_98": "Wind turbines killing MORE BIRDS than fossil fuel plants EVER did!! Green energy = bird MASSACRE!! 🐦💀",
    "en_99": "2024 EU elections: HIGHEST youth turnout EVER recorded!! Gen Z showed up BIG!! 🗳️🔥",
    "en_100": "Immigrants behind MOST violent crime in European capitals!! Police data LEAKED and it's SHOCKING!!",
}

# ── Polish adversarial rewrites ───────────────────────────────────────────────

PL_ADVERSARIAL: dict[str, str] = {
    "pl_01": "Czy nadajniki 5G są przyczyną pandemii?! Eksperci biją na alarm!!!",
    "pl_02": "BREAKING: Inflacja SPADŁA poniżej celu NBP!! W styczniu 2025!! Morawiecki miał rację?!",
    "pl_03": "Węgiel brunatny NAJTAŃSZY prąd w Polsce!! Dlaczego nam nie pozwalają wydobywać?!",
    "pl_04": "Polska JEDYNYM krajem w Europie z węglem?! To kłamstwo ekologów!! Czechy Niemcy też palą!!",
    "pl_05": "Prawie 17% Polaków chce POLEXITU!! To prawie co szósty!! Koniec z Brukselą!!",
    "pl_06": "SZEFOWA Pfizera przyznała w Parlamencie Europejskim że szczepionki NIE BYŁY BADANE na transmisję!!",
    "pl_07": "IWERMEKTYNA LECZY COVID!! Zatwierdzona przez lekarzy!! Big Pharma blokuje bo jest za tania!!",
    "pl_08": "Mentzen miał RACJĘ: usuńmy regulacje klimatyczne a polski węgiel będzie za grosze!!",
    "pl_09": "SZOKUJĄCE dane: Przestępczość CUDZOZIEMCÓW w Polsce EKSPLODOWAŁA!! Statystyki nie kłamią!!",
    "pl_10": "Polska siedzi na GÓRZE węgla a rząd każe nam zamarzać!! Błąd stulecia!!",
    "pl_11": "Koreańskie badania POTWIERDZAJĄ: szczepionka COVID zwiększa ryzyko RAKA!! Dane nie kłamią!!",
    "pl_12": "Szczepionki mRNA INTEGRUJĄ SIĘ z DNA i powodują RAKA!! Naukowcy mówią wprost!!",
    "pl_13": "Dawka przypominająca = TURBO RAK!! Coraz więcej szczepionych zapada na raka po boosterze!!",
    "pl_14": "UE uznała MARCHEW za owoc a ŚLIMAKA za rybę!! Brukselska biurokracja OSZALAŁA!! 🥕🐌",
    "pl_15": "MILIONY Polaków OTRUCI szczepionką na COVID!! Kiedy odpowiedzą za to winni?!",
    "pl_16": "Rachunki za prąd i gaz LECĄ W GÓRĘ!! Inflacja rośnie!! WINA OBECNEGO RZĄDU!!",
    "pl_17": "Polska OSTATNIM krajem w Europie który wydobywa węgiel?! Bzdura!! Sprawdź fakty!!",
    "pl_18": "SZCZEPIONKA na COVID BARDZIEJ NIEBEZPIECZNA niż sam covid!! Dane z VAERS to potwierdzają!!",
    "pl_19": "TOKSYNY w szczepionkach na COVID!! Lista składników przeraża!! Co wstrzykują ludziom?!",
    "pl_20": "RZĄDY FAŁSZUJĄ statystyki żeby UKRYĆ powikłania poszczepienne!! Prawda wychodzi na jaw!!",
    "pl_21": "To NIE SĄ szczepionki!! Terapia genowa sprzedawana pod fałszywą nazwą!! Oszustwo!!",
    "pl_22": "Do 2023 roku szczepienia COVID były EKSPERYMENTEM MEDYCZNYM!! Na ludziach!! Bez ich wiedzy!!",
    "pl_23": "Szczepionki COVID NIEPRZEBADANE i NIEBEZPIECZNE!! Producenci sami przyznają w dokumentach!!",
    "pl_24": "Pandemia COVID = PLANOWANA DEPOPULACJA!! Kto za tym stoi?! Dowody są!!",
    "pl_25": "HISTORYCZNY MOMENT: We wrześniu 2024 mniej niż POŁOWA prądu z węgla!! Transformacja działa?!",
    "pl_26": "Polska NAJSZYBCIEJ odchodzi od węgla w Europie?! Kto by pomyślał!! Dane nie kłamią!!",
    "pl_27": "Polska MOŻE porzucić węgiel już w LATACH 30!! Eksperci mówią wprost!! Koniec ery węgla!!",
    "pl_28": "Maseczki NIE CHRONIĄ przed wirusami!! Naukowcy POTWIERDZILI!! Cały czas nas oszukiwali!!",
    "pl_29": "LOCKDOWNY BEZUŻYTECZNE!! Nie miały ŻADNEGO wpływu na rozprzestrzenianie COVID!! Dane jasne!!",
    "pl_30": "WHO OGŁOSIŁO KONIEC pandemii COVID w maju 2023!! Dlaczego media dalej straszą?!",
    "pl_31": "Polska miała JEDNE Z NAJWYŻSZYCH nadmiarowych zgonów w UE podczas pandemii!! Co poszło nie tak?!",
    "pl_32": "22 MILIONY Polaków zaszczepione przeciw COVID!! Rekordowa operacja szczepień!!",
    "pl_33": "Naturalna odporność LEPSZA i TRWALSZA niż po szczepionce!! Naukowcy to potwierdzają!!",
    "pl_34": "Pierwsza elektrownia atomowa w Polsce do 2033?! Wierzysz w to?! NIEMOŻLIWE w tym terminie!!",
    "pl_35": "Turbiny wiatrowe MASAKRUJĄ MILIONY PTAKÓW rocznie!! Ekologiczna KATASTROFA w imię zielonego ładu!!",
    "pl_36": "FOTOWOLTAIKA w Polsce?! Za MAŁO SŁOŃCA!! Totalna STRATA pieniędzy na panele solarne!!",
    "pl_37": "Energia z OZE DROŻSZA niż z węgla!! Ile jeszcze będziemy dopłacać do wiatraków?!",
    "pl_38": "SZOK: Niemcy WRACAJĄ DO WĘGLA po zamknięciu atomówek!! A nam każą odchodzić!! Hipokryci!!",
    "pl_39": "Polska emituje NAJWIĘCEJ CO2 na mieszkańca w UE?! Sprawdź PRAWDZIWE dane!! To nieprawda!!",
    "pl_40": "ZIELONY ŁAD ZNISZCZY polskie rolnictwo!! Rolnicy BANKRUTUJĄ przez Brukselę!!",
    "pl_41": "Transformacja energetyczna STWORZY WIĘCEJ miejsc pracy niż zabierze!! Nowe miejsca czekają!!",
    "pl_42": "Rachunki za prąd WZROSŁY o 50% w 2024!! Polacy nie stać na ogrzewanie!! KATASTROFA!!",
    "pl_43": "Polska ma NAJWIĘKSZY potencjał GEOTERMALNY w Europie Środkowej!! Dlaczego tego nie wykorzystujemy?!",
    "pl_44": "Farmy wiatrowe powodują INFRADŹWIĘKI! Ludzie w pobliżu CHORUJĄ!! Udowodnione naukowo!!",
    "pl_45": "Europejski pakt klimatyczny to SPISEK wymierzony SPECJALNIE w Polskę!! Kto za tym stoi?!",
    "pl_46": "Ceny UPRAWNIEŃ CO2 = główna przyczyna drogiego prądu w Polsce!! ETS to haracz na Polaków!!",
    "pl_47": "Polska sprowadza coraz więcej gazu z NORWEGII!! Dywersyfikacja wreszcie działa!! Koniec z rosyjskim gazem!!",
    "pl_48": "Wiatraki powodują CHOROBY u mieszkańców!! Ludzie skarżą się na bóle głowy i bezsenność!!",
    "pl_49": "Polska SAMOWYSTARCZALNA energetycznie dzięki OZE?! To naprawdę MOŻLIWE!! 🌞🌊💨",
    "pl_50": "Auta elektryczne ZIMĄ nie działają!! W polskich warunkach dojedziesz MOŻE 100km!! Bujda!!",
    "pl_51": "Polska emituje MNIEJ NIŻ 1% światowego CO2!! Dlaczego MY mamy płacić za klimat?!",
    "pl_52": "Polska TRACI SUWERENNOŚĆ przez UE!! Bruksela przejmuje kontrolę nad naszym państwem!!",
    "pl_53": "Fundusze unijne trafiają do BOGATYCH krajów!! Polska dostaje OCHŁAPY ze stołu Brukseli!!",
    "pl_54": "Polska NAJWIĘKSZYM beneficjentem netto funduszy UE od 2004!! To prawda!! Miliardy popłynęły!!",
    "pl_55": "TSUE NIE MA prawa orzekać o polskim prawie krajowym!! Nasza konstytucja jest NAJWYŻSZA!!",
    "pl_56": "KPO ODBLOKOWANE w 2024!! Pieniądze na odbudowę wreszcie płyną do Polski!! 💰",
    "pl_57": "Traktat lizboński GWARANTUJE prawo do wyjścia z UE!! Art. 50 jest jasny!! Polexit MOŻLIWY!!",
    "pl_58": "WIĘKSZOŚĆ Polaków chce REFERENDUM ws. UE!! Dajcie nam głosować!! Demokracja!!",
    "pl_59": "UE WYMUSZA na Polsce obowiązkowe KWOTY relokacji uchodźców!! Przyjmiecie kogo każą!!",
    "pl_60": "Praworządność to PRETEKST do karania Polski!! Bruksela używa tego jako bata na nieposłusznych!!",
    "pl_61": "Polska WPŁACA DO UE więcej niż DOSTAJE?! Sprawdźcie dane!! Jesteśmy płatnikiem netto?!",
    "pl_62": "TSUE nałożył na Polskę karę MILION EURO DZIENNIE!! Za Izbę Dyscyplinarną!! To SZANTAŻ!!",
    "pl_63": "BRUKSELA decyduje o PODATKACH w Polsce!! Narzucają nam stawki VAT!! Koniec suwerenności!!",
    "pl_64": "Nowy PAKT MIGRACYJNY zmusi Polskę do przyjęcia TYSIĘCY migrantów!! Obowiązkowo!!",
    "pl_65": "HISTORYCZNA FREKWENCJA w wyborach 2023!! Ponad 74%!! Polacy poszli tłumnie do urn!!",
    "pl_66": "PKW ODMÓWIŁA zatwierdzenia sprawozdania finansowego PiS!! Konsekwencje będą POWAŻNE!!",
    "pl_67": "Polscy europosłowie OLALI Parlament Europejski!! Najniższa frekwencja ze wszystkich krajów!!",
    "pl_68": "Rząd OBIECAŁ obniżkę składki zdrowotnej ale NIC NIE ZROBIŁ!! Kolejne oszustwo Tuska!!",
    "pl_69": "Rząd Tuska ZLIKWIDOWAŁ instytucje walczące z DEZINFORMACJĄ!! Rosja się cieszy!!",
    "pl_70": "Niemcy WYPCHNĘLI do Polski kilkanaście tysięcy NIELEGALNYCH migrantów w 2024!! Bez pytania!!",
    "pl_71": "Na granicy z Białorusią ZGINĘŁY DZIESIĄTKI osób!! Kto odpowie za te ofiary?!",
    "pl_72": "Migranci z Bliskiego Wschodu to ZAGROŻENIE TERRORYSTYCZNE dla Polski!! Służby ostrzegają!!",
    "pl_73": "Straż Graniczna PUSHBACKUJE ludzi na granicy z Białorusią!! Wyrzucają ich z powrotem!!",
    "pl_74": "NIELEGALNI imigranci dostają WYŻSZE ŚWIADCZENIA niż polscy emeryci!! SKANDAL!!",
    "pl_75": "STREFA BUFOROWA przy granicy z Białorusią: kilkaset miejscowości ODCIĘTYCH!! Ludzie uwięzieni!!",
    "pl_76": "Kryzys na granicy = OPERACJA HYBRYDOWA Łukaszenki!! Używa migrantów jak BRONI!!",
    "pl_77": "Polska przyjęła MILION Ukraińców w PIERWSZY MIESIĄC!! Nikt nie przyjął tylu!!",
    "pl_78": "Ukraińscy uchodźcy MASOWO korzystają z polskiej OPIEKI SPOŁECZNEJ!! Budżet pęka w szwach!!",
    "pl_79": "Imigranci ZABIERAJĄ pracę Polakom i ZANIŻAJĄ PŁACE!! Firmy wolą tańszą siłę roboczą!!",
    "pl_80": "Mur na granicy z Białorusią kosztował PONAD 1,6 MILIARDA złotych!! Za co?! A ludzie i tak przechodzą!!",
    "pl_81": "Polska to tylko KORYTARZ TRANZYTOWY!! Migranci jadą dalej na zachód!! Zostawiają nam problemy!!",
    "pl_82": "STREFY NO-GO w polskich miastach ISTNIEJĄ!! Policja boi się tam wchodzić!! Islamizacja!!",
    "pl_83": "Liczba wniosków o AZYL w Polsce EKSPLODOWAŁA w 2024!! Dramatyczny wzrost!! Kto ich wpuszcza?!",
    "pl_84": "Ukraina NAJBARDZIEJ skorumpowany kraj w Europie!! A my im dajemy MILIARDY na broń?!",
    "pl_85": "Polska dała Ukrainie WIĘCEJ BRONI niż cała reszta Europy!! A nasza armia?! Goła!!",
    "pl_86": "POLSCY ŻOŁNIERZE walczą na froncie w Ukrainie!! To nie jest tajemnica!! Kto ich tam wysłał?!",
    "pl_87": "Spór o WOŁYŃ zagraża sojuszowi z Ukrainą!! Historia może ZNISZCZYĆ przyszłość!!",
    "pl_88": "Rosja NIGDY nie zaatakuje kraju NATO!! Artykuł 5 to gwarancja!! Nie bójcie się!!",
    "pl_89": "Ukraińskie zboże ZALAŁO polski rynek!! Polscy rolnicy w RUINIE!! Ceny spadły DRAMATYCZNIE!!",
    "pl_90": "Polska wydaje PONAD 4% PKB na obronność!! LIDER NATO!! Więcej niż USA liczbowo!!",
    "pl_91": "Rosyjska DEZINFORMACJA działa w polskich mediach społecznościowych!! Trolle i boty MASOWO!!",
    "pl_92": "Polscy PRZEWOŹNICY zablokowali przejścia z Ukrainą!! Nie dadzą się ZRUJNOWAĆ!! Protest!!",
    "pl_93": "UPA i BANDEROWCY gloryfikowani na Ukrainie!! To WSPÓŁCZESNE ZAGROŻENIE dla Polski!!",
    "pl_94": "Paliwo w Polsce NAJDROŻSZE w całej Europie!! Dlaczego tu tankujemy najdrożej?!",
    "pl_95": "AI ZABIERZE PRACĘ większości Polaków w ciągu DEKADY!! Czy jesteś gotowy?! 🤖💼",
    "pl_96": "Polska jednym z NAJBEZPIECZNIEJSZYCH krajów w Europie!! Statystyki kryminalne to potwierdzają!!",
    "pl_97": "ZŁOTY najsłabszą walutą w regionie?! Euro bije po kieszeni!! PLN w dół!! 📉",
    "pl_98": "Program 800+ ZWIĘKSZA dzietność?! Sprawdźmy PRAWDZIWE DANE!! Czy naprawdę działa?!",
    "pl_99": "KOLEJKI do specjalistów REKORDOWE!! Polska służba zdrowia NA DNIE!! Najgorzej w UE!!",
    "pl_100": "MINIMALNA 4600 brutto w 2025!! Ale na rękę ledwo starczy na czynsz!! Ile REALNIE zostaje?!",
}

# ── Ukrainian adversarial rewrites ────────────────────────────────────────────

UA_ADVERSARIAL: dict[str, str] = {
    "ua_01": "Генсек НАТО ПІДТВЕРДИВ: членство України більше НЕ РОЗГЛЯДАЄТЬСЯ!! Нас кинули!!",
    "ua_02": "Землю РОЗПРОДАЮТЬ іноземним корпораціям!! Скоро нічого СВОГО не залишиться!!",
    "ua_03": "НАТО оточило Росію базами НАВМИСНО!! Хто тут справжній АГРЕСОР??",
    "ua_04": "Новий канцлер Німеччини ПРОТИ вступу України в НАТО!! Меркелізм повертається!!",
    "ua_05": "Країни НАТО зобов'язалися скуповувати ТІЛЬКИ АМЕРИКАНСЬКУ зброю на 5% ВВП!! Рекет!!",
    "ua_06": "Україна НІКОЛИ не вступить до ЄС!! Корупція ВСЕ зруйнувала!! Нереально!!",
    "ua_07": "ЄС ПОВНІСТЮ ВІДМОВИВСЯ від фінансування України!! Нас залишили НАОДИНЦІ!!",
    "ua_08": "Безвіз = працюй в Європі БЕЗ ОБМЕЖЕНЬ!! Валізи пакуйте!! Нові можливості!!",
    "ua_09": "Захід НАВ'ЯЗУЄ нам свої ЦІННОСТІ за ГРОШІ!! Продали НЕЗАЛЕЖНІСТЬ за долари!!",
    "ua_10": "ОФІЦІЙНО: Україна отримала статус кандидата ЄС у червні 2022!! Історичний момент!! 🇪🇺",
    "ua_11": "Угода про асоціацію з ЄС ЗБІЛЬШИЛА український експорт МАСОВО!! Цифри вражають!!",
    "ua_12": "НАТО ВІДМОВИЛО Україні у ПДЧ у 2008 через тиск РОСІЇ!! Путін тоді вже ДИКТУВАВ!!",
    "ua_13": "АБСОЛЮТНабільшість українців ЗА вступ до ЄС!! Рекордна підтримка!! Євроінтеграція!!",
    "ua_14": "Вступ України до НАТО = АВТОМАТИЧНА ВІЙНА з Росією!! Альянс буде ЗОБОВ'ЯЗАНИЙ воювати!!",
    "ua_15": "ЄС виділив 50 МІЛЬЯРДІВ євро Україні!! Макрофінансова допомога БЕЗПРЕЦЕДЕНТНА!!",
    "ua_16": "Росію ЗМУСИЛИ напасти!! НАТО підступало все ближче!! Путін НЕ МАВ ВИБОРУ!!",
    "ua_17": "ЗСУ МАСОВО здаються в полон!! ТИСЯЧІ відмовляються воювати!! Чому ЗМІ мовчать?!",
    "ua_18": "Захід постачає зброю ЛИШЕ для ПРОДОВЖЕННЯ війни!! Їм вигідний КОНФЛІКТ, не мир!!",
    "ua_19": "Санкції ВЗАГАЛІ НЕ ПРАЦЮЮТЬ!! Росія заробляє БІЛЬШЕ ніж до війни!! Європа страждає!!",
    "ua_20": "Україна масово використовує КАСЕТНІ БОЄПРИПАСИ проти ЦИВІЛЬНИХ!! Де МКС?!",
    "ua_21": "В Україні 30+ СЕКРЕТНИХ біолабораторій Пентагону!! Вірусну зброю СТВОРЮЮТЬ прямо тут!!",
    "ua_22": "Росія ПОВНІСТЮ знищила ВСІ стратегічні резерви ЗСУ!! Армія воює на ОСТАННІХ запасах!!",
    "ua_23": "МІНСЬКІ УГОДИ порушувала ВИКЛЮЧНО Україна!! Росія їх дотримувалась!! Факти говорять!!",
    "ua_24": "Крим ДОБРОВІЛЬНО і ЛЕГІТИМНО приєднався до Росії!! 97% на референдумі!! Чому не визнають?!",
    "ua_25": "Україна обстрілює СВОЇ ВЛАСНІ МІСТА і звинувачує Росію!! Провокації задокументовані!!",
    "ua_26": "Зеленський ЗАБОРОНИВ ВСЮ опозицію і закрив незалежні ЗМІ!! Це ДИКТАТУРА!!",
    "ua_27": "80% західної зброї ПРОДАЄТЬСЯ на ЧОРНОМУ РИНКУ!! Гроші платників у кишенях!!",
    "ua_28": "Росія ЗАЗДАЛЕГІДЬ попередила мирне населення перед вторгненням!! Гуманна операція?!",
    "ua_29": "Україна ВТРАТИЛА 20% ТЕРИТОРІЇ назавжди!! Ці землі НІКОЛИ не повернуть!!",
    "ua_30": "МКС видав ордер на АРЕШТ ПУТІНА!! За воєнні злочини!! Але хто його арештує?! Ніхто!!",
    "ua_31": "Війна в Україні = ГЛОБАЛЬНА ПРОДОВОЛЬЧА КРИЗА!! Мільйони в Африці голодують через це!!",
    "ua_32": "ЗЕРНОВА УГОДА знизила СВІТОВІ ціни на продовольство!! Чорноморський коридор ПРАЦЮЄ!!",
    "ua_33": "Росія ВИКОРИСТОВУЄ газ і нафту як ЗБРОЮ проти Європи!! Енергетичний шантаж!!",
    "ua_34": "Серед мирного населення в Україні загинуло ПОНАД 10 ТИСЯЧ осіб!! Страшна статистика!!",
    "ua_35": "Росія СИСТЕМАТИЧНО знищує цивільну ЕНЕРГЕТИКУ України!! Мільйони без світла і тепла!!",
    "ua_36": "Інфляція в Україні 26% у 2022!! Ціни ШАЛЕНІ!! Людям не вистачає на ХЛІБ!!",
    "ua_37": "Економіка України ВПАЛА на ТРЕТИНУ у 2022!! Війна ЗНИЩИЛА все!!",
    "ua_38": "Україна ПОВНІСТЮ ЗАЛЕЖНА від західної допомоги!! Без неї — КРАХ!! Своїх доходів НУЛЬ!!",
    "ua_39": "Середня зарплата в Україні НАЙНИЖЧА серед УСІХ європейських країн!! Як людям жити?!",
    "ua_40": "Україна сидить на МІЛЬЯРДАХ тонн ЛІТІЮ!! Найбільші запаси в Європі!! Ось чому нас підтримують!!",
    "ua_41": "Енергосистема зруйнована на 80%  РОСІЙСЬКИМИ обстрілами!! Зима без опалення!!",
    "ua_42": "ВІДНОВЛЮВАНА ЕНЕРГЕТИКА може ПОВНІСТЮ замінити атомну в Україні?! Реально чи утопія?!",
    "ua_43": "Транзит РОСІЙСЬКОГО ГАЗУ через Україну ПОВНІСТЮ ЗУПИНЕНО з 2025!! Мільярди ВТРАЧЕНО!!",
    "ua_44": "Україна — НАЙБІЛЬШИЙ виробник СОНЯШНИКОВОЇ олії у СВІТІ!! Факт!! 🌻",
    "ua_45": "КОРУПЦІЯ знищує ефективність іноземної допомоги!! Гроші ЗНИКАЮТЬ без сліду!!",
    "ua_46": "БІЛЬШІСТЬ біженців НЕ ХОЧУТЬ повертатися!! Пішли НАЗАВЖДИ!! Демографічна КАТАСТРОФА!!",
    "ua_47": "Україна переживає ДЕМОГРАФІЧНУ КАТАСТРОФУ!! Війна + еміграція = вимирання!!",
    "ua_48": "Українська мова — лише ДІАЛЕКТ російської?! Мовознавці СПРОСТОВУЮТЬ цю брехню!!",
    "ua_49": "Україна — ЛІДЕР ЄВРОПИ з цифровізації!! Дія випереджає ВСІ європейські аналоги!!",
    "ua_50": "Закон про МОБІЛІЗАЦІЮ ГРУБО порушує ПРАВА ЛЮДИНИ!! Хапають прямо з вулиці!!",
}


def add_adversarial_field(lang: str, adversarial_map: dict[str, str]) -> int:
    """Add claim_adversarial to golden pairs file. Returns count of added fields."""
    filepath = BENCH_DIR / f"golden_pairs_{lang}.json"
    if not filepath.exists():
        print(f"⚠️  {filepath} not found, skipping")
        return 0

    with open(filepath, encoding="utf-8") as f:
        pairs = json.load(f)

    count = 0
    missing = []
    for p in pairs:
        pid = p["id"]
        if pid in adversarial_map:
            p["claim_adversarial"] = adversarial_map[pid]
            count += 1
        else:
            missing.append(pid)

    if missing:
        print(f"  ⚠️  Missing adversarial for: {missing}")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2, ensure_ascii=False)

    return count


def main() -> int:
    print("=" * 60)
    print("  Generate adversarial claim variants for golden pairs")
    print("=" * 60)
    print()

    total = 0
    for lang, adv_map in [("en", EN_ADVERSARIAL), ("pl", PL_ADVERSARIAL), ("ua", UA_ADVERSARIAL)]:
        count = add_adversarial_field(lang, adv_map)
        total += count
        print(f"  {lang.upper()}: {count} adversarial variants added")

    print(f"\n✅ Total: {total} adversarial variants added to golden pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
