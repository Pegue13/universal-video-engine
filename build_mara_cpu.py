"""Independently render the remaining segments with the published Spain Spanish Chatterbox weights and publisher reference. No requests to the public GPU demo."""
import sys,os,pathlib,urllib.request,random,time,gc
from build_mara_full_speech import BLOCKS,clip,validate,log,assemble
import numpy as np
import torch
import torchaudio
from huggingface_hub import snapshot_download,hf_hub_download
torch.set_num_threads(2)
torch.set_num_interop_threads(1)
os.environ["TOKENIZERS_PARALLELISM"]="false"
log("cpu_setup")
space=snapshot_download(repo_id="ResembleAI/Chatterbox-Multilingual-TTS-es-es",repo_type="space",allow_patterns=["chatterbox/src/chatterbox/**"],max_workers=4)
sys.path.insert(0,str(pathlib.Path(space)/"chatterbox/src"))
from chatterbox.tts import ChatterboxTTS
base="ResembleAI/chatterbox";model_repo="ResembleAI/Chatterbox-Multilingual-es-es"
ckpt=pathlib.Path("/tmp/mara-chatterbox-model");ckpt.mkdir(exist_ok=True)
for repo,filename in [(base,"ve.pt"),(model_repo,"grapheme_mtl_merged_expanded_v1.json"),(model_repo,"t3_es_es.safetensors"),(model_repo,"s3gen_v3.pt")]:
 src=hf_hub_download(repo_id=repo,filename=filename)
 dest=ckpt/filename
 if not dest.exists():dest.symlink_to(src)
 log("cpu_weight",file=filename,bytes=pathlib.Path(src).stat().st_size)
ref=pathlib.Path("/tmp/mara-chatterbox-reference.wav")
with urllib.request.urlopen("https://storage.googleapis.com/chatterbox-demo-samples/mtl-v3-single-language-prompts/es-es/es_es_f1.wav",timeout=30) as r:ref.write_bytes(r.read(5000000))
log("cpu_model_loading")
model=ChatterboxTTS.from_local(ckpt,"cpu")
gc.collect()
log("cpu_model_ready")
for i,script in enumerate(BLOCKS):
 if clip(i).exists():validate(clip(i));continue
 t=time.monotonic()
 torch.manual_seed(271);random.seed(271);np.random.seed(271)
 with torch.inference_mode():
  wav=model.generate(script,language_id="es",audio_prompt_path=str(ref),exaggeration=0.64,temperature=0.83,cfg_weight=0.35)
 wav=wav.detach().cpu().float().reshape(1,-1)
 if model.sr!=24000:wav=torchaudio.functional.resample(wav,model.sr,24000)
 # Gradio normally writes normalized 16-bit WAV.
 peak=float(wav.abs().max())
 if peak>0:wav=wav/peak*0.97
 torchaudio.save(str(clip(i)),wav,24000,encoding="PCM_S",bits_per_sample=16)
 _,duration=validate(clip(i))
 log("cpu_block",block=i+1,seconds=round(duration,2),wall=round(time.monotonic()-t,2))
 assemble()
