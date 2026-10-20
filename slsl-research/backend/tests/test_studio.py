import io
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import torch

from app.api.routes import studio
from app.core.config import SENSOR_COLUMNS, settings
from app.ml.continual import continuing_vocabulary, restore_training, optimizer_snapshot
from app.ml.models import CtcSignModel
from app.models.ml_model import MLModel
from app.services.dataset_service import DatasetService
from app.ml.trainer import TrainingConfig, run_training


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'data_dir', tmp_path / 'data')
    monkeypatch.setattr(settings, 'artifacts_dir', tmp_path / 'artifacts')


def sample(offset=0., label=None):
    data = pd.DataFrame({c: np.zeros(40) for c in SENSOR_COLUMNS})
    data['timestamp_ms'] = np.arange(40)*20
    data['left_flex_1'] = np.linspace(.1,.4,40) + offset
    if label:
        data['ordered_sign_labels'] = label
    return data.to_csv(index=False).encode()


def model(db):
    item = MLModel(name='SLSL Model', version='1', status='active', bundle_path='models/test',
                   vocabulary_json=json.dumps({'labels':['<blank>','I','NEED','WATER']}))
    db.add(item); db.commit()
    return item


def test_inline_labels_separated_and_invalid_upload_atomic(client, db_session):
    result = client.post('/api/studio/data/training',files={'files':('train.csv',sample(label='I|NEED|WATER'),'text/csv')})
    assert result.status_code == 200, result.text
    records = DatasetService(db_session).repo.list_recordings(result.json()['dataset_id'])
    assert records[0].ordered_sign_labels == 'I|NEED|WATER'
    stored = pd.read_csv(settings.data_dir/records[0].file_path)
    assert stored.columns.tolist() == SENSOR_COLUMNS
    assert 'ordered_sign_labels' not in stored
    before = len(DatasetService(db_session).list_datasets())
    bad = client.post('/api/studio/data/training', files={'files':('bad.csv',sample(),'text/csv')})
    assert bad.status_code == 400
    assert len(DatasetService(db_session).list_datasets()) == before


def test_test_answers_used_only_after_sensor_inference(client, db_session, monkeypatch):
    model(db_session)
    answer = b'recording_id,ordered_sign_labels\nunknown,I|NEED|WATER\n'
    response = client.post('/api/studio/data/tests', files=[('files',('unknown.csv',sample(label='WRONG|LABEL'),'text/csv')),
        ('answer_key',('answers.csv',answer,'text/csv'))])
    assert response.status_code == 200, response.text
    rows=client.get('/api/studio/tests').json()
    calls=[]
    def recognize(path, bundle):
        assert pd.read_csv(path).columns.tolist() == SENSOR_COLUMNS
        calls.append(path)
        return SimpleNamespace(predicted_signs=['I','NEED','WATER'],decoder_score=.9,inference_ms=1.)
    monkeypatch.setattr(studio,'load_bundle',lambda _:object())
    monkeypatch.setattr(studio,'recognize_from_csv',recognize)
    result=client.post('/api/studio/tests/'+rows[0]['id']+'/run').json()
    assert len(calls)==1
    assert result['result']['metrics']['exact_match'] is True
    assert client.get('/api/studio/overview').json()['accuracy']==1.
    # Re-uploading a file does not count it twice in accuracy.
    client.post('/api/studio/data/tests',files={'files':('unknown.csv',sample(),'text/csv')})
    assert len(client.get('/api/studio/tests').json())==1


