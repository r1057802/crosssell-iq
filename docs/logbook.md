# Logboek CrossSellIQ

Logboek en portfolio voor Cloud & Ops (2026-2027). Per werksessie noteer ik wat gepland was, wat er echt gebeurd is, waar ik vastliep, wat vlot ging en welke technische keuzes ik maakte.

## Planning

| Deadline | Onderdeel | Status |
|---|---|---|
| 30/09/2026 | Projectvoorstel indienen (cloudplatform en onderwerp AI-agent) | Nog te controleren |
| 02/10/2026 | Feedback op voorstel | |
| 16/10/2026 | Milestone 1: lokale baseline | Bezig |
| 13/11/2026 | Milestone 2: containerisatie en CI | |
| 04/12/2026 | Milestone 3: cloud deployment en CI/CD | |
| 18/12/2026 | Milestone 4: personalisatie en AI-agent | |
| Examenperiode | Eindpresentatie met live demo | |

### Werkplanning Milestone 1

| Periode | Wat |
|---|---|
| 1 tot 5 oktober | Pipeline: raw naar bronze, bronze naar silver, baseline-tabellen in gold, `run_pipeline.py` |
| 6 tot 12 oktober | C#-API: project, endpoint, foutafhandeling, tests |
| 13 tot 14 oktober | Webpagina en README |
| 15 oktober | Alles vanaf nul testen, buffer voor problemen |

Is de pipeline op 6 oktober niet af, dan ga ik verder met de API met wat werkt.

## Sessie 1: 1 oktober 2026

**Gepland**
Projectstructuur opzetten, de H&M-data downloaden en de eerste versie van de datapipeline schrijven.

**Gedaan**
- Projectmap `crosssell-iq` aangemaakt met de mappen `backend`, `data/raw`, `frontend`, `ml`, `tests` en `docs`.
- `CLAUDE.md` geschreven met de projectcontext, de milestones en de werkafspraken voor Claude Code.
- `.gitignore` aangemaakt zodat de data, de database, `.venv` en geheimen niet in Git komen.
- Kaggle CLI geïnstalleerd en ingelogd met `kaggle auth login`.
- `articles.csv`, `customers.csv` en `transactions_train.csv` gedownload en uitgepakt in `data/raw` (samen ongeveer 3,7 GB).
- Een Python virtual environment (`.venv`) ingesteld en gekozen als interpreter in VS Code.
- DuckDB 1.5.6 vastgelegd in een `requirements.txt`.
- Een eerste laadscript (`load_database.py`) geschreven dat de CSV's rechtstreeks naar Silver-tabellen in DuckDB laadt.
- De opdracht (Cloud & Ops-PDF) doorgenomen en mijn planning en aanpak daarmee vergeleken.
- De mappen `pipeline` en `notebooks` aangemaakt voor de nieuwe structuur.

**Waar liep ik vast**
- Kaggle aanmelden met een API-token lukte niet: de commando's op de Kaggle-pagina waren voor Mac en Linux, niet voor PowerShell. Opgelost met `kaggle auth login`, waarbij je via de browser inlogt en geen token hoeft te beheren.
- Ik heb het token per ongeluk in een screenshot gedeeld. Geleerd: tokens horen nooit in screenshots of chats. Het token moet ik nog intrekken op Kaggle (Settings, API).
- Ik had vier commando's tegelijk in de terminal geplakt, waardoor de Kaggle-downloads startten voordat de installatie klaar was.
- `pip install` installeerde DuckDB eerst in mijn globale Python 3.13 in plaats van in de `.venv` (Python 3.14). Ik leerde dat een terminal die gestart is voor je de interpreter kiest, de `.venv` niet gebruikt.
- Een map heette `Dockerfile`, maar een Dockerfile moet een bestand zijn. De map verwijderd.
- De mappen `pipeline` en `notebooks` stonden eerst in `data` in plaats van in de hoofdmap. `data` is alleen voor data, code staat ernaast.
- Ik twijfelde of de CSV's in `data/raw` al de Bronze-laag waren. Daar bestaan twee definities voor (zie technische keuzes).

**Wat ging vlot**
- De downloads zelf, en het uitpakken met PowerShell.
- De projectstructuur, zodra duidelijk was wat waar hoort.

**Technische keuzes**

*Datapipeline en medallion-structuur*
- Ik volg een strikte medallion-structuur:
  - **raw** (`data/raw`): de aanleverzone met de originele Kaggle-bestanden, die ik nooit wijzig;
  - **bronze**: de ingeladen data in DuckDB, inhoudelijk ongewijzigd (alle kolommen, alles als tekst), plus de metadatakolommen `_source_file` en `_loaded_at`;
  - **silver**: opgeschoonde tabellen met de juiste types en alleen de nodige kolommen;
  - **gold**: tabellen die klaar zijn voor gebruik. Voor Milestone 1 alleen de baseline-tabellen (populariteit per categorie, categorieën per klant, voorbeeldklanten). De modeldata volgt in Milestone 4.
