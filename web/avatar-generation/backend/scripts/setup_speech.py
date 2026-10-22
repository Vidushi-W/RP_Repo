"""Explicit one-time model download. Runtime inference never downloads models."""
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ['HF_HOME'] = str(ROOT / '.cache/huggingface')
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
from faster_whisper.utils import download_model

if __name__ == '__main__':
    target = ROOT / 'preprocessing/models/faster-whisper-base'
    print(download_model('base', output_dir=str(target)), flush=True)
