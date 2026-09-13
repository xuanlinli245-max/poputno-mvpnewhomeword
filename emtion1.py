from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
import logging
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

trips_db = []
next_id = 1

@app.route('/api/mood/analyze', methods=['POST'])
def analyze_mood():
    data = request.json
    diary_text = data.get('diary', '').strip()
    if not diary_text:
        return jsonify({"error": "Напишите дневник"}), 400

    prompt = f"""Ты профессиональный психолог и эксперт по кросс-культурному сопровождению.
Проанализируй дневник пользователя и верни ТОЛЬКО чистый JSON без Markdown.

Пример 1:
Дневник: "Я так устал, полночь, готовлюсь к экзамену. 感觉自己快要挂科了，真的想摆烂。"
Ответ: {{"mental_health_index": 35, "main_emotion": "тревога", "triggers": "академический стресс, страх провала, культурное давление", "analysis": "Смешанный русско-китайский текст указывает на высокую тревожность и признаки выученной беспомощности. Ночная подготовка и страх '挂科' усиливают эмоциональное истощение.", "recommendation": "Сделайте короткий перерыв, выспитесь. Разбейте подготовку на небольшие блоки. Помните: одна неудача не определяет вашу ценность."}}

Пример 2:
Дневник: "Сегодня гулял в парке, пил кофе, читал книгу. Спокойный день."
Ответ: {{"mental_health_index": 82, "main_emotion": "спокойствие", "triggers": "нет явных стрессоров, восстановление ресурсов", "analysis": "Текст отражает стабильное эмоциональное состояние и заботу о себе. Отсутствие стрессовых маркеров указывает на внутренний баланс.", "recommendation": "Сохраняйте этот ритм. Замечайте, что именно даёт вам спокойствие, и возвращайтесь к этим практикам в сложные дни."
{{
    "mental_health_index": число 0-100,
    "main_emotion": "эмоция",
    "triggers": "причины",
    "analysis": "анализ",
    "recommendation": "совет"
}}
Дневник: {diary_text}"""

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 800},
            timeout=30
        )
        result = response.json()
        ai_content = result['choices'][0]['message']['content']
        json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
        mood_data = json.loads(json_match.group())

        # --- 字段校验 ---
        required_fields = ["mental_health_index", "main_emotion", "triggers", "analysis", "recommendation"]
        defaults = {
            "mental_health_index": 50,
            "main_emotion": "спокойствие",
            "triggers": "Не удалось определить",
            "analysis": "Недостаточно данных для анализа",
            "recommendation": "Отдохните и попробуйте снова"
        }
        for field in required_fields:
            if field not in mood_data or mood_data[field] is None or str(mood_data[field]).strip() == "":
                mood_data[field] = defaults[field]

        try:
            mood_data["mental_health_index"] = max(0, min(100, int(mood_data["mental_health_index"])))
        except (ValueError, TypeError):
            mood_data["mental_health_index"] = 50

        for field in ["main_emotion", "triggers", "analysis", "recommendation"]:
            mood_data[field] = str(mood_data[field]).strip()

        return jsonify(mood_data)
    except Exception as e:
        logger.error(f"Analyze error: {e}")
        return jsonify({"mental_health_index": 50, "main_emotion": "спокойствие", "triggers": "Не удалось определить", "analysis": "Попробуйте ещё раз", "recommendation": "Отдохните и повторите"}), 200

@app.route('/api/test-report', methods=['GET'])
def get_test_report():
    import os
    if not os.path.exists('test_report.json'):
        return jsonify({"error": "Отчёт не найден. Запустите test_api.py"}), 404
    with open('test_report.json', 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))
@app.route('/api/trips', methods=['GET'])
def get_trips():
    return jsonify(trips_db)

@app.route('/api/trips', methods=['POST'])
def create_trip():
    global next_id
    data = request.json
    trip = {"id": next_id, "city": data.get('city'), "start_date": data.get('start_date'), "end_date": data.get('end_date'), "created_at": datetime.now().strftime("%d.%m.%Y")}
    trips_db.append(trip)
    next_id += 1
    return jsonify(trip), 201

@app.route('/api/trips/<int:trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    global trips_db
    trips_db = [t for t in trips_db if t['id'] != trip_id]
    return jsonify({"message": "Удалено"})

@app.route('/')
def index():
    return send_file('login.html')

@app.route('/app')
def app_main():
    return send_file('frontend.html')

if __name__ == '__main__':
    print("Сервер запущен: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)