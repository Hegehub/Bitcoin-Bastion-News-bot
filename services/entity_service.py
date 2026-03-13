import spacy
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class EntityService:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded")
        except Exception as e:
            logger.error(f"Failed to load spaCy: {e}")
            self.nlp = None

    def extract(self, text: str) -> List[Dict[str, str]]:
        """Возвращает список сущностей с типом и текстом."""
        if not self.nlp:
            return []
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'description': spacy.explain(ent.label_)
            })
        return entities

    def get_important_entities(self, text: str, important_labels=None) -> List[str]:
        """Возвращает только 'важные' сущности (ORG, PERSON, GPE, MONEY, EVENT)."""
        if important_labels is None:
            important_labels = ['ORG', 'PERSON', 'GPE', 'MONEY', 'EVENT']
        entities = self.extract(text)
        return [e['text'] for e in entities if e['label'] in important_labels]

entity_service = EntityService()