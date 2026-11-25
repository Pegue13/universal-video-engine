"""Full Spanish narration, preserving all previous story beats. Public demo API, default supplied voice."""
import urllib.request,urllib.parse,json,io,wave,pathlib,subprocess,hashlib,secrets,zipfile,time,array,math,sys
ROOT=pathlib.Path("/app/examples")
BASE="https://resembleai-chatterbox-multilingual-tts-es-es.hf.space"
BLOCKS=["¿Sabías que Mara Ghodoy empezó haciendo música en Mérida? Pues sí. Y antes de llegar a las cabinas... ya tocaba instrumentos. Pero lo interesante viene después: en dos mil veintiuno, descubre el mundo de las raves. Y ahí, empieza a construir su propio sonido.","Y poco a poco, de la rave al club, encuentra un sonido mucho más personal. ¿Su sonido? Jard gruv y techno hipnótico. Dos pilares de su identidad. Percusión, mezclas precisas, y tensión progresiva. La pista no para de moverse.","En dos mil veinticuatro, junto a Figa, impulsa Étika, para visibilizar el talento femenino en la electrónica. Su ciclo Hékate llega a Sala Marte, en Málaga, con una programación de diyeis mujeres.","En dos mil veinticinco, su recorrido se amplía por Basshaus, París quince y Pandora. En julio, Rastro Live publica una sesión suya que explora el techno hipnótico, el jard gruv y el raw. Se afianza en Sevilla, como residente de Cosmos Club y artista de Oscura Techno.","En marzo de dos mil veintiséis, figura en Electrolunch, en el Parque Magallanes de Sevilla. El ocho de mayo, comparte cartel con Nine Times Nine y Bárbara Lago, en Rebels. Y en julio... vuelve a Pandora, en una noche de Hyperlink encabezada por Fantasm.","En septiembre, Matadero, Murcia. Un cartel con Luciid, Armero y Figa, entre otros. Una semana después, apertura de temporada de Orion, en París quince, junto a Figa. En octubre, su agenda la sitúa en Helion, en Cosmos Club, con Grace Dahl.","Pero su recorrido no termina en España. Su dossier recoge una actuación en Los Ángeles. Y mientras sigue recorriendo cabinas, trabaja también en sus primeras producciones. Mara Ghodoy. Una identidad que se construye entre el ritmo, la cultura de club y la evolución constante."]

import os,re
def log(status,**kw):print("MARA_FULL_SPEECH "+json.dumps({"status":status,**kw},ensure_ascii=True),flush=True)
def clip(i):return ROOT/("mara-full-block-%02d.wav"%(i+1))
def validate(path):
 with wave.open(str(path),"rb") as w:
  assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getframerate()==24000
  pcm=w.readframes(w.getnframes())
 samples=array.array("h",pcm)
 if sys.byteorder!="little":samples.byteswap()
 duration=len(samples)/24000
 assert 4<duration<70 and math.sqrt(sum(x*x for x in samples)/len(samples))>100
 return pcm,duration
def collect():
 ROOT.mkdir(exist_ok=True)
 hashes=json.loads(os.environ.get("MARA_SPEECH_CLIPS","[]"))
 assert len(hashes)==4 and all(re.fullmatch(r"[0-9a-f]{64}",h) for h in hashes)
 for i,h in enumerate(hashes):
  p=clip(i)
  url=BASE+"/gradio_api/file=/tmp/gradio/"+h+"/audio.wav"
  with urllib.request.urlopen(url,timeout=35) as r:b=r.read(6000001)
  assert len(b)<6000001
  p.write_bytes(b)
  pcm,duration=validate(p)
  log("saved",block=i+1,seconds=round(duration,2))
def assemble():
 parts=[];timing=[];cursor=0.
 pauses=[0.42,0.48,0.53,0.40,0.46,0.62,0.0]
 for i,script in enumerate(BLOCKS):
  if not clip(i).is_file():break
  pcm,duration=validate(clip(i))
  parts.append(pcm);timing.append({"block":i+1,"start":round(cursor,3),"end":round(cursor+duration,3),"text":script})
  cursor+=duration
  if i+1<len(BLOCKS) and clip(i+1).is_file():
   parts.append(b"\0\0"*round(24000*pauses[i]));cursor+=pauses[i]
 if not timing:raise RuntimeError("No clips")
 complete=len(timing)==len(BLOCKS)
 wav=ROOT/"mara-full-speech.wav"
 with wave.open(str(wav),"wb") as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"".join(parts))
 mp3=ROOT/"mara-full-speech.mp3"
 subprocess.run(["ffmpeg","-v","error","-y","-i",str(wav),"-af","loudnorm=I=-16:TP=-1.5:LRA=11","-ar","48000","-c:a","libmp3lame","-b:a","128k",str(mp3)],check=True,timeout=60)
 subprocess.run(["ffmpeg","-v","error","-i",str(mp3),"-f","null","-"],check=True,timeout=60)
 with wave.open(str(wav)) as w:duration=w.getnframes()/w.getframerate()
 assert abs(duration-cursor)<0.02
 tokenpath=ROOT/"mara-full-speech.token"
 if not tokenpath.exists():tokenpath.write_text(secrets.token_urlsafe(24))
 token=tokenpath.read_text().strip()
 (ROOT/"mara-full-speech.json").write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding="utf-8")
 log("verified" if complete else "partial",duration=round(duration,2),blocks=len(timing),mp3_bytes=mp3.stat().st_size,wav_bytes=wav.stat().st_size,sha256=hashlib.sha256(mp3.read_bytes()).hexdigest(),path="/private-full-speech/"+token+"/listen",mp3="/private-full-speech/"+token+"/speech.mp3",wav="/private-full-speech/"+token+"/speech.wav")
if __name__=="__main__":
 if len(sys.argv)>1 and sys.argv[1]=="collect":collect()
 assemble()
