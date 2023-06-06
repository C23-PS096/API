from google.cloud import storage
from google.oauth2 import service_account
from keras.models import load_model
import keras.utils as image
import numpy as np
# from google.appengine.api import memcache

PROJECT_NAME = 'dev-optikoe'
CREDENTIALS = 'ml-model-read.json'
BUCKET_NAME = 'optikoe-ml-models'
MODEL_PATH_FACE = 'face_type_model.h5'
MODEL_PATH_KACAMATA = 'kacamata_type_model.h5'

AUTHENTICATION = service_account.Credentials.from_service_account_file(CREDENTIALS)
# MEMCACHE_KEY = 'cached_model'

# Load the model from Google Cloud Storage (GCS)
def load_cached_model(model_path):
    # cached_model = memcache.get(MEMCACHE_KEY)
    
    # if cached_model is not None:
    #     return cached_model

    client = storage.Client.from_service_account_json(CREDENTIALS)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.get_blob(model_path)
    
    model_file_path = "/tmp/model.h5"
    blob.download_to_filename(model_file_path)
    
    loaded_model = load_model(model_file_path)
    
    # memcache.add(MEMCACHE_KEY, loaded_model)
    
    return loaded_model

     
def predictions(image_path, model_type):
     if model_type == '0':
        model_path = MODEL_PATH_FACE
     elif model_type == '1':
        model_path = MODEL_PATH_KACAMATA
     else:
        raise ValueError("Invalid model type")
     
     cached_model = load_cached_model(model_path)
     target_size = (250, 400)
     
     img = image.load_img(image_path, target_size=target_size)
     
     # Preprocessing image
     img_array = image.img_to_array(img)

     img_array = np.expand_dims(img_array, axis=0)
     preprocessed_img = img_array / 255.0  # Normalize pixel values to the range [0, 1]

     # Process the preprocessed image using the loaded model
     predictions = cached_model.predict(preprocessed_img)
     
     # Prediction Results
     class_names = ['Oval', 'Round', 'Square', 'Oblong', 'Heart']

     # Get the index of the class with the highest probability
     predicted_class_index = np.argmax(predictions[0])

     # Get the corresponding class name and its probability
     predicted_class = class_names[predicted_class_index]
     probability = predictions[0][predicted_class_index]

     data = {
          'face_shape': predicted_class,
          'probability': probability
     }
          
     return data