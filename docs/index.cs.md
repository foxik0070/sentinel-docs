# Sentinel Commander — Dokumentace (v2026.11.014)

```
                   ##
               ++########++
              ++++###+++++++
             +++++++++++-++-.
            ++++++#++++++-+-
             ++######+++++--
             +++  ####+  -+-
              ++++######++-
              ++++#######+-#
               ++++######++-+.-+
              ++++++###+++##+---++#
            +++++++++###+#######++++++++
         -+++++++++++###+#####+#+++++----..-
      ++-++++++++#######+######++++++++--..  .
     ---++++##+++#####++####++++#++++---.....
    --+++++############++###++++#+++---........
   --++++++##++##########++++++++++----.........
   --+++++#####++#####+#+++++++++++++-.-.........
   --++++#####+########++++++-+++++-++--------.-..
   ++++##########+####++++++-+++++++-+++---------.

        S E N T I N E L   C O M M A N D E R
                    v2026.11.014
```

**Hybridní AI log monitor a analyzátor pro enterprise Linux infrastrukturu**

---

## Rychlá navigace

- **[Průvodce nasazením](./DEPLOYMENT.md)** — produkční nasazení celého systému
- **[API Reference](./API.md)** — API pro pluginy a integrace
- **[Řešení problémů](./TROUBLESHOOTING.md)** — časté problémy a jejich řešení
- **[Nastavení hostů](./host-setup.md)** — příprava monitorovaných hostů pro AI diagnostiku

---

## Co je Sentinel?

Sentinel Commander je pokročilý hybridní monitorovací systém s plnou AI vrstvou určený pro enterprise Linux infrastrukturu. Kombinuje **Pull** přístup (inotify tailing logů) s **Push** přístupem (vzdálení Python agenti POSTují telemetrii). Klíčové integrace: Hailo AI HAT 2+ NPU (hailo-ollama), lokální/externí Ollama LLM, ChromaDB (RAG).

Ve verzi v2026.11.014 systém obsahuje **1 294 automatizovaných testů** a **80/100 AI roadmap položek** pokrytých 24 novými AI moduly pro diagnostiku, verifikaci, plánování remediace, korelaci, baselining, předpovědi a správu znalostí.

---

## Co je nového ve v2026.11.012 – v2026.11.014 (2026-11-15)

| Funkce | Detail |
|---|---|
| **Ignorování issue konečně drží** | Dosud znamenalo „schovat na jednom místě": klíč šel do JSON souboru, který znal jen `chat_service`, a ten se uplatnil **až při výpisu**. Detektor tentýž klíč při dalším běhu založil znovu, notifikace odešla a v počtech byl vidět. Mechanismy na to byly **tři** a žádný u zdroje. Ignorace je nově v databázi a kontroluje ji `save_problem()` — jediné místo, kudy issue vzniká — takže ignorovaný klíč se neuloží, neodešle notifikaci ani se nezapočítá. Co bylo ignorované dřív, se jednorázově převezme, takže se po upgradu nezačne hlásit |
| **Akce u issue jsou seskupené** | U karty bylo **jedenáct ikon** vedle sebe bez uspořádání, takže nešlo poznat, co issue změní a co jen ukáže. Dvě nejčastější zůstaly inline, zbytek je v nabídce dělené podle účinku: *zjistit víc* / *upravit* / *přestat hlásit* / *ostatní*. Ignorování a mazání se nově ptají a říkají, co se stane |
| **Schválená akce šla na název clusteru, ne na stroj** | Záchyt s `cluster = OTHER` (výchozí pro hosty bez mapování) a `node = rpi` předával do SSH cluster, takže se spustilo `ssh other`. Na instanci bez `infrastructure_mapping` to potkalo **každou** schválenou akci. Cíl se nově hledá: mapování → `localhost` → `node` akce → cluster; když nic nedá stroj, akce se odmítne srozumitelnou hláškou |
| **MQTT z balíčku nejelo** | `paho-mqtt` chyběl v `requirements.txt` — instaloval ho jen `install.sh`, takže u ruční instalace fungovalo a u balíčku (vlastní venv) ne. V UI se navíc nedalo odlišit „chybí knihovna" od „broker je nedostupný"; obojí vypadalo jako *nepřipojeno* |
| **Chybějící minifikátor nechal prázdné UI** | Šablona načítá `script-*.min.js`. Když se minifikace přeskočí a soubory neexistují, Flask vrátí HTML chybovou stránku, prohlížeč ji odmítne kvůli MIME typu a **nenačte se žádný skript**. `rjsmin`/`rcssmin` jsou nově závislosti a když minifikace přesto selže, zkopírují se nezmenšené soubory pod očekávanými jmény — pomalejší je lepší než rozbité |
| **Podpětí jen ze skutečných síťových senzorů** | `ha_detector` bral každou entitu se slovem `voltage` za síťové napětí, takže napěťová větev desky (0–12 V) na vypnutém stroji hlásila „podpětí 0.0 V". Nově potřebuje výslovný seznam, nebo **historii**: entita musí někdy ukázat aspoň 100 V |
| **Testy: 1 284 → 1 294** | Plus 15 v `sentinel-plugins` a 158 v `sentinel-alert` |

!!! warning "Změna chování"
    `cluster = UNKNOWN` bez node se nově odmítne. Dřív se příkaz spustil **na serveru samotném** — spouštět cizí příkaz lokálně jen proto, že neznáme cíl, je horší než odmítnutí.

---

## Co bylo nového ve v2026.11.009 – v2026.11.011 (2026-11-15)

