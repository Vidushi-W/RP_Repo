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



def test_expression_settings_api(client):
    assert client.get('/api/studio/expression-rules').json()['words']==['HATE','DIE','STOP','ENOUGH','ANNOYING','IDIOT','LOSER','DISGUST','STUPID']
    updated=client.put('/api/studio/expression-rules',json={'enabled':True,'words':[' hate ','HATE']})
    assert updated.status_code==200 and updated.json()['words']==['HATE']
    assert client.get('/api/studio/expression-rules').json()['words']==['HATE']
    assert client.put('/api/studio/expression-rules',json={'enabled':True,'words':['*HATE*']}).status_code==400
    assert client.get('/api/studio/expression-rules').json()['words']==['HATE']


@pytest.mark.parametrize('prediction,answer,enabled,expected_label', [
    (['I','HATE','BAT'],'I|LIKE|BAT',True,'angry'),
    (['I','LIKE','BAT'],'I|HATE|BAT',True,None),
    (['I','HATE','BAT'],'I|HATE|BAT',False,None),
])
def test_expression_uses_predictions_and_does_not_change_metrics(client,db_session,monkeypatch,prediction,answer,enabled,expected_label):
    from app.ml.local_sentence import SpokenSentence
    model(db_session)
    client.put('/api/studio/expression-rules',json={'enabled':enabled,'words':['HATE']})
    key=('recording_id,ordered_sign_labels\nunknown,'+answer+'\n').encode()
    response=client.post('/api/studio/data/tests',files=[('files',('unknown.csv',sample(),'text/csv')),('answer_key',('answers.csv',key,'text/csv'))])
    assert response.status_code==200
    row=client.get('/api/studio/tests').json()[0]
    monkeypatch.setattr(studio,'load_bundle',lambda _:object())
    monkeypatch.setattr(studio,'recognize_from_csv',lambda *_:SimpleNamespace(predicted_signs=prediction,decoder_score=.9,inference_ms=1.))
    predicted=client.post('/api/studio/tests/'+row['id']+'/run').json()['result']
    assert predicted['expression']['label']==expected_label
    original_metrics=predicted['metrics'].copy()
    phrase='I hate this bat.' if 'HATE' in prediction else 'I like the bat.'
    calls=[]
    def suggest(words,uncertain=False):
        calls.append(words)
        return SpokenSentence(phrase,'suggested','AI suggestion')
    monkeypatch.setattr(studio,'generate_spoken_sentence',suggest)
    result=client.post('/api/studio/tests/'+row['id']+'/sentence',json={'recognition_id':predicted['recognition_id']})
    assert result.status_code==200,result.text
    assert result.json()['text']==phrase
    assert result.json()['display_text']==phrase+(' [angry]' if expected_label else '')
    assert result.json()['expression']['label']==expected_label
    assert calls==[prediction]
    stored=client.get('/api/studio/tests').json()[0]['result']
    assert stored['metrics']==original_metrics
    assert stored['predicted_signs']==prediction


def test_training_uses_only_selected_collections(client, db_session, monkeypatch):
    selected = client.post('/api/studio/data/training', files=[
        ('files', ('a.csv', sample(offset=.01, label='I'), 'text/csv')),
        ('files', ('b.csv', sample(offset=.02, label='I'), 'text/csv')),
    ]).json()['dataset_id']
    excluded = client.post('/api/studio/data/training', files={
        'files': ('c.csv', sample(offset=.03, label='EXCLUDED'), 'text/csv')
    }).json()['dataset_id']
    rows = DatasetService(db_session).repo.list_recordings(selected)
    rows[0].split = 'train'
    rows[1].split = 'val'
    db_session.commit()
    captured = []
    monkeypatch.setattr(studio.TrainingService, 'start_training',
        lambda self, payload: (captured.append(payload) or SimpleNamespace(id=123)))
    assert client.post('/api/studio/collections', json={'dataset_ids': [selected]}).status_code == 200
    overview = client.get('/api/studio/overview').json()
    assert overview['included_dataset_ids'] == [selected]
    assert overview['training_recordings'] == 2
    response = client.post('/api/studio/train', json={'epochs': 1})
    assert response.status_code == 200, response.text
    assert captured[0]['dataset_ids'] == [selected]
    assert set(captured[0]['studio_recording_ids']) == {r.id for r in rows}
    assert excluded not in captured[0]['dataset_ids']
    assert client.post('/api/studio/collections', json={'dataset_ids': []}).status_code == 200
    assert client.post('/api/studio/train', json={'epochs': 1}).status_code == 400
    assert len(captured) == 1


def test_overview_removes_deleted_collection_from_saved_selection(client, db_session):
    uploaded = client.post('/api/studio/data/training', files={
        'files': ('train.csv', sample(label='I'), 'text/csv')
    }).json()
    selected = uploaded['dataset_id']
    (settings.data_dir / 'studio_collections.json').write_text(json.dumps([selected, 999999]))
    overview = client.get('/api/studio/overview').json()
    assert overview['included_dataset_ids'] == [selected]
    assert client.post('/api/studio/collections', json={
        'dataset_ids': [i for i in overview['included_dataset_ids'] if i != selected]
    }).status_code == 200
    assert client.get('/api/studio/overview').json()['training_recordings'] == 0


