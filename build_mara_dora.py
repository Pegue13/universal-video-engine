"""New Spanish documentary narration with Kokoro, no artist voice cloning."""
import pathlib, tempfile, zipfile, json, wave, subprocess, secrets, shutil, math
import engine
ROOT=pathlib.Path("/app/examples")
MODEL=pathlib.Path("/tmp/kokoro-v1.0.onnx")
VOICES=pathlib.Path("/tmp/voices-v1.0.bin")
NARRATION=["¡De los instrumentos a las cabinas del techno underground! Esta es Mara Ghodoy.","Todo empieza en Mérida, Extremadura, donde se forma como instrumentista.","En dos mil veintiuno da el salto a las cabinas, dentro del movimiento rave.","Y poco a poco, de la rave al club, encuentra un sonido mucho más personal.","¿Su sonido? Hardgroove y techno hipnótico. Dos pilares de su identidad.","Percusión, mezclas precisas y tensión progresiva. ¡La pista no para de moverse!","En dos mil veinticuatro, junto a Figa, impulsa Étika para visibilizar el talento femenino en la electrónica.","Su ciclo Hékate llega a Sala Marte, en Málaga, con una programación de DJs mujeres.","En dos mil veinticinco, su recorrido se amplía por Basshaus, París quince y Pandora.","En julio, Rastro Live publica una sesión suya que explora el techno hipnótico, el hardgroove y el raw.","Se afianza en Sevilla como residente de Cosmos Club y artista de Oscura Techno.","En marzo de dos mil veintiséis, figura en Electrolunch, en el Parque Magallanes de Sevilla.","El ocho de mayo, comparte cartel con Nine Times Nine y Bárbara Lago en Rebels.","Y en julio, vuelve a Pandora, en una noche de Hyperlink encabezada por Fantasm.","En septiembre, Matadero, Murcia. Un cartel con Luciid, Armero y Figa, entre otros.","Una semana después, apertura de temporada de Orion, en París quince, junto a Figa.","En octubre, su agenda la sitúa en Helion, en Cosmos Club, con Grace Dahl.","Pero su recorrido no termina en España. Su dossier recoge una actuación en Los Ángeles.","Y mientras sigue recorriendo cabinas, trabaja también en sus primeras producciones.","Mara Ghodoy. Una identidad que se construye entre el ritmo, la cultura de club y la evolución constante."]
RATE=48000
def log(status,**kwargs):
 print("MARA_DORA "+json.dumps({"status":status,**kwargs},ensure_ascii=True),flush=True)
def run(args,timeout=120):
 p=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y"]+list(map(str,args)),capture_output=True,timeout=timeout)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors="replace")[-500:])
def spoken(s):
 for old,new in (("999999999","Nine Times Nine"),("2021","dos mil veintiuno"),("2025","dos mil veinticinco"),("ETIKA","Étika"),("DJ","diyei"),("Paris15","París quince"),("XXL","equis equis ele"),("Fhiga","Figa"),("DJs","diyeis")):
  s=s.replace(old,new)
 return s
