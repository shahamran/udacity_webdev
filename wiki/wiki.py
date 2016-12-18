from flask import Flask, request, make_response
app = Flask(__name__)

@app.route('/')
def hello_world():
    i = 0
    while i < 3:
        x = input(">> ");
        print(x)
        i += 1

with 

