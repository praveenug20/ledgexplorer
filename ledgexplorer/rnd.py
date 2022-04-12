from pydoc import cli
from pymongo import MongoClient
from pymongo.server_api import ServerApi
client = MongoClient("mongodb+srv://praveen:mongodb@cluster0.ch6mp.mongodb.net/supplychain?retryWrites=true&w=majority", server_api=ServerApi('1'))
db = client['sample']
coll = db['rnd']
coll.insert_one({"data":"hello world"})

for i in coll.find({}):
    print(i)