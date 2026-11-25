"""Full Spanish narration, preserving all previous story beats. Public demo API, default supplied voice."""
import urllib.request,urllib.parse,json,io,wave,pathlib,subprocess,hashlib,secrets,zipfile,time,array,math,sys
ROOT=pathlib.Path("/app/examples")
BASE="https://resembleai-chatterbox-multilingual-tts-es-es.hf.space"
BLOCKS=["¿Sabías que Mara Ghodoy empezó haciendo música en Mérida? Pues sí. Y antes de llegar a las cabinas... ya tocaba instrumentos. Pero lo interesante viene después: en dos mil veintiuno, descubre el mundo de las raves. Y ahí, empieza a construir su propio sonido.","Y poco a poco, de la rave al club, encuentra un sonido mucho más personal. ¿Su sonido? Jard gruv y techno hipnótico. Dos pilares de su identidad. Percusión, mezclas precisas, y tensión progresiva. La pista no para de moverse.","En dos mil veinticuatro, junto a Figa, impulsa Étika, para visibilizar el talento femenino en la electrónica. Su ciclo Hékate llega a Sala Marte, en Málaga, con una programación de diyeis mujeres.","En dos mil veinticinco, su recorrido se amplía por Basshaus, París quince y Pandora. En julio, Rastro Live publica una sesión suya que explora el techno hipnótico, el jard gruv y el raw. Se afianza en Sevilla, como residente de Cosmos Club y artista de Oscura Techno.","En marzo de dos mil veintiséis, figura en Electrolunch, en el Parque Magallanes de Sevilla. El ocho de mayo, comparte cartel con Nine Times Nine y Bárbara Lago, en Rebels. Y en julio... vuelve a Pandora, en una noche de Hyperlink encabezada por Fantasm.","En septiembre, Matadero, Murcia. Un cartel con Luciid, Armero y Figa, entre otros. Una semana después, apertura de temporada de Orion, en París quince, junto a Figa. En octubre, su agenda la sitúa en Helion, en Cosmos Club, con Grace Dahl.","Pero su recorrido no termina en España. Su dossier recoge una actuación en Los Ángeles. Y mientras sigue recorriendo cabinas, trabaja también en sus primeras producciones. Mara Ghodoy. Una identidad que se construye entre el ritmo, la cultura de club y la evolución constante."]
def log(status,**kw):print("MARA_FULL_SPEECH "+json.dumps({"status":status,**kw},ensure_ascii=True),flush=True)
def request(url,data=None,timeout=60):
 if not url.startswith(BASE+"/"):raise ValueError("Unexpected host")
 req=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),headers={"Content-Type":"application/json","User-Agent":"UniversalVideoEngine/1.0"})
 return urllib.request.urlopen(req,timeout=timeout)
def generate(script,ref):
 assert len(script)<=300
 with request(BASE+"/gradio_api/call/generate_tts_audio",{"data":[script,ref,0.64,0.83,271,0.35]},20) as r:
  event=json.load(r)["event_id"]
 with request(BASE+"/gradio_api/call/generate_tts_audio/"+event,timeout=90) as r:
  kind=None;deadline=time.monotonic()+150
  for line in r:
   if time.monotonic()>deadline:raise TimeoutError("Generation deadline")
   s=line.decode().strip()
   if s.startswith("event:"):kind=s[6:].strip()
   elif s.startswith("data:") and kind=="complete":
    url=json.loads(s[5:].strip())[0]["url"];break
   elif s.startswith("data:") and kind=="error":raise RuntimeError("Public demo generation failed: "+s[:200])
  else:raise RuntimeError("No completed output")
 with request(url,timeout=20) as r:b=r.read(6000001)
 if len(b)>6000000:raise ValueError("Audio too large")
 with wave.open(io.BytesIO(b)) as w:
  assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getframerate()==24000
  pcm=w.readframes(w.getnframes())
 samples=array.array("h",pcm)
 if sys.byteorder!="little":samples.byteswap()
 duration=len(samples)/24000
 assert 5<duration<70 and math.sqrt(sum(x*x for x in samples)/len(samples))>100
 return pcm,duration
def main():
 ROOT.mkdir(exist_ok=True)
 with request(BASE+"/config",timeout=20) as r:conf=json.load(r)
 ref=next(x["props"]["value"] for x in conf["components"] if x["id"]==5)
 assert "es_es_f1.wav" in ref["path"]
 parts=[];timing=[];cursor=0.0
 pauses=[0.42,0.48,0.53,0.40,0.46,0.62,0.0]
 for i,script in enumerate(BLOCKS):
  pcm,duration=generate(script,ref)
  parts.append(pcm);timing.append({"block":i+1,"start":round(cursor,3),"end":round(cursor+duration,3),"text":script})
  cursor+=duration
  silence=b"\0\0"*round(24000*pauses[i]);parts.append(silence);cursor+=pauses[i]
  log("block",number=i+1,total=len(BLOCKS),seconds=round(duration,2))
  if i+1<len(BLOCKS):time.sleep(1)
 wav=ROOT/"mara-full-speech.wav"
 with wave.open(str(wav),"wb") as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b"".join(parts))
 mp3=ROOT/"mara-full-speech.mp3"
 subprocess.run(["ffmpeg","-v","error","-y","-i",str(wav),"-af","loudnorm=I=-16:TP=-1.5:LRA=11","-ar","48000","-c:a","libmp3lame","-b:a","128k",str(mp3)],check=True,timeout=60)
 subprocess.run(["ffmpeg","-v","error","-i",str(mp3),"-f","null","-"],check=True,timeout=60)
 with wave.open(str(wav)) as w:duration=w.getnframes()/w.getframerate()
 assert len(timing)==len(BLOCKS) and abs(duration-cursor)<0.02
 token=secrets.token_urlsafe(24)
 (ROOT/"mara-full-speech.token").write_text(token)
 (ROOT/"mara-full-speech.json").write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding="utf-8")
 log("verified",duration=round(duration,2),blocks=len(timing),mp3_bytes=mp3.stat().st_size,wav_bytes=wav.stat().st_size,sha256=hashlib.sha256(mp3.read_bytes()).hexdigest(),path="/private-full-speech/"+token+"/listen",mp3="/private-full-speech/"+token+"/speech.mp3",wav="/private-full-speech/"+token+"/speech.wav")
if __name__=="__main__":
 try:main()
 except Exception as e:log("failed",reason=str(e)[:500]);raise
