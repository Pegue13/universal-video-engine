"""Add neural Spanish narration to the existing Mara documentary. No cloned artist voice."""
import pathlib, tempfile, zipfile, json, wave, subprocess, secrets, shutil, math
import engine
ROOT=pathlib.Path("/app/examples")
MODEL=pathlib.Path("/app/es_ES-sharvard-medium.onnx")
RATE=48000
def log(status,**kwargs):
 print("MARA_VOICE "+json.dumps({"status":status,**kwargs},ensure_ascii=True),flush=True)
def run(args,timeout=120):
 p=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y"]+list(map(str,args)),capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors="replace")[-500:])
def spoken(s):
 for old,new in (("999999999","Nine Times Nine"),("2021","dos mil veintiuno"),("2025","dos mil veinticinco"),("ETIKA","Étika"),("DJ","diyei"),("Paris15","París quince"),("XXL","equis equis ele"),("Fhiga","Figa"),("DJs","diyeis")):
  s=s.replace(old,new)
 return s
def main():
 from piper import PiperVoice,SynthesisConfig
 voice=PiperVoice.load(str(MODEL))
 source=ROOT/"mara-doc.mp4"
 assert source.is_file()
 duration=engine.probe(source)["duration"]
 with zipfile.ZipFile(ROOT/"mara-doc.zip") as z:
  timeline=json.loads(z.read("Montaje.json"))
 assert len(timeline)==20
 with tempfile.TemporaryDirectory(prefix="mara-voice-") as d:
  p=pathlib.Path(d)
  pcm=bytearray(round(duration*RATE)*2); records=[]
  for i,c in enumerate(timeline):
   start=float(c["start"]); end=min(float(c["end"]),duration)
   slot=end-start
   raw=p/f"raw{i:02}.wav"
   text=spoken(c["text"])
   if i==0:text="Mara Ghodoy. "+text
   with wave.open(str(raw),"wb") as w:
    voice.synthesize_wav(text,w,syn_config=SynthesisConfig(speaker_id=1,length_scale=1.0,noise_scale=.60,noise_w_scale=.72))
   with wave.open(str(raw),"rb") as w: rawdur=w.getnframes()/w.getframerate()
   lead=.16
   available=slot-lead-.13
   factor=max(0.88,rawdur/available)
   if factor>1.40:raise RuntimeError("Excessive speed required for segment "+str(i+1))
   dest=p/f"fit{i:02}.wav"
   run(["-i",raw,"-af",f"highpass=f=75,atempo={factor:.5f},acompressor=threshold=0.1:ratio=2:attack=10:release=100,alimiter=limit=0.85","-ar",RATE,"-ac",1,"-c:a","pcm_s16le",dest])
   with wave.open(str(dest),"rb") as w: b=w.readframes(w.getnframes())
   offset=round((start+lead)*RATE)*2
   maxlen=max(0,round((end-.04)*RATE)*2-offset)
   if len(b)>maxlen+round(.05*RATE)*2:raise RuntimeError("Narration exceeds scene duration")
   b=b[:maxlen]; pcm[offset:offset+len(b)]=b
   records.append({"scene":i+1,"start":start+lead,"speech_seconds":len(b)/2/RATE,"end":end,"tempo":round(factor,3),"text":text})
   log("scene",number=i+1,total=len(timeline),tempo=round(factor,3))
  narr=p/"Locucion_ES.wav"
  with wave.open(str(narr),"wb") as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(pcm)
  mp4=p/"MARA_GHODOY_Documental_Voz.mp4"
  run(["-i",source,"-i",narr,"-map","0:v:0","-map","1:a:0","-c:v","copy","-af","loudnorm=I=-16:TP=-1.5:LRA=7","-c:a","aac","-b:a","160k","-ar",RATE,"-t",str(duration),"-movflags","+faststart",mp4])
  info=engine.probe(mp4)
  assert info["audio"] and abs(info["duration"]-duration)<.15 and info["video"]["codec_name"]=="h264"
  run(["-i",mp4,"-map","0:v:0","-map","0:a:0","-f","null","-"])
  qa={"passed":True,"duration":info["duration"],"width":info["video"]["width"],"height":info["video"]["height"],"audio":"AAC","voice":"Piper Sharvard es_ES, female speaker 1","scene_count":len(records),"source_video_sha256":engine.digest(source),"sha256":engine.digest(mp4),"bytes":mp4.stat().st_size,"visual_audio_review_required":True}
  (p/"Locucion_Tiempos.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
  (p/"QA_Voz.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
  (p/"Creditos_Voz.txt").write_text("Narración sintética: Piper, modelo es_ES-sharvard-medium, hablante F. https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium . Modelo: MIT; dataset indicado en MODEL_CARD: CC BY 3.0, https://datashare.ed.ac.uk/handle/10283/574 . Voz genérica, no imitación de Mara Ghodoy. Metraje de prensa: revisión editorial privada; confirmar permisos antes de publicar.",encoding="utf-8")
  pack=p/"MARA_GHODOY_Documental_Voz_Pack.zip"
  with zipfile.ZipFile(pack,"w",compression=zipfile.ZIP_DEFLATED) as z:
   for n in (mp4,narr,p/"Locucion_Tiempos.json",p/"QA_Voz.json",p/"Creditos_Voz.txt"):z.write(n,n.name)
   with zipfile.ZipFile(ROOT/"mara-doc.zip") as old:
    for name in ("Guion.txt","Subtitulos.srt","Montaje.json","Creditos.json"):z.writestr(name,old.read(name))
  with zipfile.ZipFile(pack) as z:assert z.testzip() is None
  for src,name in [(mp4,"mara-voice.mp4"),(narr,"mara-voice.wav"),(pack,"mara-voice.zip")]:shutil.copyfile(src,ROOT/name)
  token=secrets.token_urlsafe(24)
  (ROOT/"mara-voice.token").write_text(token)
  log("verified",qa=qa,zip_bytes=pack.stat().st_size,video="/private-mara-voice/"+token+"/video.mp4",audio="/private-mara-voice/"+token+"/narration.wav",zip="/private-mara-voice/"+token+"/delivery.zip")
if __name__=="__main__":
 try:main()
 except Exception as e:log("failed",reason=str(e)[:500]);raise
