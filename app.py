
import os
import io
import time
import base64
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError
from groq import (
    Groq,
    APIStatusError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError
)

# ==========================================
# 1. CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

API_KEY = os.getenv("GROQ_API_KEY", "").strip()
MODEL_NAME = os.getenv(
    "GROQ_MODEL", "qwen/qwen3.8-27b"
).strip()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

DB_PATH = BASE_DIR / "krishimitra.db"
PORT = 5001

client = Groq(
    api_key=API_KEY,
    timeout=45.0,
    max_retries=1
) if API_KEY else None

SYSTEM_PROMPT = """
You are KrishiMitra AI, a helpful agricultural assistant.

Help farmers with:
- Crop recommendations
- Crop health and leaf image analysis
- Fertilizer guidance
- Irrigation planning
- Weather-based farming suggestions
- General agriculture questions

Use simple and practical language.
Respond in the farmer's language.

Never invent current weather, soil test results,
or market prices.

For plant diseases, explain possible causes,
not confirmed diagnoses.

Do not provide unsafe pesticide instructions.
Recommend local agricultural experts for
important treatment decisions.
"""


# ==========================================
# 2. DATABASE
# ==========================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature TEXT NOT NULL,
                user_input TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def save_report(feature, user_input, answer):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO reports
            (feature, user_input, ai_response, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            feature,
            user_input[:5000],
            answer[:15000],
            datetime.now().isoformat(timespec="seconds")
        ))
        conn.commit()


# ==========================================
# 3. IMAGE PROCESSING
# ==========================================

def prepare_image(image_file):
    raw = image_file.read()

    if not raw:
        raise ValueError("Uploaded image is empty.")

    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError(
                    "Only JPG, PNG and WEBP images are allowed."
                )

            image = img.convert("RGB")
            image.thumbnail((1200, 1200))

            buffer = io.BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=80
            )

    except UnidentifiedImageError:
        raise ValueError(
            "Invalid image. Please upload a clear leaf photo."
        )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return f"data:image/jpeg;base64,{encoded}"


# ==========================================
# 4. GROQ AI
# ==========================================

def ask_groq(prompt, image_url=None):

    if not client:
        raise RuntimeError(
            "GROQ_API_KEY missing in .env file."
        )

    if image_url:
        user_content = [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            }
        ]
    else:
        user_content = prompt

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_content
        }
    ]

    for attempt in range(2):
        try:
            print(
                f"Groq request: {MODEL_NAME}, "
                f"attempt {attempt + 1}",
                flush=True
            )

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.5,
                max_completion_tokens=1500
            )

            answer = (
                response.choices[0].message.content or ""
            ).strip()

            if not answer:
                raise RuntimeError(
                    "Groq returned an empty response."
                )

            print("Groq response received!", flush=True)
            return answer

        except APIStatusError as e:
            if (
                e.status_code in (500, 502, 503, 504)
                and attempt == 0
            ):
                time.sleep(2)
                continue
            raise


def generate_and_save(feature, prompt, image_url=None):
    answer = ask_groq(prompt, image_url)
    save_report(feature, prompt, answer)
    return answer


# ==========================================
# 5. ERROR HANDLING
# ==========================================

def handle_error(feature, error):
    app.logger.exception("%s failed", feature)

    if isinstance(error, RateLimitError):
        return jsonify(
            success=False,
            error=(
                "Groq free-tier rate limit reached. "
                "Please wait and try again."
            )
        ), 429

    if isinstance(error, APIStatusError):
        if error.status_code == 401:
            message = "Invalid Groq API key."
        elif error.status_code == 403:
            message = "Groq API access denied."
        elif error.status_code == 404:
            message = (
                f"Model '{MODEL_NAME}' is unavailable "
                "for this account."
            )
        elif error.status_code == 400:
            message = (
                "Groq rejected the request. "
                "Check model access and input."
            )
        elif error.status_code >= 500:
            message = (
                "Groq server is temporarily unavailable."
            )
        else:
            message = "Groq API request failed."

        return jsonify(
            success=False,
            error=message
        ), 502

    if isinstance(
        error,
        (APIConnectionError, APITimeoutError)
    ):
        return jsonify(
            success=False,
            error=(
                "Could not connect to Groq. "
                "Check your internet connection."
            )
        ), 503

    if isinstance(error, ValueError):
        return jsonify(
            success=False,
            error=str(error)
        ), 400

    return jsonify(
        success=False,
        error=(
            "Request failed. "
            "Check the VS Code terminal."
        )
    ), 500


# ==========================================
# 6. HOME
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# 7. CONNECTION TEST
# ==========================================

@app.route("/test-groq")
def test_groq():
    try:
        answer = ask_groq(
            "Say hello as KrishiMitra AI in one sentence."
        )

        return jsonify(
            success=True,
            model=MODEL_NAME,
            answer=answer
        )

    except Exception as e:
        return handle_error("Groq Test", e)


# Keep old test URL working too.
@app.route("/test-gemini")
def old_test_redirect():
    return test_groq()


