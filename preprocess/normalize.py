import re
import unicodedata
import contractions
import nltk
import spacy
from bs4 import BeautifulSoup
from nltk.tokenize.toktok import ToktokTokenizer
import numpy as np

# Make sure to download the necessary NLTK data and Spacy model
nltk.download('stopwords')
nltk.download('punkt')

class TextPreprocessor:
    def __init__(self):
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            spacy.cli.download('en_core_web_sm')
            self.nlp = spacy.load('en_core_web_sm')
            
        self.tokenizer = ToktokTokenizer()
        self.stopword_list = nltk.corpus.stopwords.words('english')
        
        # Custom stopwords can be added as needed
        custom_stopwords = ['xx', 'xxxx', 'xxxa', 'xxxxxxxx', '&#9;', 'xxxxxxx', 'yyyyyyyy']
        self.stopword_list.remove('no')
        self.stopword_list.remove('not')
        self.stopword_list.extend(custom_stopwords)

    def strip_html_tags(self, text):
        soup = BeautifulSoup(text, "html.parser")
        stripped_text = soup.get_text()
        return stripped_text

    def remove_accented_chars(self, text):
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8', 'ignore')
        return text

    def expand_contractions(self, text):
        return contractions.fix(text)

    def remove_special_characters(self, text, remove_digits=False):
        pattern = r'[^a-zA-z0-9\s]' if not remove_digits else r'[^a-zA-z\s]'
        text = re.sub(pattern, '', text)
        return text

    def lemmatize_text(self, text):
        text = self.nlp(text)
        text = ' '.join([word.lemma_ if word.lemma_ != '-PRON-' else word.text for word in text])
        return text

    def remove_stopwords(self, text, is_lower_case=False):
        tokens = self.tokenizer.tokenize(text)
        tokens = [token.strip() for token in tokens]
        if is_lower_case:
            filtered_tokens = [token for token in tokens if token not in self.stopword_list]
        else:
            filtered_tokens = [token for token in tokens if token.lower() not in self.stopword_list]
        filtered_text = ' '.join(filtered_tokens)
        return filtered_text

    def normalize_corpus(self, corpus, html_stripping=True, contraction_expansion=True,
                         accented_char_removal=True, text_lower_case=True,
                         text_lemmatization=True, special_char_removal=True,
                         stopword_removal=True, remove_digits=True):

        normalized_corpus = []
        for doc in corpus:
            if html_stripping:
                doc = self.strip_html_tags(doc)
            if accented_char_removal:
                doc = self.remove_accented_chars(doc)
            if contraction_expansion:
                doc = self.expand_contractions(doc)
            if text_lower_case:
                doc = doc.lower()
            doc = re.sub(r'[\r|\n|\r\n]+', ' ', doc)
            if text_lemmatization:
                doc = self.lemmatize_text(doc)
            if special_char_removal:
                special_char_pattern = re.compile(r'([{.(-)!}])')
                doc = special_char_pattern.sub(" \\1 ", doc)
                doc = self.remove_special_characters(doc, remove_digits=remove_digits)
            doc = re.sub(' +', ' ', doc)
            if stopword_removal:
                doc = self.remove_stopwords(doc, is_lower_case=text_lower_case)
            normalized_corpus.append(doc)
        return normalized_corpus