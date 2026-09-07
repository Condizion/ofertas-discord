"""Public Telegram previews -> attributed Discord notifications. Python stdlib only."""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


class PreviewParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.posts = []
        self.post = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('data-post'):
            self.post = {'id': attrs['data-post'], 'text': '', 'date': ''}
            self.posts.append(self.post)
            self.depth = 0
        if self.post is None:
            return
        if tag == 'time':
            self.post['date'] = attrs.get('datetime', '')
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'tgme_widget_message_text' in attrs.get('class', '').split():
                self.depth = 1
        if tag == 'br' and self.depth:
            self.post['text'] += '\n'

    def handle_endtag(self, tag):
        if tag == 'div' and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.post is not None and self.depth:
            self.post['text'] += data


def parse(html):
    parser = PreviewParser()
    parser.feed(html)
    posts = {p['id']: p for p in parser.posts}
    return sorted(posts.values(), key=lambda p: int(p['id'].rsplit('/', 1)[1]))


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower())
                   if not unicodedata.combining(c))


def relevant(post, cfg, now):
    # Match product heading, not promotional boilerplate mentioning other products.
    heading = normalized(post['text'].strip().split('\n')[0])
    def contains(term):
        return re.search(r'(?<!\w)' + re.escape(normalized(term)) + r'(?!\w)', heading)
    if not any(contains(k) for k in cfg['keywords']):
        return False
    if any(contains(k) for k in cfg.get('exclude', [])):
        return False
    try:
        age = (now - datetime.fromisoformat(post['date'])).total_seconds()
    except (ValueError, TypeError):
        return False
    return 0 <= age <= cfg['max_age_hours'] * 3600


def payload(post):
    # Short title and price only; full offer/coupons remain at the credited source.
    heading = post['text'].strip().split('\n')[0]
    heading = ' '.join(heading.split()[:20])[:200]
    price = re.search(r'R\$\s*[\d.,]+', post['text'])
    return {'username': 'Ofertas de Hardware', 'allowed_mentions': {'parse': []},
            'embeds': [{'title': heading,
                        'url': 'https://t.me/' + post['id'],
                        'description': ('Preço anunciado: ' + price.group() + '\n' if price else '')
                            + 'Confira condições, cupons e link da loja na publicação original.',
                        'footer': {'text': 'Fonte: @' + post['id'].split('/')[0]
                                   + ' • preço não verificado na loja'},
                        'color': 3066993}]}


def fetch(channel, seen, max_pages):
    if not re.fullmatch(r'[A-Za-z0-9_]+', channel):
        raise ValueError('Nome de canal inválido.')
    url = 'https://t.me/s/' + channel
    result = {}
    for _ in range(max_pages):
        req = Request(url, headers={'User-Agent': 'OfertasDiscord/1.0'})
        with urlopen(req, timeout=25) as response:
            posts = parse(response.read().decode('utf-8'))
        if not posts:
            raise RuntimeError('Fonte sem mensagens; verifique se a página pública mudou.')
        result.update({p['id']: p for p in posts})
        if not seen or any(p['id'] in seen for p in posts):
            break
        oldest = int(posts[0]['id'].rsplit('/', 1)[1])
        url = 'https://t.me/s/' + channel + '?before=' + str(oldest)
        time.sleep(1)
    return sorted(result.values(), key=lambda p: int(p['id'].rsplit('/', 1)[1]))


def send(webhook, message):
    if not re.fullmatch(r'https://discord\.com/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9_-]+', webhook):
        raise ValueError('Configure DISCORD_WEBHOOK_URL com a URL do Discord, sem parâmetros.')
    req = Request(webhook + '?wait=true', data=json.dumps(message).encode(),
                  headers={'Content-Type': 'application/json', 'User-Agent': 'OfertasDiscord/1.0'})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=25) as response:
                response.read()
            return
        except HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                delay = float(json.loads(exc.read()).get('retry_after', 5))
                time.sleep(min(max(delay, 1), 60))
                continue
            raise RuntimeError('Discord retornou HTTP ' + str(exc.code)) from None
        except URLError:
            raise RuntimeError('Falha de conexão com Discord; envio pode ter ocorrido.') from None


def save(state, path):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--preview', help='Arquivo HTML local: não envia nem altera estado')
    args.add_argument('--test-webhook', action='store_true')
    opts = args.parse_args()
    cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    if opts.preview:
        posts = parse(Path(opts.preview).read_text(encoding='utf-8'))
        matches = [p for p in posts if relevant(p, cfg, now)]
        print(json.dumps({'lidas': len(posts), 'filtradas': len(matches),
                          'exemplos': [payload(p) for p in matches[:2]]}, ensure_ascii=True))
        return
    webhook = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
    if not webhook:
        raise RuntimeError('Cadastre o secret DISCORD_WEBHOOK_URL antes de executar.')
    if opts.test_webhook:
        send(webhook, {'content': '✅ Ofertas de Hardware conectado. Fonte: @peperaiohardware. '
                                  'Novas ofertas serão filtradas automaticamente.',
                       'allowed_mentions': {'parse': []}})
        return
    path = ROOT / 'state.json'
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    sent = 0
    for channel in cfg['channels']:
        seen_list = state.get(channel, [])
        seen = set(seen_list)
        posts = fetch(channel, seen, cfg['max_pages'])
        if channel not in state:
            state[channel] = [p['id'] for p in posts]
            save(state, path)
            print(channel + ': inicializado, sem publicar ofertas antigas.')
            continue
        for post in posts:
            if post['id'] in seen:
                continue
            if relevant(post, cfg, now):
                if sent >= cfg['max_posts_per_run']:
                    break
                send(webhook, payload(post))
                sent += 1
                time.sleep(2)
            seen_list.append(post['id'])
            seen.add(post['id'])
            state[channel] = seen_list[-2000:]
            save(state, path)
        print(channel + ': leitura concluída.')
    print('Mensagens enviadas:', sent)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never print raw request URLs or exception bodies containing webhook tokens.
        print('Falha:', str(exc) if isinstance(exc, (RuntimeError, ValueError))
              else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