- Zo kan ik altijd opnieuw beginnen vanaf de originele data, en is elke stap apart te controleren.
- Mijn eerste `load_database.py` sprong rechtstreeks van de CSV's naar Silver. Ik splits het op in `raw_to_bronze.py` en `bronze_to_silver.py`, zodat ik een stap apart opnieuw kan draaien zonder telkens 3,5 GB opnieuw in te laden.
- **`article_id` als tekst**: de ID's beginnen met een nul die zou verdwijnen als getal.

*Mappenstructuur*
- **`pipeline/`** bevat de data-engineering (raw naar gold), **`ml/`** later het model (Milestone 4). Mijn laadscript stond eerst in `ml`, maar data laden en opschonen is geen machine learning. Door ze te scheiden zegt elke mapnaam wat erin zit.
- De pipeline is een apart proces dat vooraf draait en de database bouwt. De C#-API voert de pipeline nooit uit, maar leest alleen het resultaat in read-only modus.

*Notebooks om te verkennen, scripts voor de pipeline*
- Ik verken de data in Jupyter-notebooks in `notebooks/`: de data bekijken, queries uitproberen, rare waarden opsporen en grafieken maken. Daar mag het rommelig zijn.
- Wat werkt, zet ik om naar `.py`-scripts in `pipeline/`. Die scripts draaien altijd van begin tot einde in dezelfde volgorde, met één commando.
- Waarom niet de hele pipeline in notebooks? In een notebook kun je cellen in willekeurige volgorde draaien, waardoor het bij mij werkt maar elders niet. Notebooks zijn in Git ook moeilijk leesbaar, omdat ze alle uitvoer bevatten. En voor Milestone 2 moeten Docker en GitHub Actions de pipeline automatisch kunnen uitvoeren, wat met een script het eenvoudigst is.
- Ik weet dat veel data-engineeringteams wel in notebooks werken, bijvoorbeeld in Databricks of Microsoft Fabric. Daar regelt het platform de volgorde, planning en versiebeheer. In mijn project draait alles lokaal en in Docker zonder zo'n platform, dus kies ik voor scripts.
- De pipeline mag nooit afhangen van een notebook: alles wat de pipeline nodig heeft, staat in de scripts.
- `ipykernel` (nodig om notebooks te draaien) zet ik in een apart `requirements-dev.txt`, omdat de pipeline zelf het niet nodig heeft.

*Omgeving en configuratie*
- **Virtual environment en vaste versies** in `requirements.txt`: zodat mijn project op een andere computer en later in Docker op dezelfde manier werkt.
- **`.env` voor geheimen**: API-sleutels en andere geheimen komen in een `.env`-bestand dat niet in Git staat, met een `.env.example` zonder echte waarden. Voor Milestone 1 heb ik nog geen geheimen, maar de bescherming staat al in `.gitignore`.
- **Geen npm**: de API is C# (NuGet), en de webpagina maak ik met gewone HTML en JavaScript in `wwwroot`. Eén project, één container en één URL maken Milestone 2 en 3 eenvoudiger. Een JavaScript-framework overweeg ik pas voor het optionele dashboard in Milestone 4.
- **Branch `main`**: de hoofdbranch heet `main`, omdat bij Milestone 3 een push naar `main` automatisch moet deployen. Vanaf Milestone 3 werk ik op aparte branches, zodat `main` altijd werkt.

*Data en Git*
- **Data niet in Git**: 3,7 GB is te groot voor een repository, en GitHub weigert bestanden boven 100 MB. Dit moet ik oplossen voor Milestone 2, waar "git clone en één commando" de volledige applicatie moet starten. Mijn plan: de API heeft alleen de kleine gold-tabellen nodig, niet de volledige transacties.

### Keuze: DuckDB als database

**Probleem**
De H&M-dataset bevat ongeveer 31,8 miljoen transacties (3,5 GB als CSV), 1,4 miljoen klanten en 105.000 artikelen. Ik heb een database nodig die deze data snel kan tellen, groeperen en combineren, zowel in mijn pipeline (bronze, silver, gold) als voor mijn API.

