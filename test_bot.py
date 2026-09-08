import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import bot

HTML = '''<div data-post="canal/10"><a class="tgme_widget_message_photo_wrap" style="width:500px;background-image:url('https://cdn1.telesco.pe/file/produto_10.jpg')"></a><div class="tgme_widget_message_text">SSD <b>1TB</b><br/>R&#36; 299 com cupom: TECH10<br/><a href="https://loja.example/produto">Comprar</a></div><time datetime="2026-09-07T12:00:00+00:00"></time></div>
<div data-post="canal/11"><div class="tgme_widget_message_text">Smart TV<br/>R$ 999</div><time datetime="2026-09-07T12:01:00+00:00"></time></div>'''


class BotTests(unittest.TestCase):
    def test_parser_filter_and_expiration(self):
        posts = bot.parse(HTML)
        self.assertEqual(posts[0]['text'], 'SSD 1TB\nR$ 299 com cupom: TECH10\nComprar')
        cfg = {'keywords': ['ssd'], 'max_age_hours': 6}
        now = datetime(2026, 9, 7, 13, tzinfo=timezone.utc)
        self.assertTrue(bot.relevant(posts[0], cfg, now))
        self.assertFalse(bot.relevant(posts[1], cfg, now))
        self.assertFalse(bot.relevant(posts[0], cfg, now.replace(day=8)))
        self.assertEqual(bot.payload(posts[0])['allowed_mentions'], {'parse': []})
        self.assertEqual(bot.payload(posts[0])['embeds'][0]['image']['url'],
                         'https://cdn1.telesco.pe/file/produto_10.jpg')
        card = bot.payload(posts[0], {'discord_role_id': '123456789012345678',
                                      'discord_invite_url': 'https://discord.gg/exemplo'})
        self.assertEqual(card['content'], '🔥 Nova promoção para <@&123456789012345678>')
        self.assertEqual(card['allowed_mentions']['roles'], ['123456789012345678'])
        self.assertEqual(card['embeds'][0]['url'], 'https://loja.example/produto')
        self.assertIn('`TECH10`', card['embeds'][0]['description'])
        self.assertIn('Entre no Discord', card['embeds'][0]['description'])

    def test_first_run_and_dedup(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config.json').write_text(json.dumps({'channels': ['canal'],
                'max_pages': 1, 'max_posts_per_run': 8}), encoding='utf-8')
            posts = bot.parse(HTML)
            with patch.object(bot, 'ROOT', root), patch('sys.argv', ['bot.py']), \
                 patch.dict('os.environ', {'DISCORD_WEBHOOK_URL': 'placeholder'}), \
                 patch.object(bot, 'fetch', return_value=posts), \
                 patch.object(bot, 'relevant', return_value=True), \
                 patch.object(bot, 'send') as send, patch.object(bot.time, 'sleep'):
                bot.main()
                bot.main()
                send.assert_not_called()
                posts.append(dict(posts[0], id='canal/12'))
                bot.main()
                bot.main()
                self.assertEqual(send.call_count, 1)

    def test_failed_send_not_marked_seen(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config.json').write_text(json.dumps({'channels': ['canal'],
                'max_pages': 1, 'max_posts_per_run': 8}), encoding='utf-8')
            (root / 'state.json').write_text('{"canal": []}', encoding='utf-8')
            with patch.object(bot, 'ROOT', root), patch('sys.argv', ['bot.py']), \
                 patch.dict('os.environ', {'DISCORD_WEBHOOK_URL': 'placeholder'}), \
                 patch.object(bot, 'fetch', return_value=bot.parse(HTML)), \
                 patch.object(bot, 'relevant', return_value=True), \
                 patch.object(bot, 'send', side_effect=RuntimeError('HTTP 500')):
                with self.assertRaises(RuntimeError):
                    bot.main()
                self.assertEqual(json.loads((root / 'state.json').read_text()), {'canal': []})


if __name__ == '__main__':
    unittest.main()
