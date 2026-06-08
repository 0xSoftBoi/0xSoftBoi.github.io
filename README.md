# 0xSoftBoi.github.io

Personal site — CV + blog. Jekyll, served by GitHub Pages at
**https://0xsoftboi.github.io**.

## Local preview
```bash
bundle install
bundle exec jekyll serve   # http://localhost:4000
```

## Structure
- `index.html` — CV landing page  *(fill in the `// TODO` experience + education entries)*
- `blog.html` — blog index (`/blog/`)
- `_posts/` — blog posts (`YYYY-MM-DD-title.md`)
- `_layouts/` — `default` + `post`
- `assets/css/style.css` — dark / terminal-green theme
- `_config.yml` — site config

## Deploy
Push to the `main` branch of `0xSoftBoi/0xSoftBoi.github.io`, then in repo
**Settings → Pages**, set Source = "Deploy from a branch", Branch = `main` / `root`.
Live in ~1 minute at https://0xsoftboi.github.io.