**Overwogen alternatieven**
- **Pandas**: laadt alle data in het werkgeheugen. Met 3,5 GB aan transacties loopt mijn laptop vast, dus dit is niet geschikt voor de volledige dataset.
- **SQLite**: ook een database in één bestand, maar gemaakt voor kleine transacties (zoals één record opslaan of opzoeken), niet voor grote analyses. Veel trager voor mijn soort vragen.
- **PostgreSQL**: een volwaardige databaseserver. Krachtig, maar ik moet hem installeren, beheren en in Azure als aparte, betalende dienst draaien. Voor deze fase is dat te zwaar.

**Waarom DuckDB**
- Het is een analytische database die data per kolom opslaat. Bij een vraag zoals "hoeveel klanten kochten per categorie?" leest het alleen de nodige kolommen, waardoor analyses op 31 miljoen rijen in seconden gaan.
- Het draait als één bestand binnen mijn programma, zonder server, gebruikers of wachtwoorden.
- Het kan CSV-bestanden rechtstreeks lezen, wat de stap van raw naar bronze eenvoudig maakt.
- Het werkt zowel in Python (pipeline) als in C# (API, via DuckDB.NET).
- Met schema's (bronze, silver, gold) kan ik de medallion-structuur in één bestand organiseren.

**Beperkingen**
- Er kan maar één programma tegelijk naar het bestand schrijven. Ik moet dus mijn API en notebooks sluiten voordat ik de pipeline draai. Dat past bij mijn opzet: de pipeline schrijft vooraf, de API leest daarna in read-only modus.
- In de cloud is het een bestand dat met mijn container mee moet. Daarom laat ik de API alleen de kleine gold-tabellen gebruiken.

**Beslissing voor later**
Voor Milestone 1 gebruik ik alleen DuckDB. Bij Milestone 2 beslis ik of ik PostgreSQL toevoeg als database voor de API. Om die overstap makkelijk te houden, zet ik de databasetoegang in mijn API achter een interface (`IRecommendationRepository`), zodat ik alleen die laag moet aanpassen.

**Volgende stap**
- De mappen `pipeline` en `notebooks` naar de hoofdmap verplaatsen, en `requirements.txt` naar de hoofdmap.
- `pipeline/raw_to_bronze.py` schrijven en draaien, en de bronze-tabellen controleren.
- Daarna `bronze_to_silver.py`, en pas als die hetzelfde resultaat geeft, `load_database.py` verwijderen.
- Eerste commit en push naar GitHub.

## Sessie 1, vervolg: Git en de bronze-laag (1 oktober 2026)

**Gepland**
De projectregels bijwerken, de repository op GitHub zetten en de bronze-laag bouwen.

**Gedaan**
- `CLAUDE.md` bijgewerkt naar de nieuwe aanpak. `AGENTS.md` is nu alleen een verwijzing naar `CLAUDE.md`, zodat er één bron van projectregels is.
- `.gitignore` ingevuld (het bestand was leeg): data, de DuckDB-database, `.venv`, `.env`, `kaggle.json` en build-output worden uitgesloten. Getest in een aparte testrepo.
- Repository `crosssell-iq` aangemaakt op GitHub en de eerste commit gepusht ("Initial project blueprint").
- Branch `feature/notebook-pipeline` aangemaakt om de pipeline te bouwen zonder `main` te wijzigen.
- Notebook `01_bronze.ipynb` gemaakt en gedraaid: `bronze.articles` (105.542 rijen), `bronze.customers` (1.371.980) en `bronze.transactions` (31.788.324), telkens gecontroleerd tegenover de CSV's.
- Bronze daarna incrementeel gemaakt met een laadlogboek (`bronze.load_log`).
- De bronze-data verkend als basis voor de opschoonregels van silver.

**Waar liep ik vast**
- Bij de eerste push koppelde ik de remote aan een voorbeeld-URL. Opgelost met `git remote set-url origin`.
- Ik commitde het bronze-notebook op `main` voordat ik de feature-branch aanmaakte. Ik heb het zo gelaten, omdat de versie werkte en het terugdraaien de geschiedenis van `main` zou herschrijven.

**Technische keuzes**

*De pipeline eerst in notebooks, laag per laag*
- Ik bouw de pipeline eerst in notebooks: `01_bronze`, `02_silver`, `03_gold`. Een volgende laag begin ik pas als de vorige gecontroleerd is. Voor Milestone 2 zet ik de logica om naar scripts in `pipeline/`, omdat Docker en GitHub Actions scripts draaien en geen notebooks.
- Elk notebook controleert zijn resultaat (aantal rijen, kolommen, types) en stopt met een fout als een controle faalt.

