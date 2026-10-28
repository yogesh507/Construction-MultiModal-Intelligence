# Multimodal Construction Intelligence Platform (Capstone 1)

Streamlit app: PPE safety audit, crack diagnostics, INR planning & valuation, weather-aware site assistant.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Enter a Google Gemini API key in the sidebar for live AI; leave blank for demo mode.

## Deploy (Streamlit Community Cloud)
1. Push `app.py`, `requirements.txt`, `README.md` to a GitHub repo.
2. share.streamlit.io → New app → pick repo → main file `app.py` → Deploy.

No database needed — all state lives in the session.

## Epics
- Epic 2: PPE vision & crack diagnostics (Gemini 1.5 multimodal, JSON contracts)
- Epic 3: Planning & valuation (cost engine, Pollinations render)
- Epic 4: JSON data contracts (see `PPE_PROMPT`, `CRACK_PROMPT`)
- Epic 5: Weather advisory + multi-turn chatbot
- Epic 6: Styled UI, error handling, 1-click deploy
