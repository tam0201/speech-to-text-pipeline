# Medical Audio Processing Pipeline

This project is designed to provide an automated pipeline for processing medical audio files. It leverages Google Cloud Platform (GCP) services, such as Cloud Storage, Pub/Sub, and Cloud Functions, to handle audio file uploads, transcribe them, and summarize their contents.

## Challenges
- I find it is very challenging to find relevant data and code for SOAP summarization. The data i obtained for training is very small, so the model is not very accurate.
- In the business scenarios, the dataset could be much more larger than what i use here. Whenever i do test like do, i always try to find the dataset that as similar as possible in business scenarios. But for medical context, it nearly impossible
- I found two paper that address the SOAP summarization issue. https://arxiv.org/pdf/2005.01795v3.pdf https://proceedings.mlr.press/v126/schloss20a/schloss20a.pdf. But the dataset they use is not available so it is hard to reproduce their results.

## Ensure medical terminology and nuance
For speech-to-text API on GCP, it is possible to add custom vocabulary. I think it is very important to add medical terminology and nuance to the vocabulary.

## Project Overview

The pipeline operates as follows:

1. An audio file is uploaded to a Cloud Storage bucket.
2. A Cloud Function is triggered to handle the upload and publish audio metadata to a Pub/Sub topic.
3. Another Cloud Function is triggered by the Pub/Sub topic to transcribe the audio file using the Google Speech-to-Text API.
4. The transcription is then processed by a summarization function and stored in Firestore.

## Prerequisites

Before using the Makefile to deploy the pipeline, make sure you have the following:

- Google Cloud SDK (gcloud) installed and authenticated with your GCP account.
- Appropriate permissions to create and manage Cloud Storage buckets, Pub/Sub topics, and Cloud Functions.
- The `make` utility installed on your local machine.

## Configuration

The Makefile contains predefined variables for the GCP project ID, region, bucket name, Firestore database ID, and Cloud Function names. Ensure these values are set correctly to match your GCP environment.

## Using the Makefile

### Setup

To create the Cloud Storage bucket, Pub/Sub topic, and Firestore database, run:
Please adjust the project id in the Makefile to your own project id.

```bash
make setup
```
 

### Deployment

To deploy the entire pipeline, simply run:

```bash
make deploy-all
```

This command will sequentially deploy the preprocess, transcribe, and summarization functions to your GCP project.

### Individual Deployment
You can also deploy individual components by running:

```bash
make deploy-preprocess
make deploy-transcribe
make deploy-summarization
```

### Cleanup

To remove all deployed resources, run:

```bash
make cleanup
```

This command will delete the Cloud Functions, Pub/Sub topic, and Cloud Storage bucket.

### SOAP Summarization

The SOAP Summarization algorithm contains two parts:
1. The classifier, which is leverage Bio_ClinicalBert[emilyalsentzer/Bio_ClinicalBERT] model. The model then trained on the SOAP notes obtained from https://huggingface.co/datasets/biomegix/soap-notes using ktrain[https://github.com/amaiya/ktrain.git] library. The model outputs the probability of each sentence belonging to each of the SOAP categories. After predicting the probabilities, the sentences are then classified into the categories based on the highest probability. Because the dataset is only 100-ish sentences, the model is not very accurate. I can not find any other dataset that contains SOAP notes. The one of physio bank[https://physionet.org/content/mimiciii/1.4/] requires a license, so I can not use it. 

2. 
 