*Incrementele pipeline*
- De Kaggle-bestanden veranderen nooit, maar ik bouw de pipeline toch incrementeel, zodat nieuwe leveringen verwerkt kunnen worden zonder de code aan te passen.
- Bronze houdt in `bronze.load_log` bij welke bestanden al geladen zijn, en laadt alleen nieuwe bestanden (append). Een tweede run laadt niets: de pipeline is idempotent.
- Het laden van een bestand en de regel in het laadlogboek gebeuren in één databasetransactie. Mislukt een lading, dan wordt alles teruggedraaid.
- Ik volg bestanden en geen rijen, omdat identieke transactierijen echte aankopen zijn: de dataset heeft geen kolom voor het aantal stuks.
- Plan voor de volgende lagen: silver voegt nieuwe transacties toe en werkt klanten en artikels bij met `MERGE`; gold gebruikt `MERGE` voor alle tabellen.
- Met `FULL_REFRESH = True` kan ik een laag altijd van nul opnieuw opbouwen.

*Geen SCD2*
- SCD2 (historiek van wijzigingen bijhouden) gebruik ik niet: de bron is één momentopname zonder wijzigingshistoriek. `MERGE` overschrijft gewijzigde waarden (SCD1). Ik voeg SCD2 pas toe als er nieuwe momentopnames binnenkomen en de historiek nodig wordt.
- Beperking voor Milestone 4: klantkenmerken zoals `age` en `club_member_status` hebben geen datum. Als feature kunnen ze informatie van na de referentiedatum bevatten (lekkagerisico).

*Git*
- Ik werk op een feature-branch en voeg die via een Pull Request samen met `main`. Zo blijft `main` een werkende versie.

**Volgende stap**
- Bronze incrementeel draaien, twee keer, om te tonen dat de tweede run niets laadt.
- `02_silver.ipynb` incrementeel maken en draaien.
- Daarna `03_gold.ipynb` met de baseline-tabellen.

## Sessie 2: 2 oktober 2026

**Gepland**
De incrementele bronze-laag op mijn eigen database draaien en de silver-laag bouwen.

**Gedaan**
- `01_bronze.ipynb` (incrementeel) gedraaid. Omdat mijn database nog bronze-tabellen zonder laadlogboek had, bouwde het notebook bronze één keer opnieuw op en maakte het `bronze.load_log` aan met drie bestanden.
- `02_silver.ipynb` incrementeel gebouwd en gedraaid. Resultaat:
  - `silver.customers`: 1.371.980 klanten, één rij per klant;
  - `silver.articles`: 105.542 artikels, één rij per artikel;
  - `silver.transactions`: 31.788.324 transacties, van 2018-09-20 tot 2020-09-22.
- Alle 17 silver-controles geslaagd: aantallen tegenover bronze, kolommen en types, unieke sleutels, elke transactie heeft een bestaande klant en een bestaand artikel, en de opschoonregels.
- Silver een tweede keer gedraaid: 0 nieuwe bestanden en niets veranderd. Silver is dus idempotent, net als bronze.
- 9.699 klanten hebben nooit iets gekocht. Die heb ik nodig voor de foutafhandeling van de API ("klant zonder aankoopgeschiedenis").
- `CLAUDE.md` en `AGENTS.md` bijgewerkt met de silver-regels.

**Waar liep ik vast**
- Silver faalde met "bronze.load_log not found". VS Code had het bronze-notebook nog open met de oude inhoud. Daardoor draaide de oude versie, en bij het opslagen overschreef VS Code de nieuwe versie op schijf. Opgelost met `git restore notebooks/01_bronze.ipynb`, waarna ik het notebook opnieuw opende.
- De uitvoer van een run was niet zichtbaar omdat ik het notebook niet had opgeslagen na het draaien.

**Technische keuzes**

*Opschoonregels silver*
- `fn` en `active` worden `BOOLEAN`: `1.0` wordt `TRUE`, leeg blijft `NULL`. De dataset zegt niet wat leeg betekent, dus `NULL` (onbekend) is eerlijker dan `FALSE`.
- `fashion_news_frequency`: `None` en `NONE` samengevoegd tot `NONE`.
- `postal_code` laat ik weg: niet nodig voor de baseline, en minder persoonsgegevens bewaren is veiliger (dataminimalisatie). Het staat nog in bronze.
- Bij artikels houd ik alleen de leesbare namen. De numerieke codes bevatten dezelfde informatie, en `detail_desc` gebruik ik niet.
- De categorie `Unknown` blijft in silver. Silver beschrijft de data zoals ze is; of `Unknown` aanbevolen mag worden, beslis ik in gold.
- De 2.974.905 identieke transactierijen blijven staan. De dataset heeft geen kolom voor het aantal stuks: het zijn meerdere stuks van hetzelfde artikel op dezelfde dag, dus echte aankopen.
- `price` is een geschaalde waarde van Kaggle, geen bedrag in euro.

