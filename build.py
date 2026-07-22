"""Static site build for Private Walking Tours by Ivana.

Each page lives in src/pages/<page-id>/<lang>/ as a meta.json + content.html
pair. English is the canonical language, served at the site root. Additional
languages can be dropped in later under their own language prefix (e.g.
/hr/o-meni/) with no code changes — the build discovers whatever it finds.

Shared markup (header, footer, contact CTA) lives in src/partials/. Site-wide
contact details live in the CONFIG block below: change a value once here and it
updates across every page on the next build.

Run `python build.py` after editing any partial, page, or config value.
"""
import datetime
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
PAGES_DIR = os.path.join(SRC, "pages")
PARTIALS_DIR = os.path.join(SRC, "partials")

DEFAULT_LANG = "en"
LANGUAGES = ["en"]  # add "hr", "de", ... here as translations are created

# ---------------------------------------------------------------------------
# CONFIG — the only place site-wide details live. Swap placeholders for the
# real values once they exist (domain, email, socials, form endpoint).
# ---------------------------------------------------------------------------
CONFIG = {
    "SITE_NAME": "Private Walking Tours by Ivana",
    "SHORT_NAME": "Ivana",

    # PLACEHOLDER — no domain yet. Replace both when the domain is registered.
    "SITE_URL": "https://ivanaguide.com",
    "EMAIL": "info@ivanaguide.com",              # PLACEHOLDER

    "PHONE_DISPLAY": "+385 95 527 8924",
    "PHONE_E164": "+385955278924",
    "WHATSAPP_URL": "https://wa.me/385955278924",

    # PLACEHOLDER — real profile links coming later. "#" keeps the icons
    # inert (they render but go nowhere) until the URLs are dropped in.
    "INSTAGRAM": "#",
    "FACEBOOK": "#",

    # PLACEHOLDER — create a free form endpoint (e.g. Formspree) and paste the
    # action URL here. Until then the form posts nowhere.
    "FORM_ENDPOINT": "https://formspree.io/f/YOUR_FORM_ID",

    "MEETING_POINT": "Obala hrvatske mornarice 1, 22000 Šibenik (next to the INA gas station)",
    "MEETING_MAP": "https://maps.google.com/?q=Obala+hrvatske+mornarice+1+Šibenik",
}

SITE_URL = CONFIG["SITE_URL"]
DEFAULT_OG_IMAGE = f"{SITE_URL}/assets/img/sibenik-cathedral-st-james-square-sunset-land.webp"
YEAR = str(datetime.date.today().year)

HOME_LABEL = {"en": "Home"}


def compute_asset_version():
    """Short hash of styles.css + script.js so browsers fetch fresh copies
    whenever either changes, instead of serving a stale cached copy."""
    hasher = hashlib.md5()
    for name in ("styles.css", "script.js"):
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                hasher.update(f.read())
    return hasher.hexdigest()[:10]


ASSET_VERSION = compute_asset_version()


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def apply_config(text):
    """Replace {{CONFIG_KEY}} tokens with values from CONFIG, plus a couple of
    derived convenience tokens used in markup."""
    for key, value in CONFIG.items():
        text = text.replace("{{" + key + "}}", value)
    text = text.replace("{{EMAIL_URL}}", "mailto:" + CONFIG["EMAIL"])
    text = text.replace("{{PHONE_URL}}", "tel:" + CONFIG["PHONE_E164"])
    text = text.replace("{{YEAR}}", YEAR)
    return text


def url_path(lang, slug):
    """Root-relative path (no domain), e.g. / or /tours/ or /hr/ture/."""
    if lang == DEFAULT_LANG:
        path = f"{slug}/" if slug else ""
    else:
        path = f"{lang}/{slug}/" if slug else f"{lang}/"
    return f"/{path}"


def canonical_url(lang, slug):
    return f"{SITE_URL}{url_path(lang, slug)}"


def output_path(lang, slug):
    if lang == DEFAULT_LANG:
        rel = os.path.join(slug, "index.html") if slug else "index.html"
    else:
        rel = os.path.join(lang, slug, "index.html") if slug else os.path.join(lang, "index.html")
    return os.path.join(ROOT, rel)


def discover_pages():
    """Returns {page_id: {lang: meta_dict}} for every page-id/lang combo found."""
    pages = {}
    for page_id in sorted(os.listdir(PAGES_DIR)):
        page_dir = os.path.join(PAGES_DIR, page_id)
        if not os.path.isdir(page_dir):
            continue
        variants = {}
        for lang in sorted(os.listdir(page_dir)):
            lang_dir = os.path.join(page_dir, lang)
            meta_path = os.path.join(lang_dir, "meta.json")
            if lang not in LANGUAGES or not os.path.isfile(meta_path):
                continue
            with open(meta_path, "r", encoding="utf-8") as f:
                variants[lang] = json.load(f)
        if variants:
            pages[page_id] = variants
    return pages


def build_hreflang_block(variants):
    links = []
    for lang, meta in variants.items():
        url = canonical_url(lang, meta.get("slug", ""))
        links.append(f'<link rel="alternate" hreflang="{lang}" href="{url}">')
    if DEFAULT_LANG in variants:
        default_url = canonical_url(DEFAULT_LANG, variants[DEFAULT_LANG].get("slug", ""))
        links.append(f'<link rel="alternate" hreflang="x-default" href="{default_url}">')
    return "\n".join(links)


