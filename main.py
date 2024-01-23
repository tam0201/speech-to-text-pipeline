import os
import wave
import pathlib
import json
import base64
import functions_framework

from google.cloud import speech
from google.cloud import storage
from google.cloud import pubsub_v1

@functions_framework.cloud_event
def preprocess_audio(cloud_event):
    bucket_name = os.environ.get('BUCKET_NAME')
    topic_name = os.environ.get('TOPIC_NAME')
    project_id = os.environ.get('GCP_PROJECT')

    file_data = cloud_event.data
    file_name = file_data['name']

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    local_path = f'/tmp/{file_name}'
    pathlib.Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(local_path)

    # Determine if the audio is stereo and convert to mono if necessary
    with wave.open(local_path, 'rb') as audio:
        channels = audio.getnchannels()
        sample_rate = audio.getframerate()

    # Convert stereo to mono using ffmpeg if necessary
    if channels > 1:
        mono_path = f'/tmp/mono_{file_name}'
        pathlib.Path(mono_path).parent.mkdir(parents=True, exist_ok=True)
        os.system(f'ffmpeg -i {local_path} -ac 1 {mono_path}')
        processed_blob = bucket.blob(f'mono_{file_name}')
        processed_blob.upload_from_filename(mono_path)
        os.remove(mono_path)
    else:
        # If it's already mono, we don't change the file, just use the original filename
        processed_blob = blob

    message = {
        'file_name': processed_blob.name,
        'sample_rate': sample_rate
    }
    
    message_data = json.dumps(message).encode('utf-8')
    # Publish a message to the topic to trigger the transcription function
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    future = publisher.publish(topic_path, data=message_data)
    future.result()  # Verify the publish succeeded

    # Clean up the local filesystem
    os.remove(local_path)

@functions_framework.cloud_event
def transcribe_audio(cloud_event):
    data = cloud_event.data["message"]["data"]
    message = json.loads(base64.b64decode(data).decode('utf-8'))
    file_name = message.get('file_name')
    sample_rate = int(message.get('sample_rate'))
    bucket_name = os.environ.get('BUCKET_NAME')
    gcs_uri = f'gs://{bucket_name}/{file_name}'

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code='en-US',
        use_enhanced=True,
        model='medical',
        enable_automatic_punctuation=True
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=300)

    for result in response.results:
        print(f'Transcript: {result.alternatives[0].transcript}')
        transcript = result.alternatives[0].transcript
        confidence = result.alternatives[0].confidence
        pathlib.Path(f'/tmp/transcripts/{file_name}.txt').parent.mkdir(parents=True, exist_ok=True)
        with open(f'/tmp/transcripts/{file_name}.txt', 'w') as f:
            f.write(f'{transcript}\nConfidence: {confidence}')

    # upload the transcript to GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f'transcripts/{file_name}.txt')
    blob.upload_from_filename(f'/tmp/transcripts/{file_name}.txt')
    os.remove(f'/tmp/transcripts/{file_name}.txt')
     
    
     