*Incrementeel laden in silver*
- `silver.load_log` houdt bij welke bronze-bestanden silver al verwerkte.
- Transacties zijn gebeurtenissen die achteraf niet veranderen: nieuwe rijen worden toegevoegd (append).
- Klanten en artikels beschrijven een toestand die kan veranderen: ze worden bijgewerkt met `MERGE` (SCD1, de nieuwste momentopname wint).
- `customer_id` en `article_id` zijn primary keys, zodat de database zelf geen dubbele klant of dubbel artikel toelaat.
- Ik gebruik `MERGE ... UPDATE BY NAME` en niet `UPDATE SET *`. Ik testte dat `UPDATE SET *` kolommen op positie koppelt: bij een andere kolomvolgorde komen waarden ongemerkt in de verkeerde kolom.
- Wordt bronze opnieuw opgebouwd, dan merkt silver dat aan de gewijzigde laadtijden en bouwt het zichzelf ook opnieuw op. Zo kan silver nooit verouderde of dubbele data bevatten.

**Volgende stap**
- `02_silver.ipynb` committen op `feature/notebook-pipeline`.
- `03_gold.ipynb` met `gold.category_popularity`, `gold.customer_categories` en `gold.example_customers`. Eerst beslissen wat er met `Unknown` en de heel kleine categorieën gebeurt.

## Sessie 3: 4 tot 8 oktober 2026

**Gepland**
De gold-laag bouwen in `03_gold.ipynb` en de drie notebooks omzetten naar scripts in `pipeline/`, met `run_pipeline.py` als één commando.

**Gedaan**
- `03_gold.ipynb` gebouwd en gedraaid. Resultaat:
  - `gold.customers`: 1.371.980 klanten;
  - `gold.customer_categories`: 4.819.805 rijen (klant en categorie);
  - `gold.category_popularity`: 18 categorieën;
  - `gold.example_customers`: 12 demo-klanten.
- Alle 10 gold-controles geslaagd. Een tweede run gaf "Gold is already up to date": gold is idempotent.
- De logica van de drie notebooks omgezet naar scripts: `raw_to_bronze.py`, `bronze_to_silver.py`, `silver_to_gold.py`, de gedeelde controles in `check_quality.py`, en `run_pipeline.py` dat de drie lagen na elkaar draait.
- De scripts regel per regel vergeleken met de notebooks: de laadlogica en de controles zijn gelijk. De verschillen zijn bewust: `--full-refresh` in plaats van `FULL_REFRESH`, het pad naar de database, en de inspectiequeries die alleen in de notebooks staan.
- `check_quality.py` apart gedraaid op de bestaande database: alle 43 controles geslaagd (16 bronze, 17 silver, 10 gold).
- `requirements.txt` (DuckDB) en `requirements-dev.txt` (`ipykernel`) in de hoofdmap gezet; `ml/requirements.txt` verwijderd.
- README aangevuld met de stappen om de pipeline te draaien en de definitie van de populariteitsscore.

**Planning tegenover werkelijkheid**
- Gepland: pipeline klaar op 5 oktober, daarna de API van 6 tot 12 oktober.
- Werkelijk: de pipeline was op 8 oktober klaar (inclusief controle), de API is nog niet gestart.

**Waar liep ik vast**
- Bij de controle bleek dat 506 klanten alleen artikels uit de categorie `Unknown` kochten. Omdat gold `Unknown` uitsluit, hebben ze 0 categorieën en lijken ze op klanten die nooit iets kochten. Een van de drie demo-klanten met 0 categorieën is zo'n klant (zie technische keuzes).

**Technische keuzes**

*Inhoud van gold*
- `gold.category_popularity`: per categorie het aantal unieke kopers. De `popularity_score` is dat aantal gedeeld door het aantal kopers van de grootste categorie, dus tussen 0 en 1. Het is geen kans dat een klant iets koopt.
- `gold.customer_categories`: per klant de categorieën die die al kocht, met de eerste aankoopdatum en het aantal aankopen.
- `gold.customers`: alle klanten, ook wie nooit iets kocht. Zo kan de API een onbekende klant (`404`) onderscheiden van een bestaande klant zonder aankopen.
- `gold.example_customers`: telkens drie klanten met 0, 1, 2 tot 3 en 4 of meer gekochte categorieën, gekozen op laagste `customer_id`. Elke run geeft dus dezelfde demo-klanten, en omdat het ID een hash is, is die keuze in de praktijk willekeurig.

