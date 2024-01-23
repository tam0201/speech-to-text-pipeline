import os
import wave
from google.cloud import pubsub_v1
from google.cloud import storage
import functions_framework

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
    blob.download_to_filename(local_path)

    # Determine if the audio is stereo and convert to mono if necessary
    with wave.open(local_path, 'rb') as audio:
        channels = audio.getnchannels()
        sample_rate = audio.getframerate()

    # Convert stereo to mono using ffmpeg if necessary
    if channels > 1:
        mono_path = f'/tmp/mono_{file_name}'
        os.system(f'ffmpeg -i {local_path} -ac 1 {mono_path}')
        processed_blob = bucket.blob(f'mono_{file_name}')
        processed_blob.upload_from_filename(mono_path)
        os.remove(mono_path)
    else:
        # If it's already mono, we don't change the file, just use the original filename
        processed_blob = blob

    # Publish a message to the topic to trigger the transcription function
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    future = publisher.publish(topic_path, b'Trigger Transcription', file_name=processed_blob.name, sample_rate=str(sample_rate))
    future.result()  # Verify the publish succeeded

    # Clean up the local filesystem
    os.remove(local_path)