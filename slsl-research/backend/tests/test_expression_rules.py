import pytest
from app.core.config import settings
from app.ml.expression_rules import DEFAULT_ANGRY_WORDS, analyze_expression, annotate_sentence, load_rules, save_rules
from app.ml.local_sentence import validate_suggestion


@pytest.mark.parametrize('word', DEFAULT_ANGRY_WORDS)
def test_each_configured_word_marks_angry(word):
    result=analyze_expression(['I',word.lower(),'BAT'])
    assert result['label']=='angry'
    assert result['matched_words']==[word]
    assert result['source']=='configured_keyword_rule'
    assert result['rules_fingerprint']


def test_whole_words_only_and_no_neutral_guess():
    result=analyze_expression(['BUS STOP','HATES','DYING','STUPIDITY'])
    assert result['label'] is None
    assert result['status']=='not_matched'
    assert analyze_expression([])['label'] is None


def test_keyword_rule_does_not_infer_negation_or_context():
    result=analyze_expression(['I','NEVER','HATE','BAT','HATE'])
    assert result['label']=='angry' and result['matched_words']==['HATE']


def test_custom_rules_disabled_and_restored():
    save_rules(True,[' hate ','HATE'])
    assert load_rules()['words']==['HATE']
    assert analyze_expression(['STOP'])['label'] is None
    save_rules(False,['HATE'])
    assert analyze_expression(['HATE'])['status']=='disabled'
    save_rules(True,DEFAULT_ANGRY_WORDS)
    assert analyze_expression(['STOP'])['label']=='angry'


def test_suffix_is_separate_from_plain_english():
    plain={'text':'I hate this bat.','status':'suggested','message':'AI suggestion'}
    result=annotate_sentence(plain,analyze_expression(['I','HATE','BAT']))
    assert result['text']=='I hate this bat.'
    assert result['display_text']=='I hate this bat. [angry]'
    assert 'display_text' not in plain
    assert annotate_sentence({'text':''},analyze_expression(['HATE']))['display_text']==''
    assert annotate_sentence({'text':'I like the bat.'},analyze_expression(['I','LIKE','BAT']))['display_text']=='I like the bat.'


def test_invalid_rules_visible_and_repairable():
    settings.data_dir.mkdir(parents=True,exist_ok=True)
    (settings.data_dir/'expression_rules.json').write_text('{invalid')
    assert analyze_expression(['HATE'])['status']=='unavailable'
    assert analyze_expression(['HATE'])['label'] is None
    save_rules(True,DEFAULT_ANGRY_WORDS)
    assert analyze_expression(['HATE'])['label']=='angry'


def test_requested_sentence_grammar_is_accepted_without_emotion_in_lm_text():
    assert validate_suggestion(['I','HATE','BAT'],'I hate this bat.')=='I hate this bat.'
    assert validate_suggestion(['I','HATE','BAT'],'I hate bats.')=='I hate bats.'
    assert validate_suggestion(['I','HATE','BAT'],'I hate cats.') is None
    assert validate_suggestion(['HE','HATE','BAT'],'He hates the bat.')=='He hates the bat.'
    assert validate_suggestion(['STOP','TALK'],'Stop talking.')=='Stop talking.'
    assert validate_suggestion(['YOU','IDIOT'],'You are an idiot.')=='You are an idiot.'
    assert validate_suggestion(['I','HATE','BAT'],'I hate this bat. [angry]') is None
