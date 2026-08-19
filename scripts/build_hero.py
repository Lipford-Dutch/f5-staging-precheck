#!/usr/bin/env python3
"""Build the hero landing page that sits at the root of the published site.

The published site has two parts, both produced by one GitHub Pages deployment
(a repository gets exactly one Pages site, so they cannot be separate deploys):

    /            this hero landing page      <- build_hero.py
    /docs/       the technical + admin guide <- build_docs.py --out site/docs

Usage:
    python3 scripts/build_hero.py [--out site]

Deliberately stdlib-only and self-contained (inline CSS, no external assets
beyond an optional logo copy), so the hero adds no build dependency and cannot
break from an asset-path change in the docs generator.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Optional brand mark; the page renders correctly without it.
LOGO_SRC = REPO_ROOT / "demo-assets" / "branding" / "bofa-logo.png"

# Cards linking into the generated guide. Each entry is (title, blurb, href).
GUIDE_LINKS: tuple[tuple[str, str, str], ...] = (
    ("Quick start", "Install, point it at a device, read a verdict.", "docs/QUICKSTART.html"),
    ("Installation", "Requirements and setup for both tools.", "docs/INSTALL.html"),
    ("Usage", "Full CLI reference and safety behaviours.", "docs/USAGE.html"),
    ("Configuration", "Inventories, profiles, thresholds, environments.", "docs/CONFIGURATION.html"),
    ("Check catalogue", "Every check, what it asserts, and why.", "docs/MODULES.html"),
    ("Architecture", "How the validator is put together.", "docs/ARCHITECTURE.html"),
    ("Security model", "Credential handling, redaction, audit trail.", "docs/SECURITY.html"),
    ("Troubleshooting", "Common failures and how to resolve them.", "docs/TROUBLESHOOTING.html"),
)

FEATURES: tuple[tuple[str, str], ...] = (
    (
        "GO / NO-GO, not a wall of output",
        "Every run ends in one auditable verdict per device and one for the change "
        "window, so the decision to proceed is explicit rather than inferred.",
    ),
    (
        "Read-only by design",
        "Nothing mutates a device. The tooling issues reads only, which makes it "
        "safe to run during a live change window.",
    ),
    (
        "Never a silent pass",
        "A check that cannot positively confirm health degrades to WARN or FAIL. "
        "Missing a real problem is treated as worse than raising a false one.",
    ),
    (
        "Auditable by default",
        "Per-run session log, redacted evidence for every check, and a hashed "
        "machine-readable report you can attach to the change record.",
    ),
    (
        "HA aware",
        "Within an HA pair the standby is evaluated before the active member, and "
        "config-sync state is checked before anything is called ready.",
    ),
    (
        "Proven against real hardware",
        "Validated end to end against a live BIG-IP VE running TMOS 17.5.1.8, not "
        "only against fixtures.",
    ),
)


def read_python_version() -> str:
    """Read ``__version__`` from the bigip-precheck package without importing it."""
    init = REPO_ROOT / "src" / "bigip_precheck" / "__init__.py"
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else ""


def read_bash_version() -> str:
    """Read the check_multi version string from the CLI entry point."""
    script = REPO_ROOT / "bin" / "check_multi"
    if not script.is_file():
        return ""
    match = re.search(r'VERSION=["\']?([0-9][^"\'\s]*)', script.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def render(py_version: str, sh_version: str, has_logo: bool) -> str:
    cards = "\n".join(
        f'      <a class="card" href="{html.escape(href)}">'
        f"<h3>{html.escape(title)}</h3><p>{html.escape(blurb)}</p>"
        f'<span class="card-go">Read<span aria-hidden="true"> &rarr;</span></span></a>'
        for title, blurb, href in GUIDE_LINKS
    )
    features = "\n".join(
        f'      <div class="feature"><h3>{html.escape(title)}</h3>'
        f"<p>{html.escape(body)}</p></div>"
        for title, body in FEATURES
    )
    logo = (
        '<img class="brand-mark" src="assets/bofa-logo.png" alt="" width="150">\n      '
        if has_logo
        else ""
    )
    py_badge = (
        f'<span class="pill">bigip-precheck {html.escape(py_version)}</span>' if py_version else ""
    )
    sh_badge = (
        f'<span class="pill">check_multi {html.escape(sh_version)}</span>' if sh_version else ""
    )

    return f"""<!doctype html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>f5-staging-precheck &mdash; F5 BIG-IP upgrade readiness</title>
<meta name="description" content="Read-only pre-upgrade and change-window readiness validation for F5 BIG-IP, producing an auditable GO/NO-GO verdict.">
<style>
:root{{
  --bg:#ffffff; --bg-alt:#f6f8fb; --surface:#ffffff; --text:#1b2430;
  --muted:#5b6572; --border:#e3e8ef; --accent:#e4002b; --accent-2:#c8102e;
  --radius:12px; --maxw:1060px;
  --shadow:0 1px 3px rgba(16,24,40,.08),0 1px 2px rgba(16,24,40,.06);
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Helvetica,Arial,sans-serif;
}}
@media (prefers-color-scheme:dark){{
  :root{{
    --bg:#0e1420; --bg-alt:#131b29; --surface:#151d2b; --text:#e6ebf2;
    --muted:#9aa6b6; --border:#233045; --accent:#ff2d55; --accent-2:#ff5470;
    --shadow:0 1px 3px rgba(0,0,0,.4);
  }}
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
  line-height:1.6;-webkit-font-smoothing:antialiased}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}
