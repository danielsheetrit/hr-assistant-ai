import openai
from flask import Flask, jsonify, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from datetime import datetime

# local imports
from config import Config
from dialog import Dialog, get_initialized_dialog

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

# access collection
db = client["hr_assistant"]
dialogs_collection = db["dialogs"]


@app.route('/chat')
def chat():
    dialog_id = request.args.get('dialog_id')
    question = request.args.get('question')
    answer_length = request.args.get('answer_length')

    if not answer_length:
        return jsonify({'msg': 'No Answer Length provided'})

    answer_length = int(answer_length)

    if not question:
        return jsonify({'msg': 'No question provided'})

    # create or update dialog logic
    if dialog_id:
        dialog_data = dialogs_collection.find_one({"_id": ObjectId(dialog_id)})

        if not dialog_data:
            return jsonify({'msg': f'Dialog with id {dialog_id} not found.'})

        messages = dialog_data["chat"]
        messages.append(
            {"role": "user", "content": f"{question}", "created_at": datetime.now()})

        dialog = Dialog(subject="Test dialog", chat=messages)
    else:
        initalized_dialog = get_initialized_dialog(question)
        messages = initalized_dialog.get_chat()

    for message in messages:
        message.pop('created_at', None)

    try:
        response = openai.ChatCompletion.create(
            messages=messages,
            model="gpt-3.5-turbo",
            max_tokens=answer_length,
            n=1,
            stop=None,
            temperature=1,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({'msg': 'Open Ai error, no answer available, Error: \n' + str(e)})

    if not dialog_id:
        initalized_dialog.add_message(role="assistant", content=answer)

        dialogs_collection.insert_one(initalized_dialog.to_dict())
        result_chat = initalized_dialog.get_chat()
    else:
        dialog.add_message(role="assistant", content=answer)
        result_chat = dialog.get_chat()

        dialogs_collection.update_one(
            {"_id": ObjectId(dialog_id)},
            {"$set": {"chat": chat, "last_msg": datetime.now()}}
        )

    return jsonify({'chat': result_chat})


if __name__ == '__main__':
    app.run(debug=True)
