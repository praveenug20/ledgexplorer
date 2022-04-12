import requests,hashlib

protocal = "http"
host = "codesperfect.com"
port = 5000
url = protocal + "://" + host + ":" + str(port) + "/" #mine&proof"

difficulty = requests.get(url+"difficulty").text

previous_proof = int(requests.get(url+"current_proof").text)

def mine():
    new_proof = 1
    print("Started to mine new Block")
    while True:
        hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
        if(hash_operation[:len(difficulty)] == difficulty):
            print(new_proof)
            res = requests.get(url + "mine?proof="+str(new_proof))
            print("Result for mined block is " + res.text)
            return new_proof
        else:
            new_proof += 1

while True:
    mine()