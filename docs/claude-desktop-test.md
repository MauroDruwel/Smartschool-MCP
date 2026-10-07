# Smartschool uitproberen in Claude Desktop

Dit is een test voor een ouder. Je downloadt één bestand, opent het in Claude Desktop, vult vijf velden in, en stelt daarna een paar vragen. Je hebt geen extra programma nodig.

## 1. Het bestand downloaden

Je zoekt een bestand dat eindigt op `.mcpb`. GitHub stopt dat bestand in een zip.

1. Open de pagina van deze wijziging op GitHub (de link die je kreeg).
2. Klik bovenaan op **Checks**.
3. Klik op de regel **MCPB**.
4. Onderaan de pagina, bij **Artifacts**, download je **smartschool-mcp-mcpb**.
5. Dubbelklik de zip. Daarin zit `smartschool-mcp.mcpb`.

Bewaar dat `.mcpb`-bestand ergens waar je het terugvindt, bijvoorbeeld op het bureaublad.

## 2. Installeren in Claude Desktop

1. Dubbelklik `smartschool-mcp.mcpb`.
2. Claude Desktop opent en toont een venster met vijf velden.
3. Gebeurt dat niet: open Claude Desktop, ga naar **Instellingen**, dan **Extensies**, en kies daar het `.mcpb`-bestand.

De eerste keer heeft Claude internet nodig om de rest van het programma op te halen. Dat kan een minuut duren. Blijf in Claude. Er komt geen zwart venster.

## 3. De velden invullen

| Veld | Wat je typt |
| --- | --- |
| School | Alleen het eerste stuk, bijvoorbeeld `dering`. Het stuk `.smartschool.be` zetten we er zelf achter. Plak je toch `https://dering.smartschool.be`, dan halen we `https://` en `.smartschool.be` eraf. |
| Gebruikersnaam | De gebruikersnaam van het Smartschool-account. |
| Wachtwoord | Het wachtwoord van dat account. |
| Geboortedatum van je kind | `JJJJ-MM-DD`, bijvoorbeeld `2014-03-21`. Dat is de controle die Smartschool bij het inloggen vraagt. |
| Naam van je kind | De voornaam, zoals je die in huis gebruikt. |

Klik daarna op bevestigen. Claude onthoudt het wachtwoord en de geboortedatum versleuteld op deze computer.

## 4. Vragen om te stellen

Wacht tot de extensie aan staat. Stel de vragen één voor één, in gewoon Nederlands. Zet de voornaam van je kind op de plaats van de naam die je invulde.

Een geslaagde test toont gegevens uit Smartschool. Een leeg antwoord kan kloppen (geen taken, geen nieuwe berichten). Een zin met `error` of `LOGIN FAILED` betekent dat de test stopte.

| Vraag | Verwacht resultaat |
| --- | --- |
| Welke kinderen hangen aan dit account? (`get_children`) | De namen van de gekoppelde kinderen, en wie er nu actief is. |
| Zet het account op de naam die ik invulde. (`switch_child`) | Claude wisselt naar dat kind. Daarna gaan rooster en punten over dat kind. |
| Welke vakken heeft dit kind? (`get_courses`) | Een lijst met vakken en leerkrachten. |
| Wat zijn de laatste punten? (`get_results`) | Cijfers, met vak en datum. |
| Welke taken moet dit kind nog maken? (`get_future_tasks`) | Taken, gegroepeerd per dag. |
| Zijn er nieuwe berichten? (`get_messages`) | Berichten met afzender en onderwerp. |
| Wat is het rooster van vandaag? (`get_schedule`) | De lessen van vandaag, met begin- en einduur. |
| Wat staat er de komende weken in de planner? (`get_planned_elements`) | Planneritems over meerdere dagen. |
| Welke periodes zijn er dit schooljaar? (`get_periods`) | De periodes of trimesters, met datums. |
| Welke rapporten staan er? (`get_reports`) | De rapporten die de school heeft klaargezet. |
| Welke links voor leerlingenbegeleiding zijn er? (`get_student_support_links`) | De zichtbare links van de school. |
| Wat staat er in de kijker op de startpagina? (`get_homepage_blocks`) | Blokken zoals een maandmenu of een aankondiging, vaak met een foto. |

Pas daarna, als een bericht of een blok een bijlage of foto heeft:

| Vraag | Verwacht resultaat |
| --- | --- |
| Welke bijlagen heeft dat bericht? (`get_attachments`) | De namen van de bestanden bij dat ene bericht. |
| Sla die bijlage op. (`download_attachment`) | Het bestand staat in de map Downloads, in een map `smartschool`. |
| Sla die foto van de startpagina op. (`download_homepage_image`) | De foto staat in diezelfde map Downloads. |

## 5. Als inloggen mislukt

Stop. Stel de vraag niet opnieuw.

Een fout wachtwoord kan het Smartschool-account van de school blokkeren. Deze extensie stuurt het wachtwoord daarom één keer. Lukt dat niet, dan schrijft ze een bestand met de naam `auth_failed` en stuurt ze het wachtwoord niet nog een keer. Ook een antwoord dat op de inlogpagina blijft, inclusief een adres met `error=1`, telt als die ene mislukte poging.

Je herkent de stop aan de zin **LOGIN FAILED, niet opnieuw proberen**, met het pad naar dat bestand.

Zo ga je verder:

1. Verbeter het wachtwoord of de geboortedatum in Claude Desktop: **Instellingen**, **Extensies**, **Smartschool**.
2. Gooi het bestand `auth_failed` weg. Het staat in een map op je computer. De mapnaam is de Smartschool-gebruikersnaam, niet de voornaam van je kind.

Op een Mac:

1. Open Finder.
2. Klik in de menubalk op **Ga**, dan **Ga naar map**.
3. Plak `~/.cache/smartschool` en druk op Return.
4. Open de map met de gebruikersnaam.
5. Sleep `auth_failed` naar de prullenbak.

Op Windows:

1. Open Verkenner.
2. Klik op de adresbalk.
3. Plak `%USERPROFILE%\.cache\smartschool` en druk op Enter.
4. Open de map met de gebruikersnaam.
5. Verwijder `auth_failed`.

3. Sluit Claude Desktop helemaal. Op een Mac: menu **Claude**, **Stop Claude**. Op Windows: klik met de rechtermuisknop op het Claude-icoon naast de klok en kies afsluiten. Open Claude daarna opnieuw.
4. Stel één testvraag.

Heb je het wachtwoord al een paar keer op de Smartschool-website geprobeerd, dan kan de school het account zelf geblokkeerd hebben. Het bestand wissen maakt dat niet ongedaan. Neem contact op met de school en probeer het wachtwoord niet verder.