| Funkce | Detail |
|---|---|
| **Detektory jsou samostatný balíček** | Sentinel si nově nechává jen základ: `base.py` (odkud pochází `api.BaseDetector`) a dva detektory, bez kterých nemá smysl běžet — `system_detector` a `services_detector`. Zbylých deset se přestěhovalo do repozitáře `sentinel-plugins` a instaluje se vlastním `.deb`/`.rpm`. Oprava detektoru tak neznamená vydat celý Sentinel a vydání Sentinelu nepřepíše detektory, které si někdo doplnil. Viz [Sentinel Plugins](./sentinel-plugins.md) |
| **`plugin_dir` smí být seznam** | Dřív to byl jediný adresář, což je přesně ten důvod, proč se detektory pro dané pracoviště musely kopírovat **do** adresáře Sentinelu — uspořádání, které stálo za dvěma provozními incidenty. Nově se hledá v uvedeném pořadí; jediný řetězec se chová jako dřív |
| **Hailo: JSON úlohy vracejí JSON** | `hailo-ollama` ignoruje `format` i `response_format`, takže remediace a klasifikace závažnosti chodily zabalené v markdownu a `process_ai_proposal()` je neuparsoval. Jediná páka, která zabírá, je system zpráva podle `context.source`; musí být jednořádková, protože LF v `content` rozbíjí vnitřní rendering hailo-ollamy. Měřeno s produkčním promptem: tři případy ze tří bez ní nevrátily JSON, s ní všechny a rychleji |
| **Řídicí tokeny ven** | Malé modely občas propustí vlastní řídicí značku do odpovědi (`<turn\|>`, `<\|im_end\|>`). Odstraňují se teď ze všech odpovědí, ne jen z Hailo cesty. Filtr je úzký, takže běžného `<br>` se nedotkne |
| **Balíčky pro šest komponent** | `.deb` a `.rpm` pro Sentinel, agenta, alert, overhealth, konzoli a pluginy, vydávané jako release a do Debian/RPM registry. Viz [Deployment](./DEPLOYMENT.md) |
| **Překlep v configu už neshodí službu** | `plugin_dir` zapsaný jako seznam vyhodil `TypeError` ve `_validate_config()`. Ta se volá při `import sentinel.config`, takže výjimka zabila celou aplikaci — a se `Restart=always` je z toho smyčka restartů bez webu a bez příjmu od agentů. Validace i kontrola schématu jsou nově ošetřené: když selžou, zaloguje se to a konfigurace se použije dál. Diagnostika nemá právo zabít to, co diagnostikuje. Cesty se navíc kontrolují typově: `plugin_dir` bere řetězec nebo seznam řetězců, `log_dir` a `data_dir` jen řetězec, cokoliv jiného je `error` a jede se s výchozí hodnotou |
| **`--check-config`** | `python3 -m sentinel --check-config` vypíše nálezy validace, `plugin_dir` a počet detektorů; vrací nenulový kód při chybě nebo chybějícím souboru. Ověřování importem `sentinel.config` je přesně to, co nestačí — validace je záměrně nekritická, takže import projde i u rozbitého configu |
| **Testy: 1 260 → 1 275** | Plus 10 v `sentinel-plugins`, který má nově vlastní sadu, a 102 v `sentinel-agent` |

!!! warning "Pořadí při povýšení"
    `sentinel-plugins` nainstalovat **dřív**, než se povýší na v2026.11.010. Detektor, který `config.yaml` vyžaduje a jeho soubor není nikde v `plugin_dir`, založí `SENTINEL|detectors_missing` (critical).

---

## Co bylo nového ve v2026.11.005 – v2026.11.008 (2026-11-13)

| Vlastnost | Detail |
|---|---|
| **Scope `read:root` — přehled bez práva zápisu** | Role se odvozuje ze **scope klíče**, ne od jeho vlastníka. Na `admin`/`superadmin` ale mapovaly jedině scopy, které umí i zapisovat, takže nástroj, který z principu jen čte, musel volit mezi úplným přehledem a menším rozsahem škody při úniku klíče. Nový `read:root` zůstává v roli `viewer` a viditelnost kanálu ROOT řeší samostatným oprávněním. Vydat ho smí i `admin` — ROOT už v UI vidí, takže čtecí klíč se stejným rozsahem není eskalace |
| **Verze serveru v `status_check`** | `GET /api/status_check` vrací `version`. Klienti do té doby odhadovali schopnosti serveru podle toho, jestli v datech našli konkrétní pole — fungovalo to, ale byla to detekce po hmatu |
| **Surová pole v `/api/v1/issues`** | `first_seen`, `occurrence_count`, `plugin_name`, `db_severity`, `acknowledged_by` a `snoozed_until`. Bez nich si klient neuměl spočítat stáří problému ani ho seřadit podle skutečné závažnosti a musel si je dobírat druhým voláním. Pole `severity` zůstává odvozené z kanálu kvůli mobilní aplikaci, pravá hodnota z DB je vedle jako `db_severity` |
| **`?include_ignored=1`** | Vrátí i ignorované issues, označené příznakem `ignored`. Záměrně opt-in: bez parametru se chování nemění, aby se stávajícím klientům neobjevily položky, které si jejich uživatel schoval |
| **Dvě tlačítka u karet issue nedělala nic** | Ikona „Přidat komentář (inline)" a tečka barevného štítku vykreslovaly `onclick` na funkce, které ve frontendu vůbec neexistovaly. Klik skončil chybou v konzoli — bez hlášky a bez požadavku na server. Backend byl přitom u obou hotový. Nový test teď prochází všechny `on*="fn(…)"` atributy a ověřuje, že ke každému existuje funkce |
| **Komentáře přímo v kartě** | Daly se přečíst jen po rozkliknutí odznaku s číslem, takže kdo seznam přelétl, nevěděl, že k problému někdo něco napsal. Nově se kreslí v kartě vlastní barvou; poslední tři, zbytek za odkazem do modalu. Načítají se jedním dotazem pro celý seznam |
| **Rozepsaný komentář přežije obnovu** | Modal se překresluje každé 3 sekundy a řádek pro komentář se vykresluje zavřený, takže obnova ho zavřela i s textem. Víc než tři vteřiny psaní se nedalo stihnout. Obnova teď pamatuje otevřené řádky, jejich obsah, pozici kurzoru i fokus |
| **Testy: 1 229 → 1 260** | Nové pokrývají scope `read:root` (hlavně to, že neumí zapisovat), surová pole a `include_ignored`, komentáře v kartě a existenci funkcí za `onclick` |

---

## Co bylo nového ve v2026.10.001 – v2026.11.004 (2026-11-12)

