"""One offline translation or speech request; process exit releases model memory."""
import json
import sys
import wave
from pathlib import Path

from speech_styles import SPEECH_STYLES


def main():
    request = json.loads(sys.stdin.read())
    if request['action'] == 'translate':
        import torch
        from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
        torch.set_num_threads(2)
        tokenizer = M2M100Tokenizer.from_pretrained(request['model_dir'], local_files_only=True)
        tokenizer.src_lang = 'en'
        model = M2M100ForConditionalGeneration.from_pretrained(request['model_dir'],
            local_files_only=True, trust_remote_code=False, use_safetensors=False)
        model.eval()
        encoded = tokenizer(request['text'], return_tensors='pt', truncation=False)
        if encoded['input_ids'].shape[1] > 256:
            raise ValueError('Sentence is too long for this translation request')
        with torch.inference_mode():
            tokens = model.generate(**encoded, forced_bos_token_id=tokenizer.get_lang_id('si'),
                max_new_tokens=192, num_beams=4, do_sample=False)
        text = tokenizer.batch_decode(tokens, skip_special_tokens=True)[0].strip()
        print(json.dumps(dict(text=text), ensure_ascii=True), flush=True)
    elif request['action'] == 'speak':
        from piper import PiperVoice, SynthesisConfig
        directory = Path(request['voice_dir']) / 'onnx'
        voice = PiperVoice.load(str(directory/'si_LK-dilu-medium.onnx'),
            config_path=str(directory/'si_LK-dilu-medium.onnx.json'), use_cuda=False)
        style = request.get('emotion') or 'normal'
        if style not in SPEECH_STYLES:
            raise ValueError('Unsupported speaking style')
        config = SynthesisConfig(**SPEECH_STYLES[style])
        with wave.open(request['output_file'], 'wb') as wav:
            voice.synthesize_wav(request['text'], wav, syn_config=config)
        print(json.dumps(dict(style=style, style_method='prosody_preset' if style != 'normal' else 'default_voice')), flush=True)
    else:
        raise ValueError('Unknown worker action')


if __name__ == '__main__':
    main()
