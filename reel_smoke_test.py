"""Network integration check using MDN's CC0 example video, not artist footage."""
import json, pathlib, tempfile
import engine, media_import

def check():
    with tempfile.TemporaryDirectory(prefix="uve-https-test-") as d:
        work=pathlib.Path(d)
        for bad in ("http://interactive-examples.mdn.mozilla.net/flower.mp4",
                    "https://127.0.0.1/secret","https://example.com/file.mp4"):
            try: media_import.validate(bad)
            except engine.EngineError: pass
            else: raise AssertionError("Invalid host or protocol accepted")
        source=work/"source.mp4"
        try:
            info=media_import.fetch("https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",source)
            print("IMPORT_SMOKE "+json.dumps({"status":"download_verified","bytes":info["size"],"duration":info["duration"],"width":info["video"]["width"],"height":info["video"]["height"],"sha256":engine.digest(source)}),flush=True)
            bundle,qa=engine.render(work,[source],{"usage_authorized":True,"permission_reference":"MDN CC0 sample video","width":360,"audio_mode":"mute","segments":[{"asset":0,"start":0,"duration":1.5}],"title":"Direct import test"})
            print("IMPORT_SMOKE "+json.dumps({"status":"render_verified","qa":qa["passed"],"zip_bytes":bundle.stat().st_size}),flush=True)
        except Exception as e:
            print("IMPORT_SMOKE "+json.dumps({"status":"failed","reason":str(e)[:350]}),flush=True)
if __name__=="__main__": check()
