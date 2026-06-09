# 0xSoftBoi.github.io

Personal site — landing page + blog. Jekyll, served by GitHub Pages at
**https://0xsoftboi.github.io**.

## Local preview
```bash
bundle install
bundle exec jekyll serve   # http://localhost:4000
```

## Structure
- `index.html` — landing page: intro, writing index, selected work
- `about.html` — about / bio (`/about/`)
- `tags.html` — posts grouped by tag (`/tags/`)
- `_posts/` — blog posts (`YYYY-MM-DD-title.md`), permalink `/blog/:title/`
- `_layouts/` — `default` + `post`
- `assets/` — CSS, OG images, fonts
- `_config.yml` — site config

## Deploy
Push to `main` on `0xSoftBoi/0xSoftBoi.github.io`. Pages is configured under
**Settings → Pages** (Source = "Deploy from a branch", Branch = `main` / root).
Live in ~1 minute at https://0xsoftboi.github.io.
