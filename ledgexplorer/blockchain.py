from crypt import methods
from random import sample
from pymongo import MongoClient
from bitcoin import *
from flask import *
import datetime,hashlib,json,sys
from requests import post
from pymongo.server_api import ServerApi

# Connection
mongoclient = MongoClient("mongodb+srv://praveen:mongodb@cluster0.ch6mp.mongodb.net/supplychain?retryWrites=true&w=majority", server_api=ServerApi('1'))
print("Mongo connected..")
    # "mongodb://localhost:27017/")

# Database
mongodb = mongoclient['supplychain']

# Collections
hash  = mongodb['hash']
address   = mongodb['address']
block = mongodb['block']
hash_index = mongodb['hash_index']

# BlockChain
class BlockChain:
    def __init__(self) -> None:
        self.height = block.count_documents({})
        self.difficulty = '000000'
        self.formats = ['M','D','R','C']
        if self.height == 0:
            data = self.create_block(1,"0000000000000000000000000000000000000000000000000000000000000000",1)
            block.insert_one(data)
            self.height = block.count_documents({})  
            
    def new_block(self,proof):
        prev_block = block.find_one({"_id":self.height})['block']
        validate_proof = hashlib.sha256(str(
            proof**2 - prev_block['proof']**2
        ).encode()).hexdigest()
        if validate_proof[:len(self.difficulty)] == self.difficulty:
            _prev_block = json.dumps(prev_block).encode()
            data = self.create_block(self.height+1,hashlib.sha256(_prev_block).hexdigest(),proof)
            block.insert_one(data)
            self.height = block.count_documents({})
            return True 
        else:
            raise Exception
    
    def create_block(self,height,prev_hash,proof):
        data = {
                "_id":height,
                "block":{
                    "height":height,
                    "previous_hash":prev_hash,
                    "proof":proof,
                    "timestamp":str(datetime.datetime.now()),
                    "data":[]
                    }
                }
        return data
    
    def is_valid_address(self,address):
        if is_address("1"+address[1:]) and address[0] in self.formats:
            return True
        else:
            return False
        
    def validate_signature(self,address,key):
        try:
            if self.is_valid_address(address):
                if privtoaddr(key)[1:] == address[1:]:
                    return True
        except:
            return False
        return False
    
    def commit(self,hash_id,data):
        cblock = block.find_one({"_id":self.height})['block']
        hash_ = hashlib.sha256(json.dumps(cblock).encode()).hexdigest()
        cblock['data'].append({
            "hash":hash_,
            "data":data
        })
        block.update_one(
            {"_id":self.height},
            {"$set":{
                'block':cblock
                }
            }
        )
        hash_index.insert_one({"_id":hash_,"block":self.height,"index":len(cblock['data'])-1})
        if hash.count_documents({"_id":hash_id}) == 0:
            hash.insert_one({"_id":hash_id,"data":[]})
            from_addr_count = address.count_documents({"_id":data["from"]})
            to_addr_count = address.count_documents({"_id":data["to"]})
            if  from_addr_count == 0:
                address.insert_one({"_id":data["from"],"data":[]})
            if to_addr_count == 0:
                address.insert_one({"_id":data["to"],"data":[]})
            adata = address.find_one({"_id":data["from"]})["data"]
            adata.append(hash_id)
            address.update_one({"_id":data["from"]},{"$set":{
               "data":adata 
            }})
            bdata = address.find_one({"_id":data["to"]})["data"]
            bdata.append(hash_id)
            address.update_one({"_id":data["to"]},{"$set":{
               "data":adata 
            }})
        hdata = hash.find_one({"_id":hash_id})['data']
        hdata.append(hash_)
        hash.update_one({"_id":hash_id},{"$set":{
           "data":hdata 
        }})
        
    def initialize_data(self,inputs):
      try:
        ''' 
        SAMPLE INPUT
        -----------
        {"from":"ME31zhi39v1Esd4Ui5BYzf4H8vGzDuqWXC","to":"DE31zhi39v1Esd4Ui5BYzf4H8vGzDuqWXC",
                             "key":"fba0549a46c35b6097c1dc735d15ac557c7f828fe481955424c9162a6f80895d","data":{
                                 "serial_no":"sample",
                                 "product_no":"hello"
                             }}
        '''
        if type(inputs) is dict:
            k = inputs.keys()
            if 'from' in k and 'to' in k and  'key' in k and 'data' in k : # from address, to address , private key (hex format)
                if self.is_valid_address(inputs['from']) and self.is_valid_address(inputs['to']):
                    if self.validate_signature(inputs['from'] , inputs['key']):
                        inputs['data'].update({"timestamp":str(datetime.datetime.now())}),
                        hash_id = hashlib.sha256(json.dumps(inputs['data']).encode()).hexdigest()
                        data = {
                            "from": inputs['from'],
                            "to"  : inputs['to'],
                            "hash": hash_id,
                            "data": inputs['data'],
                            "timestamp":str(datetime.datetime.now())
                        }
                        self.commit(hash_id,data)
                        return hash_id
                    else:
                        raise Exception("authentication failed")
                else:
                    raise Exception("invalid address")
            else:
                raise Exception("invalid inputs")
        else:
            raise Exception("initialization not valid!")
      except Exception as e:
          raise Exception(str(e))
      
    def get_currentOwnership_usingData(self,hash_data):
        if(len(hash_data) >= 0 ):
            chash = hash_data['data'][-1]
            chash = hash_index.find_one({"_id":chash})
            if chash != None :
                data = block.find_one({"_id":chash["block"]})["block"]["data"]
                return data[chash["index"]]["data"]["to"],data[chash["index"]]["data"]["from"],hash_data['data'][-1],chash
        return None
    
    def get_currentOwnership_usingHashId(self,hash_id):
        hash_data = hash.find_one({"_id":hash_id})
        if(hash_data != None):
            return self.get_currentOwnership_usingData(hash_data)
        return None
        
    def transferOwnership(self,hash_id,to_address,key):
        try:
            c_owner = self.get_currentOwnership_usingHashId(hash_id)
            if self.is_valid_address(to_address) and c_owner != None and self.validate_signature(c_owner[0],key):
                data = block.find_one({"_id":c_owner[-1]['block']})["block"]["data"][c_owner[-1]["index"]]["data"]
                data["from"] = c_owner[0]
                data["to"] = to_address
                data["timestamp"] = str(datetime.datetime.now())
                self.commit(hash_id,data)
                return "ownership transferred"
            else:
                raise Exception("validation failed")
        except Exception as e:
            raise Exception(str(e))

