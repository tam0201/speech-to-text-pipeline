# Variables
GCP_PROJECT := fleet-furnace-412021
REGION := us-central1
BUCKET_NAME := tam-do-medical-audio
PREPROCESS_FUNCTION_NAME := preprocess-audio
TRANSCRIBE_FUNCTION_NAME := transcribe-audio
TOPIC_NAME := medical-audio-preprocess
ENTRY_POINT_PREPROCESS := preprocess_audio
ENTRY_POINT_TRANSCRIBE := transcribe_audio

# Deployment Commands
create-topic:
	gcloud pubsub topics create $(TOPIC_NAME) --project=$(GCP_PROJECT)

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

# Optionally, include the cleanup commands
delete-topic:
	gcloud pubsub topics delete $(TOPIC_NAME) --project=$(GCP_PROJECT)

delete-function:
	gcloud functions delete $(PREPROCESS_FUNCTION_NAME) --project=$(GCP_PROJECT) --region=$(REGION)
	gcloud functions delete $(TRANSCRIBE_FUNCTION_NAME) --project=$(GCP_PROJECT) --region=$(REGION)

delete-bucket:
	gsutil rm -r gs://$(BUCKET_NAME)

# Phony Targets
.PHONY: create-topic deploy-preprocess deploy-transcribe delete-topic delete-function delete-bucket

# Grouped Deployment
deploy-all: deploy-preprocess deploy-transcribe

# Grouped Cleanup
cleanup: delete-topic delete-function delete-bucket