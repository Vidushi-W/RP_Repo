import pytest
from app.core.config import settings
from app.ml import local_sentence


@pytest.mark.parametrize('tokens,sentence', [
    (['I','WANT','FOOD'], 'I want food.'),
    (['MY','BAG','RED'], 'My bag is red.'),
    (['TODAY','I','GO','HOSPITAL'], 'Today I go to the hospital.'),
    (['I','NOT','WANT','FOOD'], 'I do not want food.'),
])
def test_content_preserving_sentence(tokens, sentence):
    assert local_sentence.validate_suggestion(tokens, sentence) == sentence


@pytest.mark.parametrize('tokens,sentence', [
    (['I','WANT','FOOD'], 'I want pizza.'),
    (['I','WANT','FOOD'], 'You want food.'),
    (['I','NOT','WANT','FOOD'], 'I want food.'),
    (['I','WANT','FOOD'], 'I do not want food.'),
    (['I','WANT','FOOD'], 'I want food in hospital.'),
    (['I','WANT','FOOD'], 'Sentence: I want food.'),
    (['I','WANT','FOOD'], 'I want food.\nThis is a translation.'),
    (['I','HAVE','2','BAG'], 'I have 3 bag.'),
])
def test_changed_content_is_rejected(tokens, sentence):
    assert local_sentence.validate_suggestion(tokens, sentence) is None


def test_no_model_needed_for_empty_uncertain_or_untranslated_labels(monkeypatch):
    def forbidden(*args):
        pytest.fail('Language model must not run')
    monkeypatch.setattr(local_sentence, '_run_local_model', forbidden)
    assert local_sentence.generate_spoken_sentence([]).status == 'empty'
    assert local_sentence.generate_spoken_sentence(['I','WANT','FOOD'], uncertain=True).status == 'fallback'
    assert local_sentence.generate_spoken_sentence(['SOURCE1 KUNU']).status == 'unsupported'


def test_missing_model_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'sentence_model_dir', tmp_path/'missing')
    assert local_sentence.generate_spoken_sentence(['I','WANT','FOOD']).status == 'fallback'


def test_model_result_is_checked(tmp_path, monkeypatch):
    (tmp_path/'model.safetensors').write_bytes(b'test-placeholder')
    (tmp_path/'config.json').write_text('{}')
    monkeypatch.setattr(settings, 'sentence_model_dir', tmp_path)
    monkeypatch.setattr(local_sentence, '_run_local_model', lambda *args: 'My bag is red.')
    result = local_sentence.generate_spoken_sentence(['MY','BAG','RED'])
    assert result.status == 'suggested' and result.text == 'My bag is red.'
    monkeypatch.setattr(local_sentence, '_run_local_model', lambda *args: 'My bag is blue.')
    assert local_sentence.generate_spoken_sentence(['MY','BAG','RED']).status == 'fallback'


@pytest.mark.parametrize('word',['HATE','DIE','STOP','ENOUGH','ANNOYING','IDIOT','LOSER','DISGUST','STUPID'])
def test_every_known_angry_word_has_fallback_without_model(word,tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'sentence_model_dir',tmp_path/'missing')
    result=local_sentence.generate_spoken_sentence([word])
    assert result.text and word.lower() in result.text
    assert result.status=='fallback' and result.model_name=='Word-based fallback'


@pytest.mark.parametrize('tokens,expected',[
    (['MY','SON','STUPID'],'My son is stupid.'),
    (['WE','IDIOT'],'We are idiots.'),
    (['OUR','CHILDREN','ANNOYING'],'Our children are annoying.'),
])
def test_known_fallback_grammar(tokens,expected,tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'sentence_model_dir',tmp_path/'missing')
    result=local_sentence.generate_spoken_sentence(tokens)
    assert result.text==expected and result.status=='fallback'