blockchain = BlockChain()

app = Flask(__name__)

@app.route("/")
def home():
    return "<center><i>|--| |--| |--| |--| |--| |--| |--| |--| |--| |--| |--| |--| |--| |--| |--|</i><h1>Node >< Running</h1></center><hr><center><i>node for supply chain management has been successfully running<br>ledgexplorer.com</i></center>"

@app.route("/latest_block")
def latest_blocks():
    try:
        c = block.count_documents({})
        r = 0
        data = []
        while c > 0 and r <= 50:
            a = block.find_one({"_id":c})
            a = a["block"]
            data.append({
                "height":a["height"],
                "previous_hash":a["previous_hash"],
                "proof":a["proof"],
                "timestamp":a["timestamp"]
            })
            c -= 1
            r += 1
        return jsonify(data)
    except Exception as e:
        return jsonify([])
    
@app.route("/mine")
def mine():
    try:
        proof = int(request.args.get("proof"))
        blockchain.new_block(proof)
        return jsonify({"mes":"proof accepted and validated successfully :)"})
    except:
        return jsonify({"mes":"proof not valid"}) 
    
@app.route("/block/<height>")
def findblock(height):
    try:
        data = block.find_one({"_id":int(height)})["block"]
        if data != None:
            return jsonify(data)
        else:
            raise Exception
    except:
        return jsonify({})

@app.route("/hash/<hash_>")
def find_hash(hash_):
    try:
        hashes = hash.find_one({"_id":hash_})["data"]
        result = []
        for i in range(len(hashes)):
            ihash = hash_index.find_one({"_id":hashes[i]})
            data = block.find_one({"_id":ihash["block"]})["block"]["data"][ihash["index"]]
            result.append({"data":data})
        return jsonify({
            "hash":hash_,
            "blocks":result
            })
    except Exception as e:
        return jsonify({})
    
@app.route("/otid/<hash_>")
def otid(hash_):
    try:
        ihash = hash_index.find_one({"_id":hash_})
        data = block.find_one({"_id":ihash["block"]})["block"]["data"][ihash["index"]]
        return jsonify(data)
    except:
        return jsonify({})
    
@app.route("/initiate",methods=['POST'])
def initiate():
    try:
        return jsonify({
            "error":"no",
            "mes":"initialization successfull",
            "hash":blockchain.initialize_data(request.json)
            })
    except Exception as e:
        return jsonify({"error":"yes","mes":str(e)})
        
@app.route("/transfer_ownership",methods=['POST'])
def transfer_ownership():
    try:
        return jsonify({
            "error":"no",
            "mes":blockchain.transferOwnership(request.form["hash"],request.form["to"],request.form["key"])
        })
    except Exception as e:
        return jsonify({"error":"yes","mes":str(e)})
            
            
@app.route("/difficulty")
def get_difficulty():
    return blockchain.difficulty

@app.route("/height")
def get_height():
    return str(blockchain.height)

@app.route("/current_proof")
def current_proof():
    try:
        return str(block.find_one({"_id":blockchain.height})["block"]["proof"])
    except:
        return "0"

@app.route("/verify_ownership")
def veridy():
    try:
        c_owner = blockchain.get_currentOwnership_usingHashId(request.form["hash"])
        if blockchain.validate_signature(c_owner[0],request.form["key"]):
            return jsonify({"owner":True})
        jsonify({"owner":False})
    except :
        return jsonify({"owner":False})

app.debug = True
app.run(port=5000,host='0.0.0.0')