_PARTIAL_CACHE = {}


def load_partial(name, lang):
    """Language-specific partial <name>.<lang>.html if present, else <name>.html."""
    key = (name, lang)
    if key not in _PARTIAL_CACHE:
        localized = os.path.join(PARTIALS_DIR, f"{name}.{lang}.html")
        path = localized if os.path.isfile(localized) else os.path.join(PARTIALS_DIR, f"{name}.html")
        _PARTIAL_CACHE[key] = read(path)
    return _PARTIAL_CACHE[key]


def build_nav(current_slug, lang):
    """Header nav with the current page marked active."""
    items = [
        ("", "Home"),
        ("tours", "Tours"),
        ("about", "About"),
        ("contact", "Contact"),
    ]
    links = []
    for slug, label in items:
        cls = "nav-link active" if slug == current_slug else "nav-link"
        links.append(f'<a href="{url_path(lang, slug)}" class="{cls}">{label}</a>')
    return "\n        ".join(links)


def build_variant(lang, meta, content_path, base_tpl, hreflang_block, variants):
    slug = meta.get("slug", "")
    body = read(content_path)
    body = body.replace("{{CONTACT_CTA}}", load_partial("contact-cta", lang))

    canonical = canonical_url(lang, slug)
    header_html = load_partial("header", lang).replace("{{NAV}}", build_nav(slug, lang))
    footer_html = load_partial("footer", lang)

    schema = meta.get("schema")
    schema_list = schema if isinstance(schema, list) else ([schema] if schema else [])
    if slug:  # breadcrumb on every page except home
        schema_list = list(schema_list) + [{
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": HOME_LABEL.get(lang, "Home"),
                 "item": canonical_url(lang, "")},
                {"@type": "ListItem", "position": 2, "name": meta["title"].split(" | ")[0].strip(),
                 "item": canonical},
            ],
        }]
    schema_block = "\n".join(
        '<script type="application/ld+json">\n' + json.dumps(s, indent=2, ensure_ascii=False) + "\n</script>"
        for s in schema_list
    )

    html = base_tpl
    html = html.replace("{{LANG}}", lang)
    html = html.replace("{{TITLE}}", meta["title"])
    html = html.replace("{{DESCRIPTION}}", meta["description"])
    html = html.replace("{{KEYWORDS}}", meta.get("keywords", ""))
    html = html.replace("{{CANONICAL}}", canonical)
    html = html.replace("{{HREFLANGS}}", hreflang_block)
    html = html.replace("{{OG_IMAGE}}", meta.get("og_image", DEFAULT_OG_IMAGE))
    html = html.replace("{{SCHEMA}}", schema_block)
    html = html.replace("{{ASSET_VERSION}}", ASSET_VERSION)
    html = html.replace("{{HEADER}}", header_html)
    html = html.replace("{{FOOTER}}", footer_html)
    html = html.replace("{{BODY}}", body)
    html = apply_config(html)

    out_path = output_path(lang, slug)
    write(out_path, html)
    print(f"built {os.path.relpath(out_path, ROOT)}")


def page_priority(slug):
    if slug == "":
        return "1.0"
    if slug == "tours":
        return "0.9"
    if slug == "contact":
        return "0.7"
    return "0.8"


def write_sitemap(pages):
    today = datetime.date.today().isoformat()
    entries = []
    for page_id, variants in pages.items():
        alts = [(lang, canonical_url(lang, variants[lang].get("slug", "")))
                for lang in LANGUAGES if lang in variants]
        default_lang = DEFAULT_LANG if DEFAULT_LANG in variants else next(iter(variants))
        xdefault = canonical_url(default_lang, variants[default_lang].get("slug", ""))
        for lang, meta in variants.items():
            loc = canonical_url(lang, meta.get("slug", ""))
            entries.append((loc, page_priority(meta.get("slug", "")), alts, xdefault))
    entries.sort(key=lambda e: e[0])

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, prio, alts, xdefault in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append("    <changefreq>monthly</changefreq>")
        lines.append(f"    <priority>{prio}</priority>")
        for lang, href in alts:
            lines.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{href}"/>')
        lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{xdefault}"/>')
        lines.append("  </url>")
    lines.append("</urlset>")
    write(os.path.join(ROOT, "sitemap.xml"), "\n".join(lines) + "\n")
    print(f"built sitemap.xml ({len(entries)} URLs)")


def write_robots():
    txt = ("User-agent: *\n"
           "Allow: /\n\n"
           f"Sitemap: {SITE_URL}/sitemap.xml\n")
    write(os.path.join(ROOT, "robots.txt"), txt)
    print("built robots.txt")


def main():
    base_tpl = read(os.path.join(PARTIALS_DIR, "base.html"))
    pages = discover_pages()
    for page_id, variants in pages.items():
        hreflang_block = build_hreflang_block(variants)
        for lang, meta in variants.items():
            content_path = os.path.join(PAGES_DIR, page_id, lang, "content.html")
            build_variant(lang, meta, content_path, base_tpl, hreflang_block, variants)
    write_sitemap(pages)
    write_robots()


if __name__ == "__main__":
    main()