*Categorieën*
- `Unknown` en lege categorieën worden in gold uitgesloten: een aanbeveling "Unknown" is niet bruikbaar.
- Heel kleine categorieën (bijvoorbeeld `Fun` met 5 kopers) blijven staan. Door hun lage score komen ze altijd onderaan de ranking.

*Klanten met alleen `Unknown`-aankopen*
- De 506 klanten die alleen `Unknown` kochten, krijgen dezelfde aanbevelingen als klanten die nooit iets kochten. Gold scheidt die twee groepen daarom niet.
- De API mag wel niet zeggen dat zo'n klant nooit iets kocht. De melding wordt "geen aankopen in een aanbeveelbare categorie". Dat staat nu in `03_gold.ipynb` en in `CLAUDE.md`/`AGENTS.md`.

*Incrementeel laden in gold*
- `gold.source_log` onthoudt welke silver-versie gold verwerkte. Is silver niet veranderd, dan slaat gold alles over.
- Is silver wel veranderd, dan berekent gold alle tabellen opnieuw. Silver-transacties houden hun bronbestand niet bij, dus gold kan niet per bestand bijwerken. Voor 18 categorieën en één momentopname is volledig herberekenen eenvoudig en correct.
- Dit wijkt af van het oorspronkelijke plan "`MERGE` voor alle gold-tabellen": de code doet wel een `MERGE`, maar na het leegmaken van de tabellen werkt dat in de praktijk als volledig herladen.
- Het herberekenen en het bijwerken van `gold.source_log` gebeuren in één transactie.

*Geen sterschema*
- Gold is geen sterschema met feiten- en dimensietabellen. Gold heeft één gebruiker, de API, en bevat daarom kleine tabellen die precies op de aanbevelingsvraag zijn afgestemd. Een sterschema is vooral nuttig voor BI-analyse en zou hier extra joins toevoegen. De opdracht vraagt er ook niet om. Bij het optionele dashboard in Milestone 4 bekijk ik dit opnieuw.

*Scripts*
- Elk script heeft een `main()`-functie, sluit de databaseverbinding altijd (ook bij een fout) en kan apart draaien. `--full-refresh` bouwt een laag opnieuw op.
- De controles staan één keer in `check_quality.py`. De scripts gebruiken ze na het laden, en het bestand kan ook alleen draaien om een bestaande database read-only te controleren.

*Voor Milestone 4*
- De populariteit gebruikt nu alle data tot september 2020. Om de baseline eerlijk met het gepersonaliseerde model te vergelijken, moet ik ze opnieuw berekenen met alleen data tot de referentiedatum, anders lekt er informatie uit de toekomst in.

**Volgende stap**
- `run_pipeline.py` twee keer draaien om te tonen dat de scripts idempotent zijn.
- `01_bronze.ipynb` opnieuw draaien en opslaan met uitvoer.
- Silver, gold en de scripts committen op `feature/notebook-pipeline`.
- Beginnen aan de C#-API: project, `GET /health`, read-only DuckDB-verbinding en de repository.

## Sessie 4: 8 oktober 2026

**Gepland**
De pipeline committen en pushen, en de C#-API starten.

**Gedaan**
- De pipeline in kleine commits op `feature/notebook-pipeline` gezet en gepusht: de genummerde secties in het bronze-notebook, het silver-notebook, het gold-notebook, de pipeline-scripts met de requirements, en de bijgewerkte projectregels en het logboek.
- Pull Request #1 gemerged in `main`.
- `run_pipeline.py` twee keer gedraaid: elke laag meldde "up to date", alle 43 controles slaagden en het databasebestand bleef ongewijzigd. De scripts zijn dus idempotent, net als de notebooks.
- De DuckDB CLI geïnstalleerd (`winget install DuckDB.cli`) om de database te bekijken in de browser met `duckdb -readonly data\crossselliq.duckdb -ui`.
- API stap 1: een ASP.NET Core-project (.NET 10) in `backend/CrossSellIQ.Api` en een solution-bestand `CrossSellIQ.slnx` in de hoofdmap, met `GET /health`.
- API stap 2: een read-only DuckDB-verbinding (DuckDB.NET 1.5.6, dezelfde versie als de pipeline). `/health` controleert nu ook of de gold-tabellen leesbaar zijn.
- Getest: met de juiste database geeft `/health` `200 Healthy`; met een verkeerd pad `503 Unhealthy`; met een leeg pad start de API niet. Terwijl de API draait, kan de pipeline de database nog openen om te schrijven.
- De werking van de 506 klanten met alleen `Unknown`-aankopen vastgelegd in `03_gold.ipynb`, `CLAUDE.md` en `AGENTS.md`.

