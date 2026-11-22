# KrishiMitra AI – All-in-One Farming Assistant

A beginner-friendly Flask web application for a student project. It uses **one AI provider: Google Gemini API**.

## Features

- KrishiBot farming chatbot (Hindi or English prompts supported)
- Crop recommendation from location, soil type, season and pH
- Crop leaf image analysis (possible issues only; not a confirmed diagnosis)
- General fertilizer guidance
- Smart irrigation guidance
- Weather-based advice using weather details entered by the user
- SQLite history of recent AI reports
- Responsive green-and-white dashboard

## Technology

- Frontend: HTML, CSS, JavaScript
- Backend: Python Flask
- AI: Google Gemini API through the official `google-genai` Python SDK
- Database: SQLite

## 1. Requirements

Install Python 3.10 or newer. You also need an internet connection and a Gemini API key.

Create a key in Google AI Studio: https://aistudio.google.com/apikey

**Never paste your API key into HTML or JavaScript, and never share it in screenshots or messages.**

## 2. Open the project

Extract the ZIP file. Open the `KrishiMitra-AI` folder in VS Code or another editor.

## 3. Create a virtual environment

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Install packages

```bash
pip install -r requirements.txt
```

## 5. Configure Gemini

Make a copy of `.env.example` and name the copy `.env`.

Open `.env` and replace the placeholder with your own key:

```env
GEMINI_API_KEY=your_real_key_here
GEMINI_MODEL=gemini-2.5-flash
```

If this model is not available to your account, choose an available Flash model in Google AI Studio and update `GEMINI_MODEL`.

## 6. Run the project

```bash
python app.py
```

Open this address in your browser:

http://127.0.0.1:5000/

The SQLite database `krishimitra.db` is created automatically on first run.

## 7. Test each feature

1. Open Crop Recommendation and enter sample farm details.
2. Upload a clear JPG/PNG/WEBP leaf photo in Leaf Health Check.
3. Try Fertilizer Assistant and Smart Irrigation with crop and soil details.
4. Enter weather information manually in Weather-Based Advice.
5. Ask KrishiBot a question in Hindi or English.
6. Refresh Recent Reports to see saved results.

## Important limitations

- This is a working **student-project MVP**, not a certified agricultural decision system.
- The weather feature does not fetch live weather. It only reasons from weather details typed by the user.
- Leaf analysis gives possible causes, not a guaranteed disease diagnosis.
- Fertilizer and chemical decisions must be checked against a soil test, local crop guidance and a qualified agriculture expert.
- Gemini API usage can have quotas and charges depending on the account and current plan.
- `debug=True` is suitable only for local development. Do not deploy this development server publicly.

## Project structure

```text
KrishiMitra-AI/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── krishimitra.db       # generated automatically
├── uploads/             # temporary image uploads
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## Common errors

**Gemini API key is not configured**
- Confirm the file is named `.env`, not `.env.example`.
- Check that `GEMINI_API_KEY` has a valid key and no extra quotation marks.

**Model not found / model unavailable**
- Select a model available in your Google AI Studio account and update `GEMINI_MODEL` in `.env`.

**Quota or rate-limit error**
- Check current Gemini API quotas and billing in Google AI Studio / Google Cloud.

**Module not found**
- Activate your virtual environment and run `pip install -r requirements.txt` again.
