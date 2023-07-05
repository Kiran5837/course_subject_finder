import os
from sqlalchemy import create_engine

class Config(object):
    DB_USERNAME = os.getenv('DB_USERNAME')  # The name of the environment variable is 'DB_USERNAME'
    DB_PASSWORD = os.getenv('DB_PASSWORD')  # The name of the environment variable is 'DB_PASSWORD'
    DB_NAME = os.getenv('DB_NAME')  # The name of the environment variable is 'DB_NAME'
    DB_HOST = os.getenv('DB_HOST')  # The name of the environment variable is 'DB_HOST'
    DB_PORT = os.getenv('DB_PORT')  # The name of the environment variable is 'DB_PORT'

# Create an instance of the Config class
config = Config()

DATABASE_URI = f"postgresql://{config.DB_USERNAME}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
engine = create_engine(DATABASE_URI)