| Vlastnost | Detail |
|---|---|
| **Prompt injection: logy jako data, ne jako pokyny** | `ai_guard.wrap_untrusted()` existoval, ale používala ho jen diagnostika, knowledge a analýza incidentů. Chat ho obcházel — ocas logů, řádky alertů, obsah otevřeného souboru i hláška pro autofix šly do promptu holé, ve stejné zprávě jako otázka uživatele, takže řádek „ignore previous instructions" z logu model nijak neodlišil od pokynu. Všechny cesty jsou teď ohraničené, system prompty nesou `UNTRUSTED_RULE` a odpověď ukládaná do historie prochází `sanitize()` |
| **Ohraničení platí pro všechny prompty** | Po opravě chatu zbylo asi 15 míst, kde `last_line` nebo obsah logu šel do modelu holý — eskalace, remediace, řetěz příčin, návrh patternů, denní digest, re-analýza, root cause, hromadná analýza, clustery, runbook, postmortem. Všechna procházejí `ai_guard.untrusted()`. Neobalené zůstává jen to, co z logů nepochází: telemetrie, trend, komentáře přihlášených uživatelů a statické evaly |
| **Varování u rizikových příkazů v odpovědi** | `ai_guard.risky_commands()` prožene code bloky i inline příkazy z odpovědi přes `safety.classify()`; u rizikových se pod odpovědí ukáže varování. Model sám nic nespustí, ale uživatel příkaz zkopíruje — autofix risk skóre měl, volný chat ne |
| **Přehled „AI uživatelé"** | Nový pohled: kdo na strojích pouští AI, jakým nástrojem, s jakým modelem a jak dlouho. Pokrývá interaktivní CLI agenty, lokální LLM runtimy, MCP servery a procesy držící spojení na API poskytovatele, které nejde poznat podle jména. Data chodí od agenta mimo tabulku issues, takže nic nealertuje a nic nevisí |
| **Identita sezení** | Sezení se pozná podle `(host, pid, started_at)`. Samotný pid se po restartu stroje recykluje, čas startu procesu se mezi polly nemění — opakovaný poll proto řádek jen potvrdí. `started_at` se ukládá jako prázdný řetězec, ne `NULL`: dva `NULL` se v `UNIQUE` indexu nerovnají a sezení bez známého času startu by se dedupovat nedalo |
| **Skládací přehled po technologiích** | Modal se skládá po úrovních **technologie → agent → uživatel → sezení**, každá s počtem „běží / celkem". Při stovkách souběžných procesů je plochý seznam nečitelný. Co uživatel zavře, zůstane zavřené i po obnovení |
| **Počet v hlavičce nesedel na obsah** | Odznak počítal všechna běžící sezení, ale endpoint je protahoval stropem na stroj, který nerozlišoval stav — stroj se stovkami procesů jich vrátil jen tolik, kolik je strop. Strop nyní platí jen na ukončená sezení, běžící projdou vždy |
| **Sezení po spadlém agentovi** | Sezení se uzavírá tím, že chybí v dalším snímku svého stroje. Když agent přestane hlásit úplně, žádný snímek nepřijde a sezení zůstanou „běžící" navždy. Nově se uzavře, co nikdo nepotvrdil déle než `ai_sessions_stale_minutes` (30) |
| **Self-service API klíče** | Uživatel si spravuje vlastní dlouhodobé klíče pro skripty (`X-API-Key`); tajná část se ukáže jen jednou, při vytvoření. Klíč v URL je omezený — query stringy končí v logách proxy i prohlížeče |
| **Integrace s Request Trackerem** | Výpis tiketů s filtrem podle fronty a textu, komentář se záznamem autora, převzetí tiketu a změna stavu |
| **Méně šumu z detektorů** | Vyřešené záchyty disku mizí, loopback porty se neberou jako nové, teplota kontejnerů se neměří proti hostiteli a známé hlášky už nezakládají issues |
| **Remediation plan i pro viewer** | Role `viewer` si směla nechat vygenerovat plán, ale ne ho zobrazit. K tomu validace parametrů u `logs/view` a oprava výchozí role při přihlášení přes LDAP |
| **Testy: 1 188 → 1 229** | Nové pokrývají úložiště AI sezení (identita, uzavírání, retence), ohraničení nedůvěryhodných dat a detektory s méně šumem |

---

## Co bylo nového ve v2026.09.001 – v2026.09.016 (2026-09-08)

