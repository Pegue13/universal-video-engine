"""Short audition only. Do not replace the finished video before approval."""
import asyncio, pathlib, json, subprocess, secrets
import edge_tts
ROOT=pathlib.Path("/app/examples")
SCRIPT="¿Cómo pasa una artista de tocar instrumentos en Mérida a hacerse un hueco en las cabinas del techno? Hoy hablamos de Mara Ghodoy. Hardgroove, techno hipnótico y una forma de entender la pista que no deja de evolucionar."
def log(status,**kw):print("MARA_AUDITION "+json.dumps({"status":status,**kw}),flush=True)
async def main():
 ROOT.mkdir(exist_ok=True)
 voices=await asyncio.wait_for(edge_tts.list_voices(),25)
 candidates=[v for v in voices if v.get("Locale")=="es-ES" and v.get("Gender")=="Female"]
 available={v["ShortName"] for v in candidates}
 log("available",voices=sorted(available))
 choices=[("elvira","es-ES-ElviraNeural","+5%","+3Hz"),("abril","es-ES-AbrilNeural","+3%","+2Hz")]
 successful=[]
 for name,voice,rate,pitch in choices:
  if voice not in available:continue
  p=ROOT/("audition-"+name+".mp3")
  try:
   await asyncio.wait_for(edge_tts.Communicate(SCRIPT,voice,rate=rate,pitch=pitch).save(str(p)),30)
   probe=subprocess.check_output(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(p)],timeout=10)
   info=json.loads(probe);duration=float(info["format"]["duration"])
   assert 8<duration<30 and p.stat().st_size>10000 and any(s["codec_type"]=="audio" for s in info["streams"])
   subprocess.run(["ffmpeg","-v","error","-i",str(p),"-f","null","-"],check=True,timeout=15)
   successful.append(name)
   log("verified_sample",voice=voice,seconds=duration,bytes=p.stat().st_size)
  except Exception as e:
   p.unlink(missing_ok=True)
   log("failed",voice=voice,reason=str(e)[:200])
   if "403" in str(e) or "401" in str(e) or "429" in str(e):break
 if successful:
  token=secrets.token_urlsafe(24)
  (ROOT/"audition.token").write_text(token)
  log("ready",names=successful,path="/private-audition/"+token+"/listen")
 else:log("unavailable")
if __name__=="__main__":
 try:asyncio.run(main())
 except Exception as e:log("failed",reason=str(e)[:300])
