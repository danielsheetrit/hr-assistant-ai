import openai
from flask import Flask, jsonify, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from datetime import datetime

# local imports
from config import Config
from dialog import Dialog
from system_prompt import hr_prompt
from chat import get_chat, get_dialog_subject
from validations import chat_validations

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


@app.route('/chat/initialize')
def chat_initialize():
    # args
    question = request.args.get("question")
    answer_length = request.args.get("answer_length")

    # validations
    res = chat_validations(question, answer_length)
    if res:
        return jsonify({'msg': res})

    # intialize variables
    answer_length = int(answer_length)

    title = get_dialog_subject(question)
    if not title:
        return jsonify({'msg': 'Could not generate a title'})

    dialog = Dialog(subject=title, chat=[])
    dialog.add_message(role="system", content=hr_prompt)
    dialog.add_message(role="assistant", content="How can I help you today?")
    dialog.add_message(role="user", content=question)

    # openai logic
    copy = []
    for message in dialog.chat:
        copy.append({"role": message["role"], "content": message["content"]})
    try:
        answer = get_chat(copy, answer_length)
    except Exception as e:
        return jsonify({"msg": "Open Ai error, no answer available, Error: \n" + str(e)})

    # applying the answer
    dialog.add_message(role="assistant", content=answer)
    dialogs_collection.insert_one(dialog.to_dict())

    return jsonify({"chat": dialog.chat})


@app.route('/chat')
def chat():
    # args
    dialog_id = request.args.get('dialog_id')
    question = request.args.get('question')
    answer_length = request.args.get('answer_length')

    # validations
    res = chat_validations(question, answer_length)
    if res:
        return jsonify({'msg': res})

    if not dialog_id:
        return jsonify({'msg': 'Dialog Id was not provided'})

    # find the dialog in db
    dialog_data = dialogs_collection.find_one({"_id": ObjectId(dialog_id)})
    if not dialog_data:
        return jsonify({'msg': f'Dialog with id {dialog_id} not found.'})

    messages = dialog_data["chat"]

    dialog = Dialog(subject="Test dialog", chat=messages)
    dialog.add_message(role="user", content=question)

    # openai logic
    answer_length = int(answer_length)
    copy = []
    for message in dialog.chat:
        copy.append({"role": message["role"], "content": message["content"]})

    try:
        answer = get_chat(copy, answer_length)
    except Exception as e:
        return jsonify({'msg': 'Open Ai error, no answer available, Error: \n' + str(e)})

    # apply answer
    dialog.add_message(role="assistant", content=answer)
    dialogs_collection.update_one(
        {"_id": ObjectId(dialog_id)},
        {"$set": {"chat": dialog.chat, "last_msg": datetime.now()}}
    )

    return jsonify({'chat': dialog.chat})


if __name__ == '__main__':
    app.run(debug=True)