.wrap{{max-width:var(--maxw);margin:0 auto;padding:0 22px}}
.hero{{padding:76px 0 60px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,var(--bg-alt),var(--bg))}}
.brand-mark{{display:block;margin-bottom:26px;height:auto}}
h1{{font-size:clamp(2.1rem,4.6vw,3.2rem);line-height:1.12;margin:0 0 16px;letter-spacing:-.02em}}
.tagline{{font-size:clamp(1.05rem,2vw,1.3rem);color:var(--muted);margin:0 0 26px;max-width:62ch}}
.pills{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:30px}}
.pill{{font-family:var(--mono);font-size:.78rem;padding:5px 11px;border-radius:999px;
  background:var(--surface);border:1px solid var(--border);color:var(--muted)}}
.cta{{display:flex;flex-wrap:wrap;gap:12px}}
.btn{{display:inline-block;padding:12px 22px;border-radius:var(--radius);font-weight:600;
  border:1px solid transparent;transition:transform .06s ease}}
.btn:active{{transform:translateY(1px)}}
.btn-primary{{background:var(--accent);color:#fff}}
.btn-primary:hover{{background:var(--accent-2);text-decoration:none}}
.btn-ghost{{border-color:var(--border);color:var(--text);background:var(--surface)}}
.btn-ghost:hover{{border-color:var(--accent);text-decoration:none}}
section{{padding:58px 0}}
h2{{font-size:1.6rem;margin:0 0 8px;letter-spacing:-.01em}}
.section-sub{{color:var(--muted);margin:0 0 30px;max-width:64ch}}
.grid{{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(268px,1fr))}}
.feature h3,.card h3{{font-size:1.03rem;margin:0 0 7px}}
.feature p,.card p{{margin:0;color:var(--muted);font-size:.94rem}}
.feature{{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow)}}
.card{{display:block;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow);
  color:inherit;transition:border-color .12s ease,transform .12s ease}}
.card:hover{{border-color:var(--accent);transform:translateY(-2px);text-decoration:none}}
.card-go{{display:inline-block;margin-top:11px;color:var(--accent);font-weight:600;font-size:.88rem}}
.tools{{background:var(--bg-alt);border-top:1px solid var(--border);
  border-bottom:1px solid var(--border)}}
pre{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:16px 18px;overflow-x:auto;font-family:var(--mono);font-size:.86rem;line-height:1.55}}
code{{font-family:var(--mono)}}
.verdict{{font-family:var(--mono);font-size:.86rem}}
.go{{color:#1a7f45;font-weight:700}}
.nogo{{color:var(--accent);font-weight:700}}
@media (prefers-color-scheme:dark){{ .go{{color:#41d18b}} }}
footer{{padding:34px 0;color:var(--muted);font-size:.88rem;border-top:1px solid var(--border)}}
</style>
</head>
<body>

<header class="hero">
  <div class="wrap">
    {logo}<h1>Know it&rsquo;s safe to upgrade &mdash; before the window opens.</h1>
    <p class="tagline">Read-only pre-upgrade and change-window readiness validation for
      F5&nbsp;BIG-IP. Every run ends in one auditable <strong>GO&nbsp;/&nbsp;NO-GO</strong>
      verdict, with the evidence behind it.</p>
    <div class="pills">{py_badge}{sh_badge}<span class="pill">read-only</span><span class="pill">LTM &amp; GTM</span></div>
    <div class="cta">
      <a class="btn btn-primary" href="docs/QUICKSTART.html">Get started</a>
      <a class="btn btn-ghost" href="docs/">Documentation</a>
    </div>
  </div>
</header>

<section>
  <div class="wrap">
    <h2>Why it exists</h2>
    <p class="section-sub">An upgrade that fails at 2am usually failed a check nobody ran.
      This turns that pre-flight into something repeatable, evidenced, and reviewable.</p>
    <div class="grid">
{features}
    </div>
  </div>
</section>

<section class="tools">
  <div class="wrap">
    <h2>Two tools, one job</h2>
    <p class="section-sub">Use whichever fits the task &mdash; they share an inventory
      mindset and both stay read-only.</p>
    <div class="grid">
      <div class="feature">
        <h3>bigip-precheck <span class="pill">Python</span></h3>
        <p>Deep validation over iControl REST: system, HA, LTM and GTM object state,
          role auto-detection, and pre/post snapshots that prove nothing regressed.</p>
      </div>
      <div class="feature">
        <h3>check_multi <span class="pill">Bash</span></h3>
        <p>Fast parallel SSH/tmsh sweeps across a large inventory, with plugin-style
          check modules and executive reporting.</p>
      </div>
    </div>
    <p style="margin-top:26px" class="section-sub">A run reduces to a verdict you can act on:</p>
<pre class="verdict">$ bigip-precheck run inventory.yaml --profile full

system.license        <span class="nogo">FAIL</span>  service-check date has passed; a new install may be blocked
system.boot-volumes   WARN  only one boot volume present; no free install target
ha.sync-status        INFO  device is standalone (no config-sync peer)

UPGRADE READINESS: <span class="nogo">NO-GO</span></pre>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Documentation</h2>
    <p class="section-sub">The technical user and administrator guide.</p>
    <div class="grid">
{cards}
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    f5-staging-precheck &mdash; internal use. Read-only tooling; it never modifies a device.
  </div>
</footer>

</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the hero landing page")
    parser.add_argument("--out", default="site", help="site root directory (default: site)")
    args = parser.parse_args()

    out_dir = (REPO_ROOT / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    has_logo = LOGO_SRC.is_file()
    if has_logo:
        assets = out_dir / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LOGO_SRC, assets / "bofa-logo.png")

    # Pages otherwise runs the artifact through Jekyll, which can drop paths that
    # begin with an underscore. The docs generator writes its own copy alongside
    # its output; this is the one for the site root.
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    page = render(read_python_version(), read_bash_version(), has_logo)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    print(f"Built hero landing page → {out_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
