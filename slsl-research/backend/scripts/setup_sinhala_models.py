"""Install pinned offline Sinhala models. Downloads weights only; never uploads user data."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

MODELS = [
    dict(repo='facebook/m2m100_418M', revision='55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636',
        folder='m2m100-418m', weight='pytorch_model.bin', size=1935796948,
        sha256='d907ea45e4e4b9db163382a6674f6218b3c59566fe06d77f4055c208b4e87ed1',
        files=['README.md','config.json','generation_config.json','sentencepiece.bpe.model','special_tokens_map.json','tokenizer_config.json','vocab.json']),
    dict(repo='chaturadilan/dilu-tts', revision='437ddc177e948a1626a8a59fd48a4b6650a5cce3',
        folder='dilu-sinhala', weight='onnx/si_LK-dilu-medium.onnx', size=63531379,
        sha256='04f56c9ed332e976ff8549b6420387d1b39f59b502a897ebc6b2ea6745502b9d',
        files=['README.md','onnx/si_LK-dilu-medium.onnx.json']),
]


def checksum(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()


def install(model, directory, verify_only):
    directory.mkdir(parents=True,exist_ok=True)
    url=f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/"
    weight=directory/model['weight']
    valid=weight.is_file() and weight.stat().st_size==model['size'] and checksum(weight)==model['sha256']
    if verify_only and (not valid or any(not (directory/f).is_file() for f in model['files'])):
        raise RuntimeError(f"Missing or invalid model: {directory}")
    if not verify_only:
        for name in model['files']:
            target=directory/name;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.is_file():
                with urllib.request.urlopen(url+name+'?download=true',timeout=120) as response:target.write_bytes(response.read())
        if not valid:
            parts=directory/'.download-parts';parts.mkdir(exist_ok=True);chunk=4*1024*1024
            count=(model['size']+chunk-1)//chunk
            def fetch(index):
                lo=index*chunk;hi=min(model['size'],lo+chunk)-1;part=parts/f'{index:04d}.part'
                if part.exists() and part.stat().st_size==hi-lo+1:return
                for attempt in range(4):
                    try:
                        req=urllib.request.Request(url+model['weight']+f'?slsl_chunk={index}',headers={'Range':f'bytes={lo}-{hi}'})
                        with urllib.request.urlopen(req,timeout=90) as response:
                            if response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {lo}-{hi}/'):
                                raise RuntimeError('Download server did not honor byte range')
                            data=response.read()
                        if len(data)!=hi-lo+1:raise RuntimeError('Incomplete download chunk')
                        part.write_bytes(data);return
                    except Exception:
                        if attempt==3:raise
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                for done,_ in enumerate(pool.map(fetch,range(count)),1):
                    if done%16==0 or done==count:print(model['folder'],done,'/',count,'chunks',flush=True)
            temporary=weight.with_suffix('.verified-download');temporary.parent.mkdir(parents=True,exist_ok=True)
            with temporary.open('wb') as output:
                for i in range(count):output.write((parts/f'{i:04d}.part').read_bytes())
            if checksum(temporary)!=model['sha256']:raise RuntimeError('Model checksum mismatch')
            temporary.replace(weight)
            for i in range(count):(parts/f'{i:04d}.part').unlink()
            parts.rmdir()
    (directory/'download_manifest.json').write_text(json.dumps({k:v for k,v in model.items() if k!='files'},indent=2))
    print('Verified:',model['repo'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,default=Path(__file__).resolve().parents[2]/'local_models')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    for model in MODELS:install(model,args.destination.resolve()/model['folder'],args.verify_only)
