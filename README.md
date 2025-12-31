# 🌍 GeoLingo

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal)
![Leaflet](https://img.shields.io/badge/Leaflet-Map-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![Railway](https://img.shields.io/badge/Deployed%20on-Railway-purple)

**GeoLingo** is an interactive world map for exploring how languages are distributed across countries.

> **Explore languages across the globe**

🔗 **Live demo:** https://geolingo.world  

---

## ✨ Features

- 🗺️ Interactive world map (Natural Earth 50m)
- 🔍 Language search with autocomplete
- 🏷️ Multi-language selection using removable chips
- 🌐 Country highlighting by selected languages
- 📊 Country info panel:
  - Country name + flag
  - Multiple official languages
  - Speakers per language
  - Total population
- 🎨 Clean visual style:
  - Invisible borders by default
  - Borders appear only on hover or selection
- 🚀 Production-ready deployment on Railway with HTTPS

---

## 🧠 How It Works

1. **Backend (FastAPI)**  
   - Serves country metadata
   - Calculates language coverage across countries
2. **Frontend (Leaflet + Vanilla JS)**  
   - Renders an interactive world map
   - Handles language search and selection
   - Updates map styles dynamically
3. **Data Layer**  
   - Based on Natural Earth geometry
   - Enriched country/language data (optionally via OpenAI + web search)

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Map Engine:** Leaflet.js
- **Map Data:** Natural Earth (50m)
- **Templates:** Jinja2
- **Deployment:** Railway
- **Optional Enrichment:** OpenAI Responses API + Web Search

---

## 🚀 Run Locally

```bash
git clone https://github.com/nikuznetsov/geolingo.git
cd geolingo

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
uvicorn app:app --reload

Open: http://127.0.0.1:8000
```

##  📜 License

MIT License — free to use, modify, and distribute.

## 🙌 Credits

- Natural Earth — geographic data
- OpenStreetMap & Leaflet ecosystem
- Railway — deployment platform

## Contacts

- 💼 **[LinkedIn](https://www.linkedin.com/in/nikita-kuznetsov-ab196a245/)**
- 📧 **[Email](mailto:nikuznetsoff@gmail.com)** 
- 🐙 **[GitHub](https://github.com/nikuznetsov)** 
