from google.cloud import ndb
from google.cloud import storage
from keras.models import load_model
import keras.utils as image
import numpy as np

PROJECT_NAME = 'dev-optikoe'
CREDENTIALS = 'ml-model-read.json'
BUCKET_NAME = 'optikoe-ml-models'
MODEL_PATH = 'face_type_model.h5'

class CachedModel(ndb.Model):
     model = ndb.PickleProperty()
     timestamp = ndb.DateTimeProperty(auto_now = True)
     
# Load the model from Google Cloud Storage (GCS) and cache it in NDB
def load_cached_model():
     cached_model = CachedModel.query().get()
     
     if cached_model and cached_model.model:
          return  cached_model.model
     
     client = storage.Client(project=PROJECT_NAME, credentials=CREDENTIALS)
     bucket = client.bucket(BUCKET_NAME)
     blob = bucket.blob(MODEL_PATH)
     
     model_file_path = "/tmp/model.h5"  # Temporarily store the model file
    
     blob.download_to_filename(model_file_path)
    
     # Load the model
     loaded_model = load_model(model_file_path)
     
     # Save the model to ndb
     if not cached_model:
        cached_model = CachedModel()
    
     cached_model.model = loaded_model
     cached_model.put()
    
     return loaded_model

     
def predictions(image_path):
     cached_model = load_cached_model()
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