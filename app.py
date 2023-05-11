from mongo import initialize_db
from validations import chat_validations
from chat import get_chat, get_dialog_subject
from system_prompt import hr_prompt
from controllers.dialog import Dialog
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
from bson.json_util import dumps
from functools import wraps
from bson import ObjectId
from flask import Flask, jsonify, request
from flask_cors import CORS
import openai
import jwt

app = Flask(__name__)
cors = CORS(app)
app.config.from_pyfile('settings.py')

bcrypt = Bcrypt(app)
openai.api_key = app.config['OPEN_AI_SECRET']

# collections
collections = initialize_db(app)
dialogs_collection = collections["dialogs_coll"]
users_collection = collections["users_coll"]
prompts_collection = collections["prompts_coll"]


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
        except Exception as e:
            return jsonify({'msg': 'Invalid token. error:' + str(e)}), 401

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


@app.route('/user-by-id', methods=['GET'])
@token_required
def getUserById(current_user):
    return jsonify({"user": dumps(current_user)})


@app.route('/chat', methods=['POST'])
@token_required
def chat_initialize(current_user):
    # args
    data = request.get_json()
    question = data['question']
    answer_length = data['answer_length']

    # validations
    res = chat_validations(question, answer_length)
    if res:
        return jsonify({'msg': res}), 400

    # intialize variables
    answer_length = int(answer_length)

    title = get_dialog_subject(question)
    if not title:
        return jsonify({'msg': 'Could not generate a title'}), 500

    dialog = {
        "user_id": current_user["_id"],
        "title": title,
        "chat": [
            {"role": "system", "content": hr_prompt,
             "created_at": datetime.now()},
            {"role": "assistant", "content": " How can I help you today?",
             "created_at": datetime.now()},
            {"role": "user", "content": question,
             "created_at": datetime.now()}
        ]
    }

    # openai logic
    copy = []
    for message in dialog["chat"]:
        copy.append({"role": message["role"], "content": message["content"]})
    try:
        answer = get_chat(copy, answer_length)
    except Exception as e:
        return jsonify({"msg": "Open Ai error, no answer available, Error: \n" + str(e)}), 500

    # applying the answer
    dialog["chat"].append({"role": "assistant", "content": answer,
                           "created_at": datetime.now()})
    dialog["last_msg"] = datetime.now()

    try:
        res = dialogs_collection.insert_one(dialog)
    except Exception as e:
        return jsonify({"msg": "MongoDB Error: \n" + str(e)}), 500

    dialog["_id"] = res.inserted_id

    return jsonify({"dialog": dumps(dialog)})


@app.route('/chat', methods=['PUT'])
@token_required
def chat(current_user):
    # args
    data = request.get_json()
    question = data["question"]
    dialog = data['dialog']
    answer_length = data['answer_length']

    # validations
    if not dialog or not answer_length:
        return jsonify({'msg': 'Dialog arguments was not provided'}), 400

    dialog_id = dialog["_id"]
    messages = dialog["chat"]

    messages.append({"role": "user", "content": question,
                     "created_at": datetime.now()})

    # openai logic
    answer_length = int(answer_length)
    copy = []
    for message in messages:
        copy.append({"role": message["role"], "content": message["content"]})

    try:
        answer = get_chat(copy, answer_length)
    except Exception as e:
        return jsonify({'msg': 'Open Ai error, no answer available, Error: \n' + str(e)}), 500

    # apply answer
    messages.append({"role": "assistant", "content": answer,
                     "created_at": datetime.now()})

    dialogs_collection.update_one(
        {"_id": ObjectId(dialog_id["$oid"])},
        {"$set": {"chat": messages, "last_msg": datetime.now()}}
    )

    dialog["chat"] = messages
    dialog["last_msg"] = datetime.now()

    return jsonify({'dialog': dumps(dialog)})

# --------------------------------------------------------------------


@app.route("/dialog", methods=['GET'])
@token_required
def get_dialog(current_user):
    # Get the dialog_id from request arguments
    dialog_id = request.args.get('dialog_id')

    if not dialog_id:
        return jsonify({"message": "No dialog_id provided"}), 400

    # Find the dialog with the given dialog_id and user_id
    dialog = dialogs_collection.find_one(
        {"_id": ObjectId(dialog_id), "user_id": current_user["_id"]})

    if not dialog:
        return jsonify({"message": "No dialog found with the specified dialog_id"}), 404

    return jsonify({"dialog": dumps(dialog)})


@app.route("/dialogs", methods=['GET'])
@token_required
def dialogs(current_user):
    pipeline = [
        {"$match": {"user_id": ObjectId(current_user["_id"])}},
        {"$project": {
            "_id": {"$toString": "$_id"},
            "title": 1,
            "last_msg": 1,
            "created_at": 1
        }},
        {"$addFields": {
            "last_msg": {"$dateToString": {"format": "%Y-%m-%dT%H:%M:%S.%LZ", "date": "$last_msg"}}
        }},
        {"$sort": {"created_at": 1}}
    ]
    dialogs_cursor = dialogs_collection.aggregate(pipeline)
    dialogs = list(dialogs_cursor)

    return jsonify({'dialogs': dialogs})


@app.route("/dialogs-delete", methods=['DELETE'])
@token_required
def bulk_delete_dialogs(current_user):
    # Get the array of _ids from request JSON data
    data = request.get_json()
    dialogs_ids = data['dialogs_ids']

    if not dialogs_ids:
        return jsonify({"message": "No ids provided"}), 400

    # Convert string ids to ObjectId instances
    object_ids = [ObjectId(_id) for _id in dialogs_ids]
    # Delete all dialogs with matching _ids and user_id
    try:
        dialogs_collection.delete_many(
            {"_id": {"$in": object_ids}, "user_id": current_user["_id"]})
    except Exception as e:
        return jsonify({"msg": f"Error deleting dialog, error: {e}"})

    return jsonify({"msg": "Deleted successfully"})


if __name__ == '__main__':
    app.run()
