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