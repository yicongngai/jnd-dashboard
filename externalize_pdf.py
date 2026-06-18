#!/usr/bin/env python3
"""One-time: pull the embedded Elevate Playbook PDF out of index-live-auto.html.
 - extract id="pb-data" base64 -> playbook.pdf (served on demand)
 - remove the 64 MB <script id="pb-data"> blob
 - rewrite window.pbLoad() to fetch 'playbook.pdf' instead of decoding base64
Result: deploy HTML drops ~70 MB -> ~2 MB; the PDF loads only when the Playbook tab is opened."""
import re, base64, os

F = "index-live-auto.html"
html = open(F, encoding="utf-8").read()
before = len(html)

# 1. extract + decode the PDF
m = re.search(r'<script[^>]*id="pb-data"[^>]*>([A-Za-z0-9+/=\s]*?)</script>', html, re.S)
if not m:
    raise SystemExit("pb-data block not found")
b64 = re.sub(r"\s+", "", m.group(1))
pdf = base64.b64decode(b64)
open("playbook.pdf", "wb").write(pdf)
print(f"wrote playbook.pdf ({len(pdf)/1e6:.1f} MB)")

# 2. remove the blob (leave a tiny marker comment)
html = html[:m.start()] + "<!-- pb-data externalized -> playbook.pdf -->" + html[m.end():]

# 3. rewrite the loader to fetch the external file
new_loader = '''window.pbLoad = function() {
  if (window.pbLoaded) return;
  var host = document.getElementById('pb-host');
  if (!host) return;
  var url = 'playbook.pdf';
  if (window.pbIsIOS) {
    host.innerHTML = '<div style="color:#fff;text-align:center;padding:24px;max-width:520px;">' +
      '<div style="font-size:48px;margin-bottom:8px;">\\uD83D\\uDCD8</div>' +
      '<div style="font-size:18px;font-weight:600;margin-bottom:6px;">JND Elevate Playbook</div>' +
      '<div style="font-size:13px;opacity:.75;margin-bottom:18px;">Tap to open the deck in Safari for best performance.</div>' +
      '<a href="' + url + '" target="_blank" rel="noopener" download="JND-Elevate-Playbook.pdf" ' +
      'style="display:inline-block;background:#c8102e;color:#fff;border:0;padding:14px 28px;font-size:14px;font-weight:600;border-radius:6px;text-decoration:none;font-family:inherit;">' +
      'Open in Safari \\u2192</a></div>';
  } else {
    var f = document.createElement('iframe');
    f.src = url + '#toolbar=1&navpanes=0&view=FitH';
    f.title = 'JND Elevate Playbook';
    f.setAttribute('allowfullscreen', '');
    f.style.cssText = 'width:100%;height:100%;border:0;display:block;background:#525659;';
    host.innerHTML = '';
    host.appendChild(f);
  }
  window.pbLoaded = true;
};'''
html2, n = re.subn(r'window\.pbLoad = function\(\) \{.*?\}, 50\);\s*\};', lambda _m: new_loader, html, count=1, flags=re.S)
if n != 1:
    raise SystemExit("pbLoad function not matched — aborting (file unchanged)")
html = html2

open(F, "w", encoding="utf-8").write(html)
print(f"{F}: {before/1e6:.1f} MB -> {os.path.getsize(F)/1e6:.2f} MB")
print("pb-data removed:", 'id="pb-data"' not in html, "| loader fetches playbook.pdf:", "var url = 'playbook.pdf'" in html)
