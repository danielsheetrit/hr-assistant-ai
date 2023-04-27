import os
from dotenv import load_dotenv

load_dotenv()


OPEN_AI_SECRET = os.getenv('OPEN_AI_SECRET')
MONGO_URI = os.getenv('MONGO_URI')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
