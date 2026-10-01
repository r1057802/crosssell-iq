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

## Leerpaden en certificaten

- AZ-900 (Microsoft Azure Fundamentals) leerroute: gepland als voorbereiding op Milestone 3.
