# Universal Video Engine

Standalone Python / FFmpeg video-editing API, independent of any brand. Prototype release 0.2.0.

## Deploy

Use Render's Blueprint with the included `render.yaml`. The configuration creates one free Docker web service in Frankfurt. It generates VIDEO_ENGINE_API_KEY in the server environment; never put that value in Git or public URLs. Supply it as an Authorization: Bearer header. The only public routes are the health and API documentation pages. No paid plan, database, permanent media storage, or external AI service is required.

Docker builds run a synthetic video self-test covering crop, caption, soundtrack, cover, contact sheet, ZIP and technical QA. A successful build does not prove Instagram access.

## API

- GET /health — readiness and configuration checks.
- POST /v1/inspect — multipart field video; returns media properties and SHA-256.
- POST /v1/import/instagram — JSON object with url, download_authorized, usage_authorized, permission_reference; authorized public Reel and video-post URLs only. No cookies or account access. Availability depends on Instagram and the extractor.
- POST /v1/render — multipart fields videos (repeat for each input), spec (JSON text), optional logo (PNG), optional audio (MP3/WAV/MP4/WebM). Returns a ZIP directly.

The render spec requires usage_authorized=true and a nonempty permission_reference. Optional fields: width (360, 540, 720 or 1080), ratio (9:16, 1:1, 16:9), fps (24, 25, 30), fit (crop or contain), segments (asset index, start, duration in seconds), title, subtitle, captions (start, end, text), audio_mode (mute, source or external), audio_authorized, audio_asset, audio_start, copy, credits. Audio defaults to mute. Up to six videos, 12 shots, 30 seconds of output, 32 MiB per video and 80 MiB combined input.

Example render spec (for your own authorized media):
```json
{"usage_authorized":true,"permission_reference":"Own footage","width":540,"ratio":"9:16","segments":[{"asset":0,"start":0,"duration":3}],"audio_mode":"mute","title":"Artist name"}
```

After deployment, use the service's actual HTTPS URL and securely stored key:
```bash
curl --fail-with-body -H "Authorization: Bearer $VIDEO_ENGINE_API_KEY" \
  -F 'videos=@authorized.mp4' \
  -F 'spec={"usage_authorized":true,"permission_reference":"Own footage","width":540,"audio_mode":"mute"}' \
  "$VIDEO_ENGINE_URL/v1/render" -o delivery.zip
```

The ZIP contains video.mp4, cover.jpg, contact_sheet.jpg, captions.srt, caption.txt, credits.json, edit.json, qa.json. Human creative and permissions review remains necessary. Inputs and outputs are temporary and are not published. The free service may sleep or be resource-limited; begin with short 360/540-pixel previews. No guarantee of automated third-party video downloads. No automatic beat detection, transcription, or semantic scene selection in this release.

## Alternative media ingestion

- POST /v1/import/direct: accepts an approved HTTPS URL and both authorization declarations, returns MP4 or WebM.
- POST /v1/render/direct: accepts a list of 1–6 authorized direct sources and the edit specification, returning a delivery ZIP in one call. This avoids uploading the video twice.
- Input hosts default to interactive-examples.mdn.mozilla.net and upload.wikimedia.org. A service administrator can add specific trusted media hosts using MEDIA_ALLOWED_HOSTS (comma-separated exact hostnames). Each redirect is checked, DNS is pinned to public IPs, TLS is validated, and files are bounded and inspected. No unrestricted URL fetch, no cookies, no private media access.
- Instagram's mobile download option (if enabled by the creator), original files supplied by the artist, and media_url from a legitimately authorized professional Meta account are supported via file upload or an approved direct media host. This does not imply rights to remix or repost. No private API or third-party scraper is included.
- The build network smoke test uses the MDN CC0 flower clip solely to verify complete HTTPS file transfer and real rendering. It is not an artist clip or Instagram download.