def main():
 import numpy as np
 import urllib.request
 from kokoro_onnx import Kokoro
 import onnxruntime as rt
 base="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
 for target in (MODEL,VOICES):
  with urllib.request.urlopen(base+target.name,timeout=45) as r, target.open("wb") as f:
   shutil.copyfileobj(r,f,1024*1024)
  if target.stat().st_size<1000000:raise RuntimeError("Incomplete model asset")
 log("model_loaded",model_bytes=MODEL.stat().st_size,voices_bytes=VOICES.stat().st_size)
 opts=rt.SessionOptions()
 opts.intra_op_num_threads=2
 opts.inter_op_num_threads=1
 session=rt.InferenceSession(str(MODEL),sess_options=opts,providers=["CPUExecutionProvider"])
 voice=Kokoro.from_session(session,str(VOICES))
 assert "ef_dora" in voice.get_voices()
 source=ROOT/"mara-doc.mp4"
 assert source.is_file()
 duration=engine.probe(source)["duration"]
 with zipfile.ZipFile(ROOT/"mara-doc.zip") as z:
  timeline=json.loads(z.read("Montaje.json"))
 assert len(timeline)==20
 with tempfile.TemporaryDirectory(prefix="mara-dora-") as d:
  p=pathlib.Path(d)
  pcm=bytearray(round(duration*RATE)*2); records=[]
  for i,c in enumerate(timeline):
   start=float(c["start"]); end=min(float(c["end"]),duration)
   slot=end-start
   raw=p/f"raw{i:02}.wav"
   text=NARRATION[i]
   # Pronunciation adjustments are applied to synthesis, not displayed captions.
   pronunciation=text.replace("DJs","diyeis").replace("DJ","diyei").replace("Fhiga","Figa").replace("Hardgroove","jard gruv").replace("hardgroove","jard gruv").replace("Basshaus","bas jaus").replace("Rastro Live","Rastro laiv").replace("Nine Times Nine","nain taims nain").replace("Luciid","lúsid").replace("Grace Dahl","greis dal")
   speeds=(1.06,1.00,1.04,1.00,1.02,1.06,1.02,1.0,1.02,1.01,1.0,1.02,1.04,1.03,1.04,1.02,1.01,1.00,1.00,0.98)
   samples,sr=voice.create(pronunciation,"ef_dora",speed=speeds[i],lang="es")
   samples=np.asarray(samples,dtype=np.float32).reshape(-1)
   if len(samples)<sr*0.3 or not np.all(np.isfinite(samples)) or np.sqrt(np.mean(samples**2))<0.001:raise RuntimeError("Empty or inaudible speech")
   with wave.open(str(raw),"wb") as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.clip(samples,-1,1)*32760).astype("<i2").tobytes())
   with wave.open(str(raw),"rb") as w: rawdur=w.getnframes()/w.getframerate()
   lead=.10
   available=slot-lead-.22
   factor=max(0.95,rawdur/available)
   if factor>1.48:raise RuntimeError("Excessive speed required for segment "+str(i+1))
   dest=p/f"fit{i:02}.wav"
   run(["-i",raw,"-af",f"highpass=f=75,atempo={factor:.5f},acompressor=threshold=0.12:ratio=1.7:attack=12:release=110,alimiter=limit=0.85","-ar",RATE,"-ac",1,"-c:a","pcm_s16le",dest])
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
  mp4=p/"MARA_GHODOY_Documental_Dora.mp4"
  run(["-i",source,"-i",narr,"-map","0:v:0","-map","1:a:0","-c:v","copy","-af","loudnorm=I=-16:TP=-1.5:LRA=7","-c:a","aac","-b:a","160k","-ar",RATE,"-t",str(duration),"-movflags","+faststart",mp4])
  info=engine.probe(mp4)
  assert info["audio"] and abs(info["duration"]-duration)<.15 and info["video"]["codec_name"]=="h264"
  run(["-i",mp4,"-map","0:v:0","-map","0:a:0","-f","null","-"])
  qa={"passed":True,"duration":info["duration"],"width":info["video"]["width"],"height":info["video"]["height"],"audio":"AAC","voice":"Kokoro 82M v1.0 ef_dora, Spanish female","scene_count":len(records),"source_video_sha256":engine.digest(source),"sha256":engine.digest(mp4),"bytes":mp4.stat().st_size,"visual_audio_review_required":True}
  (p/"Locucion_Tiempos.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
  (p/"QA_Voz.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
  (p/"Creditos_Voz.txt").write_text("Narración sintética: Kokoro 82M v1.0, ef_dora, español, voz femenina genérica. https://huggingface.co/hexgrad/Kokoro-82M . No imita a Mara Ghodoy. Revisión editorial privada; confirmar permisos antes de publicar.",encoding="utf-8")
  pack=p/"MARA_GHODOY_Documental_Dora_Pack.zip"
  with zipfile.ZipFile(pack,"w",compression=zipfile.ZIP_DEFLATED) as z:
   for n in (mp4,narr,p/"Locucion_Tiempos.json",p/"QA_Voz.json",p/"Creditos_Voz.txt"):z.write(n,n.name)
   with zipfile.ZipFile(ROOT/"mara-doc.zip") as old:
    for name in ("Guion.txt","Subtitulos.srt","Montaje.json","Creditos.json"):z.writestr(name,old.read(name))
  with zipfile.ZipFile(pack) as z:assert z.testzip() is None
  log("speech_coverage",spoken_seconds=round(sum(r["speech_seconds"] for r in records),2),total_seconds=duration)
  for src,name in [(mp4,"mara-dora.mp4"),(narr,"mara-dora.wav"),(pack,"mara-dora.zip")]:shutil.copyfile(src,ROOT/name)
  token=secrets.token_urlsafe(24)
  (ROOT/"mara-dora.token").write_text(token)
  log("verified",qa=qa,zip_bytes=pack.stat().st_size,video="/private-mara-dora/"+token+"/video.mp4",audio="/private-mara-dora/"+token+"/narration.wav",zip="/private-mara-dora/"+token+"/delivery.zip")
if __name__=="__main__":
 try:main()
 except Exception as e:log("failed",reason=str(e)[:500]);raise