def test_accuracy_recomputed_with_coverage_and_no_unlabelled_successes():
    def row(rid, ref, pred, **extra):
        return dict(id=rid, expected_signs=ref, result=dict(model_id=3, evaluation_version=2,
            predicted_signs=pred, metrics={'exact_match': True}, motion_fingerprint=rid, **extra))
    rows=[row('a',['I'],['I']), row('b',['I'],['YOU']), row('c',[],['I']),
          dict(id='d',expected_signs=['I'],result=None),
          dict(id='e',expected_signs=['I'],result={'model_id':2,'evaluation_version':2,'predicted_signs':['I']}),
          row('f',['I'],['I'],accuracy_excluded_reason='Training copy')]
    score=studio.evaluation_summary(rows,3)
    assert score['accuracy']==.5 and score['exact_matches']==1
    assert score['evaluated_recordings']==2 and score['labelled_test_recordings']==5
    assert score['pending_evaluations']==2 and score['excluded_evaluations']==1
    assert score['unlabelled_test_recordings']==1 and score['sign_error_rate']==.5
    assert score['accuracy_interval'][0]<.5<score['accuracy_interval'][1]
    score=studio.evaluation_summary([row('only',['I'],['I'])],3)
    assert score['accuracy']==1 and score['accuracy_interval'][0]<.5


def test_duplicate_test_does_not_inflate_accuracy():
    a=dict(id='a',expected_signs=['I'],result=dict(model_id=3,evaluation_version=2,
        predicted_signs=['I'],motion_fingerprint='same'))
    b=dict(id='b',expected_signs=['I'],result=dict(a['result']))
    score=studio.evaluation_summary([a,b],3)
    assert score['evaluated_recordings']==1 and score['excluded_evaluations']==1
    assert score['sign_error_rate']==0


def test_validation_and_ancestor_training_copy_excluded(client,db_session,monkeypatch):
    uploaded=client.post('/api/studio/data/training',files={'files':('train.csv',sample(label='I'),'text/csv')}).json()
    r=DatasetService(db_session).repo.list_recordings(uploaded['dataset_id'])[0]
    r.split='test';db_session.commit()
    m=model(db_session)
    current=settings.artifacts_dir/m.bundle_path;current.mkdir(parents=True)
    ancestor=settings.artifacts_dir/'models'/'previous';ancestor.mkdir(parents=True)
    (current/'training_sources.json').write_text('[]')
    (current/'training_settings.json').write_text(json.dumps({'source_bundle_path':str(ancestor.resolve())}))
    (ancestor/'training_sources.json').write_text(json.dumps([{'id':r.id,'split':'val'}]))
    assert r.id in studio.exposed_recording_ids(db_session,m)
    # An identical signal with a different absolute clock must also be excluded.
    shifted=pd.read_csv(io.BytesIO(sample()));shifted.timestamp_ms+=500
    client.post('/api/studio/data/tests',files=[('files',('copy.csv',shifted.to_csv(index=False).encode(),'text/csv')),
        ('answer_key',('answers.csv',b'recording_id,ordered_sign_labels\ncopy,I\n','text/csv'))])
    t=client.get('/api/studio/tests').json()[0]
    monkeypatch.setattr(studio,'load_bundle',lambda _:object())
    monkeypatch.setattr(studio,'recognize_from_csv',lambda *_:SimpleNamespace(predicted_signs=['I'],decoder_score=.9,inference_ms=1.))
    result=client.post('/api/studio/tests/'+t['id']+'/run').json()['result']
    assert result['metrics'] is None and result['accuracy_excluded_reason']


def test_delete_test_removes_files_and_updates_accuracy(client,db_session):
    m=model(db_session)
    result=client.post('/api/studio/data/tests',files=[
        ('files',('one.csv',sample(),'text/csv')),
        ('files',('two.csv',sample(offset=.1),'text/csv')),
        ('answer_key',('answers.csv',b'recording_id,ordered_sign_labels\none,I\ntwo,I\n','text/csv'))])
    assert result.status_code==200
    rows=client.get('/api/studio/tests').json()
    for i,row in enumerate(rows):
        row['result']=dict(model_id=m.id,evaluation_version=2,predicted_signs=['I'] if i==0 else ['YOU'],motion_fingerprint=row['id'])
        studio.save_test_record(row)
    assert client.get('/api/studio/overview').json()['accuracy']==.5
    removed=rows[0]['id'];kept=rows[1]['id']
    assert client.delete('/api/studio/tests/'+removed).status_code==200
    assert not (studio.test_dir()/(removed+'.csv')).exists()
    assert not (studio.test_dir()/(removed+'.json')).exists()
    assert (studio.test_dir()/(kept+'.csv')).exists()
    overview=client.get('/api/studio/overview').json()
    assert overview['test_recordings']==1 and overview['evaluated_recordings']==1
    assert overview['accuracy']==0 and overview['model']['id']==m.id
    assert client.delete('/api/studio/tests/'+removed).status_code==404


def test_deleted_recording_cannot_be_restored_by_inflight_prediction(client,db_session,monkeypatch):
    model(db_session)
    client.post('/api/studio/data/tests',files={'files':('test.csv',sample(),'text/csv')})
    row=client.get('/api/studio/tests').json()[0]
    monkeypatch.setattr(studio,'load_bundle',lambda _:object())
    def predict(*args):
        studio.delete_test(row['id'])
        return SimpleNamespace(predicted_signs=['I'],decoder_score=.9,inference_ms=1.)
    monkeypatch.setattr(studio,'recognize_from_csv',predict)
    response=client.post('/api/studio/tests/'+row['id']+'/run')
    assert response.status_code==404
    assert client.get('/api/studio/tests').json()==[]