| Vlastnost | Detail |
|---|---|
| **Zamrzání procesu při `close()` DB spojení (kritické)** | Instance s velkou databází padala několikrát denně a mezitím bylo UI nedostupné. `sqlite3.Connection.close()` **neuvolňuje GIL** a Sentinel nedržel žádné trvalé DB spojení — každé `close()` bylo *poslední* a SQLite pod ním provedl plný WAL checkpoint, po jehož dobu byl zmrazený celý proces. Oprava: `state_base._ensure_keeper()` otevře při startu jedno spojení a drží ho. Naměřeno na 111MB databázi: `close()` z 0,233 s na 0,000 s |
| **Jedno zamrznutí, tři projevy** | Tentýž GIL vysvětlil všechno: web vlákno se nedostalo k `accept()` (accept fronta rostla ke 128, pak `Connection refused`), watchdog vlákno neodeslalo ping (SIGABRT po 300 s) a signal handler nedoběhl (SIGTERM ignorován 91 s → SIGKILL) |
| **File Integrity Monitoring — doimplementován** | FIM měl config, dokumentaci i testy, ale **žádnou implementaci**; volal ho jen mrtvý `scheduler.py` smazaný ve v2026.08.003. `watcher.fim_check()` nyní počítá SHA-256 sledovaných souborů proti baseline v `kv_settings['fim_state']`, běží každou minutu z hlavní smyčky a zakládá issue `FIM_CHANGE\|<cesta>` v kanálu `security` se severity `high` |
| **Root audit přestal vkládat znovu** | Agent cesta při **každém** hlášení zavřela a znovu vložila všechny aktivní relace — jeden stroj vyrobil 126 řádků za 36 minut a tabulka narostla na 105 000 řádků. Relace se nyní sesouhlasí podle `(server, tty, čas přihlášení)`: trvající se potvrdí, nová vloží, nehlášená uzavře. Přírůstek klesl na nulu |
| **Délka relace konečně měří délku relace** | `connected_at` se resetoval při každém pollu, takže „délka" ukazovala dobu od posledního hlášení. Nyní drží **skutečný čas přihlášení** vyparsovaný z hlášení agenta |
| **Zapomenuté root relace expirují** | Relace, které detektor přestal hlásit, zůstávaly `is_active=1` napořád — denní pruning maže jen `is_active=0`, takže je přeskočil (záznamy 67 dní staré se pořád tvářily jako aktivní). Nový `root_audit.last_seen` a minutový sweep řízený `root_audit_stale_minutes` (výchozí 30) |
| **Rozlišení detektor vs. agent** | Obě cesty píšou do `root_audit`, ale do `server` ukládají něco jiného: detektor název clusteru, agent hostname. Nový sloupec `root_audit.origin` je odliší; u detektorových záznamů **je** cluster přímo hodnota `server`, což zároveň opravilo `CS` padající do `INFRA` (pravidlo `.cs.` na holé `CS` nesedělo) |
| **Historie seskupená a limitovaná po clusterech** | Modal historie relací sdružuje záznamy do sbalitelných sekcí **cluster → server**. Globální `LIMIT 100` dával celé okno jedinému rušnému clusteru; nově je to posledních `root_audit_history_per_cluster` (výchozí 30) **na cluster**, aktivní relace se ukazují vždy |
| **„Chyba komunikace" pod hotovou odpovědí** | Odpověď se vykreslila celá a hláška naskočila **pod ní**; nginx logoval `upstream prematurely closed connection` na `/api/chat/stream`. SSE generátor se vyhodnocuje **až po návratu view**, kdy Flask request kontext neexistuje — hned za událostí `done` ale volal `log_event(..., user=g.username)`, což vyhodí `RuntimeError`, generátor umře a spojení se utne uprostřed streamu. Jméno se nyní zachytí před definicí generátoru; stejná chyba byla ve streamu výpisu SSH příkazu v `actions.py`. Test prochází těla obou generátorů a hlídá, že na `g` nesahají |
| **Chat odpovídal z KB místo z issues** | Streamovaná větev chatu — ta, kterou používá webové UI — skládala kontext jen z historie, knowledge base a otázky: **aktivní issues v něm nebyly vůbec**. Na dotaz o aktuálních problémech model odpověděl z jediného, co měl — z KB dokumentů o účtech a kvótách. Starší neproudová větev přehled alertů posílala, takže UI mělo *méně* kontextu než cesta, kterou nahradilo. `ChatService.build_alerts_context()` je nyní sdílená pro obě |
| **Fronta požadavků ukazovala jinou frontu** | Modal vypisoval paměťový čítač jako „AI fronta", ale seznam bral z DB tabulky `task_queue` — dvě nesouvisející věci, takže hlásil „AI fronta: 1" nad „Fronta je prázdná", i když požadavek skutečně běžel. Nyní vypisuje reálně běžící AI požadavky, se stavem `waiting` (čeká na semafor) odlišeným od `processing` |
| **Únik čítače AI fronty** | `chat_queue_depth` se zvyšoval před `llm_semaphore.acquire()` a snižoval až za ním — jakákoli výjimka mezi tím nechala čítač napořád nahoře. Tentýž `finally` uvolňoval semafor, který se možná nezamkl, čímž tiše rostl limit souběžnosti |
| **`ollama_extra_body`** | Nová volba, která přimíchá extra pole do těla OpenAI `/v1` požadavku. Potřebná pro reasoning modely: `qwen3-32b` bez `chat_template_kwargs.enable_thinking=false` posílá `<think>` bloky **uvnitř `content`** (ne v `reasoning_content`), takže by skončily v chatu, v denním digestu i v auto-klasifikaci severity |
| **Návrh autofixu jako syrový text** | Modely píšou do JSON stringů shellové regexy (`"grep -i 'a\|b'"`); `\|` není platná JSON escape sekvence, `json.loads` selhal a návrh se ukázal doslova s příkazem `N/A`. `extract_json()` to nyní zkusí znovu s osamocenými lomítky zdvojenými, platné escapy zůstávají |
| **Vymyšlené stroje bez uvozujícího slova** | `ai_verify` označil halucinovaný stroj jen tam, kde ho model uvedl („na stroji web-server-03"). Holé „zkontroluj db-master-01" prošlo, protože každý token s pomlčkou a bez tečky se zahazoval jako příkaz. Takový token nyní projde, má-li **číselný segment**; `read-only`, `dry-run` a `self-signed` zůstávají odfiltrované. Hostname regex pracuje unicodově |
| **Testy: 1 087 → 1 165** | Včetně 11 dlouhodobě padajících, které nikdy nebyly zelené: 9 FIM testů mířilo na funkci, která nikdy neexistovala, 2 testy `ai_verify` pokrývaly výše popsanou mezeru v detekci |

---

## Co je nového ve v2026.08.006 (2026-08-19)

| Funkce | Detail |
|---|---|
| **Oprava watchdog ABRT pádu (kritické)** | Sentinel padal každých 5–38 min s `Failed with result 'watchdog'`. Příčina: neblokující socket pro systemd notify — při přetížení WebSocket vlákny kernel vracel `EAGAIN`, pings se ztrácely, systemd po 120 s poslal SIGABRT. Oprava: `sock.settimeout(1.0)` — send čeká max 1 s, pak obnoví socket |
| **Konfigurovatelná cluster detekce** | `host_cluster_rules` v config.yaml — seznam pravidel `{pattern, cluster}` pro mapování hostname na clustery. Priorita: explicitní pole `cluster` → prefix `[CLUSTERNAME]` v `last_line` → konfigurační pravidla → `default_cluster`. Žádné hardkódované názvy clusterů |
| **`api.get_cluster_from_host()`** | Sdílená funkce v `sentinel/api.py` — pluginy ji volají místo svých hardkódovaných `_cluster_from_host()` metod. `detector_icinga` a `detector_who` migrovány |
| **`ignored_host_services`** | Nový parametr v konfiguraci `detector_icinga` — potlačuje specifické služby na specifických hostech (`service_pattern@host_pattern`). Eliminuje false positives pro služby, které na daném typu nodu neběží |
| **Stale ROOT relace po restartu** | `detector_who`: po restartu byl `_scan_prev` prázdný → stale relace z DB se nikdy neuzavřely. Opraveno seedováním z `api.get_active_keys()` na začátku prvního scanu |
| **Slurmctld debounce** | `detector_cluster`: `Slurmctld ping: DOWN` se hlásí až po `slurmctld_threshold` (výchozí 2) po sobě jdoucích DOWN skanech — transientní výpadky pingu nevytvářejí issues |
| **Oprava tlačítek issues** | Tlačítka smazat/ignorovat v modal oknech nově volají přímé REST endpointy (`/api/issues/<key>/delete`, `/api/issues/<key>/ignore`) místo routování přes chat |
| **2-úrovňové seskupení issues** | Incident Matrix a všechny modály seskupují issues do stromu CLUSTER → DETEKTOR. Cluster složky vždy otevřené, detektorové složky se sbalí při ≥5 issues |
| **Zachování stavu složek** | Auto-refresh modalu (3 s) nově trackuje explicitně zavřené složky — zůstanou zavřené přes obnovení |
| **Agent systemd unit names** | `agent_systemd_global_monitor`: flag `--plain` + parsování z pozice `[1]` — zobrazuje skutečná jména jednotek místo `●, ●, ●` |
| **Nasazení chybějících pluginů** | Bylo nasazených jen 4/15 pluginů. `deploy-auto.sh` nově synchronizuje všechny `detector_*.py` a chrání je před smazáním |
| **Odstraněny Teams test notifikace** | `__main__.py` už neposílá na neexistující kanál `tests` při startu/stopu |

---

## Co je nového ve v2026.08.003 (2026-08-17)

| Funkce | Detail |
|---|---|
| **Issue lifecycle auto-close** | Čtyři mechanismy: strop stáří pro event-typy, rekonciliace detektorů (HA, kapacita), periodický auto-recheck a přísnější matchování v `system_detector` (regexy s hranicemi slov + konfigurovatelný ignore-list). Produkce: **47 → 21 aktivních issues** |
| **Reasoning modely v chatu** | Detekce API klíče pro v1 rozhraní; `reasoning_content` streamovaný s příznakem `reasoning`, vykreslovaný do ztlumeného bloku nad odpovědí |
| **Opravy mobilního UI** | Issue karty a modal na mobilu byly nečitelné/oříznuté — sdílené CSS třídy, sekundární akce schovány pod 480 px, `.issue-msg` vyloučen z badge truncation |
| **Smazán mrtvý `scheduler.py`** | Modul nikdo neimportoval; odkazoval na tři neexistující symboly. Dvě reálné opravy (konstanta retence, napojení auto-rechecku) v něm tiše uvízly. Funkční úlohy přesunuty do smyčky `chat_service.py` a nového `issue_lifecycle.py` |
| **Tři plánované úlohy konečně běží** | Hodinový vtip, kontrola DNS, denní AI digest — existovaly, ale plán měly jen v mrtvém modulu |
| **Opravy memory leaků** | Hodinové prořezání `_GEO_CACHE` a GC `user_sessions` nyní běží (byly to jediné úklidové cesty, obě uvízlé v mrtvém scheduleru) |
| **Testy: 1 050 → 1 087** | Nový `test_issue_lifecycle.py` (21 testů); celkem 1 087 |

---

## Co je nového ve v2026.08.001 (2026-08-03)

| Funkce | Detail |
|---|---|
| **Testy: 938 → 1 050** | 112 nových testů pokrývajících knowledge base, infra audit a dependency mapping |
| **80/100 AI roadmap položek** | Nárůst ze 66/100 ve v2026.07 |
| **3 kritické SSH bugy opraveny** | SSH diagnostika + remediace nefungovaly 30. 7. – 1. 8.; zcela vyřešeno |
| **`knowledge.py`** | Runbooky, prevention hinty, tréninkové páry, přenos KB mezi instancemi |
| **`infra_audit.py`** | Detekce config driftu, zombie procesy, expirace certů, post-reboot checklist, kontrola přesnosti dokumentace |
| **`dependencies.py`** | Graf závislostí hostů, výpočet blast-radius, simulace odstavení |
| **`host-setup.md`** | Nový průvodce: příprava monitorovaných hostů pro AI diagnostiku (sentinel user, sudoers, journal group) |

---

## Co je nového ve v2026.07.001 (2026-07-31)

### AI vrstva — 21 nových modulů

| Modul | Co dělá |
|---|---|
| `ai_guard.py` | Obrana proti prompt-injection v obsahu logů, hodinový limit akcí, detekce smyčky |
| `ai_verify.py` | Kontrola halucinací — ověřuje AI tvrzení proti známé infrastruktuře |
| `ai_profiles.py` | Profily kontextového okna dle typu úlohy (triage, hloubková analýza, chat) |
| `ai_runtime.py` | Cache odpovědí, konzistence, token budget, routing modelů |
| `diagnostics.py` | Pevný katalog read-only příkazů — AI vybírá ID příkazů, nikdy raw shell; spustí a interpretuje reálný výstup |
| `fix_verify.py` | Verifikace opravu ~15 min po každém pokusu; selhání se zaznamenají jako anti-vzory |
| `remediation.py` | Stupňovitý žebříček: observe → reload → restart → reboot |
| `remediation_plan.py` | Rollback, kontextové hodnocení rizika, dry-run mód, fronta práce |
| `policy.py` | Vysvětlení blokace, návrhy allowlistu/auto-execute |
| `escalation.py` | Eskalace s kontextem (co bylo zkuseno a proč to selhalo) |
| `correlate.py` | Změnová korelace, kauzální řetězce, cross-host vzory |
| `incident_analysis.py` | Společný jmenovatel, timeline incidentu, detekce kaskád, seřazené hypotézy |
| `trend_detect.py` | Tichá degradace (regrese + r²), detekce chybějících signálů |
| `baseline.py` | Per-host normální profil, sezónnost, audit auth logů |
| `alert_quality.py` | Těžba false-alarmů z historických dat |
| `playbooks.py` | Postupy naučené z manuálních oprav — buduje institucionální paměť |
| `foresight.py` | Kapacitní prognóza, týdenní infrastrukturní výhled |
| `unmatched.py` | Náhodné vzorkování log řádků, které žádný plugin nezachytí |
| `rag_utils.py` | Komprese, hybridní vyhledávání, citace, správa chunků |
| `knowledge.py` | (preview ve v07, stabilní ve v08) |
| `infra_audit.py` | (preview ve v07, stabilní ve v08) |

### Rozsah

- Testy: **317 → 938** (+621 nových testů pokrývajících celou AI vrstvu)
- AI roadmap: **66/100** dokončeno
- Kompletní audit trail každé AI akce
- Všechny AI moduly plně integrovány do údržbové smyčky (`chat_service.py` + `issue_lifecycle.py`)

---

## Co je nového ve v2026.06.024 (oproti v2026.06.005)

### Bezpečnostní hardening

| Funkce | Detail |
|---|---|
| **2FA / TOTP** | Kompletní stack: pyotp (RFC 6238), QR enrollment (Google Authenticator / Authy), dvoukrokový login flow, DB tabulka `user_totp`, admin může 2FA komukoliv deaktivovat |
| **bcrypt hashování hesel** | `web.password_hash: "$2b$12$..."` má prioritu před plaintextem; tlačítko „Hash hesla" v Settings vygeneruje hash; viewer heslo analogicky |
| **CSRF ochrana** | Token v session + SameSite=Strict cookie + globální `fetch` wrapper přidává `X-CSRF-Token` ke všem POST/PUT/DELETE |
| **Brute-force ochrana** | Form login i Basic auth: IP ban po 5 selháních na 300 s; auto-registrace agentů limitována na 10/min per IP |
| **XSS hardening** | Všechny AI odpovědi escapovány přes `html.escape()` před `innerHTML` — obsah logů je pod kontrolou útočníka |
| **SSH hardening** | `ssh_utils.py`: `accept-new` + `UserKnownHostsFile` místo `StrictHostKeyChecking=no`; `ssh-keyscan` při registraci agenta; known_hosts UI (zobrazit / rescan / smazat klíče) |
| **API key scopes** | Jemné: `read:issues`, `write:actions`, `admin:users` — se zpětnou kompatibilitou |
| **Práce se secrets** | `{SECRET:ENV_VAR}` substituce v config.yaml (proměnné po použití smazány z `os.environ`); `/api/config/view` maskuje password/token/secret/api_key jako `***` |
| **Kontrola sessions** | Absolutní 12h timeout (`security.session_max_hours`), refresh role z DB každých 5 min, revokované sessions přežijí restart (DB) |
| **Audit trail** | Tabulka `config_audit` (kdo, kdy, IP, jaké klíče), audit 403/401 přístupů, prohlížeč audit trailu v Settings |
| **SSRF + validace vstupů** | `/api/admin/validate_url` odmítá privátní IP rozsahy; regex validace hostname na všech SSH/ingest endpointech; `int_param()` kontrola mezí na 20+ endpointech |
| **Security self-check** | `/api/admin/security_check` vrací bezpečnostní známku A/B/C/D |

### Notifikace a integrace

| Funkce | Detail |
|---|---|
| **Odchozí kanály** | MS Teams · Slack · PagerDuty · Discord (embeds) · Telegram bot · Opsgenie (Events API v2) · ntfy.sh · Gotify · SMTP e-mail (STARTTLS 587 / SSL 465) · Matrix · Home Assistant · MQTT · obecný Webhook (HMAC-SHA256 + replay ochrana) |
| **Příchozí webhooky** | `/api/inbound/grafana` (legacy + unified alerting) · `/api/inbound/alertmanager` (Prometheus AM) · `/api/inbound/zabbix` (Media Type flat JSON) |
| **Spolehlivost** | Retry fronta s exponenciálním backoffem (30 s/120 s/300 s, max 3 pokusy); throttling per severity (critical/security/root 15 min, high 1 h, medium/low 4 h) |
| **Granularita** | Per-detektor 🔔 toggle, per-kanál toggle, jméno instance v prefixu všech titulků (`[Instance] CHANNEL alert`) |
| **Lifecycle webhooky** | Konfigurovatelné webhooky při CREATED / ACKNOWLEDGED / RESOLVED |
| **Gitea issue sync** | Kritické issues automaticky zakládány v Gitea repozitáři (`GITEA_URL/TOKEN/REPO`) |
| **Grafana anotace** | `_send_grafana_annotation()` při critical/security alertu |
| **Prometheus** | `GET /metrics` scrape endpoint + pushgateway export self-metrik Sentinelu |

### Analytika a AI

| Funkce | Detail |
|---|---|
| **Health score per host** | `/api/agents/<hostname>/health_score` — kompozitní 0–100 se známkou A–D |
| **Předpověď issues** | `/api/analytics/forecast` — lineární regrese, výhled 7 dní |
| **SLA & fatigue reporty** | Tabulka resolution-time, alert-fatigue graf, widget flapping issues, změny od posledního přihlášení |
| **AI kapacitní plánování** | `/api/reports/capacity_plan` — telemetrie agregovaná per host, AI vrací karty HOST/PROBLÉM/DOPORUČENÍ/PRIORITA |
| **Auto-clustering** | `/api/analyze/auto_clusters` — seskupení issues dle pluginu/hostu v 30min oknech, AI pojmenuje root cause |
| **AI postmortem** | `/api/issues/<key>/postmortem` — AI generovaný Markdown postmortem incidentu |
| **Auto-severity & duplikáty** | Severity přiřazená LLM, automatická detekce duplikátů |
| **Týdenní digest** | Obsahuje flapping issues a průměrnou dobu řešení |

### Správa flotily agentů

| Funkce | Detail |
|---|---|
| **Batch SSH** | `POST /api/ssh/batch` — paralelní SSH přes ThreadPoolExecutor (10 vláken, max 50 hostů, 15 s per-host timeout), allowlist kontrolován |
| **Per-agent thresholdy** | `check_agent_thresholds()` vynucováno při každém ingest payloadu; quick-buttons CPU > 90 %, RAM > 90 %, Disk > 85 % |
| **HW metriky přes SSH** | síť (`/proc/net/dev`), GPU (nvidia-smi/rocm-smi), SMART (smartctl), UPS (apcaccess/upsc) |
| **CVE scanner** | `apt list --upgradable` / `dnf --security check-update` per agent |
| **Inventář balíčků** | `dpkg-query` / `rpm -qa` s live filtrem v detailu agenta |
| **QR registrace** | Token modal generuje QR `{hostname, token, ingest_url}`; kopírování tokenu jedním klikem; hromadná rotace tokenů (`/api/agents/rotate_all_tokens`) |
| **Okna údržby** | Snooze pravidla per host; detail agenta zobrazuje vlastní okna |
| **Version drift alert** | Issue při registraci agenta s buildem starším 30 dní; délka offline trackována v telemetrii |

### Provoz a spolehlivost

| Funkce | Detail |
|---|---|
| **Health endpointy** | `/healthz` (Kubernetes/UptimeKuma JSON probe, 503 při chybě DB) · přepracovaná veřejná stránka `/status` (auto-refresh 30 s) |
| **Správa konfigurace** | jsonschema validace kritických klíčů · backup/restore s automatickými snapshoty před restore (drží 10) · diff snapshotů endpoint + UI |
| **Hot reload** | SIGHUP reloaduje config **i** watcher patterns **i** pluginy; `/api/admin/log_level` mění log level za běhu |
| **Graceful shutdown** | SIGTERM flushne telemetry buffer + publikuje MQTT `sentinel/status: offline` |
| **Zálohy** | `/api/admin/backup/download` (tar.gz) + `/api/admin/backup/s3` (upload na S3/MinIO) |
| **File Integrity Monitoring** | SHA-256 hash kritických souborů kontrolován každou minutu → security issue při změně |
| **Ansible runner** | `/api/ansible/run` — validovaná cesta playbooku, streamovaný výstup |
| **Syntetické checky** | HTTP health checky (`SYNTHETIC_CHECKS`), heartbeat URL monitoring, expirace SSL certifikátů (< 14 dní → security issue) |
| **Self-monitoring** | Self-metriky RAM/vlákna/fronta/load každou minutu · memory watchdog (RSS > 1,5 GB → warning) · alert na backlog AI fronty · alert na velikost DB · no-agent alert · profilace startu |

### Výkon

- **Issues cache** s TTL 5 s + double-checked `threading.Lock`; invalidace při zápisu
- **Dávkování zápisu telemetrie** (buffer flushovaný periodicky), dashboard sparklines dotaz cachován 5 min
- **Kompozitní DB indexy** (`idx_problems_plugin_ch_ts`, `idx_issue_hist_plugin_ts`, severity + telemetrie)
- **WAL tuning** — `wal_autocheckpoint=200`, `synchronous=NORMAL`, explicitní checkpoint po prune; VACUUM po > 10 k smazaných řádcích; 90denní retence historie issues
- **HTTP cachování** — ETag + `max-age` + 304 conditional GET pro statiku; `defer` + `preload` načítání skriptů; gzip
- **SocketIO backpressure** — omezená fronta na frontend (500, drop-oldest); dedup WS zpráv v 1s okně
- **Virtual scroll** — issues stránkované po 50 s tlačítkem „Načíst více"

### UI / UX

- Tab **Runbooks** v Tools s CRUD + runbook modalem
- **Moderní interaktivní grafy** — min/max/avg badge, přerušovaná průměrová linie, bohaté tooltipy (dashboard trend, donut s celkovým počtem uprostřed, alert timeline, agent sparklines)
- **Fullscreen overlay issue**, inline komentáře, barevné štítky, drag & drop záložky, mobilní swipe (vpravo = acknowledge, vlevo = delete)
- **Kopie issue jako Markdown**, hromadný CSV export (`Alt+E`), hromadný acknowledge (`Alt+A`), export chatu do Markdownu
- **Přístupnost** — ARIA `role="dialog"`, `aria-modal`, `aria-labelledby` na všech modalech, Escape pro zavření
- **DB management panel** v Settings — velikost, počty záznamů, tlačítka „Prune nyní" a „Agregovat telemetrii"
- **Chat** — kontextové chips s navrženými dotazy, LIVE tag (obohacuje prompt o kontext aktivních issues), Markdown rendering
- **Časová zóna** — `DISPLAY_TZ`, `/api/timezone/info`, `/api/timezone/convert`

### Inženýrská kvalita

- **1 294 automatizovaných testů** (v2026.11.014) — route, security, integrační, AI vrstva, issue lifecycle, benchmark
- **CI pipeline** — Gitea Actions (`pytest` + `node --check` + `make build`), `pre-push` git hook, `make ci`
- **Linting** — ruff (Python), ESLint s `no-redeclare=error` (JS), pinované `requirements.txt`
- **Refaktoring** — `notifier.py` (všechny odchozí kanály), `issue_lifecycle.py` (auto-zavírání issues) a `ssh_utils.py` extrahovány z `chat_service.py`; maintenance smyčka integrována přímo v `chat_service.py`
- **CONTRIBUTING.md** — diagram architektury, vývojový workflow, bezpečnostní pravidla

---

## Přehled funkcí

| Oblast | Schopnosti |
|---|---|
| **AI inference** | Hailo-10H NPU (hailo-ollama) · CPU Ollama · external API · runtime přepínání modelu |
| **RAG znalostní báze** | ChromaDB + nomic-embed-text · BM25 TF×IDF fallback · vlastní upload (.md/.txt/.pdf/.docx/.csv) · reindex jedním klikem |
| **AI bezpečnost** | Obrana proti prompt-injection · hodinový limit akcí · detekce smyčky · kontrola halucinací · audit trail (`ai_guard.py`, `ai_verify.py`) |
| **AI diagnostika** | Pevný read-only katalog příkazů — AI vybírá ID, nikdy raw shell; spustí a interpretuje reálný výstup (`diagnostics.py`) |
| **AI verifikace** | Kontrola opravy ~15 min po každé remediaci; selhání se ukládají jako anti-vzory (`fix_verify.py`) |
| **AI remediace** | Stupňovitý žebříček: observe → reload → restart → reboot · rollback · dry-run · hodnocení rizika (`remediation.py`, `remediation_plan.py`) |
| **AI korelace** | Kauzální řetězce · změnová korelace · cross-host vzory · detekce kaskád · timelines incidentů · seřazené hypotézy (`correlate.py`, `incident_analysis.py`) |
| **AI baselining** | Per-host normální profil · sezónnost · tichá degradace (regrese + r²) · chybějící signály (`baseline.py`, `trend_detect.py`) |
| **AI prognózy** | Kapacitní prognóza · týdenní výhled · těžba false-alarmů · vzorkování nezachycených logů (`foresight.py`, `alert_quality.py`, `unmatched.py`) |
| **Znalostní báze** | Runbooky · prevention hinty · tréninkové páry · přenos KB mezi instancemi (`knowledge.py`) |
| **Infra audit** | Config drift · zombie procesy · expirace certů · post-reboot checklist · blast-radius závislostí (`infra_audit.py`, `dependencies.py`) |
| **Hybridní telemetrie** | Pull (inotify logy) + Push (agenti přes Bearer token) · více IP adres na agenta · tracking verze agenta (SHA) · version drift badge v detailu agenta |
| **Autofix** | AI navrhne opravu → admin Schválit/Zamítnout → SSH exec na mgmt nodu · allowlist příkazů · autonomní exec |
| **Prediktivní analytika** | TTC (Time-To-Critical) pro disky · Mann-Kendall trend test · předpověď lineární regresí · kapacitní plánování |
| **Bezpečnostní profiler** | Brute-force, sudo abuse, CVE scan, neoprávněné porty, honeypot, FIM, expirace SSL |
| **Notifikace** | 13 odchozích kanálů · 3 příchozí webhooky · retry fronta · throttle per severity · per-detektor/kanál toggles |
| **Prometheus** | `GET /metrics` scrape + pushgateway export; auth přes scrape_token |
| **Dashboard** | Stat karty · interaktivní min/max/avg grafy · trend chart · donut · health trend · flapping widget · live hodiny |
| **Autentizace** | viewer / admin / superadmin · LDAP (lldap + OpenLDAP) · **2FA/TOTP** · **bcrypt** · rate-limit + IP ban · **CSRF** |
| **Workflow issues** | `active` → `acknowledged` → `validating` → `resolved` · eskalační pravidla · lifecycle webhooky · 2-úrovňové seskupení CLUSTER→DETEKTOR |
| **Auto-remediace** | Jednorázová SSH oprava · allowed_commands s `auto_execute` · AUTOFAIL issues · SSH jump host (ProxyJump) · Ansible runner |
| **Plugin hot-reload** | `POST /api/plugins/reload` · SIGHUP plný reload · Pattern Editor s regex testerem + AI návrhy patternů |
| **Telemetrie** | Detekce anomálií (3σ) · pevné thresholdy · per-agent thresholdy · InfluxDB export · heatmap · health score historie |
| **Topologie** | Mapa topologie agentů · graf závislostí pluginů · SNMP CDP/LLDP · Canvas force-directed graf |
| **SSH akce** | Jump host (ProxyJump) · SSH modal (admin+) · streaming výstup (SSE) · **batch SSH** · správa known_hosts |
| **API dokumentace** | `GET /api/docs` — Swagger UI · `GET /api/openapi.json` — OpenAPI 3.0 spec |
| **Hailo TUI** | `hailo_models.py` — Unicode TUI správce modelů: htop-style CPU/Mem bary, RX/TX, NPU arch+FW, TPS benchmark graf |
| **UI i18n** | Čeština (výchozí) · angličtina toggle · `localStorage` persistence · konfigurace časové zóny |
| **Bezpečnost** | Symlink containment · limit uploadů (5 MB) · secure_filename · timing-safe ověření tokenů · CSP hlavičky · maskování secrets · SSRF guard |

---

## Architektura

```
  Log soubory ──inotify──▶ watcher.py ──▶ plugins[] ──▶ api.report_problem()
  Vzdálení agenti ──POST──▶ /api/v1/agent/ingest            │
  Grafana/AM/Zabbix ──POST──▶ /api/inbound/*                │
                                                            ▼
                                                   state.py (SQLite WAL)
                                                            │
                         ┌──────────────────────────────────┤
                         ▼                                  ▼
               ollama_service.py                   Flask + SocketIO :5050
               (AI worker pool)                    (chat_service.py + routes/)
                         │                                  │
         ┌───────────────┼───────────────┐         ┌────────┴────────┐
         ▼               ▼               ▼         ▼                 ▼
  hailo-ollama      Ollama CPU      external   issue_lifecycle   notifier.py
  (NPU :8000)       (:11434)        API        + maintenance    (13 kanálů)
```

### Hlavní moduly

| Soubor | Zodpovědnost |
|---|---|
| `chat_service.py` | Flask/SocketIO app factory, RBAC, WebSocket |
| `auth.py` | Autentizace, LDAP, 2FA/TOTP, bcrypt, sessions, ověření API klíčů |
| `state.py` (`state_base/issues/agents`) | SQLite WAL orchestrace — issues, telemetrie, agenti |
| `watcher.py` | inotify filesystem eventy, hot config reload, FIM |
| `plugin_manager.py` | Dynamické načítání pluginů, routing patternů, hot-reload |
| `ollama_service.py` | AI worker thread pool, přepínání modelů |
| `rag.py` | ChromaDB, nomic-embed-text, BM25 fallback |
| `actions.py` | Lifecycle autofixu — create, approve, reject, SSH exec |
| `notifier.py` | Všechny odchozí notifikace + retry fronta + throttling |
| `issue_lifecycle.py` | Auto-zavírání issues: strop stáří, rekonciliace detektorů, periodický auto-recheck |
| `ssh_utils.py` | Centrální SSH bezpečnost — `build_ssh_cmd()`, sken host klíčů |
| `analytics.py` | TTC, Mann-Kendall, Z-Score, health score, forecast |
| `topology.py` | Topologie agentů, SNMP CDP/LLDP |
| `routes/` | Flask Blueprints: main, issues, agents, actions, system, export, integrations, chat |

### AI vrstva (v2026.07+)

| Soubor | Zodpovědnost |
|---|---|
| `ai_guard.py` | Obrana proti prompt-injection, limit akcí, detekce smyčky |
| `ai_verify.py` | Kontrola halucinací proti známé infrastruktuře |
| `ai_profiles.py` | Profily kontextového okna dle typu úlohy |
| `ai_runtime.py` | Cache odpovědí, konzistence, token budget, routing modelů |
| `diagnostics.py` | Pevný katalog read-only příkazů — AI vybírá ID, nikdy raw shell |
| `fix_verify.py` | Verifikace opravy po remediaci; selhání se ukládají jako anti-vzory |
| `remediation.py` | Stupňovitý žebříček remediace s rollbackem |
| `remediation_plan.py` | Hodnocení rizika, dry-run, fronta práce |
| `policy.py` | Vysvětlení blokace, návrhy allowlistu/auto-execute |
| `escalation.py` | Eskalace s kontextem předchozích pokusů |
| `correlate.py` | Změnová korelace, kauzální řetězce, cross-host vzory |
| `incident_analysis.py` | Timeline, detekce kaskád, seřazené hypotézy |
| `trend_detect.py` | Tichá degradace, chybějící signály |
| `baseline.py` | Per-host normální profil, sezónnost, audit auth logů |
| `alert_quality.py` | Těžba false-alarmů z historických dat |
| `playbooks.py` | Postupy naučené z manuálních oprav |
| `foresight.py` | Kapacitní prognóza, týdenní výhled |
| `unmatched.py` | Vzorkování nezachycených log řádků |
| `rag_utils.py` | Komprese, hybridní vyhledávání, citace, správa chunků |
| `knowledge.py` | Runbooky, prevention hinty, přenos KB |
| `infra_audit.py` | Config drift, zombie procesy, certifikáty, post-reboot check |
| `dependencies.py` | Graf závislostí hostů, blast-radius, simulace odstavení |

---

## Datové toky

### A. Ingest & detekce

1. Log řádek zapsán do `/var/log/sentinel/logs/` → inotify event
2. `watcher.py` čte nové řádky přes `mmap`
3. `PluginManager` routuje řádky na odpovídající detektory dle masky souboru
4. Detektor generuje unikátní klíč (např. `DISK_FULL|proxmox01|/data`)
5. Stav zapsán do tabulky `problems` → task vložen do `task_queue`
6. Push cesta: agenti POSTují `/api/v1/agent/ingest` (nebo `/api/v1/ingest/bulk` pro dávky); pole `metrics` se kontroluje proti per-agent thresholdům

### B. AI inference + RAG

1. AI worker vyzvedne task z `task_queue`
2. Načte prompt šablonu dle kanálu (security, clusters, infra, root, icinga)
3. RAG: ChromaDB dotaz → relevantní kontext vložen do system promptu
4. Prompt odeslán do Ollama (NPU/CPU/external)
5. Pokud odpověď obsahuje remediation skript → `actions.py` vytvoří `pending` akci

### C. Zpětnovazební smyčka remediace

1. `actions.py` vytvoří DB záznam s navrženým SSH příkazem
2. Frontend dostane WebSocket event `new_action`
3. Admin s rolí `admin` nebo `superadmin` klikne Schválit nebo Zamítnout
4. Při schválení: SSH připojení na management node → vykonání příkazu (allowlist pre-validován)
5. STDOUT/STDERR zalogován → incident přechází do stavu `validating`

### D. Notifikační pipeline

1. Issue uloženo → `notifier.send_notification()` fan-out na všechny zapnuté kanály
2. Nejdřív se kontrolují per-detektor a per-kanál toggles
3. Aplikuje se throttle per severity (critical 15 min … low 4 h)
4. Selhání jdou do retry fronty (backoff 30 s → 120 s → 300 s)
5. Lifecycle webhooky se spouští při CREATED / ACKNOWLEDGED / RESOLVED

---

## Workflow issues

```
  detekováno ──▶  active  ──▶  acknowledged (tlačítko ✓✓)
                    │                │
                    │           validating ──▶ resolved
                    │
                    └──▶ (auto-resolved detektorem nebo expiry pravidlem)
```

**Eskalační pravidla:** Pokud issue zůstane `active` nebo `acknowledged` déle než N hodin bez vyřešení, severity se automaticky zvýší na další úroveň.

**Lifecycle webhooky** mohou notifikovat externí systémy při každém přechodu a kritické issues lze zrcadlit do **Gitea**.

---

## Instalace

```bash
git clone <repo> /opt/Sentinel
sudo bash /opt/Sentinel/install.sh        # Debian/Ubuntu/RHEL/Rocky/Pi OS
sudo python3 /opt/Sentinel/sentinel_init.py   # interaktivní konfigurační wizard
sudo systemctl enable --now sentinel
```

Setup wizard odmítá výchozí hesla, generuje systemd unit s `WatchdogSec=900` a WAL-checkpoint `ExecStartPre` a vytváří `/var/lib/sentinel`.

### Klíčová konfigurace (config.yaml)

```yaml
web:
  port: 5050
  password_hash: "$2b$12$..."      # bcrypt — má prioritu před plaintext `password`

security:
  login_max_attempts: 5
  login_ban_time: 300
  session_max_hours: 12

ollama:
  url: "http://localhost:11434"
  model: "llama3.2"
  workers: 3

hailo_ollama:
  enabled: false
  url: "http://localhost:8000"

ldap:
  enabled: false
  host: "ldaps://ldap.example.com"
  base_dn: "dc=example,dc=com"

prometheus:
  enabled: true
  scrape_token: "{SECRET:PROM_TOKEN}"   # substituce z env proměnné

telemetry_alerts:
  cpu_critical: 95
  disk_critical: 95
  temp_critical: 85

fim:
  enabled: true
  paths: [/etc/passwd, /etc/shadow, /etc/ssh/sshd_config]

host_cluster_rules:
  - pattern: node1
    cluster: COMPUTE
  - pattern: storage
    cluster: STORAGE
default_cluster: INFRA
```

---

## Požadavky

- Python 3.13+ · Flask · Flask-SocketIO · ChromaDB · paho-mqtt
- `pyotp` (2FA) · `qrcode` + `pillow` (QR enrollment) · `bcrypt` · `jsonschema`
- Ollama s `nomic-embed-text` (pro embeddingy)
- **Volitelně:** Hailo AI HAT 2+ s hailo-ollama 5.3.0 pro NPU inferenci

---

## Ekosystém komponent

| Komponenta | Popis | Port |
|---|---|---|
| **Sentinel** | Centrální server (tato dokumentace) | 5050 |
| **sentinel-agent** | Push agent na každém monitorovaném nodu | — |
| **sentinel-overhealth** | SSH pull orchestrátor (cron) | — |
| **sentinel-plugins** | 11 detektorových pluginů | — |
| **sentinel-alert** | Standalone síťový bezpečnostní dashboard (vč. MikroTik + PiHole) | 5056 |
| **sentinel-hw** | Fyzický RPi robot | 5055 |
| **sentinel-app** | Android mobilní klient | — |
| **sentinel-console** | TUI terminálový klient | — |