# ==========================================
# 8. CHATBOT
# ==========================================

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message") or ""
    ).strip()

    if not message:
        return jsonify(
            success=False,
            error="Please enter your question."
        ), 400

    if len(message) > 3000:
        return jsonify(
            success=False,
            error="Message is too long."
        ), 400

    prompt = f"""
You are KrishiBot.

Answer the farmer's question in easy language.

Question:
{message}

Give practical and helpful agricultural advice.
"""

    try:
        answer = generate_and_save(
            "Chatbot", prompt
        )

        return jsonify(
            success=True,
            answer=answer
        )

    except Exception as e:
        return handle_error("Chatbot", e)


# ==========================================
# 9. CROP RECOMMENDATION
# ==========================================

@app.route(
    "/api/crop-recommendation",
    methods=["POST"]
)
def crop_recommendation():
    data = request.get_json(silent=True) or {}

    required = ["location", "soil", "season", "ph"]

    for field in required:
        if not str(data.get(field, "")).strip():
            return jsonify(
                success=False,
                error=f"Please enter {field}."
            ), 400

    try:
        ph = float(data["ph"])
    except (ValueError, TypeError):
        return jsonify(
            success=False,
            error="Invalid soil pH."
        ), 400

    if not 0 <= ph <= 14:
        return jsonify(
            success=False,
            error="Soil pH must be between 0 and 14."
        ), 400

    prompt = f"""
You are a crop recommendation expert.

Farmer details:

Location: {data['location']}
Soil: {data['soil']}
Season: {data['season']}
Soil pH: {ph}
Water Availability: {data.get('water', 'Unknown')}

Suggest 3 suitable crops.

For each crop explain:
1. Crop name
2. Why it may suit the conditions
3. Water needs
4. Basic growing requirements
5. Precautions

Mention that recommendations should be
verified against local conditions.

Use simple language.
"""

    try:
        answer = generate_and_save(
            "Crop Recommendation",
            prompt
        )

        return jsonify(
            success=True,
            answer=answer
        )

    except Exception as e:
        return handle_error(
            "Crop Recommendation", e
        )


# ==========================================
# 10. LEAF DISEASE ANALYSIS
# ==========================================

@app.route(
    "/api/disease-detection",
    methods=["POST"]
)
def disease_detection():
    image_file = request.files.get("leaf_image")

    crop = (
        request.form.get("crop") or "Unknown"
    ).strip()

    notes = (
        request.form.get("notes") or "None"
    ).strip()

    if not image_file or not image_file.filename:
        return jsonify(
            success=False,
            error="Please upload a leaf image."
        ), 400

    try:
        image_url = prepare_image(image_file)

        prompt = f"""
Analyze this crop leaf image.

Crop: {crop}
Symptoms reported by farmer: {notes}

Explain:

1. Visible leaf condition
2. Possible disease or pest problems
3. Possible nutrient deficiency
4. Safe immediate care
5. Prevention tips
6. When to consult an agricultural expert

Do not claim a confirmed diagnosis.
Avoid exact pesticide dosing.
"""

        answer = generate_and_save(
            "Leaf Disease Analysis",
            prompt,
            image_url
        )

        return jsonify(
            success=True,
            answer=answer
        )

    except Exception as e:
        return handle_error(
            "Disease Detection", e
        )


# ==========================================
# 11. FARM ADVICE
# ==========================================

@app.route(
    "/api/farm-advice",
    methods=["POST"]
)
def farm_advice():
    data = request.get_json(silent=True) or {}

    feature = str(
        data.get("feature") or ""
    ).strip()

    details = str(
        data.get("details") or ""
    ).strip()

    allowed_features = {
        "Fertilizer Assistant":
            "Give safe general fertilizer guidance.",

        "Smart Irrigation":
            "Suggest an irrigation plan.",

        "Weather-Based Advice":
            "Give advice based on farmer-provided weather."
    }

    if feature not in allowed_features:
        return jsonify(
            success=False,
            error="Invalid farming feature."
        ), 400

    if len(details) < 8:
        return jsonify(
            success=False,
            error="Please enter farming details."
        ), 400

    prompt = f"""
You are KrishiMitra AI.

Task:
{allowed_features[feature]}

Farmer information:
{details}

Provide simple step-by-step farming advice.

Do not invent weather or soil-test data.

Do not recommend exact fertilizer quantities
without adequate information.
"""

    try:
        answer = generate_and_save(
            feature,
            prompt
        )

        return jsonify(
            success=True,
            answer=answer
        )

    except Exception as e:
        return handle_error(feature, e)


# ==========================================
# 12. HISTORY
# ==========================================

@app.route("/api/history")
def history():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                feature,
                user_input,
                ai_response,
                created_at
            FROM reports
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

    return jsonify(
        success=True,
        reports=[dict(row) for row in rows]
    )


# ==========================================
# 13. UPLOAD ERROR
# ==========================================

@app.errorhandler(413)
def too_large(error):
    return jsonify(
        success=False,
        error="Maximum upload size is 5 MB."
    ), 413


# ==========================================
# 14. START SERVER
# ==========================================

init_db()

if __name__ == "__main__":
    print("\n==============================")
    print("KRISHIMITRA AI - GROQ VERSION")
    print("==============================")
    print("Website: http://127.0.0.1:5001")
    print("Model:", MODEL_NAME)
    print("API Key Loaded:", bool(API_KEY))
    print("==============================\n")

    app.run(
        host="127.0.0.1",
        port=PORT,
        debug=True
    )
