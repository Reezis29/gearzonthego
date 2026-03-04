"""
Blog Engine for Gearz On The Go
Parses Markdown files with YAML frontmatter from content/blog/
"""

import os
import re
import math
import frontmatter
import markdown
from datetime import datetime

BLOG_DIR = os.path.join(os.path.dirname(__file__), 'content', 'blog')

CATEGORY_SLUGS = {
    'Langkawi Travel': 'langkawi-travel',
    'Camera Tips': 'camera-tips',
    'Travel Vlogging': 'travel-vlogging',
    'Langkawi Guides': 'langkawi-guides',
}


def slugify(text):
    """Convert heading text to a URL-safe ID."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def estimate_read_time(content):
    """Estimate reading time based on word count (200 wpm)."""
    words = len(content.split())
    return max(1, math.ceil(words / 200))


def generate_toc(html_content):
    """Extract H2/H3 headings from HTML and generate TOC items."""
    toc = []
    pattern = re.compile(r'<(h[23])[^>]*>(.*?)</h[23]>', re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html_content):
        tag = match.group(1).lower()
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        heading_id = slugify(text)
        level = 2 if tag == 'h2' else 3
        toc.append({'id': heading_id, 'text': text, 'level': level})
    return toc


def add_heading_ids(html_content):
    """Add id attributes to H2/H3 headings for anchor links."""
    def replacer(match):
        tag = match.group(1)
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        heading_id = slugify(text)
        return f'<{tag} id="{heading_id}">{match.group(2)}</{tag}>'
    return re.sub(r'<(h[23])>(.*?)</h[23]>', replacer, html_content, flags=re.IGNORECASE | re.DOTALL)


def load_post(slug):
    """Load a single blog post by slug. Returns None if not found."""
    filepath = os.path.join(BLOG_DIR, f'{slug}.md')
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    md = markdown.Markdown(extensions=['extra', 'nl2br'])
    raw_html = md.convert(post.content)
    html_with_ids = add_heading_ids(raw_html)
    toc = generate_toc(html_with_ids)

    meta = post.metadata
    read_time = meta.get('read_time') or estimate_read_time(post.content)
    category = meta.get('category', '')

    return {
        'slug': meta.get('slug', slug),
        'title': meta.get('title', ''),
        'excerpt': meta.get('excerpt', ''),
        'category': category,
        'category_slug': meta.get('category_slug', CATEGORY_SLUGS.get(category, 'general')),
        'date': str(meta.get('date', '')),
        'cover_image': meta.get('cover_image', ''),
        'meta_title': meta.get('meta_title', ''),
        'meta_description': meta.get('meta_description', ''),
        'author': meta.get('author', 'Gearz On The Go'),
        'read_time': read_time,
        'recommended_activity': meta.get('recommended_activity', ''),
        'recommended_camera': meta.get('recommended_camera', ''),
        'recommended_link': meta.get('recommended_link', '/#availability'),
        'content_html': html_with_ids,
        'toc': toc,
    }


def load_all_posts():
    """Load all blog posts, sorted by date descending."""
    posts = []
    if not os.path.exists(BLOG_DIR):
        return posts
    for filename in os.listdir(BLOG_DIR):
        if filename.endswith('.md'):
            slug = filename[:-3]
            post = load_post(slug)
            if post:
                posts.append(post)
    posts.sort(key=lambda p: p['date'], reverse=True)
    return posts


def get_related_posts(current_slug, all_posts, count=3):
    """Get related posts excluding the current one."""
    return [p for p in all_posts if p['slug'] != current_slug][:count]


def get_all_slugs():
    """Return list of all post slugs for sitemap generation."""
    if not os.path.exists(BLOG_DIR):
        return []
    return [f[:-3] for f in os.listdir(BLOG_DIR) if f.endswith('.md')]
