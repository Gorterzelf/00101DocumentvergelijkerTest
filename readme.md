# 📄 DocumentvergelijkerTest (Grok)

Een AI-ondersteunde tool voor beleidsanalyse, gericht op documentvergelijking, standpuntvergelijking, externe reacties en communicatiestrategie.

---

## 📦 Functionaliteit
De applicatie bestaat uit **vier modules**:

### 1. 📊 Versie Vergelijking
Vergelijkt twee versies van een beleidsdocument en identificeert de inhoudelijke verschillen.

### 2. 🎯 ActiZ Positie Analyse
Toetst hoe ActiZ-standpunten zich verhouden tot nieuw of gewijzigd beleid.

### 3. 💬 Externe Reactie Analyse
Analyseert reacties van derden op beleidsvoorstellen en identificeert sentiment en zorgpunten.

### 4. 🚀 Strategische Communicatie
Combineert beleidsdocumenten, communicatieplannen en stakeholder-input voor één communicatiestrategie.

---

## 📁 Projectstructuur

```bash
00101DocumentvergelijkerTest/
├── .gitignore
├── .env                # (uitgesloten van repo, bevat API-sleutels)
├── README.md           # Dit bestand
├── requirements.txt    # Python-dependencies
├── web_app.py          # Main Flask-applicatie
├── templates/          # HTML UI-templates
│   └── index.html      # UI met 4 analyse-vakken (zoals op screenshot)
├── static/
│   ├── style.css       # Styling in ActiZ-kleuren
├── logic/
│   ├── version_compare.py       # Vergelijking 2 versies beleidsdocument
│   ├── position_analysis.py     # Analyse t.o.v. ActiZ-visie
│   ├── external_analysis.py     # Analyse externe reacties
│   ├── strategy_analysis.py     # Analyse communicatiestrategie
│   └── utils.py                 # Algemene hulpfuncties (tekstextractie, PDF, enz.)
```

---

## 🚀 Installatie & Uitvoering

```bash
# 1. Clone deze repo
https://github.com/Gorterzelf/00101DocumentvergelijkerTest.git

# 2. (Optioneel) Maak een virtuele omgeving
python -m venv .venv
.venv\Scripts\activate

# 3. Installeer packages
pip install -r requirements.txt

# 4. Start de applicatie
python web_app.py
```

Ga dan naar `http://localhost:5000` in je browser.

---

## 📌 Let op
- `.env` wordt automatisch genegeerd dankzij `.gitignore`.
- De tool is in ontwikkeling — inhoudelijke validatie gewenst bij gebruik.

---

## 🤝 Mede mogelijk gemaakt door
ActiZ — team Digitaal Denken en Doen
