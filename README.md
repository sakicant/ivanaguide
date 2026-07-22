# Private Walking Tours by Ivana

Static marketing site for Ivana, a licensed local guide in Šibenik, Croatia.
Four pages — Home, Tours, About, Contact — built from partials so more
languages can be added later without touching the layout.

## How it works

- Page content lives in `src/pages/<page-id>/en/` as a `meta.json` (title,
  description, slug, schema) + `content.html` pair.
- Shared markup (header, footer, contact call-to-action) lives in
  `src/partials/`.
- `styles.css` and `script.js` at the repo root are the design system.
- `python build.py` renders every page to static `index.html` files at the
  repo root (`/`, `/tours/`, `/about/`, `/contact/`) and regenerates
  `sitemap.xml` and `robots.txt`.

Run the build after any edit to a page, partial, config value, CSS, or JS:

```bash
python build.py
```

## Placeholders to replace before launch

All site-wide details live in one place: the `CONFIG` block at the top of
`build.py`. Change a value there and rebuild — it updates everywhere.

| What | Where | Current value |
|------|-------|---------------|
| Domain | `SITE_URL` in `build.py` | `https://ivanaguide.com` *(placeholder)* |
| Booking email | `EMAIL` in `build.py` | `info@ivanaguide.com` *(placeholder)* |
| Instagram URL | `INSTAGRAM` in `build.py` | `#` *(placeholder)* |
| Facebook URL | `FACEBOOK` in `build.py` | `#` *(placeholder)* |
| Contact-form endpoint | `FORM_ENDPOINT` in `build.py` | Formspree placeholder |
| Ivana's headshot | `src/pages/about/en/content.html` | placeholder block |

Phone / WhatsApp (`+385 95 527 8924`) is real and already wired.

### Contact form

The form on the Contact page posts to `FORM_ENDPOINT`. Create a free
[Formspree](https://formspree.io) form (or similar), paste its endpoint into
`build.py`, and rebuild. Until then the form shows a friendly "use WhatsApp or
email" message instead of silently failing.

## Deploy (Vercel)

This is a plain static site. In Vercel: **Add New → Project → import the
GitHub repo**. No build command and no framework preset are needed — set the
output/root directory to the repo root. Vercel serves the pre-built
`index.html` files directly. Add the custom domain once it's registered.