def test_training_copy_excluded_from_accuracy(client,db_session,monkeypatch):
    client.post('/api/studio/data/training',files={'files':('train.csv',sample(label='I|NEED|WATER'),'text/csv')})
    from app.models.dataset import Recording
    from sqlalchemy import select
    record=db_session.scalar(select(Recording));record.split='train';db_session.commit()
    model(db_session)
    client.post('/api/studio/data/tests',files=[('files',('same.csv',sample(),'text/csv')),
        ('answer_key',('answers.csv',b'recording_id,ordered_sign_labels\nsame,I|NEED|WATER\n','text/csv'))])
    test=client.get('/api/studio/tests').json()[0]
    monkeypatch.setattr(studio,'load_bundle',lambda _:object())
    monkeypatch.setattr(studio,'recognize_from_csv',lambda *_:SimpleNamespace(predicted_signs=['I','NEED','WATER'],decoder_score=.9,inference_ms=1.))
    result=client.post('/api/studio/tests/'+test['id']+'/run').json()['result']
    assert result['metrics'] is None and result['accuracy_excluded_reason']
    assert client.get('/api/studio/overview').json()['accuracy'] is None


def test_vocab_expansion_preserves_weights_and_optimizer(tmp_path):
    source=tmp_path/'source';source.mkdir()
    vocab=continuing_vocabulary(['I','WATER'],None)
    (source/'vocabulary.json').write_text(json.dumps(vocab))
    old=CtcSignModel(num_classes=3)
    opt=torch.optim.Adam(old.parameters())
    old(torch.randn(1,12,22))[0].square().mean().backward();opt.step()
    torch.save(old.state_dict(),source/'model.pt')
    torch.save(optimizer_snapshot(opt),source/'optimizer.pt')
    expanded=continuing_vocabulary(['HELLO','I'],source)
    assert expanded['labels'][:3]==vocab['labels']
    assert expanded['label_to_id']['HELLO']==3
    new=CtcSignModel(num_classes=4)
    new_opt=torch.optim.Adam(new.parameters())
    assert restore_training(new,new_opt,source)
    assert torch.equal(new.classifier.weight[:3],old.classifier.weight)
    assert torch.equal(new.backbone.conv[0].weight,old.backbone.conv[0].weight)
    assert torch.count_nonzero(new_opt.state[new.classifier.weight]['exp_avg'][3])==0
    new_opt.zero_grad();new(torch.randn(1,12,22))[0].sum().backward();new_opt.step()


def test_real_training_resumes_normalization_and_adds_vocabulary(db_session,tmp_path):
    svc=DatasetService(db_session)
    ds=svc.generate_synthetic({'name':'Continuation','total_recordings':30,'seed':42})
    recordings=svc.repo.list_recordings(ds.id)
    training=[r for r in recordings if r.split=='train']
    validation=[r for r in recordings if r.split=='val']
    first=tmp_path/'first'
    run_training(training,validation,TrainingConfig(dataset_id=ds.id,dataset_version='1',provenance='synthetic',epochs=1),first)
    old_vocab=json.loads((first/'vocabulary.json').read_text())
    # Add a new target token without replacing any existing vocabulary IDs.
    training[0].ordered_sign_labels += '|NEW_SIGN'
    second=tmp_path/'second'
    result=run_training(training,validation,TrainingConfig(dataset_id=ds.id,dataset_version='1',provenance='synthetic',epochs=1,
        training_mode='finetune',source_bundle_path=str(first)),second)
    new_vocab=json.loads((second/'vocabulary.json').read_text())
    assert new_vocab['labels'][:len(old_vocab['labels'])]==old_vocab['labels']
    assert 'NEW_SIGN' in new_vocab['labels']
    assert result['metrics']['optimizer_resumed'] is True
    assert (first/'preprocessing.json').read_bytes()==(second/'preprocessing.json').read_bytes()
    assert not (second/'emotion_model.pkl').exists()


def test_collection_selection_and_reset_keep_data(client,db_session):
    uploaded=client.post('/api/studio/data/training',files={'files':('train.csv',sample(label='I'),'text/csv')}).json()
    model(db_session)
    assert client.post('/api/studio/collections',json={'dataset_ids':[]}).status_code==200
    assert client.get('/api/studio/overview').json()['training_recordings']==0
    assert client.post('/api/studio/reset',json={'confirmation':'RESET'}).status_code==200
    assert client.get('/api/studio/overview').json()['model'] is None
    assert DatasetService(db_session).repo.list_recordings(uploaded['dataset_id'])


