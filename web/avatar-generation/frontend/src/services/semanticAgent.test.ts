import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseSemanticResult, processTranscript } from './semanticAgent';
import { assetUrl } from './animationLoader';
import { loadAnimation } from './animationLoader';
import calibration from '../../public/hand-animations/fixtures/calibration-a.json';
const pending={englishText:'nurse',signs:['NURSE'],researchPreview:true,unsupported:[],matches:[{signId:'NURSE',canonicalLabel:'nurse',evidence:'nurse',explanation:'Registry match',method:'verified vocabulary',animationFile:'hand-animations/recorded/nurse.json',reviewStatus:'pending'}],manifest:{schemaVersion:1,fixture:false,signs:[{signId:'NURSE',label:'nurse',aliases:['nurse'],animationUrl:'hand-animations/recorded/nurse.json',datasetReference:'Owner recording, review pending',reviewed:false,sha256:'0'.repeat(64)}]}};
afterEach(()=>vi.unstubAllGlobals());
describe('semantic transcript boundary',()=>{
  it('requires explicit preview mode for pending recordings',()=>{
    expect(parseSemanticResult(pending,true).signs).toEqual(['NURSE']);
    expect(()=>parseSemanticResult({...pending,researchPreview:false},false)).toThrow('reviewed');
    expect(()=>parseSemanticResult(pending,false)).toThrow();
  });
  it('rejects invented paths or mismatched queue order',()=>{
    expect(()=>parseSemanticResult({...pending,signs:['PHONE']},true)).toThrow();
    expect(()=>parseSemanticResult({...pending,matches:[{...pending.matches[0],animationFile:'../secret.json'}]},true)).toThrow();
  });
  it('accepts speech transcripts through the same API without frontend keys',async()=>{
    const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>pending});vi.stubGlobal('fetch',fetcher);
    expect((await processTranscript('nurse',true)).signs).toEqual(['NURSE']);
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({text:'nurse',researchPreview:true});
    expect(fetcher.mock.calls[0][1].headers).toEqual({'Content-Type':'application/json'});
  });
  it('surfaces failed AI requests without silently switching to keyword matching',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:'AI request failed'})}));
    await expect(processTranscript('The nurse is working')).rejects.toThrow('AI request failed');
  });
  it('preserves and URL-encodes Sinhala filenames while rejecting traversal',()=>{
    const sinhalaFilename='\u0dc4\u0dd9\u0daf\u0dd2\u0dba.json';
    expect(assetUrl('hand-animations/recorded/'+sinhalaFilename)).toContain(encodeURIComponent(sinhalaFilename));
    expect(()=>assetUrl('hand-animations/%2e%2e/secret.json')).toThrow();
    expect(()=>assetUrl('hand-animations/../secret.json')).toThrow();
  });
  it('checks the downloaded bytes before reading stored keyframes',async()=>{
    const bytes=new TextEncoder().encode(JSON.stringify({...calibration,signId:'NURSE',metadata:{...calibration.metadata,fixture:false}}));
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
    const manifest=parseSemanticResult(pending,true).manifest;
    manifest.signs[0].sha256=hash;
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,arrayBuffer:async()=>bytes.buffer}));
    expect((await loadAnimation('NURSE',manifest)).frames).toEqual(calibration.frames);
    manifest.signs[0].sha256='0'.repeat(64);
    await expect(loadAnimation('NURSE',manifest)).rejects.toThrow('checksum');
  });
  it('keeps a recognized PHONE concept separate from an empty playback queue',()=>{
    const result=parseSemanticResult({englishText:'cellphone',signs:[],researchPreview:false,matches:[],unsupported:['PHONE has no animation'],manifest:{schemaVersion:1,fixture:false,signs:[]},concepts:[{concept:'PHONE',evidence:'cellphone',animationAvailable:false}],inference:{performed:true,model:'qwen3:1.7b',mode:'structured-output orchestration'}},false);
    expect(result.concepts[0].concept).toBe('PHONE');
    expect(result.concepts[0].animationAvailable).toBe(false);
    expect(result.signs).toEqual([]);
    expect(result.inference?.model).toBe('qwen3:1.7b');
  });
  it('rejects malformed concept metadata instead of handing it to playback',()=>{
    expect(()=>parseSemanticResult({...pending,concepts:[{concept:'PHONE',evidence:'phone',animationAvailable:'yes'}]},true)).toThrow('concept');
  });
});

