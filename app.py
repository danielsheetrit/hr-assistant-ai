import jwt
import openai
from flask import Flask, jsonify, request
from bson import ObjectId
from functools import wraps
from bson.json_util import dumps
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt

# local imports
from config import Config
from controllers.dialog import Dialog
from system_prompt import hr_prompt
from chat import get_chat, get_dialog_subject
from validations import chat_validations

# mongo
from mongo import initialize_db

app = Flask(__name__)
app.config.from_object(Config)

bcrypt = Bcrypt(app)
openai.api_key = app.config['OPEN_AI_SECRET']

# collections
collections = initialize_db(app)
dialogs_collection = collections["dialogs_coll"]
users_collection = collections["users_coll"]


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]

        if not token:
            return jsonify({'msg': 'Token is missing.'}), 401

        try:
            data = jwt.decode(
                token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one(
                {'_id': ObjectId(data['user_id'])})
        except:
            return jsonify({'msg': 'Invalid token.'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@app.route('/register', methods=['POST'])
def regsiter():
    data = request.get_json()
    name = data['name']
    username = data['username']
    password = data['password']

    if not username or len(password) < 6 or not name:
        return jsonify({"msg": 'One the parameters provided are incorrect'}), 400

    user_from_db = users_collection.find_one({'username': username})
    if user_from_db:
        return jsonify({"msg": 'Username already in use'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = {"name": name, 'username': username, 'password': hashed_password,
            "created_at": datetime.now()}

    users_collection.insert_one(user)

    return jsonify({"msg": 'Register successfully'})


@app.route('/login', methods=['POST'])
def login():
    # get username and password from request
    data = request.get_json()
    username = data['username']
    password = data['password']

    # check if username and password are present
    if not username or not password:
        return jsonify({'msg': 'Username and password are required.'}), 400

    # query database to check if user exists
    user = users_collection.find_one({'username': username})

    if not user:
        return jsonify({'msg': 'Invalid username or password.'}), 401

    # check if password is correct
    if not bcrypt.check_password_hash(user['password'], password):
        return jsonify({'msg': 'Invalid username or password.'}), 401

    # generate JWT token
    payload = {
        'user_id': str(user['_id']),
        'exp': datetime.utcnow() + timedelta(minutes=300)
    }

    token = jwt.encode(
        payload, app.config['JWT_SECRET_KEY'], algorithm="HS256")

    # return JWT token to user
    return jsonify({'token': token, 'user': dumps(user)}), 200


@app.route('/chat/initialize')
@token_required
def chat_initialize(current_user):
    # args
    question = request.args.get("question")
    answer_length = request.args.get("answer_length")

    # validations
    res = chat_validations(question, answer_length)
    if res:
        return jsonify({'msg': res}), 400

    # intialize variables
    answer_length = int(answer_length)

    title = get_dialog_subject(question)
    if not title:
        return jsonify({'msg': 'Could not generate a title'}), 500

    dialog = Dialog(user_id=current_user['_id'], title=title, chat=[])
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
        return jsonify({"msg": "Open Ai error, no answer available, Error: \n" + str(e)}), 500

    # applying the answer
    dialog.add_message(role="assistant", content=answer)
    dialogs_collection.insert_one(dialog.to_dict())

    return jsonify({"chat": dialog.chat})


@app.route('/chat')
@token_required
def chat():
    # args
    dialog_id = request.args.get('dialog_id')
    question = request.args.get('question')
    answer_length = request.args.get('answer_length')

    # validations
    res = chat_validations(question, answer_length)
    if res:
        return jsonify({'msg': res}), 400

    if not dialog_id:
        return jsonify({'msg': 'Dialog Id was not provided'}), 400

    # find the dialog in db
    dialog_data = dialogs_collection.find_one({"_id": ObjectId(dialog_id)})
    if not dialog_data:
        return jsonify({'msg': f'Dialog with id {dialog_id} not found.'}), 500

    messages = dialog_data["chat"]

    dialog = Dialog(user_id="not_important",
                    title="not_important", chat=messages)
    dialog.add_message(role="user", content=question)

    # openai logic
    answer_length = int(answer_length)
    copy = []
    for message in dialog.chat:
        copy.append({"role": message["role"], "content": message["content"]})

    try:
        answer = get_chat(copy, answer_length)
    except Exception as e:
        return jsonify({'msg': 'Open Ai error, no answer available, Error: \n' + str(e)}), 500

    # apply answer
    dialog.add_message(role="assistant", content=answer)
    dialogs_collection.update_one(
        {"_id": ObjectId(dialog_id)},
        {"$set": {"chat": dialog.chat, "last_msg": datetime.now()}}
    )

    return jsonify({'chat': dialog.chat})


if __name__ == '__main__':
    app.run(debug=True)
