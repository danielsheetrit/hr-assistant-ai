import openai
from flask import Flask, jsonify, request

# local imports
from system_prompt import s_prompt
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# openai config
openai.api_key = app.config['OPEN_AI_SECRET']

messages = [
    {"role": "system", "content": f"{s_prompt}"},
    {"role": "assistant", "content": "How can I help you today?"}
]


@app.route('/')
def chat():
    question = request.args.get('question')
    messages.append({"role": "user", "content": f"{question}"})

    response = openai.ChatCompletion.create(
        messages=messages,
        model="gpt-3.5-turbo",
        max_tokens=160,
        n=1,
        stop=None,
        temperature=0.7,
    )
    answer = response.choices[0].message.content.strip()
    messages.append({"role": "assistant", "content": f"{answer}"})

    return jsonify({'data': answer})


app.run()

# if __name__ == '__main__':
#     app.run(debug=True)
