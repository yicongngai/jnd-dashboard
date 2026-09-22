#!/usr/bin/env python3
"""Compile published JND Launches into the sun map; never read preview/drops files.

Run in the clean deployment checkout, before inject_data_all.py. A reviewed
map-model.json is accepted only for the exact current geometry source digest.
No inference of building positions or heights from images is performed here.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit, unquote
from urllib.request import urlopen

GEOMETRY = re.compile(r'site[\s_-]*plan|schematic|elevation|orientation|massing|block[\s_-]*layout', re.I)
FIELDS = ('address', 'towers', 'site_sqft', 'site_sqm', 'plot_ratio', 'building_heights', 'storeys')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
    temp.replace(path)


def normal(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def point(value):
    return (isinstance(value, list) and len(value) == 2
            and all(isinstance(n, (float, int)) and not isinstance(n, bool) and math.isfinite(n) for n in value)
            and 103.55 < value[0] < 104.15 and 1.15 < value[1] < 1.5)


def ring(value):
    return (isinstance(value, list) and len(value) >= 4 and value[0] == value[-1]
            and all(point(p) for p in value)
            and abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(value, value[1:]))) > 1e-12)


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.geometry = set()
        self.siteplans = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        label = ' '.join(str(attrs.get(k, '')) for k in ('src', 'href', 'alt', 'title', 'data-cap'))
        if GEOMETRY.search(label):
            for k in ('src', 'data-src', 'data-lb', 'href'):
                raw = attrs.get(k, '')
                if raw.startswith(('assets/', './assets/')):
                    rel = unquote(urlsplit(raw).path).removeprefix('./')
                    self.geometry.add(rel)
                    if re.search(r'site[\s_-]*plan', label, re.I):
                        self.siteplans.add(rel)


def source_snapshot(folder, facts):
    config = read(folder/'map-source.json') if (folder/'map-source.json').exists() else {}
    parser = Assets()
    if (folder/'index.html').exists():
        parser.feed((folder/'index.html').read_text())
    # Named geometry assets also catch replacements before an HTML caption changes.
    paths = parser.geometry | {p.relative_to(folder).as_posix() for p in (folder/'assets').rglob('*')
                               if p.is_file() and GEOMETRY.search(p.name)}
    paths |= set(config.get('geometryAssets', []))
    files, missing = {}, []
    for rel in sorted(paths):
        path = (folder/rel).resolve()
        if not path.is_relative_to((folder/'assets').resolve()):
            raise ValueError('Geometry source must be inside published assets: ' + rel)
        if path.is_file():
            files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            missing.append(rel)
    geometry_facts = {k: facts.get(k) for k in FIELDS if k in facts}
    geometry_facts['location'] = config.get('location')
    payload = {'facts': geometry_facts, 'assets': files, 'missingAssets': missing, 'sitePlans': sorted(parser.siteplans)}
    if config.get('developerDocument'):
        payload['developerDocument'] = config['developerDocument']
    return config, payload, digest(payload)


def locate(name):
    """Accept only exact OneMap building-name matches at a single location."""
    found = []
    first_url = None
    for page in range(1, 6):
        url = 'https://www.onemap.gov.sg/api/common/elastic/search?' + urlencode({
            'searchVal': name, 'returnGeom': 'Y', 'getAddrDetails': 'Y', 'pageNum': page})
        first_url = first_url or url
        with urlopen(url, timeout=15) as response:
            data = json.load(response)
        for result in data.get('results', []):
            if normal(result.get('BUILDING', '')) == normal(name):
                p = [float(result['LONGITUDE']), float(result['LATITUDE'])]
                if point(p):
                    found.append(p)
        total = int(data.get('totalNumPages', 1))
        if total > 5:
            return None
        if page >= total:
            break
    # Multiple addresses across a development require an explicit reviewed centre.
    if found and all(abs(p[0]-found[0][0]) < .0001 and abs(p[1]-found[0][1]) < .0001 for p in found):
        return {'center': found[0], 'source': first_url}
    return None


def validate_model(model, fingerprint, project):
    if model.get('sourceFingerprint') != fingerprint:
        raise ValueError('Model was reviewed against a different source version')
    if not model.get('reviewedAt') or not model.get('reviewNote'):
        raise ValueError('Model needs a review date and evidence note')
    if not ring(model.get('site')) or not point(model.get('center', project.get('center'))):
        raise ValueError('Model needs a valid Singapore site boundary and centre')
    towers = model.get('towers')
    if not isinstance(towers, list) or not towers:
        raise ValueError('Model has no building sections')
    names = set()
    for tower in towers:
        floors = tower.get('floors')
        geom = tower.get('geometry', {})
        if (not tower.get('name') or tower['name'] in names or isinstance(floors, bool)
                or not isinstance(floors, (int, float)) or not 0 < floors <= 100
                or geom.get('type') != 'Polygon' or not geom.get('coordinates')
                or not all(ring(r) for r in geom['coordinates'])):
            raise ValueError('Invalid building name, floor count or polygon')
        # Reject geographically misplaced sections, even if still within Singapore.
        xs, ys = zip(*model['site'])
        if any(not min(xs)-.00001 <= p[0] <= max(xs)+.00001 or not min(ys)-.00001 <= p[1] <= max(ys)+.00001
               for r in geom['coordinates'] for p in r):
            raise ValueError('Building section lies outside site bounds')
        names.add(tower['name'])


def check_developer_document(document):
    """Check the public developer brochure; never accept changed plans automatically."""
    url = document['url']
    # A replacement brochure may have a new URL on the same developer page.
    page = document.get('page')
    if page:
        with urlopen(page, timeout=20) as response:
            html = response.read(2_000_000).decode('utf-8', errors='replace')
        candidates = set(re.findall(r'https://www\.simlian\.com\.sg/[^\s\"<>]+Amberwood[^\s\"<>]*eBrochure[^\s\"<>]*\.pdf', html, re.I))
        if candidates and candidates != {url}:
            return 'changed'
        if not candidates:
            raise ValueError('Developer brochure link unavailable')
    if urlsplit(url).hostname != 'www.simlian.com.sg' or urlsplit(url).scheme != 'https':
        raise ValueError('Unapproved developer document host')
    with urlopen(url, timeout=30) as response:
        body = response.read(25_000_001)
    if len(body) > 25_000_000 or not body.startswith(b'%PDF'):
        raise ValueError('Developer response is not a supported PDF')
    return 'unchanged' if hashlib.sha256(body).hexdigest() == document['sha256'] else 'changed'


def compile_catalog(root, catalog, checked_at, resolver=locate, document_checker=None):
    catalog = copy.deepcopy(catalog)
    projects = catalog['projects']
    reports = []
    sources = [(f, False) for f in sorted((root/'launch').glob('*'))
               if (f/'launch.json').exists() and (f/'index.html').exists()]
    sources += [(f, True) for f in sorted((root/'sun-map/data/launch-sources').glob('*')) if (f/'source.json').exists()]
    seen = set()
    for folder, external in sources:
        if folder.name in seen:
            continue  # A published JND deck takes precedence over the developer snapshot.
        seen.add(folder.name)
        facts = read(folder/('source.json' if external else 'launch.json'))
        config, source, fingerprint = source_snapshot(folder, facts)
        matches = [p for p in projects if p['id'] == folder.name]
        if not matches:
            matches = [p for p in projects if normal(p['name']) == normal(facts['name'])]
        if len(matches) > 1:
            raise ValueError('Ambiguous launch identity: ' + folder.name)
        if matches:
            project = matches[0]
        else:
            project = {'id': folder.name, 'name': facts['name'], 'center': None, 'towers': [], 'top': '', 'asOf': ''}
            projects.append(project)
        location = config.get('location')
        if location:
            if not point(location.get('center')) or not location.get('source'):
                raise ValueError('Published map location needs coordinates and source: ' + folder.name)
            project.update(center=location['center'], coordinateSource=location['source'], coordinateDate=location.get('verifiedAt', ''))
        elif not point(project.get('center')):
            try:
                location = resolver(facts['name'])
            except Exception as error:
                print(f'Location pending for {folder.name}: {type(error).__name__}')
            if location:
                project.update(center=location['center'], coordinateSource=location['source'], coordinateDate=checked_at[:10])
        source_label = facts.get('sourceLabel', 'Developer brochure') if external else 'JND Launches'
        asset_base = 'https://jndtoolkit.com/' + folder.relative_to(root).as_posix() + '/'
        url = facts['sourceUrl'] if external else asset_base
        project.update(name=facts['name'], address=facts.get('address', ''), top=facts.get('novp') or project.get('top', ''), source=url)
        try:
            revision = subprocess.check_output(['git', 'log', '-1', '--format=%cI', '--', str(folder.relative_to(root))], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            revision = ''
        previous = project.get('launchSync', {})
        status, reason = 'awaiting-site-plan', 'Awaiting a published site plan. No new building geometry has been added.'
        has_plan = bool(set(source['sitePlans']) & set(source['assets'])) or any(re.search(r'site[\s_-]*plan', p, re.I) for p in source['assets']) or facts.get('checklist', {}).get('Site plan') is True and bool(source['assets'])
        if has_plan:
            status, reason = 'awaiting-model', 'Site plan released. Building placement and storeys await model review.'
        if project.get('towers'):
            status, reason = 'review-required', 'Earlier model retained. It has not been verified against the current JND Launches slides.'
        # Reusing generated output must never make a review flag disappear.
        if previous.get('status') == 'current' and previous.get('sourceFingerprint') != fingerprint:
            reason = 'Site plan or building facts changed. Earlier model retained pending review.'
        if source['missingAssets']:
            status, reason = 'source-unavailable', 'A published geometry source is missing. Earlier geometry retained pending review.'
        model_path = folder/'map-model.json'
        if model_path.exists():
            model = read(model_path)
            try:
                # A previously reviewed file remains the last checked geometry,
                # even after its supporting slide is replaced in a later commit.
                validate_model(model, model.get('sourceFingerprint'), project)
                if not re.fullmatch(r'[0-9a-f]{64}', model.get('sourceFingerprint', '')):
                    raise ValueError('Model needs a valid source fingerprint')
            except ValueError as error:
                status, reason = 'review-required', str(error) + '. Earlier geometry retained pending review.'
            else:
                for k in ('towers', 'site', 'center', 'excludeExistingOsmIds', 'planImage', 'elevationImage', 'scaleNote', 'northClockwise', 'sourceHash', 'floorRange'):
                    if k in model:
                        project[k] = model[k]
                project.update(asOf=model['reviewedAt'], modelNote=model['reviewNote'], planDataset=source_label + ' site plan and building facts')
                if source['missingAssets']:
                    status, reason = 'source-unavailable', 'A published geometry source is missing. Earlier checked model retained pending review.'
                elif model['sourceFingerprint'] == fingerprint and has_plan:
                    # Prefer a site plan over a schematic for the direct source link.
                    plan = next((p for p in source['assets'] if re.search(r'site[\s_-]*plan', p, re.I)), next(iter(source['assets'])))
                    project['planUrl'] = asset_base + plan
                    status, reason = 'current', 'Model checked against the published site plan and building facts. Heights remain estimates.'
                    if model.get('openQuestions'):
                        status, reason = 'provisional', 'Layout reviewed; ' + ' '.join(model['openQuestions'])
                else:
                    status, reason = 'review-required', 'Site plan or building facts changed. Earlier checked model retained pending review.'
        document = config.get('developerDocument')
        if document:
            # Preserve a live warning during an offline rebuild until a successful check clears it.
            remote_state = previous.get('documentStatus', 'not-checked')
            remote_checked = previous.get('documentCheckedAt', '')
            if document_checker:
                try:
                    remote_state = document_checker(document)
                except Exception as error:
                    print(f'Developer check unavailable for {folder.name}: {type(error).__name__}')
                    remote_state = 'unavailable'
                remote_checked = checked_at
            if remote_state == 'changed':
                status, reason = 'review-required', 'Developer brochure changed. Earlier checked model retained until the new plans are reviewed.'
            elif remote_state in ('unavailable', 'not-checked'):
                status, reason = 'source-unavailable', 'Saved developer plans are modelled; the latest online brochure could not be verified.'
        report = {'id': project['id'], 'slug': folder.name, 'name': project['name'], 'url': url, 'sourceLabel': source_label,
                  'status': status, 'message': reason, 'located': point(project.get('center')),
                  'sitePlanAvailable': has_plan, 'sourceFingerprint': fingerprint, 'sourceUpdatedAt': revision,
                  'modelAsOf': project.get('asOf', ''), 'modelSections': len(project.get('towers', [])),
                  'geometrySources': [{'url': asset_base+p, 'file': p, 'sha256': sha} for p, sha in source['assets'].items()],
                  'missingAssets': source['missingAssets'], 'buildingFacts': source['facts']}
        if document:
            report.update(documentStatus=remote_state, documentCheckedAt=remote_checked, documentUrl=document['url'])
        project['launchSync'] = report
        reports.append(report)
    catalog['launchSync'] = {'checkedAt': checked_at, 'source': 'Published JND Launches and developer plans', 'count': len(reports)}
    return catalog, {'checkedAt': checked_at, 'projects': reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    path = root/'sun-map/data/future-projects.json'
    checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
    catalog, report = compile_catalog(root, read(path), checked, (lambda _: None) if args.offline else locate,
                                     None if args.offline else check_developer_document)
    write(path, catalog)
    write(root/'sun-map/data/launch-updates.json', report)
    # Keep the embedded map cache key aligned without rewriting committed market data.
    page = root/'index-live-auto.html'
    if page.exists():
        content = re.sub(r'(embed=1&amp;v=|theme-os-toolkit.css\?v=sun-)(25|26|27|28)\b', r'\g<1>29', page.read_text())
        preloader = '<script defer src="sun-map/preload-embed.js?v=29"></script>'
        if 'src="sun-map/preload-embed.js' in content:
            content = re.sub(r'<script[^>]*src="sun-map/preload-embed.js[^"]*"[^>]*></script>', preloader, content)
        else:
            content = content.replace('</body>', preloader + '\n</body>')
        page.write_text(content)
    summary = f"JND Launches → sun map: {len(report['projects'])} published projects; " + str(sum(p['status'] != 'current' or not p['located'] for p in report['projects'])) + ' need model/source/location review.'
    print(summary)
    import os
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
            out.write('## Launch map sync\n\n'+summary+'\n\n')
            for p in report['projects']:
                out.write(f"- {p['name']}: {p['status']}" + ('' if p['located'] else ' · location pending') + '\n')


if __name__ == '__main__':
    main()