**Waar liep ik vast**
- Pull Request #1 bevatte alleen de bronze-commit, omdat de andere commits toen nog niet gemaakt waren. De rest gaat via een tweede Pull Request naar `main`.
- Na `winget install DuckDB.cli` herkende de terminal het commando `duckdb` niet. Windows had het pad aangepast, maar een terminal die al openstond, ziet dat pas na een herstart.
- In `.gitignore` stond `data/`. Die regel geldt voor elke map met die naam, op elk niveau, en omdat Windows geen onderscheid maakt tussen hoofdletters en kleine letters, negeerde Git ook de map `Data/` van de API. De API-code zou dus nooit in Git terechtkomen. Opgelost met `/data/`, zodat alleen de datamap in de hoofdmap genegeerd wordt.

**Technische keuzes**

*Opbouw van de API*
- Lagen: Controller, Service, Repository, database. Elke laag heeft één taak, en de controller bevat geen SQL.
- Het lege `web`-sjabloon in plaats van `webapi`, zodat er geen voorbeeldcode in zit die ik later moet weghalen.
- Een solution-bestand in de hoofdmap, zodat `dotnet build` en `dotnet test` met één commando werken. Dat is ook nodig voor GitHub Actions in Milestone 2.

*Health check*
- `/health` gebruikt de ingebouwde health checks van ASP.NET Core. Docker (Milestone 2) en Azure (Milestone 3) kunnen dat endpoint gebruiken om te zien of de app werkt.
- Bij een fout ziet de buitenwereld alleen `Unhealthy`. De details (pad en foutmelding) staan in de serverlog.

*Databaseverbinding*
- Het pad naar de database staat in `appsettings.json` en niet in de code. In Docker kan ik het overschrijven met de omgevingsvariabele `Database__Path`.
- Een leeg pad is een configuratiefout: de API stopt dan meteen bij het opstarten. Een pad naar een ontbrekend bestand laat de API wel starten, maar `/health` geeft dan `503`. Zo zie je wat er mis is.
- De verbinding is read-only: de API kan de database technisch niet wijzigen.
- Elke aanvraag opent een eigen verbinding en sluit die meteen. Zo blokkeert een draaiende API de pipeline niet.

**Volgende stap**
- API stap 3 tot 6: repository, service en endpoint, foutafhandeling en tests.
- De webpagina en de README.

## Sessie 5: 10 oktober 2026

**Gepland**
De rest van de API (repository, service, endpoints, foutafhandeling, tests), de webpagina en de README.

**Gedaan**
- API stap 3, de repository: `IRecommendationRepository` met de implementatie `DuckDbRecommendationRepository`. Die leest uit gold of een klant bestaat, de populariteit per categorie, de gekochte categorieën van een klant en de demo-klanten. Alle SQL gebruikt parameters.
- API stap 4, de service en de endpoints: `GET /api/recommendations/{customerId}?limit=5` en `GET /api/example-customers`.
- API stap 5, de foutafhandeling: `400` bij een ongeldig ID of een ongeldige `limit`, `404` bij een onbekende klant, `503` als de database niet bereikbaar is, en een melding als een klant geen aanbeveelbare aankopen heeft of al alle categorieën kocht. Daarnaast beveiligingsheaders, waaronder een Content Security Policy.
- API stap 6: een testproject `tests/CrossSellIQ.Api.Tests` met 24 tests. Alle 24 slagen.
- Stap 7: een webpagina in `wwwroot` met een invoerveld, 12 demo-klanten, een tabel met aanbevelingen en score, de al gekochte categorieën, en laad- en foutmeldingen.
- Stap 8: de README herschreven, van clonen tot demo, met de API-endpoints en de definitie van de score.
- Tegen de echte database getest. Een klant met 7 gekochte categorieën kreeg 5 nieuwe, zonder één al gekochte. Een klant zonder aanbeveelbare aankopen kreeg de populairste categorieën met een melding. Een ID in hoofdletters werkte, `abc` gaf `400`, een onbekend ID `404`, en een verkeerd databasepad `503`.
- De webpagina in de browser getest, ook op een mobiele breedte (390 pixels): geen fouten in de console, geen overtredingen van de Content Security Policy, en geen horizontaal scrollen.
- De map `backend` hernoemd naar `src`, en de lege map `frontend` verwijderd. De API staat nu in `src/CrossSellIQ.Api`; het solution-bestand, het testproject en de README zijn aangepast.

**Planning tegenover werkelijkheid**
- Gepland: de API van 6 tot 12 oktober, de webpagina en README op 13 en 14 oktober.
- Werkelijk: de API, de webpagina en de README stonden op 10 oktober. De achterstand van de pipeline is daarmee ingehaald.

