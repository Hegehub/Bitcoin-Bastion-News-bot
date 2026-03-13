import pytest
from services.entity_service import entity_service

def test_extract_entities():
    text = "BlackRock files for Bitcoin ETF with SEC"
    entities = entity_service.extract(text)
    assert len(entities) > 0
    # Проверяем, что извлеклись организации
    orgs = [e for e in entities if e['label'] == 'ORG']
    assert len(orgs) > 0

def test_important_entities():
    text = "BlackRock files for Bitcoin ETF with SEC"
    important = entity_service.get_important_entities(text)
    assert 'BlackRock' in important or 'SEC' in important