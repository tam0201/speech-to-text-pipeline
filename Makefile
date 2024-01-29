# Variables
GCP_PROJECT := fleet-furnace-412021
REGION := us-central1
BUCKET_NAME := tam-do-medical-audio
DATABASE_ID := medical-audio
LOCATION := us-central1
DATABASE_TYPE := datastore-mode
PREPROCESS_FUNCTION_NAME := handle_audio_upload
TRANSCRIBE_FUNCTION_NAME := transcribe_audio_file
SUMMARIZATION_FUNCTION_NAME := summarize_transcript
TOPIC_NAME := medical-audio-preprocess
ENTRY_POINT_PREPROCESS := handle_audio_upload
ENTRY_POINT_TRANSCRIBE := transcribe_audio_file

install-deps:
	p

# Deployment Commands
create-topic:
	gcloud pubsub topics create $(TOPIC_NAME) --project=$(GCP_PROJECT)

create-firestore:
	gcloud alpha firestore databases create \
					--database=$(DATABASE_ID) \
					--location=$(LOCATION) \
					--type=$(DATABASE_TYPE) \
					[--delete-protection]

create-bucket:
 	gcloud storage buckets create gs://$(BUCKET_NAME)

deploy-preprocess:
	gcloud functions deploy $(PREPROCESS_FUNCTION_NAME) \
	--runtime python39 \
	--trigger-resource $(BUCKET_NAME) \
	--trigger-event google.storage.object.finalize \
	--entry-point $(ENTRY_POINT_PREPROCESS) \
	--set-env-vars BUCKET_NAME=$(BUCKET_NAME),TOPIC_NAME=$(TOPIC_NAME),GCP_PROJECT=$(GCP_PROJECT) \
	--project=$(GCP_PROJECT) \
	--region=$(REGION)

deploy-transcribe:
	gcloud functions deploy $(TRANSCRIBE_FUNCTION_NAME) \
	--runtime python39 \
	--trigger-topic $(TOPIC_NAME) \
	--entry-point $(ENTRY_POINT_TRANSCRIBE) \
	--set-env-vars BUCKET_NAME=$(BUCKET_NAME) \
	--project=$(GCP_PROJECT) \
	--region=$(REGION)

deploy-summarization:
	gcloud functions deploy $(SUMMARIZATION_FUNCTION_NAME) \
	--runtime python39 \
	--trigger-topic $(TOPIC_NAME) \
	--entry-point $(ENTRY_POINT_SUMMARIZATION) \
	--set-env-vars BUCKET_NAME=$(BUCKET_NAME) \
	--project=$(GCP_PROJECT) \
	--region=$(REGION)

# Optionally, include the cleanup commands
delete-topic:
	gcloud pubsub topics delete $(TOPIC_NAME) --project=$(GCP_PROJECT)

delete-function:
	gcloud functions delete $(PREPROCESS_FUNCTION_NAME) --project=$(GCP_PROJECT) --region=$(REGION)
	gcloud functions delete $(TRANSCR IBE_FUNCTION_NAME) --project=$(GCP_PROJECT) --region=$(REGION)

delete-firestore:
	gcloud alpha firestore databases delete $(DATABASE_ID) --project=$(GCP_PROJECT)

delete-bucket:
	gsutil rm -r gs://$(BUCKET_NAME)

# Phony Targets
.PHONY: create-topic deploy-preprocess deploy-transcribe delete-topic delete-function delete-bucket

# Grouped Setup
setup: create-topic create-firestore create-bucket

# Grouped Deployment
deploy-all: deploy-preprocess deploy-transcribe deploy-summarization

# Grouped Cleanup
cleanup: delete-topic delete-function delete-bucket delete-firestore
