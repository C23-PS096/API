from google.cloud import storage
from keras.models import load_model
import keras.utils as image
import h5py
import numpy as np

PROJECT_NAME = 'dev-optikoe'
CREDENTIALS = 'ml-model-read.json'
BUCKET_NAME = 'optikoe-ml-models'
MODEL_PATH = 'face_type_model.h5'

# client = storage.Client.from_service_account_json(CREDENTIALS)
# bucket = client.get_bucket(BUCKET_NAME)
# blob = bucket.get_blob(MODEL_PATH)

# print(blob)

# with blob.open('rb') as model_file:
     # model_gcs = h5py.File(model_file, 'r')
     # myModel = load_model(model_gcs)
     # print("Model Loaded")

myModel = load_model(MODEL_PATH)
print("Model Loaded")

# File to process
image_path = 'contoh/tes2.png'
target_size = (400, 250)

# Load and preprocess the image
img = image.load_img(image_path, target_size=target_size)
img = img.resize(target_size)

img_array = image.img_to_array(img)

img_array = np.expand_dims(img_array, axis=0)
preprocessed_img = img_array / 255.0  # Normalize pixel values to the range [0, 1]

# Process the preprocessed image using the loaded model
predictions = myModel.predict(preprocessed_img)

print(predictions)

# Assuming there are five classes
class_names = ['Oval', 'Round', 'Square', 'Oblong', 'Heart']

# Get the index of the class with the highest probability
predicted_class_index = np.argmax(predictions[0])

# Get the corresponding class name and its probability
predicted_class = class_names[predicted_class_index]
probability = predictions[0][predicted_class_index]

print("Predicted class:", predicted_class)
print("Probability:", probability)