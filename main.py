import os
import wave
import pathlib
import json
import base64
import functions_framework

from google.cloud import speech
from google.cloud import storage
from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud.exceptions import NotFound
from loguru import logger

# Configure loguru to log to a file with daily rotation
logger.add("/tmp/audio_processing_{time}.log", rotation="1 day")

# Environment variable names
ENV_GCP_PROJECT_ID = 'GCP_PROJECT_ID'
ENV_STORAGE_BUCKET_NAME = 'STORAGE_BUCKET_NAME'
ENV_PUBSUB_TOPIC_NAME = 'PUBSUB_TOPIC_NAME'
ENV_TRANSCRIPT_PATH = 'TRANSCRIPT_PATH'
ENV_MODEL_PATH = 'PREDICTOR_MODEL_PATH'

# Error handler decorator
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (GoogleAPICallError, NotFound, RetryError, Exception) as e:
            logger.error(f'An error occurred in {func.__name__}: {e}')
            raise
    return wrapper

@functions_framework.cloud_event
@handle_errors
def handle_audio_upload(cloud_event):
    """
    Triggered by a Cloud Event when an audio file is uploaded.
    Extracts audio metadata and publishes it to a Pub/Sub topic.
    """
    bucket_name = os.environ[ENV_STORAGE_BUCKET_NAME]
    topic_name = os.environ[ENV_PUBSUB_TOPIC_NAME]
    project_id = os.environ[ENV_GCP_PROJECT_ID]

    file_data = cloud_event.data
    file_name = file_data['name']
    logger.info(f"Processing file upload: {file_name}")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    local_path = f'/tmp/{file_name}'
    pathlib.Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(local_path)

    with wave.open(local_path, 'rb') as audio:
        channels = audio.getnchannels()
        sample_rate = audio.getframerate()

    os.remove(local_path)  # Clean up the local file after processing

    message = {
        'file_name': blob.name,
        'sample_rate': sample_rate,
        'channels': channels
    }
    message_data = json.dumps(message).encode('utf-8')
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    future = publisher.publish(topic_path, data=message_data)
    future.result()
    logger.info(f"Published metadata for {file_name} to {topic_name}")


@functions_framework.cloud_event
@handle_errors
def transcribe_audio_file(cloud_event):
    """
    Triggered by a Cloud Event when an audio file's metadata is published.
    Transcribes the audio using Google Cloud Speech-to-Text.
    """
    bucket_name = os.environ[ENV_STORAGE_BUCKET_NAME]
    topic_name = os.environ[ENV_PUBSUB_TOPIC_NAME]
    project_id = os.environ[ENV_GCP_PROJECT_ID]
    transcript_path = os.environ.get(ENV_TRANSCRIPT_PATH, 'transcripts')

    data = cloud_event.data["message"]["data"]
    message = json.loads(base64.b64decode(data).decode('utf-8'))
    file_name = message.get('file_name')
    sample_rate = message.get('sample_rate')
    channels = message.get('channels')
    gcs_uri = f'gs://{bucket_name}/{file_name}'

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)

    diarization_config = speech.SpeakerDiarizationConfig(
        enable_speaker_diarization=True,
        min_speaker_count=2,
        max_speaker_count=6,
    )

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code='en-US',
        model='video',
        audio_channel_count=channels,
        diarization_config=diarization_config,
        enable_automatic_punctuation=True,
        enable_word_confidence=True,
        enable_separate_recognition_per_channel=True,
        enable_word_time_offsets=True
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=10000)

    transcripts = []
    for i, result in enumerate(response.results):
        alternative = result.alternatives[0]
        transcript = alternative.transcript
        confidence = alternative.confidence
        transcripts.append(transcript)

        logger.info("-" * 20)
        logger.info(f"Confidence: {confidence}")
        logger.info(f"Transcript: {transcript}")

    transcript_text = '\n'.join(transcripts)
    logger.info(f"Completed transcription for {file_name}")
    # Save the transcript text
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    transcript_blob = bucket.blob(f'{transcript_path}/{file_name}.txt')
    transcript_blob.upload_from_string(transcript_text)
    logger.info(f"Uploaded transcript for {file_name}")

    # Publish a message withthe transcript and confidence
    message = {
        'file_name': file_name,
        'transcript': transcript_text,
        'confidence': confidence
    }

    message_data = json.dumps(message).encode('utf-8')
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    future = publisher.publish(topic_path, data=message_data)
    future.result()
    logger.info(f"Published transcript for {file_name} to {topic_name}")

@functions_framework.cloud_event
@handle_errors
def summarize_transcript(cloud_event):
    """
    Triggered by a Cloud Event when a transcript is published.
    Analyzes the transcript and uploads a summary to Firestore.
    """
    import ktrain
    import pandas as pd 
    import firebase_admin
    from firebase_admin import firestore
    # initialize firebase
    app = firebase_admin.initialize_app()
    db = firestore.client()
    # Get transcript from Pub/Sub message
    model_path = os.environ[ENV_MODEL_PATH]
    data = cloud_event.data["message"]["data"]
    message = json.loads(base64.b64decode(data).decode('utf-8'))
    file_name = message['file_name']
    transcript = message['transcript']

    logger.info(f"Summarizing transcript for {file_name}")

    predictor = ktrain.get_predictor(os.path.join('/tmp', model_path))
    label_dict={}
    # label each sentence
    for sentence in transcript.split('\n'):
        prediction = predictor.predict(sentence)
        logger.info(f'{sentence} - {prediction}')
        # parse into summary
        label_dict[prediction] = sentence
    
    summary_df = pd.DataFrame(label_dict.items(), columns=['label', 'sentence'])
    summary = summary_df.groupby('label').agg({'sentence': ' '.join})
    summary = summary.to_dict()['sentence']
    summary = json.dumps(summary)
    logger.info(f'Summary: {summary}')
    # Save the summary to Firestore
    db = firestore.Client()
    doc_ref = db.collection(u'soap_summaries').document(file_name)
    doc_ref.set({
        file_name: summary
    })
     
    logger.info('Summary uploaded to firebase')
