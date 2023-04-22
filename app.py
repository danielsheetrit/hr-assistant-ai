import openai
from flask import Flask, jsonify, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# local imports
from system_prompt import s_prompt
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

openai.api_key = app.config['OPEN_AI_SECRET']
client = MongoClient(app.config['MONGO_URI'], server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("[MONGO_DB] You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# chat route


@app.route('/chat')
def chat():
    question = request.args.get('question')
    if not question:
        return jsonify({'msg': 'No question provided'})

    messages = [
        {"role": "system", "content": f"{s_prompt}"},
        {"role": "assistant", "content": "How can I help you today?"}
    ]

    messages.append({"role": "user", "content": f"{question}"})

    response = openai.ChatCompletion.create(
        messages=messages,
        model="gpt-3.5-turbo",
        max_tokens=200,
        n=1,
        stop=None,
        temperature=1,
    )
    answer = response.choices[0].message.content.strip()
    messages.append({"role": "assistant", "content": f"{answer}"})

    return jsonify({'data': answer})

# dialog route


if __name__ == '__main__':
    app.run(debug=True)
