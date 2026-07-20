# -*- coding: utf-8 -*-
"""Aggregate blog cards from all sister properties into blog/index.html.

Sources:
  1. Main site posts  - the 13 existing cards in blog/index.html (kept verbatim)
  2. Florida Solar Exit - parsed from ../florida-solar-exit/content/blog.ts
  3. WWS safety guides  - parsed from wwslgc/guides/*.html in this repo

Sister cards link out to their own domains (canonical lives there) with
target=_blank and a source-labeled pill. Re-run any time sister content
changes; the grid regenerates in place between the post-grid div and the
empty-state paragraph. k5 has no blog; intentionally excluded.
"""
import glob
import html
import os
import re

REPO = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(REPO, 'blog', 'index.html')
SOLAR_TS = r'C:\Users\kjburnz\florida-solar-exit\content\blog.ts'
SOLAR_BASE = 'https://solarexit.collaborativeconceptsfl.com/blog/'
WWS_DIR = os.path.join(REPO, 'wwslgc', 'guides')
WWS_BASE = 'https://wwslgc.collaborativeconceptsfl.com/guides/'

CARD_STYLE = 'background:var(--paper); border:1px solid var(--sand); transition:.22s;'


def unescape_ts(s):
    return s.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')


def parse_main_cards(index_html):
    """Grab the existing local cards exactly as they are, with their dates."""
    grid_m = re.search(
        r'<div id="post-grid"[^>]*>(.*?)</div>\s*(?=<p id="empty-state")',
        index_html, re.DOTALL)
    if not grid_m:
        raise SystemExit('FATAL: could not locate post-grid section')
    cards = re.findall(r'<a href="/blog/[^"]*".*?</a>', grid_m.group(1), re.DOTALL)
    out = []
    for c in cards:
        d = re.search(r'>(\d{4}-\d{2}-\d{2})<', c)
        out.append({'date': d.group(1) if d else '0000-00-00', 'html': c})
    return out


def parse_solar_posts():
    src = open(SOLAR_TS, encoding='utf-8').read()
    chunks = re.split(r'\n\s*slug:\s*"', src)[1:]
    posts = []
    for ch in chunks:
        slug = ch.split('"', 1)[0]
        def field(name):
            m = re.search(name + r':\s*\n?\s*"((?:[^"\\]|\\.)*)"', ch)
            return unescape_ts(m.group(1)) if m else ''
        title, desc, date = field('title'), field('description'), field('date')
        if not (slug and title):
            continue
        posts.append({'slug': slug, 'title': title, 'desc': desc,
                      'date': date or '0000-00-00'})
    return posts


def parse_wws_guides():
    guides = []
    for fp in sorted(glob.glob(os.path.join(WWS_DIR, '*.html'))):
        name = os.path.basename(fp)
        if name == 'index.html':
            continue
        s = open(fp, encoding='utf-8').read()
        if 'noindex' in s[:3000]:
            continue
        t = re.search(r'<title>(.*?)</title>', s, re.DOTALL)
        d = re.search(r'<meta name="description" content="([^"]*)"', s)
        if not t:
            continue
        title = html.unescape(re.sub(r'\s+', ' ', t.group(1)).strip())
        title = re.split(r'\s*\|\s*', title)[0].strip()
        guides.append({'slug': name[:-5],
                       'title': title,
                       'desc': html.unescape(d.group(1)) if d else ''})
    return guides


def esc(s):
    return html.escape(s, quote=False)


def clip(s, n=190):
    s = s.strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'


def solar_card(p):
    return (f'<a href="{SOLAR_BASE}{p["slug"]}" target="_blank" rel="noopener" '
            f'data-cat="solar" class="post-card group rounded-2xl p-7 flex flex-col" style="{CARD_STYLE}">\n'
            '<div class="flex items-center gap-3 mb-3">\n'
            '<span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded" '
            'style="background:#15803d15;color:#15803d">Solar Exit</span>\n'
            f'<span class="text-xs text-on-surface-variant">{p["date"]}</span>\n'
            '</div>\n'
            f'<h2 class="font-extrabold text-primary text-lg leading-snug group-hover:text-secondary transition-colors">{esc(p["title"])}</h2>\n'
            f'<p class="text-sm text-on-surface-variant mt-3 leading-relaxed flex-1">{esc(clip(p["desc"]))}</p>\n'
            '<span class="mt-5 inline-flex items-center gap-1 text-sm font-bold text-primary group-hover:text-secondary">'
            'Read on Solar Exit <span aria-hidden="true">↗</span></span>\n'
            '</a>')


def wws_card(g):
    return (f'<a href="{WWS_BASE}{g["slug"]}" target="_blank" rel="noopener" '
            f'data-cat="safety" class="post-card group rounded-2xl p-7 flex flex-col" style="{CARD_STYLE}">\n'
            '<div class="flex items-center gap-3 mb-3">\n'
            '<span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded" '
            'style="background:#b4530915;color:#b45309">Safety &amp; Compliance</span>\n'
            '<span class="text-xs text-on-surface-variant">WWS Guide</span>\n'
            '</div>\n'
            f'<h2 class="font-extrabold text-primary text-lg leading-snug group-hover:text-secondary transition-colors">{esc(g["title"])}</h2>\n'
            f'<p class="text-sm text-on-surface-variant mt-3 leading-relaxed flex-1">{esc(clip(g["desc"]))}</p>\n'
            '<span class="mt-5 inline-flex items-center gap-1 text-sm font-bold text-primary group-hover:text-secondary">'
            'Read the guide <span aria-hidden="true">↗</span></span>\n'
            '</a>')


def main():
    index_html = open(INDEX, encoding='utf-8').read()

    main_cards = parse_main_cards(index_html)
    solar = parse_solar_posts()
    wws = parse_wws_guides()
    print(f'sources: main={len(main_cards)} solar={len(solar)} wws={len(wws)}')

    dated = ([{'date': c['date'], 'html': c['html']} for c in main_cards]
             + [{'date': p['date'], 'html': solar_card(p)} for p in solar])
    dated.sort(key=lambda x: x['date'], reverse=True)
    undated = [wws_card(g) for g in sorted(wws, key=lambda g: g['title'])]

    all_cards = [d['html'] for d in dated] + undated
    grid_inner = '\n<!-- AGGREGATED from main + Solar Exit + WWS by _blog_aggregator.py -->\n' \
                 + '\n\n'.join(all_cards) + '\n'

    new_html = re.sub(
        r'(<div id="post-grid"[^>]*>).*?(</div>)(\s*<p id="empty-state")',
        lambda m: m.group(1) + grid_inner + m.group(2) + m.group(3),
        index_html, count=1, flags=re.DOTALL)

    # Add the Safety & Compliance chip once
    if 'data-cat="safety"' not in new_html:
        new_html = new_html.replace(
            '<button class="cat-chip" data-cat="market" style="--chip-color:#0e7490">Florida Market</button>',
            '<button class="cat-chip" data-cat="market" style="--chip-color:#0e7490">Florida Market</button>\n'
            '<button class="cat-chip" data-cat="safety" style="--chip-color:#b45309">Safety &amp; Compliance</button>')

    # Refresh the intro copy to reflect aggregation (idempotent)
    new_html = new_html.replace(
        'Written by the team running the operation, not a content shop.',
        'Written by the team running the operation, not a content shop. '
        'Aggregated from Collaborative Concept, Florida Solar Exit, and WWS — '
        'sister-site articles open on their own sites.')

    open(INDEX, 'w', encoding='utf-8').write(new_html)
    total = len(all_cards)
    print(f'wrote {total} cards to blog/index.html')


if __name__ == '__main__':
    main()
