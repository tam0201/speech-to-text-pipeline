from omegaconf import OmegaConf
import ktrain
from ktrain import text as ktrain_text
from preprocess.normalize import TextPreprocessor

class BERTModelTrainer:
    def __init__(self, train_data, val_data, train_labels, val_labels, config):
        self.config = config
        self.train_data = train_data
        self.val_data = val_data
        self.train_labels = train_labels
        self.val_labels = val_labels
        self.preprocessor = TextPreprocessor()

    def preprocess_data(self):
        self.preprocessor.normalize_corpus_config = {
            # Unpack the preprocessing section of the config
            **self.config.preprocessing
        }
        # Use the preprocessor to normalize the train and validation data
        self.normalized_train_text = self.preprocessor.normalize_corpus(self.train_data, **self.preprocessor.normalize_corpus_config)
        self.normalized_val_text = self.preprocessor.normalize_corpus(self.val_data, **self.preprocessor.normalize_corpus_config)

    def train(self):
        self.preprocess_data()
        # Initialize the transformer model for text classification
        print(type(self.config.model.target_names))
        transformer = ktrain_text.Transformer(self.config.model.name, maxlen=self.config.model.max_sequence_length, class_names=list(self.config.model.target_names))

        # Preprocess the training and validation data
        trn = transformer.preprocess_train(self.normalized_train_text, self.train_labels.tolist())
        val = transformer.preprocess_test(self.normalized_val_text, self.val_labels.tolist())

        # Get the classifier model
        model = transformer.get_classifier()

        # Create a Learner object
        learner = ktrain.get_learner(model, train_data=trn, val_data=val, batch_size=self.config.model.batch_size)

        # Train the model using the learning rate finder
        learner.fit_onecycle(self.config.model.learning_rate, self.config.model.epochs)

        # Validate the model
        learner.validate(class_names=self.config.model.target_names)

        # Load the predictor for saving
        predictor = ktrain.get_predictor(learner.model, preproc=transformer)
        predictor.save(self.config.model.model_path)

        return predictor

