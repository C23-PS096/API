from keras.models import load_model
import h5py
import gcsfs

PROJECT_NAME = 'dev-optikoe'
CREDENTIALS = 'service_account.json'
BUCKET_NAME = 'gs://optikoe-ml-models/'
MODEL_PATH = BUCKET_NAME + 'face_type_model.h5'

