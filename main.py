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

    message = {
        'file_name': blob.name,
        'sample_rate': sample_rate,
        'n_channels': channels
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
    n_channels = int(message.get('n_channels'))
    bucket_name = os.environ.get('BUCKET_NAME')
    gcs_uri = f'gs://{bucket_name}/{file_name}'

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code='en-US',
        model='medical',
        audio_channel_count=n_channels,
        enable_separate_recognition_per_channel=True,
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=300)

    transcripts = []  # Store all the transcripts

    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        transcript = alternative.transcript
        confidence = alternative.confidence

        transcripts.append(transcript)  # Add transcript to the list

        print("-" * 20)
        print(f"First alternative of result {i}")
        print(f"Transcript: {transcript}")
        print(f"Channel Tag: {result.channel_tag}")
        print(f"Confidence: {confidence}")

    # Save all the transcripts to a file
    transcript_text = '\n'.join(transcripts)
    transcript_file_path = f'/tmp/transcripts/{file_name}.txt'
    
    # Upload the transcript file to GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f'transcripts/{file_name}.txt')
    blob.upload_from_string(transcript_text)

     