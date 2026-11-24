"""Fixed CC BY-SA 4.0 audiovisual sample; no user media exposed."""
import hashlib,json,pathlib,tempfile,shutil
import engine,media_import
URL="https://upload.wikimedia.org/wikipedia/commons/9/9d/DJ_Liek.webm"
SOURCE="https://commons.wikimedia.org/wiki/File:DJ_Liek.webm"
LICENSE="https://creativecommons.org/licenses/by-sa/4.0/"
SHA1="951f75b6a55c023e3e13f116042d31340c021278"
DEST=pathlib.Path("/app/examples")
def report(status,**fields):
    print("DJ_LIEK "+json.dumps({"status":status,**fields}),flush=True)
def main():
    DEST.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="uve-liek-") as d:
        work=pathlib.Path(d)
        source=work/"source.webm"
        info=media_import.fetch(URL,source)
        with source.open("rb") as f: sha=hashlib.file_digest(f,"sha1").hexdigest()
        if sha!=SHA1: raise RuntimeError("Source checksum mismatch")
        report("source_verified",bytes=info["size"],duration=info["duration"],sha1=sha)
        spec={"usage_authorized":True,"permission_reference":"CC BY-SA 4.0; "+SOURCE,
              "width":540,"ratio":"9:16","fit":"contain","fps":25,"audio_mode":"mute",
              "title":"DJ LIEK","subtitle":"Minneapolis / Live mix",
              "segments":[{"asset":0,"start":s,"duration":5} for s in (12,52,96)],
              "captions":[{"start":10,"end":15,"text":"Footage: BFileUpload | CC BY-SA 4.0"}],
              "copy":"DJ Liek | live mix in Minneapolis, March 2024. Edited sample: cut, reframed and muted.",
              "credits":"DJ Liek.webm by BFileUpload, March 30, 2024. "+SOURCE+" | "+LICENSE+" | Adapted under CC BY-SA 4.0: cuts, reframing, overlays, muted audio. No artist endorsement implied."}
        bundle,qa=engine.render(work,[source],spec)
        shutil.copyfile(work/"video.mp4",DEST/"dj-liek-reel.mp4")
        shutil.copyfile(bundle,DEST/"dj-liek-reel.zip")
        report("render_verified",qa=qa,zip_bytes=bundle.stat().st_size)
if __name__=="__main__":
    try: main()
    except Exception as e: report("failed",reason=str(e)[:350])
