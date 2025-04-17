from flask import Flask, render_template, request, jsonify, session
import requests
import re
import os

app = Flask(__name__)
# Use a fixed secret key so session persists across code reloads
app.secret_key = 'your_fixed_secret_key_here'

@app.route('/', methods=['GET'])
def index():
    # Render the custom chat interface
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = (data.get('question') or '').strip()
    # Инициализируем или получаем историю из сессии
    history = session.get('history', [])
    # Определяем сообщения для отправки
    if question.lower().startswith('контекст:'):
        args = question[len('контекст:'):].strip()
        parts = args.split(' ', 1)
        identifier = parts[0]
        new_q = parts[1] if len(parts) > 1 else ''
        # Ищем предыдущий ответ ассистента по началу текста
        match = next((m for m in history if m['role'] == 'assistant' and m['content'].strip().startswith(identifier)), None)
        if match:
            messages_list = [
                {'role': 'assistant', 'content': match['content']},
                {'role': 'user', 'content': new_q}
            ]
        else:
            messages_list = [{'role': 'user', 'content': new_q}]
        # Сохраняем новый вопрос в историю
        history.append({'role': 'user', 'content': new_q})
    else:
        messages_list = [{'role': 'user', 'content': question}]
        history.append({'role': 'user', 'content': question})
    # Сохраняем историю обратно в сессии
    session['history'] = history
    # Формируем payload с системным сообщением
    payload = {
        'model': 'claude-3-7-sonnet-20250219',
        'system': 'You are a helpful assistant.',
        'messages': messages_list,
        'max_tokens': 8192
    }
    url = "https://api.langdock.com/anthropic/eu/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-ImZqt0rKS_OGU_znzFQnMS_KNDiQ2hjAt9VkvU1xUkGDMYU5H-urjgUsP7pvIMbVO6yv97Ia8tJuAqeQv_COZQ"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        content = response_data.get("content")
        if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict) and "text" in content[0]:
            answer = content[0]["text"]
        else:
            answer = str(content)
        # Сохраняем ответ ассистента в истории
        session['history'].append({"role": "assistant", "content": answer})
        # Автоматически оборачиваем большие куски кода в markdown-блоки
        def code_block_replacer(match):
            return f"\n```python\n{match.group(0).strip()}\n```\n"
        answer = re.sub(r'((?:^(?:\s*#|\s*import |\s*def |\s*class |\s{4,}).*\n?){3,})', code_block_replacer, answer, flags=re.MULTILINE)
    else:
        answer = f"Ошибка: {response.status_code}\n{response.text}"
    return jsonify({"answer": answer})

if __name__ == '__main__':
    app.run(debug=True)