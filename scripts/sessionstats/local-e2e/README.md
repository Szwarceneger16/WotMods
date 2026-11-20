# Session Stats — lokalne testy E2E

Chromium ładuje rzeczywisty HTML, CSS i JavaScript moda. Kod Pythona liczy statystyki, filtruje zakresy i odpowiada na polecenia panelu. Dane i usługi okna WoT są symulowane. Przebieg działa bez uruchamiania gry i bez logowania.

## Instalacja na Windows x64

1. Zainstaluj Node.js 22 lub nowszy. Możesz wybrać linię 24 LTS i instalator x64. [Pobierz Node.js](https://nodejs.org/en/download)
2. Zainstaluj Python 3 x64 i dodaj go do `PATH`. Przebieg sprawdzono na Pythonie 3.12.14. [Pobierz Pythona dla Windows](https://www.python.org/downloads/windows/)
3. W PowerShellu przejdź do katalogu zawierającego ten plik i wykonaj poniższe polecenia. Pakiet `tzdata` dostarcza strefę `Europe/Warsaw` także na Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SESSIONSTATS_PYTHON = (Resolve-Path .\.venv\Scripts\python.exe).Path
npm.cmd install
```

Skrypt PowerShell wykrywa Edge w standardowej lokalizacji. Możesz też zainstalować Chromium dostarczane przez Playwright albo podać ścieżkę do przeglądarki jako `--chrome`. [Instalacja przeglądarek Playwright](https://playwright.dev/docs/browsers)

```powershell
npx.cmd playwright install chromium
```

## Lokalne zasoby WoT i anonimowy profil

Instalacja wymagania `requirements-local-assets.txt` dodaje Pillow do konwersji grafik map. Tryb lokalny odczytuje wprost z pakietów WoT oba fonty Warhelios i fabryczne grafiki dobrane do fikcyjnych map i pojazdów. Pakiety są otwierane tylko do odczytu. Fonty i grafiki trafiają do tymczasowego katalogu renderera i są kasowane po zakończeniu.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-local-assets.txt
```

Opcjonalny eksporter odczytuje zweryfikowaną lokalną historię i zapisuje szerokie przedziały statystyk po odrzuceniu rzadkich wartości. Backend losuje z przedziałów fikcyjne bitwy. Profil przechowuj poza repozytorium. Powstałe daty, identyfikatory, nazwy i kwoty są fikcyjne. Grafikę przypisuje numer testowego pojazdu lub mapy.

```powershell
$profil = Join-Path $env:LOCALAPPDATA 'SessionStatsQA/profil-lokalny.json'
New-Item -ItemType Directory -Path (Split-Path -Parent $profil) -Force
.\.venv\Scripts\python.exe -B anonymize_history.py --output $profil
.\run-local.ps1 -Suite smoke -Profile $profil
.\run-local.ps1 -Suite full -Profile $profil
```

Możesz wskazać inną instalację parametrem `-GameClient`. Raporty z lokalnym profilem lub grafikami powstają domyślnie w `%LOCALAPPDATA%/SessionStatsQA/runs/`. Zapis takich raportów wewnątrz checkoutu Git jest blokowany.

## Uruchamianie na żądanie

Sprawdź rozmiar i zakres konfiguracji bez uruchamiania renderera.

```powershell
node run.cjs --suite full --plan
```

Chromium jest domyślnym silnikiem. `build` sprawdza osiem przypadków i podstawowe interakcje, `smoke` rozszerza próbę na kilka szerokości i oba główne zakresy.

```powershell
node run.cjs --engine chromium --suite smoke
node run.cjs --engine chromium --suite full --chrome 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
```

PowerShellowy `-Suite full` obejmuje wszystkie warianty sortowania we wszystkich przygotowanych zakresach. Przy bezpośrednim użyciu Node odpowiada mu `--suite full --all-ranges`. Sama opcja `--suite full` ogranicza sortowanie w mniej typowych zakresach do chronologii. Podstawowe widoki mają wysokość 730 lub 900 px i maksymalnie trzy ruchy kółkiem. Osobne scenariusze obejmują menu, kalendarz, rozwinięte szczegóły i powrót z wybranej bitwy.

Pełna macierz wymaga dużo czasu i miejsca na dysku. Opcja `-FinalOnly` zachowuje wynik każdego przypadku i sprawdza wszystkie pozycje przewijania, a na dysku zapisuje końcowy zrzut JPEG lub zrzut błędu.

```powershell
.\run-local.ps1 -Suite full -Plan -Profile $profil
node run.cjs --engine chromium --suite full --widths 365,780 --heights 730,900 --ranges history,since-sunday --languages en,pl --limit 40
node run.cjs --engine chromium --suite smoke --source '../WotMods-pr17-next/mods/sessionstats' --python 'C:/Python312/python.exe'
```

`--source` wskazuje katalog `mods/sessionstats` z wybranego checkoutu. W repozytorium przebieg znajduje go automatycznie. W osobnym katalogu szuka też sąsiedniego `WotMods-pr17-next`. `--python` zastępuje ścieżkę z `SESSIONSTATS_PYTHON` lub polecenie `python`. W nowej sesji PowerShell ustaw `$env:SESSIONSTATS_PYTHON` ponownie, jeśli korzystasz z `.venv`. Pełną listę opcji wyświetla `node run.cjs --help`.

## GitHub Actions

Zwykły build uruchamia krótki zestaw w Chromium. Po scaleniu workflow **Session Stats Chromium matrix** do domyślnej gałęzi uruchom go nowym komentarzem na otwartym PR z gałęzi tego repozytorium. Sam komentarz `/sessionstats-matrix` obejmuje wszystkie warianty sortowania we wszystkich przygotowanych zakresach dat. `/sessionstats-matrix smoke` sprawdza raport na krótkiej próbie, a `/sessionstats-matrix full` sprawdza pełne sortowanie w głównych zakresach dat. Wynik pojawi się w Actions jako **Session Stats matrix · PR #…**.

Każdy przebieg CI korzysta z fikcyjnych danych i grafik testowych. Job scalający publikuje `index.html`, `catalog.js` i odnośne zrzuty, w tym dostępne wyniki przy niepełnym przebiegu. Po rozpakowaniu artefaktu otwórz `index.html`. Pełna macierz na runnerze zapisuje ostatnią fazę każdego przypadku, a domyślny przebieg lokalny zapisuje wszystkie cztery.

## Raporty i porównania

Polecenie wypisuje ścieżkę do nowego katalogu. Otwórz `index.html`, żeby przejrzeć przypadki i zrzuty. `run.json` zapisuje wersję i podsumowanie. `results.ndjson` zawiera wyniki pojedynczych przypadków i pomiary. `-OutputDirectory` lub `--out` pozwala wskazać nowy katalog.

Po obejrzeniu pierwszego przebiegu możesz użyć go jako wzorca. Następny przebieg uruchom z tym samym rendererem, wersją, źródłem danych i grafik, wymiarami i zakresem. `--threshold 0.002` dopuszcza domyślnie do 0,2% różniących się pikseli. Porównanie pomija wnętrze pola z bieżącym czasem w nagłówku. Dla różnic ponad próg raport zapisuje zrzut, wzorzec i obraz różnic.

```powershell
node run.cjs --engine chromium --suite smoke --out 'runs/wzorzec'
node run.cjs --engine chromium --suite smoke --baseline 'runs/wzorzec' --out 'runs/porownanie'
```

Test w Gameface Playerze sprawdza rysowanie panelu i obsługę poleceń w symulowanym oknie. Dokładny czas i zachowanie podczas przeciągania okna wewnątrz WoT zależą też od integracji gry.

## Budowa paczki moda

Do kompilacji wersji instalacyjnej istniejący `tools/build.py` potrzebuje dodatkowo **CPython 2.7.18**. Uruchom polecenie z tego samego katalogu i wskaż właściwą ścieżkę do interpretera. Wynik pojawi się w `dist/` katalogu moda. [Pobierz CPython 2.7.18](https://www.python.org/downloads/release/python-2718/)

```powershell
python ../WotMods-pr17-next/mods/sessionstats/tools/build.py --python27 'C:/Python27/python.exe' --client-version 2.4.1.1
```
