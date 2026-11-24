"""Reproducible, fixed, openly licensed DJ Q-Bert source-clip pack."""
import hashlib, json, pathlib, tempfile, zipfile
from PIL import Image,ImageDraw
import engine, media_import

URL="https://upload.wikimedia.org/wikipedia/commons/6/67/DJ_QBert_at_Rainbow_Warehouse%2C_Birmingham_UK.webm"
SOURCE="https://commons.wikimedia.org/wiki/File:DJ_QBert_at_Rainbow_Warehouse,_Birmingham_UK.webm"
LICENSE="https://creativecommons.org/licenses/by/3.0/"
SHA1="0f08bdc4900565e630adcb225b6ea89848966618"
DEST=pathlib.Path("/app/examples/dj-qbert-source-clips.zip")

def main():
    DEST.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="uve-dj-qbert-") as d:
        work=pathlib.Path(d)
        source=work/"original.webm"
        original=media_import.fetch(URL,source,max_bytes=70*1024*1024)
        with source.open("rb") as f:
            actual=hashlib.file_digest(f,"sha1").hexdigest()
        if actual!=SHA1:
            raise RuntimeError("Original source checksum does not match Wikimedia metadata.")
        print("DJ_PACK "+json.dumps({"status":"source_verified","bytes":original["size"],"duration":original["duration"],"sha1":actual,"sha256":engine.digest(source)}),flush=True)
        clips=[]
        thumb=Image.new("RGB",(1024,616),(20,20,20))
        draw=ImageDraw.Draw(thumb)
        for i,start in enumerate((45,180,320,550),1):
            name=f"clip_{i:02d}_{start:03d}s.mp4"
            path=work/name
            engine.ff(["-ss",str(start)]+engine.source_args(source)+["-t","6","-map","0:v:0","-an","-sn","-dn","-vf","setsar=1,fps=25"]+engine.encode_flags()+["-movflags","+faststart",str(path)],90)
            info=engine.probe(path)
            if abs(info["duration"]-6)>0.2 or info["video"]["codec_name"]!="h264" or info["audio"]:
                raise RuntimeError("Clip failed technical validation.")
            clips.append({"filename":name,"source_start_seconds":start,"source_end_seconds":start+6,
                "duration_seconds":info["duration"],"width":info["video"]["width"],"height":info["video"]["height"],
                "bytes":info["size"],"sha256":engine.digest(path),"audio":False})
            frame=work/f"frame_{i}.jpg"
            engine.frame_at(path,3,frame)
            with Image.open(frame) as im:
                im=im.convert("RGB"); im.thumbnail((512,288))
                x=((i-1)%2)*512; y=((i-1)//2)*308
                thumb.paste(im,(x,y))
                draw.text((x+8,y+289),f"CLIP {i:02d} | source {start}s - {start+6}s",fill="white")
        thumb.save(work/"contact_sheet.jpg",quality=92)
        manifest={"artist":"DJ Q-Bert","event":"Scratch Club, Rainbow Warehouse, Birmingham, UK",
            "performance_date":"2008-09-13","source_title":"DJ QBert at Rainbow Warehouse, Birmingham UK",
            "author":"Chris Bates","license":"CC BY 3.0 Unported","license_url":LICENSE,"source_page":SOURCE,
            "source_file":URL,"source_sha1":actual,"source_sha256":engine.digest(source),
            "changes":"Four chronological excerpts, H.264 MP4, audio removed, frame rate normalized to 25fps.",
            "selection":"Four distributed technical samples; not visually curated or music-synchronized.",
            "clips":clips,"technical_checks_passed":True,"visual_review_required":True,
            "publication_note":"Attribution and license link required. No endorsement implied. Check other applicable rights."}
        (work/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
        (work/"CREDITOS.txt").write_text("DJ QBert at Rainbow Warehouse, Birmingham UK — Chris Bates.\nFuente: "+SOURCE+"\nLicencia: CC BY 3.0 Unported — "+LICENSE+"\nCambios: cuatro extractos, MP4 H.264 a 25 fps, sin sonido.\nNo es un DJ de Granada. No hay patrocinio o aval del artista.\n",encoding="utf-8")
        (work/"LEEME.txt").write_text("PACK DE METRAJE FUENTE — DJ Q-BERT\n\n4 clips de 6 segundos del mismo set, sin marca ni montaje final.\nResolución original conservada, 25 fps, audio eliminado.\nLos cortes son muestras distribuidas temporalmente, no una selección creativa validada.\nConsulta contact_sheet.jpg y manifest.json para elegir planos.\nOriginal completo: "+URL+"\nCréditos y licencia: CREDITOS.txt.\n",encoding="utf-8")
        with zipfile.ZipFile(DEST,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for name in [c["filename"] for c in clips]+["manifest.json","CREDITOS.txt","LEEME.txt","contact_sheet.jpg"]:
                z.write(work/name,name)
        with zipfile.ZipFile(DEST) as z:
            assert z.testzip() is None and len(z.namelist())==8
        print("DJ_PACK "+json.dumps({"status":"pack_verified","clips":clips,"zip_bytes":DEST.stat().st_size,"zip_sha256":engine.digest(DEST)}),flush=True)
if __name__=="__main__": main()
