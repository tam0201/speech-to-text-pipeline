from omegaconf import OmegaConf
from models.bert import BERTModelTrainer
 
# Load configuration from the YAML file
config = OmegaConf.load('config/model/bert.yaml')

def load_csv_dataset():
    import pandas as pd 
    
    data_training_file = "data/training_data.csv"
    data_testing_file = "data/test_data.csv"
    
    training_data = pd.read_csv(data_training_file, encoding='latin-1').sample(frac=1).drop_duplicates()
    testing_data = pd.read_csv(data_testing_file, encoding='latin-1').sample(frac=1).drop_duplicates()

    train_texts = training_data["Text"]
    train_labels = training_data["Label"]

    val_texts = testing_data["Text"]
    val_labels = testing_data["Label"]

    return (train_texts, train_labels), (val_texts, val_labels)

(train_texts, train_labels), (val_texts, val_labels) = load_csv_dataset()
# Create an instance of the BERTModelTrainer class
bert_trainer = BERTModelTrainer(train_texts, 
                                val_texts, 
                                train_labels, 
                                val_labels, 
                                config)

bert_predictor = bert_trainer.train()
