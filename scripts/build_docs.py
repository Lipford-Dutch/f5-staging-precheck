#!/usr/bin/env python3
"""Static documentation-site generator for check_multi.

Reads Markdown from ``docs/`` (plus the top-level ``README.md`` as the home
page), converts each file to a styled, responsive HTML page, and writes a
self-contained site to ``site/``. The design is theme-aware (light/dark),
includes client-side nav search, a per-page table of contents, and
copy-to-clipboard code blocks.

Usage:
    python3 scripts/build_docs.py [--out site] [--base-url /repo/]

Dependencies: ``markdown`` and ``pygments`` (see requirements-docs.txt).
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parent.parent

SITE_TITLE = "check_multi"
SITE_TAGLINE = "Enterprise Device Audit Framework"
REPO_URL = "https://github.com/willyd61/f5-staging-precheck"

# Explicit ordering + friendly labels for known pages. Anything not listed is
# appended alphabetically, so dropping a new Markdown file into docs/ "just
# works" (the CRUD story: create/update/delete a .md file, rebuild, publish).
NAV_ORDER = [
    ("index", "Home", "home"),
    ("QUICKSTART", "Quick Start", "rocket"),
    ("INSTALL", "Installation", "download"),
    ("USAGE", "Usage", "terminal"),
    ("CONFIGURATION", "Configuration", "sliders"),
    ("MODULES", "Modules & Roadmap", "grid"),
    ("ARCHITECTURE", "Architecture", "layers"),
    ("SECURITY", "Security", "shield"),
    ("TROUBLESHOOTING", "Troubleshooting", "life-buoy"),
    ("FAQ", "FAQ", "help"),
]
NAV_META = {slug: (label, icon) for slug, label, icon in NAV_ORDER}
NAV_INDEX = {slug: i for i, (slug, _, _) in enumerate(NAV_ORDER)}

MD_EXTENSIONS = [
    "extra",
    "admonition",
    "sane_lists",
    "toc",
    "tables",
    "fenced_code",
    "codehilite",
]
MD_EXTENSION_CONFIGS = {
    "codehilite": {"guess_lang": False, "css_class": "highlight"},
    "toc": {"permalink": "#"},
}


@dataclass
class Page:
    slug: str
    title: str
    description: str
    source: Path
    order: int = 999
    icon: str = "file"
    html: str = ""
    toc: str = ""
    headings: list[tuple[str, str]] = field(default_factory=list)

    @property
    def out_name(self) -> str:
        return f"{self.slug}.html"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse an optional ``--- key: value ---`` YAML-ish frontmatter block.

    Kept deliberately tiny (no PyYAML dependency): only ``key: value`` lines.
    """
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            block = text[4:end]
            for line in block.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip().lower()] = value.strip()
            text = text[end + 4 :].lstrip("\n")
    return meta, text


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def first_paragraph(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") or s.startswith("[!["):
            continue
        if not s:
            if lines:
                break
            continue
        lines.append(s)
    para = " ".join(lines)
    para = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)  # strip md links
    para = re.sub(r"[*`_]", "", para)
    return para[:200]


def rewrite_links(md_text: str, known_slugs: set[str]) -> str:
    """Rewrite intra-repo Markdown links so the built site stays navigable.

    - ``docs/X.md`` / ``X.md`` -> ``X.html`` when X is a known page.
    - ``README.md`` -> ``index.html``.
    - Bare ``docs/`` prefixes are dropped for known pages.
    Unknown targets are left untouched.
    """

    def repl(match: re.Match) -> str:
        label, target = match.group(1), match.group(2)
        # Leave absolute URLs, mailto and pure in-page anchors untouched.
        if re.match(r"^(https?:|mailto:|#)", target):
            return match.group(0)
        anchor = ""
        if "#" in target:
            target, anchor = target.split("#", 1)
            anchor = "#" + anchor
        base = target.rsplit("/", 1)[-1]
        if base in ("README.md", "README"):
            return f"[{label}](index.html{anchor})"
        stem = base[:-3] if base.endswith(".md") else base
        if stem in known_slugs:
            return f"[{label}]({stem}.html{anchor})"
        # Any other repo-relative path (CONTRIBUTING.md, CHANGELOG.md,
        # .github/workflows/ci.yml, …) is not a rendered page — link to the
        # canonical copy on GitHub so it resolves from the published site.
        clean = re.sub(r"^(?:\.{1,2}/)+", "", target)
        return f"[{label}]({REPO_URL}/blob/main/{clean}{anchor})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, md_text)


def discover_pages() -> list[Page]:
    pages: list[Page] = []
    sources: list[tuple[str, Path]] = []

    readme = REPO_ROOT / "README.md"
    if readme.exists():
        sources.append(("index", readme))

    docs_dir = REPO_ROOT / "docs"
    for path in sorted(docs_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        sources.append((path.stem, path))

    for slug, path in sources:
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        label, icon = NAV_META.get(slug, (None, "file"))
        title = meta.get("title") or label or first_heading(body) or slug
        description = meta.get("description") or first_paragraph(body)
        order = int(meta.get("order", NAV_INDEX.get(slug, 999)))
        pages.append(
            Page(
                slug=slug,
                title=title,
                description=description,
                source=path,
                order=order,
                icon=meta.get("icon", icon),
            )
        )

    pages.sort(key=lambda p: (p.order, p.title.lower()))
    return pages


def render_markdown(pages: list[Page]) -> None:
    known = {p.slug for p in pages}
    for page in pages:
        raw = page.source.read_text(encoding="utf-8")
        _, body = parse_frontmatter(raw)
        body = rewrite_links(body, known)
        md = markdown.Markdown(
            extensions=MD_EXTENSIONS, extension_configs=MD_EXTENSION_CONFIGS
        )
        page.html = md.convert(body)
        page.toc = getattr(md, "toc", "")
        page.headings = [
            (item["id"], item["name"]) for item in getattr(md, "toc_tokens", [])
        ]


def icon_svg(name: str) -> str:
    """Return an inline stroke SVG for a small set of Feather-style icons."""
    paths = {
        "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
        "rocket": '<path d="M5 13c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 8-10 22 22 0 0 1 2 8 22 22 0 0 1-7 5z"/>',
        "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
        "terminal": '<path d="M4 17l6-6-6-6"/><path d="M12 19h8"/>',
        "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><circle cx="4" cy="12" r="2"/><circle cx="12" cy="10" r="2"/><circle cx="20" cy="14" r="2"/>',
        "grid": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
        "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
        "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        "life-buoy": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="4.93" y1="4.93" x2="9.17" y2="9.17"/><line x1="14.83" y1="14.83" x2="19.07" y2="19.07"/><line x1="14.83" y1="9.17" x2="19.07" y2="4.93"/><line x1="9.17" y1="14.83" x2="4.93" y2="19.07"/>',
        "help": '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
        "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    }
    body = paths.get(name, paths["file"])
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'width="16" height="16" aria-hidden="true">{body}</svg>'
    )


def build_nav(pages: list[Page], current: Page) -> str:
    items = []
    for page in pages:
        active = " active" if page.slug == current.slug else ""
        items.append(
            f'<a class="nav-link{active}" href="{page.out_name}" '
            f'data-title="{html.escape(page.title.lower())}">'
            f'<span class="nav-ic">{icon_svg(page.icon)}</span>'
            f"<span>{html.escape(page.title)}</span></a>"
        )
    return "\n".join(items)


def build_toc(page: Page) -> str:
    if not page.headings:
        return ""
    links = "".join(
        f'<a href="#{hid}">{html.escape(name)}</a>' for hid, name in page.headings
    )
    return f'<nav class="toc"><p class="toc-title">On this page</p>{links}</nav>'


def render_page(page: Page, pages: list[Page]) -> str:
    nav = build_nav(pages, page)
    toc = build_toc(page)
    year = datetime.now(timezone.utc).year
    return PAGE_TEMPLATE.format(
        title=html.escape(page.title),
        site_title=SITE_TITLE,
        tagline=html.escape(SITE_TAGLINE),
        description=html.escape(page.description),
        nav=nav,
        toc=toc,
        content=page.html,
        repo_url=REPO_URL,
        year=year,
        toc_class="has-toc" if toc else "no-toc",
    )


def write_site(pages: list[Page], out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    assets = out_dir / "assets"
    assets.mkdir(parents=True)
    (assets / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (assets / "app.js").write_text(APP_JS, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    for page in pages:
        (out_dir / page.out_name).write_text(render_page(page, pages), encoding="utf-8")
    print(f"Built {len(pages)} page(s) → {out_dir}")


# --------------------------------------------------------------------------- #
# Templates & assets (kept inline so the generator is a single dependency-light
# file). Braces used by CSS/JS are escaped as {{ }} because PAGE_TEMPLATE is a
# str.format template; the CSS/JS strings themselves are inserted verbatim.
# --------------------------------------------------------------------------- #

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site_title}</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>">
</head>
<body class="{toc_class}">
<a class="skip-link" href="#main">Skip to content</a>
<header class="topbar">
  <button class="menu-toggle" aria-label="Toggle navigation" onclick="toggleNav()">☰</button>
  <a class="brand" href="index.html">
    <span class="brand-mark">🛡️</span>
    <span class="brand-text"><b>{site_title}</b><small>{tagline}</small></span>
  </a>
  <div class="topbar-actions">
    <a class="ghlink" href="{repo_url}" title="GitHub repository" aria-label="GitHub">GitHub ↗</a>
    <button class="theme-toggle" aria-label="Toggle colour theme" onclick="toggleTheme()"><span class="theme-ic"></span></button>
  </div>
</header>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="search"><input type="search" id="navSearch" placeholder="Search pages…" oninput="filterNav(this.value)" aria-label="Search pages"></div>
    <nav class="nav">{nav}</nav>
  </aside>
  <main class="content" id="main">
    <article class="prose">{content}</article>
    <footer class="page-footer">
      <span>© {year} {site_title} · {tagline}</span>
      <a href="{repo_url}">Source on GitHub ↗</a>
    </footer>
  </main>
  {toc}
</div>
<script src="assets/app.js"></script>
</body>
</html>
"""

STYLE_CSS = r"""
:root{
  --bg:#ffffff; --bg-alt:#f6f8fb; --surface:#ffffff; --text:#1b2430;
  --muted:#5b6572; --border:#e3e8ef; --accent:#e4002b; --accent-2:#c8102e;
  --code-bg:#f4f6f9; --shadow:0 1px 3px rgba(16,24,40,.08),0 1px 2px rgba(16,24,40,.06);
  --radius:12px; --nav-w:264px; --toc-w:220px; --maxw:820px;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Helvetica,Arial,sans-serif;
}
:root[data-theme="dark"]{
  --bg:#0e1420; --bg-alt:#131b29; --surface:#151d2b; --text:#e6ebf2;
  --muted:#9aa6b6; --border:#233045; --accent:#ff2d55; --accent-2:#ff5470;
  --code-bg:#0b111c; --shadow:0 1px 3px rgba(0,0,0,.4);
}
@media (prefers-color-scheme:dark){
  :root[data-theme="auto"]{
    --bg:#0e1420; --bg-alt:#131b29; --surface:#151d2b; --text:#e6ebf2;
    --muted:#9aa6b6; --border:#233045; --accent:#ff2d55; --accent-2:#ff5470;
    --code-bg:#0b111c; --shadow:0 1px 3px rgba(0,0,0,.4);
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
  line-height:1.65;-webkit-font-smoothing:antialiased;font-size:16px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.skip-link{position:absolute;left:-999px;top:0;background:var(--accent);color:#fff;padding:8px 14px;z-index:100}
.skip-link:focus{left:8px}

.topbar{position:sticky;top:0;z-index:40;display:flex;align-items:center;gap:14px;
  height:60px;padding:0 18px;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:saturate(180%) blur(10px);border-bottom:1px solid var(--border)}
.brand{display:flex;align-items:center;gap:10px;color:var(--text)}
.brand:hover{text-decoration:none}
.brand-mark{font-size:22px}
.brand-text{display:flex;flex-direction:column;line-height:1.1}
.brand-text small{color:var(--muted);font-size:11px;font-weight:500}
.topbar-actions{margin-left:auto;display:flex;align-items:center;gap:10px}
.ghlink{color:var(--muted);font-size:14px;font-weight:600}
.theme-toggle,.menu-toggle{background:var(--surface);border:1px solid var(--border);
  color:var(--text);border-radius:9px;height:36px;min-width:36px;cursor:pointer;font-size:16px}
.menu-toggle{display:none}
.theme-ic::before{content:"◐"}

.layout{display:grid;grid-template-columns:var(--nav-w) minmax(0,1fr) var(--toc-w);
  max-width:1400px;margin:0 auto;align-items:start}
body.no-toc .layout{grid-template-columns:var(--nav-w) minmax(0,1fr)}

.sidebar{position:sticky;top:60px;height:calc(100vh - 60px);overflow-y:auto;
  padding:18px 12px;border-right:1px solid var(--border)}
.search input{width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:9px;
  background:var(--bg-alt);color:var(--text);font-size:14px;margin-bottom:12px}
.nav{display:flex;flex-direction:column;gap:2px}
.nav-link{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:9px;
  color:var(--muted);font-weight:500;font-size:14.5px}
.nav-link:hover{background:var(--bg-alt);color:var(--text);text-decoration:none}
.nav-link.active{background:color-mix(in srgb,var(--accent) 12%,transparent);
  color:var(--accent);font-weight:600}
.nav-ic{display:inline-flex;opacity:.85}

.content{min-width:0;padding:34px clamp(20px,4vw,56px) 60px}
.prose{max-width:var(--maxw)}
.toc{position:sticky;top:60px;height:calc(100vh - 60px);overflow-y:auto;padding:28px 18px;
  font-size:13.5px;display:flex;flex-direction:column;gap:6px}
.toc-title{text-transform:uppercase;letter-spacing:.06em;font-size:11px;color:var(--muted);
  font-weight:700;margin:0 0 4px}
.toc a{color:var(--muted);display:block;padding:2px 0;border-left:2px solid transparent;padding-left:10px}
.toc a:hover,.toc a.active{color:var(--accent);border-color:var(--accent);text-decoration:none}

.prose h1{font-size:2.1rem;line-height:1.2;margin:.2em 0 .5em;letter-spacing:-.02em}
.prose h2{font-size:1.5rem;margin:1.8em 0 .6em;padding-top:.3em;border-top:1px solid var(--border)}
.prose h3{font-size:1.2rem;margin:1.4em 0 .4em}
.prose h1 .headerlink,.prose h2 .headerlink,.prose h3 .headerlink{opacity:0;margin-left:8px;
  font-weight:400;color:var(--muted)}
.prose h1:hover .headerlink,.prose h2:hover .headerlink,.prose h3:hover .headerlink{opacity:1}
.prose p{margin:0 0 1em}
.prose ul,.prose ol{padding-left:1.3em}
.prose li{margin:.25em 0}
.prose code{font-family:var(--mono);font-size:.88em;background:var(--code-bg);
  padding:.15em .4em;border-radius:6px;border:1px solid var(--border)}
.prose pre{position:relative;background:var(--code-bg);border:1px solid var(--border);
  border-radius:var(--radius);padding:16px 18px;overflow:auto;margin:0 0 1.2em;box-shadow:var(--shadow)}
.prose pre code{background:none;border:none;padding:0;font-size:.86em;line-height:1.6}
.copy-btn{position:absolute;top:8px;right:8px;font-size:12px;padding:4px 9px;border-radius:7px;
  border:1px solid var(--border);background:var(--surface);color:var(--muted);cursor:pointer;opacity:0;transition:.15s}
.prose pre:hover .copy-btn{opacity:1}
.copy-btn.ok{color:#12a150;border-color:#12a150}

.prose table{width:100%;border-collapse:collapse;margin:0 0 1.4em;font-size:14.5px;
  border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.prose th,.prose td{padding:9px 13px;border-bottom:1px solid var(--border);text-align:left}
.prose thead th{background:var(--bg-alt);font-weight:650}
.prose tbody tr:hover{background:var(--bg-alt)}
.prose blockquote{margin:0 0 1.2em;padding:.6em 1.1em;border-left:3px solid var(--accent);
  background:var(--bg-alt);border-radius:0 8px 8px 0;color:var(--muted)}
.prose img{max-width:100%}
.prose hr{border:none;border-top:1px solid var(--border);margin:2em 0}

.admonition{border:1px solid var(--border);border-left:4px solid var(--accent);
  background:var(--bg-alt);border-radius:8px;padding:.4em 1em;margin:0 0 1.2em}
.admonition-title{font-weight:700;margin:.4em 0}

.page-footer{max-width:var(--maxw);margin-top:48px;padding-top:20px;border-top:1px solid var(--border);
  display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:13.5px}

/* Landing hero when the home page leads with an h1 + badges */
.prose h1 img{vertical-align:middle}

@media (max-width:1080px){
  .layout{grid-template-columns:var(--nav-w) minmax(0,1fr)}
  .toc{display:none}
}
@media (max-width:760px){
  .layout{grid-template-columns:1fr}
  .menu-toggle{display:inline-block}
  .sidebar{position:fixed;left:0;top:60px;bottom:0;width:min(80vw,300px);background:var(--bg);
    transform:translateX(-105%);transition:transform .2s ease;z-index:45;box-shadow:var(--shadow)}
  .sidebar.open{transform:none}
  .brand-text small{display:none}
}
"""

APP_JS = r"""
(function(){
  var t = localStorage.getItem('cm-theme');
  if(t){document.documentElement.setAttribute('data-theme', t);}
})();
function toggleTheme(){
  var el=document.documentElement, cur=el.getAttribute('data-theme');
  var order=['auto','light','dark'];
  var next=order[(order.indexOf(cur)+1)%order.length];
  el.setAttribute('data-theme', next);
  localStorage.setItem('cm-theme', next);
}
function toggleNav(){document.getElementById('sidebar').classList.toggle('open');}
function filterNav(q){
  q=(q||'').toLowerCase();
  document.querySelectorAll('.nav-link').forEach(function(a){
    var hit=a.getAttribute('data-title').indexOf(q)>-1;
    a.style.display=hit?'':'none';
  });
}
document.addEventListener('DOMContentLoaded', function(){
  // Copy buttons on code blocks
  document.querySelectorAll('.prose pre').forEach(function(pre){
    var btn=document.createElement('button');
    btn.className='copy-btn'; btn.type='button'; btn.textContent='Copy';
    btn.addEventListener('click', function(){
      var code=pre.querySelector('code'); var text=code?code.innerText:pre.innerText;
      navigator.clipboard.writeText(text).then(function(){
        btn.textContent='Copied'; btn.classList.add('ok');
        setTimeout(function(){btn.textContent='Copy';btn.classList.remove('ok');},1500);
      });
    });
    pre.appendChild(btn);
  });
  // Scroll-spy for the table of contents
  var links=[].slice.call(document.querySelectorAll('.toc a'));
  if(links.length){
    var map={};
    links.forEach(function(l){var id=l.getAttribute('href').slice(1);map[id]=l;});
    var obs=new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if(e.isIntersecting){
          links.forEach(function(l){l.classList.remove('active');});
          if(map[e.target.id])map[e.target.id].classList.add('active');
        }
      });
    },{rootMargin:'-64px 0px -75% 0px'});
    Object.keys(map).forEach(function(id){var el=document.getElementById(id);if(el)obs.observe(el);});
  }
});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the check_multi docs site")
    parser.add_argument("--out", default="site", help="output directory (default: site)")
    args = parser.parse_args()

    out_dir = (REPO_ROOT / args.out).resolve()
    pages = discover_pages()
    if not pages:
        print("No Markdown pages found.")
        return 1
    render_markdown(pages)
    write_site(pages, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
