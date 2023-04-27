from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


def initialize_db(app):
    client = MongoClient(app.config['MONGO_URI'], server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("[MONGO_DB] You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

    db = client["hr_assistant"]
    db.write_concern = {'w': 'majority'}
    dialogs_collection = db["dialogs"]
    users_collection = db["users"]
    prompts_collection = db["prompts"]

    return {"dialogs_coll": dialogs_collection,
            "users_coll": users_collection,
            "prompts_coll": prompts_collection}
