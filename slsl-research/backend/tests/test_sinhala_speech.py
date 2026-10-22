import io
import json
import wave
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from app.api.routes import studio
from app.core.config import SENSOR_COLUMNS, settings
from app.ml import sinhala_speech
from app.ml.local_sentence import SpokenSentence
from app.ml.expression_rules import save_rules
from app.models.ml_model import MLModel


def wav_bytes():
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(22050);w.writeframes(b'\x00\x00'*2205)
    return out.getvalue()


@pytest.fixture
def recognized(client,db_session,monkeypatch):
    model=MLModel(name='Test',version='1',status='active',bundle_path='models/test',vocabulary_json='{}')
    db_session.add(model);db_session.commit()
    frame=pd.DataFrame({c:np.zeros(40) for c in SENSOR_COLUMNS});frame.timestamp_ms=np.arange(40)*20
    response=client.post('/api/studio/data/tests',files=[('files',('motion.csv',frame.to_csv(index=False).encode(),'text/csv')),
        ('answer_key',('answers.csv',b'recording_id,ordered_sign_labels\nmotion,SECRET|ANSWER\n','text/csv'))])
    assert response.status_code==200
    row=client.get('/api/studio/tests').json()[0]
    monkeypatch.setattr(studio,'load_bundle',lambda _:object())
    monkeypatch.setattr(studio,'recognize_from_csv',lambda *_:SimpleNamespace(predicted_signs=['I','HATE','BAT'],decoder_score=.9,inference_ms=1.))
    monkeypatch.setattr(studio,'generate_spoken_sentence',lambda *_args,**_kwargs:SpokenSentence('I hate bats.','suggested','Test phrase'))
    return row['id']


@pytest.mark.parametrize('enabled',[True,False])
def test_translation_speech_separate_emotion_scoring_and_delete(client,recognized,monkeypatch,enabled):
    save_rules(enabled,['HATE'])
    rid=recognized
    run=client.post(f'/api/studio/tests/{rid}/run').json()['result']
    payload={'recognition_id':run['recognition_id']}
    assert client.post(f'/api/studio/tests/{rid}/sentence',json=payload).status_code==200
    calls=[]
    def translate(text):
        calls.append(('translate',text));return 'මම වවුලන්ට වෛර කරනවා.'
    def speak(text,emotion):
        calls.append(('speak',text,emotion));return wav_bytes()
    monkeypatch.setattr(sinhala_speech,'translate_sentence',translate)
    monkeypatch.setattr(sinhala_speech,'synthesize_sinhala',speak)
    translated=client.post(f'/api/studio/tests/{rid}/translate',json=payload)
    assert translated.status_code==200,translated.text
    t=translated.json();assert t['emotion']==('angry' if enabled else None)
    response=client.post(f'/api/studio/tests/{rid}/speech',json={**payload,'translation_id':t['translation_id']})
    assert response.status_code==200,response.text
    result=response.json();assert result['speech']['style_method']==('prosody_preset' if enabled else 'default_voice')
    assert calls==[('translate','I hate bats.'),('speak',t['text'],'angry' if enabled else None)]
    edited=client.patch(f'/api/studio/tests/{rid}/translation',json={**payload,'translation_id':t['translation_id'],'text':'මම වවුලන්ට වෛර කරනවා.'})
    assert edited.status_code==200 and edited.json()['status']=='edited'
    assert edited.json()['translation_id']!=t['translation_id'] and edited.json()['speech'] is None
    assert client.get(result['speech']['audio_url']).status_code==409
    t=edited.json()
    result=client.post(f'/api/studio/tests/{rid}/speech',json={**payload,'translation_id':t['translation_id']}).json()

    url=result['speech']['audio_url'];audio=client.get(url)
    assert audio.status_code==200 and audio.content==wav_bytes()
    after=client.get('/api/studio/tests').json()[0]['result']
    assert after['metrics']==run['metrics'] and after['predicted_signs']==run['predicted_signs']
    # Old audio is rejected after a new recognition, even if words are identical.
    client.post(f'/api/studio/tests/{rid}/run')
    assert client.get(url).status_code==409
    assert client.delete(f'/api/studio/tests/{rid}').status_code==200
    assert not list(sinhala_speech.audio_directory(rid).glob('*.wav'))
    assert client.get(url).status_code==404


def test_stale_translation_and_unknown_emotion_are_rejected(client,recognized,monkeypatch):
    rid=recognized;run=client.post(f'/api/studio/tests/{rid}/run').json()['result'];payload={'recognition_id':run['recognition_id']}
    client.post(f'/api/studio/tests/{rid}/sentence',json=payload)
    def translate(text):
        studio.delete_test(rid)
        return 'සිංහල වාක්‍යයක්.'
    monkeypatch.setattr(sinhala_speech,'translate_sentence',translate)
    assert client.post(f'/api/studio/tests/{rid}/translate',json=payload).status_code==404
    with pytest.raises(ValueError,match='not supported'):
        sinhala_speech.synthesize_sinhala('සිංහල','happy')


def test_translation_failure_keeps_english(client,recognized,monkeypatch):
    rid=recognized;run=client.post(f'/api/studio/tests/{rid}/run').json()['result'];payload={'recognition_id':run['recognition_id']}
    client.post(f'/api/studio/tests/{rid}/sentence',json=payload)
    def fail(text):raise sinhala_speech.SpeechUnavailable('Model unavailable')
    monkeypatch.setattr(sinhala_speech,'translate_sentence',fail)
    assert client.post(f'/api/studio/tests/{rid}/translate',json=payload).status_code==503
    result=client.get('/api/studio/tests').json()[0]['result']
    assert result['spoken_sentence']['text']=='I hate bats.'
    assert 'sinhala' not in result
