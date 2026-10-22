"""One-time download from the official Qwen repository. No user recordings are uploaded.

Resumable range downloads, pinned revision, full weights SHA-256 verification.
Run with --destination and set SLSL_SENTENCE_MODEL_DIR in backend/.env if desired.
"""
import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.request
from pathlib import Path

parser=argparse.ArgumentParser(description='Install the pinned local spoken-English model once; subsequent inference is offline.')
parser.add_argument('--destination', type=Path, default=Path(__file__).resolve().parents[2]/'local_models'/'qwen2.5-0.5b-instruct')
directory=parser.parse_args().destination.resolve()
directory.mkdir(parents=True,exist_ok=True)
revision='7ae557604adf67be50417f59c2c2f167def9a775'
base='https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/resolve/'+revision+'/'
size=988097824
expected='fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe'
for filename in ['LICENSE','README.md','config.json','generation_config.json','merges.txt','tokenizer.json','tokenizer_config.json','vocab.json']:
    path=directory/filename
    if not path.is_file():
        print('Downloading',filename,flush=True)
        with urllib.request.urlopen(base+filename+'?download=true',timeout=60) as response:
            path.write_bytes(response.read())

existing=directory/'model.safetensors'
if existing.is_file() and existing.stat().st_size==size:
    checksum=hashlib.sha256()
    with existing.open('rb') as source:
        while data:=source.read(1024*1024):checksum.update(data)
    if checksum.hexdigest()==expected:
        print('Verified local model already installed:', directory,flush=True)
        raise SystemExit(0)
parts=directory/'.download-parts'
parts.mkdir(exist_ok=True)
chunk=8*1024*1024
count=(size+chunk-1)//chunk
started=time.time()

def download(index):
    start=index*chunk; end=min(size,start+chunk)-1
    path=parts/f'{index:04d}.part'
    if path.exists() and path.stat().st_size==end-start+1:return index
    for attempt in range(4):
        try:
            request=urllib.request.Request(base+'model.safetensors?download=true&slsl_chunk='+str(index),headers={'Range':f'bytes={start}-{end}'})
            with urllib.request.urlopen(request,timeout=60) as response:
                assert response.status==206 and response.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/')
                with path.open('wb') as f:
                    while data:=response.read(256*1024):f.write(data)
            assert path.stat().st_size==end-start+1
            return index
        except Exception:
            if attempt==3:raise
    raise RuntimeError(index)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for completed,_ in enumerate(pool.map(download,range(count)),1):
        if completed%8==0 or completed==count:print(f'Weights: {min(completed*chunk,size)/1e6:.0f}/{size/1e6:.0f} MB; elapsed {time.time()-started:.0f}s',flush=True)

destination=directory/'model.safetensors'
digest=hashlib.sha256()
with destination.with_suffix('.verified-download').open('wb') as target:
    for i in range(count):
        with (parts/f'{i:04d}.part').open('rb') as source:
            while data:=source.read(1024*1024):target.write(data);digest.update(data)
assert digest.hexdigest()==expected
destination.with_suffix('.verified-download').replace(destination)
for filename in ['tokenizer.json','tokenizer_config.json','vocab.json']:
    print('Downloading',filename,flush=True)
    with urllib.request.urlopen(base+filename+'?download=true',timeout=60) as response:
        (directory/filename).write_bytes(response.read())
manifest=dict(repository='Qwen/Qwen2.5-0.5B-Instruct',revision=revision,weights_sha256=expected,weights_bytes=size)
(directory/'download_manifest.json').write_text(json.dumps(manifest,indent=2))
for p in parts.glob('*.part'):p.unlink()
parts.rmdir()
print('VERIFIED local model ready',flush=True)