@pytest.mark.parametrize("has_model", [False, True])
def test_overview_with_unrun_test_recordings(client, db_session, has_model):
    if has_model:
        model(db_session)
    response = client.post('/api/studio/data/tests', files={
        'files': ('unrun.csv', sample(), 'text/csv')
    })
    assert response.status_code == 200
    assert client.get('/api/studio/tests').json()[0]['result'] is None
    for _ in range(2):
        response = client.get('/api/studio/overview')
        assert response.status_code == 200
        overview = response.json()
        assert overview['test_recordings'] == 1
        assert overview['evaluated_recordings'] == 0
        assert overview['accuracy'] is None



def test_local_sentence_only_sees_predictions_and_preserves_scores(client, db_session, monkeypatch):
    from app.ml.local_sentence import SpokenSentence
    model(db_session)
    client.post('/api/studio/data/tests', files=[
        ('files', ('unknown.csv', sample(), 'text/csv')),
        ('answer_key', ('answers.csv', b'recording_id,ordered_sign_labels\nunknown,SECRET|ANSWER\n', 'text/csv'))
    ])
    row=client.get('/api/studio/tests').json()[0]
    monkeypatch.setattr(studio,'load_bundle',lambda _: object())
    monkeypatch.setattr(studio,'recognize_from_csv',lambda *_:SimpleNamespace(predicted_signs=['MY','BAG','RED'], decoder_score=.9, inference_ms=1.))
    predicted=client.post('/api/studio/tests/'+row['id']+'/run').json()['result']
    calls=[]
    def suggest(tokens, uncertain=False):
        calls.append((tokens, uncertain))
        return SpokenSentence('My bag is red.', 'suggested', 'Local AI suggestion')
    monkeypatch.setattr(studio,'generate_spoken_sentence',suggest)
    response=client.post('/api/studio/tests/'+row['id']+'/sentence',json={'recognition_id':predicted['recognition_id']})
    assert response.status_code==200, response.text
    assert response.json()['text']=='My bag is red.'
    assert calls==[(['MY','BAG','RED'],False)]
    stored=client.get('/api/studio/tests').json()[0]['result']
    assert stored['predicted_signs']==predicted['predicted_signs']
    assert stored['metrics']==predicted['metrics']
    assert stored['spoken_sentence']['status']=='suggested'
    # A new recognition invalidates an older sentence request.
    client.post('/api/studio/tests/'+row['id']+'/run')
    stale=client.post('/api/studio/tests/'+row['id']+'/sentence',json={'recognition_id':predicted['recognition_id']})
    assert stale.status_code==409


def test_local_sentence_never_overwrites_newer_motion_prediction(client, db_session, monkeypatch):
    from app.ml.local_sentence import SpokenSentence
    model(db_session)
    client.post('/api/studio/data/tests',files={'files':('unknown.csv',sample(),'text/csv')})
    row=client.get('/api/studio/tests').json()[0]
    monkeypatch.setattr(studio,'load_bundle',lambda _:object())
    monkeypatch.setattr(studio,'recognize_from_csv',lambda *_:SimpleNamespace(predicted_signs=['I','WANT','FOOD'],decoder_score=.9,inference_ms=1.))
    predicted=client.post('/api/studio/tests/'+row['id']+'/run').json()['result']
    def suggest(*args, **kwargs):
        updated=studio.test_records()[0]
        updated['result']['recognition_id']='newer-prediction'
        studio.save_test_record(updated)
        return SpokenSentence('I want food.','suggested','Local AI suggestion')
    monkeypatch.setattr(studio,'generate_spoken_sentence',suggest)
    response=client.post('/api/studio/tests/'+row['id']+'/sentence',json={'recognition_id':predicted['recognition_id']})
    assert response.status_code==409
    stored=client.get('/api/studio/tests').json()[0]['result']
    assert stored['recognition_id']=='newer-prediction'
    assert 'spoken_sentence' not in stored
