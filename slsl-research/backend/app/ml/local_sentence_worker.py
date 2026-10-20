"""One CPU-only local LM request. Process exit releases model RAM."""
import json
import sys


def main():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    request = json.loads(sys.stdin.read())
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(request['model_dir'], local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(request['model_dir'], local_files_only=True,
        trust_remote_code=False, use_safetensors=True, dtype=torch.float32)
    model.eval()
    # Keep full-precision CPU inference: dynamic int8 degraded instruction following
    # in the local phrase checks. Process exit still releases the model's RAM.
    messages = [
        {'role': 'system', 'content': 'Rewrite telegraphic English as one short grammatical sentence. Preserve all supplied content words and meaning. Add only grammar words. Do not guess a new subject, object, action, place, or time. Reply with the sentence only.'},
        {'role': 'user', 'content': ' '.join(request['tokens'])},
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors='pt')
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=48, do_sample=False, stop_strings=["\n"], tokenizer=tokenizer,
            pad_token_id=tokenizer.eos_token_id, use_cache=True)
    sentence = tokenizer.decode(output[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
    print(json.dumps({'sentence': sentence}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
