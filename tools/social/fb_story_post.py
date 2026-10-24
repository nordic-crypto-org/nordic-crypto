"""Post a rendered story image as a Facebook Page story and an Instagram story, and record it in the ledger.
Usage: python3 tools/social/fb_story_post.py <story_id> <image.png> [--ledger fb-stories-posted.json] [--result out.json] [--note TEXT] [--dry-run]
Env (never printed): META_PAGE_TOKEN, META_PAGE_ID, META_IG_USER_ID. Optional META_GRAPH_VERSION (v23.0)."""
import argparse, datetime, json, os, sys, time, urllib.error, urllib.parse, urllib.request, uuid

V = os.environ.get('META_GRAPH_VERSION', 'v23.0')

def env(n):
    v = os.environ.get(n)
    if not v: sys.exit(f'missing env {n}')
    return v

def _send(req, tok):
    try: body = urllib.request.urlopen(req, timeout=120).read().decode()
    except urllib.error.HTTPError as e: body = e.read().decode()
    return json.loads(body.replace(tok, '***'))

def call(tok, method, path, params=None):
    p = dict(params or {}); p['access_token'] = tok
    url = f'https://graph.facebook.com/{V}/{path}'
    if method == 'GET': req = urllib.request.Request(url + '?' + urllib.parse.urlencode(p))
    else: req = urllib.request.Request(url, data=urllib.parse.urlencode(p).encode(), method='POST')
    return _send(req, tok)

def upload(tok, pid, img):
    b = uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in (('published', 'false'), ('access_token', tok))]
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="source"; filename="s.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(img, 'rb').read() + b'\r\n')
    parts.append(f'--{b}--\r\n'.encode())
    req = urllib.request.Request(f'https://graph.facebook.com/{V}/{pid}/photos', data=b''.join(parts),
                                 headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    return _send(req, tok)

def post(sid, img, result=None):
    tok, pid, ig = env('META_PAGE_TOKEN'), env('META_PAGE_ID'), env('META_IG_USER_ID')
    res = {}
    def save():
        if result: json.dump(res, open(result, 'w'), indent=1)
    res['upload'] = up = upload(tok, pid, img); save()
    photo = up.get('id'); url = None
    if photo:
        res['fb'] = call(tok, 'POST', f'{pid}/photo_stories', {'photo_id': photo}); save()
        im = call(tok, 'GET', photo, {'fields': 'images'}).get('images') or []
        if im: url = max(im, key=lambda x: x.get('width', 0)).get('source')
    if url and 'fbcdn' in url:
        c = call(tok, 'POST', f'{ig}/media', {'media_type': 'STORIES', 'image_url': url}); res['ig_create'] = c; save()
        cid = c.get('id')
        if cid:
            st = {}
            for _ in range(30):
                st = call(tok, 'GET', cid, {'fields': 'status_code'})
                if st.get('status_code') in ('FINISHED', 'ERROR', 'EXPIRED'): break
                time.sleep(5)
            res['ig_status'] = st
            if st.get('status_code') == 'FINISHED':
                res['ig_pub'] = p = call(tok, 'POST', f'{ig}/media_publish', {'creation_id': cid})
                if p.get('id'): res['ig_permalink'] = call(tok, 'GET', p['id'], {'fields': 'permalink'}).get('permalink')
            save()
    return photo, res

def record(ledger, sid, photo, res, note=None):
    L = json.load(open(ledger)) if os.path.exists(ledger) else {'posted': [], 'details': {}}
    fb_ok = bool(res.get('fb', {}).get('success')); ig_ok = bool(res.get('ig_pub', {}).get('id'))
    det = {'posted_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    if note: det['note'] = note
    if fb_ok: det.update(fb_photo_id=photo, fb_story_post_id=res['fb'].get('post_id'))
    if ig_ok: det.update(ig_media_id=res['ig_pub']['id'], ig_permalink=res.get('ig_permalink'))
    if fb_ok or ig_ok:
        if not (fb_ok and ig_ok): det['partial'] = 'fb' if fb_ok else 'ig'
        L.setdefault('details', {})[sid] = det
        if sid not in L.setdefault('posted', []): L['posted'].append(sid)
    L['last_run'] = det['posted_at']
    json.dump(L, open(ledger, 'w'), indent=1, ensure_ascii=False)
    return fb_ok, ig_ok

if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('sid'); a.add_argument('image')
    a.add_argument('--ledger', default='fb-stories-posted.json'); a.add_argument('--result'); a.add_argument('--note')
    a.add_argument('--dry-run', action='store_true')
    o = a.parse_args()
    if not os.path.exists(o.image): sys.exit(f'no image {o.image}')
    if o.dry_run:
        L = json.load(open(o.ledger)) if os.path.exists(o.ledger) else {'posted': []}
        print('would post', o.sid, o.image, '(already posted)' if o.sid in L.get('posted', []) else ''); sys.exit(0)
    photo, res = post(o.sid, o.image, o.result)
    print(json.dumps(res, indent=1))
    fb_ok, ig_ok = record(o.ledger, o.sid, photo, res, o.note)
    print('fb_ok', fb_ok, 'ig_ok', ig_ok)
    sys.exit(0 if fb_ok or ig_ok else 1)
