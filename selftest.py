"""Build-time functional check using generated test footage (not artist footage)."""
import json
import tempfile
import zipfile
from pathlib import Path
import engine

def main():
    with tempfile.TemporaryDirectory(prefix="uve-test-") as d:
        p=Path(d); a=p/"source.mp4"
        engine.ff(["-f","lavfi","-i","testsrc2=size=320x240:rate=24",
                   "-f","lavfi","-i","sine=frequency=440:sample_rate=48000",
                   "-t","2","-c:v","libx264","-threads","1","-pix_fmt","yuv420p","-c:a","aac",str(a)])
        spec={"usage_authorized":True,"permission_reference":"Generated build fixture",
              "width":360,"fps":24,"title":"Universal Video Engine",
              "segments":[{"asset":0,"start":0,"duration":1.5}],
              "captions":[{"start":0.2,"end":1.3,"text":"TEST"}],"audio_mode":"source","audio_authorized":True}
        bundle,qa=engine.render(p,[a],spec)
        assert qa["passed"] and qa["width"]==360 and qa["height"]==640
        with zipfile.ZipFile(bundle) as z:
            assert z.testzip() is None and "video.mp4" in z.namelist() and "qa.json" in z.namelist()
        try:
            engine.parse_edit({"usage_authorized":False},[engine.probe(a)])
        except engine.EngineError: pass
        else: raise AssertionError("Rights gate missing")
        from app import canonical_reel
        assert canonical_reel("https://instagram.com/reel/abcde/?igsh=x")=="https://www.instagram.com/reel/abcde/"
        try: canonical_reel("https://example.com/reel/abcde/")
        except engine.EngineError: pass
        else: raise AssertionError("URL gate missing")
        print("BUILD SELFTEST PASSED: render, captions, audio, ZIP, QA and rights gate")

if __name__=="__main__": main()
