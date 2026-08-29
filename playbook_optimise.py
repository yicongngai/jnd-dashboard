#!/usr/bin/env python3
"""playbook_optimise.py — make the Elevate Playbook tab open fast.

    python3 playbook_optimise.py --pages 1,121,415 --cap 1400 --quality 80 -o /tmp/t.pdf
    python3 playbook_optimise.py --cap 1400 --quality 80 -o playbook.optimised.pdf

WHY
---
The tab took 5-8 seconds to show slide 1. It was never the download: with the file
fully cached in the browser it STILL took that long, so the cost is decoding, not
transfer. The deck is a PowerPoint export whose images are JPEG 2000 (/JPXDecode) —
312 of 435 in a sample — and browsers decode JPX roughly an order of magnitude slower
than baseline JPEG. Measured here: ~40 ms per JPX image against ~3 ms for the same
image as JPEG, across ~2,600 images.

So this rewrites every JPX image as baseline JPEG. Nothing else about the file is
touched: page tree, text, fonts, bookmarks and the several hundred internal
navigation links are left exactly as they are.

TWO THINGS IT IS CAREFUL ABOUT
  * Alpha. A JPX image can carry transparency. Flattening it to RGB would paint a
    black box where a logo used to float, so any alpha channel is preserved as a
    separate /SMask.
  * Generation loss. These images are ALREADY lossy, so re-encoding at a high quality
    just stores compression artefacts faithfully and wastes bytes. The cap and quality
    are arguments, and the right values were chosen by rendering pages and looking.
"""
import argparse
import io
import os
import sys
import time

import pypdf
from pypdf.generic import NameObject, NumberObject, DecodedStreamObject
from PIL import Image


def transcode(obj, cap, quality):
    """JPX -> baseline JPEG in place. Returns (before, after) bytes, or None if skipped."""
    raw = getattr(obj, "_data", b"")
    if not raw:
        return None
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        return None                      # unreadable: leave the original alone

    alpha = None
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        alpha = im.convert("RGBA").getchannel("A")
    im = im.convert("RGB")

    if cap and max(im.size) > cap:
        s = cap / max(im.size)
        size = (max(1, int(im.width * s)), max(1, int(im.height * s)))
        im = im.resize(size, Image.LANCZOS)
        if alpha is not None:
            alpha = alpha.resize(size, Image.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    jpeg = buf.getvalue()

    obj._data = jpeg
    obj[NameObject("/Filter")] = NameObject("/DCTDecode")
    obj[NameObject("/Width")] = NumberObject(im.width)
    obj[NameObject("/Height")] = NumberObject(im.height)
    obj[NameObject("/ColorSpace")] = NameObject("/DeviceRGB")
    obj[NameObject("/BitsPerComponent")] = NumberObject(8)
    for dead in ("/DecodeParms", "/Decode"):
        if dead in obj:
            del obj[NameObject(dead)]

    if alpha is not None:
        sm = DecodedStreamObject()
        sm.set_data(alpha.tobytes())
        sm[NameObject("/Type")] = NameObject("/XObject")
        sm[NameObject("/Subtype")] = NameObject("/Image")
        sm[NameObject("/Width")] = NumberObject(alpha.width)
        sm[NameObject("/Height")] = NumberObject(alpha.height)
        sm[NameObject("/ColorSpace")] = NameObject("/DeviceGray")
        sm[NameObject("/BitsPerComponent")] = NumberObject(8)
        obj[NameObject("/SMask")] = sm
    return len(raw), len(jpeg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="playbook.pdf")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--cap", type=int, default=1400)
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--pages", help="1-based, comma separated — extract only these")
    a = ap.parse_args()

    reader = pypdf.PdfReader(a.src)
    writer = pypdf.PdfWriter()
    want = [int(x) - 1 for x in a.pages.split(",")] if a.pages else range(len(reader.pages))
    if a.pages:
        for i in want:
            writer.add_page(reader.pages[i])
    else:
        writer.append(reader)            # keeps outlines and named destinations

    seen, before, after, n = set(), 0, 0, 0
    t0 = time.time()
    for pi, page in enumerate(writer.pages):
        res = page.get("/Resources", {})
        xo = res.get("/XObject")
        if not xo:
            continue
        xo = xo.get_object()
        for key in list(xo.keys()):
            obj = xo[key].get_object()
            if obj.get("/Subtype") != "/Image":
                continue
            if str(obj.get("/Filter")) != "/JPXDecode":
                continue
            ident = id(obj)
            if ident in seen:            # shared XObject: convert once
                continue
            seen.add(ident)
            r = transcode(obj, a.cap, a.quality)
            if r:
                before += r[0]; after += r[1]; n += 1
        if not a.pages and pi % 100 == 0 and pi:
            print(f"    {pi}/{len(writer.pages)} slides…", flush=True)

    tmp = a.out + ".tmp"
    with open(tmp, "wb") as fh:
        writer.write(fh)
    # RE-LINEARIZE. The source was linearized ("Fast Web View") and pypdf does not
    # preserve that, which would have handed back in download latency exactly what the
    # transcode won on decode. qpdf, via pikepdf, puts the first page and its objects at
    # the front of the file again, and recompresses the object streams while it is there.
    import pikepdf
    with pikepdf.open(tmp) as pdf:
        pdf.save(a.out, linearize=True,
                 object_stream_mode=pikepdf.ObjectStreamMode.generate,
                 compress_streams=True)
    os.remove(tmp)
    print(f"  {n} JPX images -> JPEG   {before/1e6:.1f} MB -> {after/1e6:.1f} MB"
          f"   ({time.time()-t0:.0f}s)")
    print(f"  {os.path.basename(a.src)} {os.path.getsize(a.src)/1e6:.0f} MB"
          f"  ->  {os.path.basename(a.out)} {os.path.getsize(a.out)/1e6:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
