from flask import Flask, jsonify, request
from ml_models import predictions
from io import BytesIO

app = Flask(__name__)

@app.route("/", methods=['GET'])
def helloWorld():
    return jsonify({
        'status': 200,
        'message': "Hello, flask!!"
    })

@app.route("/face", methods=['POST'])
def getFacePrediction():
    if request.method == "POST":
        file_upload = request.files['file']
        
        if file_upload:    
            file_contents = file_upload.read()
            file_stream = BytesIO(file_contents)
            
            prediction_result = predictions(file_stream)
            prediction_result['probability'] = float(prediction_result['probability'])
            print(prediction_result)
            
            return jsonify({
                'status': 200,
                'message': "Success",
                'data': prediction_result
            })

if __name__ == "__main__":
    app.run(host="localhost", port=8000, debug=True)