**Waar liep ik vast**
- Ik heb `git add backend/` gecommit terwijl stap 3 tot 5 al in de map stonden. Commit `39bfe37` ("Add API project with health endpoint and read-only DuckDB connection") bevat daardoor ook de repository, de service en de foutafhandeling. Bovendien verwijst `CrossSellIQ.slnx` in die commit al naar het testproject, dat er nog niet in zit, waardoor `dotnet build` op precies die commit faalt. Ik heb de commit niet herschreven, omdat hij al gepusht was. De volgende commit voegt de tests toe, en daarmee bouwt het project weer.
- Op de webpagina stond bij de demo-klanten eerst "0 categories bought". Dat klopt niet voor de klant die alleen `Unknown` kocht, en het is hetzelfde probleem als bij de API-melding. Aangepast naar "No recommendable purchases yet".

**Technische keuzes**

*De logica zit in de service, niet in de SQL*
- De repository haalt ruwe gegevens op: de 18 categorieën met hun score, en de categorieën die de klant al kocht. De service sluit de gekochte categorieën uit, sorteert en beperkt het aantal.
- Zo test ik de echte baseline-logica zonder database. Het gaat om zo weinig rijen dat het geen verschil in snelheid maakt.

*Validatie*
- Een klant-ID moet uit precies 64 hexadecimale tekens bestaan. Spaties en hoofdletters worden eerst opgevangen.
- De controle gebeurt vóór er SQL draait. Een poging tot SQL-injectie geeft dus al een `400`, en de SQL gebruikt daarnaast toch parameters.
- `limit` ligt tussen 1 en 20, standaard 5.

*Klanten zonder aanbeveelbare aankopen*
- Dat is geen fout: ze krijgen `200`, de populairste categorieën en de melding "no purchases in a recommendable category". Die melding klopt zowel voor de 9.699 klanten die nooit iets kochten als voor de 506 klanten die alleen `Unknown` kochten.

*Database niet bereikbaar*
- Een centrale handler zet elke databasefout om in `503`. Hij reageert op `DbException`, de gemeenschappelijke basisklasse van databasestuurprogramma's in .NET, zodat het ook werkt als ik later PostgreSQL gebruik.
- De oorzaak staat alleen in de serverlog, niet in het antwoord.

*Antwoord van de API*
- Naast de afgesproken velden (`customerId`, `recommendations` met `category`, `score` en `reason`) geeft de API ook `purchasedCategories` en `message` terug. Zo zie je in de demo meteen dat al gekochte categorieën nooit aanbevolen worden.

*Tests*
- De tests gebruiken een nep-repository met vaste gegevens in plaats van de database. Ze werken dus ook in GitHub Actions (Milestone 2), waar de database van 3 GB niet staat.
- Twee soorten tests: tests van de service (de baseline-logica) en tests van de hele HTTP-route met `WebApplicationFactory` (statuscodes, foutafhandeling).
- In de nep-gegevens staan de categorieën bewust niet gesorteerd, zodat de test bewijst dat de service sorteert.

*Webpagina*
- Gewone HTML, CSS en JavaScript, zonder framework, geserveerd door de API zelf. Eén project en één URL maken Docker en Azure eenvoudiger.
- Alle gegevens uit de API worden met `textContent` op de pagina gezet, nooit met `innerHTML`. Zo kan data uit de API nooit als HTML of script uitgevoerd worden (bescherming tegen XSS).
- De Content Security Policy laat alleen scripts en stijlen van de eigen site toe. Daarom staan JavaScript en CSS in aparte bestanden.
- Toegankelijkheid: labels bij elk veld, zichtbare focus, foutmeldingen die een schermlezer voorleest, en na een zoekopdracht gaat de focus naar de resultaten.

*Mapnamen: `src` in plaats van `backend` en `frontend`*
- De webpagina staat in `wwwroot`, de standaardmap van ASP.NET voor statische bestanden, en wordt door de API zelf geserveerd. Daardoor bevatte de map `backend` ook de frontend, en bleef de map `frontend` leeg.
- `src` (de broncode van de applicatie, naast `tests`) is de gebruikelijke naam in .NET-projecten en beschrijft de inhoud correct. Komt er in Milestone 4 een apart dashboard met een framework, dan kan een aparte frontend-map opnieuw zinvol worden.

**Volgende stap**
- De tests, de webpagina en de README committen en pushen.
- Eindtest: de repository in een lege map clonen en alles opstarten met alleen de README.
- Pull Request #2 naar `main`.

## Leerpaden en certificaten

- AZ-900 (Microsoft Azure Fundamentals) leerroute: gepland als voorbereiding op Milestone 3.
