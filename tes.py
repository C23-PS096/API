from google.cloud import storage
from keras.models import load_model
import keras.utils as image
import h5py
import numpy as np
import os

PROJECT_NAME = 'dev-optikoe'
CREDENTIALS = 'ml-model-read.json'
BUCKET_NAME = 'optikoe-ml-models'
MODEL_PATH = 'face_type_model.h5'

MODEL_FILE_PATH = "model1.h5"
cached_model = None

# Load the model from Google Cloud Storage (GCS) and cache it
def load_cached_model():
     global cached_model
     
     if cached_model is None:
          if os.path.exists(MODEL_FILE_PATH):
               cached_model = load_model(MODEL_FILE_PATH)
          
          else:
               client = storage.Client.from_service_account_json(CREDENTIALS)
               bucket = client.bucket(BUCKET_NAME)
               blob = bucket.get_blob(MODEL_PATH)
               
               
               blob.download_to_filename(MODEL_FILE_PATH)
               cached_model = load_model(MODEL_FILE_PATH)
          

def predictions(image_path):
     load_cached_model()
     target_size = (250, 400)
     
     img = image.load_img(image_path, target_size=target_size)
     
     # Preprocessing image
     img_array = image.img_to_array(img)

     img_array = np.expand_dims(img_array, axis=0)
     preprocessed_img = img_array / 255.0  # Normalize pixel values to the range [0, 1]

     # Process the preprocessed image using the loaded model
     predictions = cached_model.predict(preprocessed_img)
     return predictions

# File to process
# image_path = 'contoh/tes2.png'

img_directory = 'contoh/'
for filename in os.listdir(img_directory):
     print(filename)
     
     img =os.path.join(img_directory, filename)
     
     result = predictions(img)
     print(result)
     

# # Prediction Results
# class_names = ['Oval', 'Round', 'Square', 'Oblong', 'Heart']

# # Get the index of the class with the highest probability
# predicted_class_index = np.argmax(predictions[0])

# # Get the corresponding class name and its probability
# predicted_class = class_names[predicted_class_index]
# probability = predictions[0][predicted_class_index]

# print("Predicted class:", predicted_class)
# print("Probability:", probability)