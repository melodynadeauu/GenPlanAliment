"""Design tokens and the global stylesheet for the app.

Aesthetic: a nutrition dossier -- warm paper, forest ink, serif numerals for the
figures that matter and a mono face reserved for measured data (kcal, grams,
FDC ids). Every colour, space, size and radius used by ui/components lives here,
emitted once as CSS custom properties so components never invent a value.

Two scales, and nothing off them:
    space  --s-1 .. --s-8   4px base, doubling loosely
    type   --t-micro .. --t-2xl   fixed px, ~1.15 ratio (product UI, not fluid)
"""

COLORS = {
    "paper": "#f4f1ea",
    "paper_2": "#efeae0",
    "surface": "#ffffff",
    "surface_2": "#e7e1d4",
    "ink": "#14201b",
    "ink_2": "#46564f",
    "ink_3": "#5f6f68",
    "line": "#dbd3c3",
    "line_soft": "#e9e3d7",
    "accent": "#0e7a63",
    "accent_deep": "#0a4034",
    "accent_soft": "#e2efea",
    "on_deep": "#ffffff",
    "on_deep_2": "#a9c9c0",
    "on_deep_3": "#6fd3b6",
    "ochre": "#8a5a0c",
    "ochre_soft": "#f6eedd",
    "danger": "#8f3427",
    "danger_soft": "#f7e7e2",
}

FONT_SANS = "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace"
FONT_SERIF = "'Newsreader', Georgia, serif"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&display=swap"
)

# Fixed height for a day card. Two reasons it is pinned rather than intrinsic:
# Streamlit sizes its own element containers from a stale measurement (so an
# intrinsic card renders its last line outside its own border), and the seven
# cards have to share a height for the row to read as a row. Sized for the worst
# case -- a two-line activity name over a two-line duration/intensity meta, which
# is what the narrowest supported window produces. Extra px keeps descenders
# (e.g. "high") from clipping against the kcal line below.
DAY_CARD_HEIGHT = "152px"
DAY_CARD_HEIGHT_COLLAPSED = "52px"


def pref_tag_css(tab: str) -> str:
    """Streamlit multiselect tag colours scoped to the active preferences tab."""
    if tab == "dislikes":
        bg, border, color = COLORS["danger_soft"], COLORS["danger"], COLORS["danger"]
    else:
        bg, border, color = COLORS["accent_soft"], COLORS["accent"], COLORS["accent_deep"]
    return f"""
    section[data-testid="stSidebar"] [data-baseweb="tag"] {{
        background-color: {bg} !important;
        border: 1px solid {border} !important;
        border-radius: 999px !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="tag"] span {{
        color: {color} !important;
        font-size: var(--t-xs) !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="tag"] svg {{ fill: {color} !important; }}
    """


def build_global_css() -> str:
    """Return the <style> block injected once by ui/layout.py."""
    c = COLORS
    return f"""
    @import url('{GOOGLE_FONTS_URL}');

    :root {{
        --s-1: 4px;  --s-2: 8px;  --s-3: 12px; --s-4: 16px;
        --s-5: 20px; --s-6: 24px; --s-7: 32px; --s-8: 40px;

        --t-micro: 12px; --t-xs: 13px; --t-sm: 14px; --t-base: 15px;
        --t-md: 17px;    --t-lg: 21px; --t-xl: 27px; --t-2xl: 30px;

        --r-sm: 6px; --r-md: 12px; --r-pill: 999px;

        --paper: {c['paper']};   --surface: {c['surface']};
        --ink: {c['ink']};       --ink-2: {c['ink_2']};  --ink-3: {c['ink_3']};
        --line: {c['line']};     --line-soft: {c['line_soft']};
        --accent: {c['accent']}; --accent-deep: {c['accent_deep']};
    }}

    html, body, .stApp, [data-testid="stAppViewContainer"], section[data-testid="stSidebar"],
    button, input, select, textarea, p, div, span, label, li, h1, h2, h3, h4, h5, h6 {{
        font-family: {FONT_SANS};
    }}

    body, .stApp {{ background-color: var(--paper); color: var(--ink); }}

    /* No horizontal scroll: clip anything that spills past the viewport. */
    html, body {{
        overflow-x: hidden;
        max-width: 100%;
    }}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stSidebarContent"], section[data-testid="stSidebar"] {{
        overflow-x: hidden;
        max-width: 100%;
    }}
    [data-testid="stHorizontalBlock"] {{
        max-width: 100%;
        min-width: 0;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
        min-width: 0 !important;
    }}

    /* ---------- browser surfaces: the parts Streamlit leaves at default ---- */
    ::selection {{ background: {c['accent_soft']}; color: {c['accent_deep']}; }}
    input, textarea {{ caret-color: var(--accent); }}
    * {{ scrollbar-width: thin; scrollbar-color: {c['line']} transparent; }}
    *::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    *::-webkit-scrollbar-thumb {{
        background: {c['line']}; border-radius: var(--r-pill);
        border: 3px solid transparent; background-clip: content-box;
    }}
    *::-webkit-scrollbar-thumb:hover {{ background: {c['ink_3']}; background-clip: content-box; }}
    *::-webkit-scrollbar-track {{ background: transparent; }}
    :focus-visible {{
        outline: 2px solid var(--accent) !important;
        outline-offset: 2px !important; border-radius: var(--r-sm);
    }}
    .am-i {{ flex: 0 0 auto; vertical-align: -.18em; }}
    /* Reaches screen readers, never the page. */
    .am-sr {{
        position: absolute; width: 1px; height: 1px; margin: -1px;
        padding: 0; overflow: hidden; white-space: nowrap;
        clip-path: inset(50%); border: 0;
    }}

    /* Streamlit's own `[data-testid] p` rule outranks a single class, so any
       paragraph of ours has to match it on specificity to keep its size. */
    [data-testid="stMarkdownContainer"] p.am-tag {{ font-size: var(--t-xs); }}
    [data-testid="stMarkdownContainer"] p.am-hint {{ font-size: var(--t-sm); }}
    [data-testid="stMarkdownContainer"] p.am-empty-p {{ font-size: var(--t-sm); }}

    /* Every figure on this page is measured, so every figure gets even columns. */
    .am-num, .am-step-val, .am-sum-big, .am-food-g, .am-food-kcal,
    .am-meal-kcal, .am-day-burn, .am-sum-foot b {{ font-variant-numeric: tabular-nums; }}

    /* ---------- shell ----------------------------------------------------- */
    .block-container, .stMainBlockContainer {{
        padding: 0 var(--s-6) var(--s-6);
        max-width: min(1440px, 100%);
        width: 100%;
        box-sizing: border-box;
    }}
    /* Tight inside a section; the section headings carry the space *between*
       sections through their own top margin, so grouping is unambiguous. */
    [data-testid="stVerticalBlock"] {{ gap: var(--s-3); }}
    [data-testid="stMain"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {{ margin: 0; }}
    /* The injected <link>/<style> blocks are zero-height, but each still takes a
       slot on the flex column and so pays a full gap -- 24px of dead paper above
       the masthead, and the same again in the sidebar. */
    [data-testid="stElementContainer"]:has(style),
    [data-testid="stElementContainer"]:has(link) {{ display: none !important; }}

    /* The header is flattened for density, so it must not swallow clicks meant
       for the page beneath it -- only its own controls stay interactive. */
    header[data-testid="stHeader"] {{
        background: transparent !important; box-shadow: none !important;
        height: 0; pointer-events: none;
    }}
    header[data-testid="stHeader"] * {{ pointer-events: auto; }}
    /* Not the whole toolbar: it is the only thing that holds the sidebar's
       expand button. Hide Streamlit's own chrome piece by piece instead. */
    /* stStatusWidget stays: it is the only sign that the app is running a
       script or has lost its connection. Hidden, a disconnected tab looks
       perfectly normal and every button silently does nothing. */
    [data-testid="stDecoration"],
    [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
    #MainMenu, footer {{ display: none !important; }}
    [data-testid="stToolbar"] {{ background: transparent !important; }}

    /* Both sidebar controls, always reachable. Streamlit hides the collapse
       button until hover and puts the expand button inside that flattened
       header, which leaves a collapsed sidebar with no way back. */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"] {{
        display: block !important; visibility: visible !important; opacity: 1 !important;
    }}
    [data-testid="stSidebarCollapseButton"] button {{ color: {c['ink_2']} !important; }}
    /* Streamlit only mounts this button while the sidebar is collapsed, and it
       mounts it inside the flattened header -- where it computes to 0x0 and the
       sidebar can never be reopened. Take it out of that header's layout and
       give it its own size. */
    [data-testid="stExpandSidebarButton"] {{
        position: fixed !important; top: var(--s-3); left: var(--s-3); z-index: 1000000;
        display: flex !important; align-items: center !important; justify-content: center !important;
        visibility: visible !important; opacity: 1 !important;
        width: 36px !important; height: 36px !important; min-width: 36px !important;
        padding: 0 !important;
        background: var(--surface) !important; color: var(--ink) !important;
        border: 1px solid var(--line) !important; border-radius: var(--r-sm) !important;
    }}
    [data-testid="stExpandSidebarButton"] > * {{
        display: flex !important; align-items: center; justify-content: center;
        color: var(--ink) !important;
    }}
    [data-testid="stExpandSidebarButton"]:hover {{
        border-color: var(--accent) !important; background: {c['accent_soft']} !important;
    }}

    /* Deliberately no width override. Streamlit drives the sidebar's width,
       min-width and max-width from inline styles to run its collapse; an author
       `width: !important` loses to those and strands the panel at 1px with no
       way to reopen it. Colour it, leave its geometry alone. */
    section[data-testid="stSidebar"] {{
        background: {c['paper_2']};
        border-right: 1px solid var(--line);
    }}
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: var(--s-3); }}
    /* stSidebarContent is the sidebar's scroller; its header is a sibling of the
       user content inside it, so `sticky` there pins the title bar and lets the
       fields below scroll under it -- the same deal the masthead makes on the
       main column. */
    [data-testid="stSidebarContent"] {{
        padding-left: 0 !important; gap: 0 !important;
    }}
    [data-testid="stSidebarHeader"] {{
        position: sticky; top: 0; z-index: 20;
        display: flex; align-items: center; justify-content: space-between;
        gap: var(--s-2);
        padding: var(--s-3) var(--s-3) var(--s-3) var(--s-4) !important;
        height: auto !important; min-height: 0 !important;
        background: {c['paper_2']};
        border-bottom: 1px solid var(--line);
    }}
    /* The section title lives in the header bar, beside the collapse button,
       rather than costing a row of its own below it. */
    [data-testid="stSidebarHeader"]::before {{
        content: "Your profile";
        font-size: var(--t-md); font-weight: 600; color: var(--ink);
        line-height: 1.2; letter-spacing: -.01em;
    }}
    /* An empty 32px reservation for a logo this app does not set. */
    [data-testid="stLogoSpacer"] {{ display: none !important; }}
    /* No top/bottom pad — Streamlit's default 96px bottom reservation looks unfinished;
       sides stay tight so fields use the sidebar width. */
    [data-testid="stSidebarUserContent"] {{
        padding: 0 var(--s-2) !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child {{
        margin-top: 0 !important; padding-top: 0 !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"],
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] {{
        margin-top: 0 !important;
    }}
    section[data-testid="stSidebar"] .block-container,
    section[data-testid="stSidebar"] > div {{ padding-top: 0; }}
    section[data-testid="stSidebar"] hr {{
        border-color: var(--line); margin: var(--s-4) 0;
    }}

    /* ---------- loading spinner ------------------------------------------- */
    [data-testid="stElementContainer"]:has([data-testid="stSpinner"]) {{
        padding-top: var(--s-4) !important;
        margin-top: 0 !important;
    }}

    /* ---------- masthead -------------------------------------------------- */
    /* Sticky masthead: profile + actions stay visible while the plan scrolls. */
    /* Streamlit wraps every keyed container in a layout wrapper sized exactly to
       its content, and a sticky element can only travel inside its containing
       block -- so `sticky` on the container itself never moves. The wrapper is
       the flex child of the scrolling column, so that is where it belongs. */
    [data-testid="stLayoutWrapper"]:has(> div.st-key-masthead) {{
        position: sticky; top: 0; z-index: 900;
    }}
    div.st-key-masthead {{
        box-sizing: border-box;
        background: var(--paper);
        border-bottom: 1px solid var(--line);
        /* No full bleed: Streamlit pins an explicit pixel width on this
           wrapper, so a negative margin shifts the band rather than widening
           it and the rule stops short of the right gutter. Inside the gutter
           it lines up with every card below it instead. */
        margin: 0 0 var(--s-2);
        padding: var(--s-4) 0;
        box-shadow: 0 4px 12px -8px rgba(20, 32, 27, .12);
    }}
    /* Brand block and actions on one centre line. */
    div.st-key-masthead [data-testid="stHorizontalBlock"] {{ align-items: center; }}
    /* Wordmark and tagline share a baseline instead of stacking: the masthead is
       identity plus one sentence, and it should cost one band of the page, not
       four. Stacks again only when the row would squeeze the sentence. */
    .am-mast {{ display: flex; align-items: baseline; gap: var(--s-4); min-width: 0; max-width: 100%; }}
    .am-word {{
        font-family: {FONT_SERIF};
        font-size: var(--t-2xl); font-weight: 600; letter-spacing: -.025em;
        line-height: 1.05; color: var(--ink); white-space: nowrap;
    }}
    .am-word em {{ font-style: normal; color: var(--accent); }}
    .am-tag {{
        flex: 1; font-size: var(--t-xs); line-height: 1.4; color: var(--ink-3);
        max-width: 62ch; text-wrap: pretty; min-width: 0;
    }}
    .am-tag b {{ color: var(--ink); font-weight: 600; }}
    @media (max-width: 820px) {{
        .am-mast {{ flex-direction: column; align-items: flex-start; gap: var(--s-2); }}
    }}
    /* Three columns of masthead only survive while the two actions still fit
       their labels. Below that the actions take their own full-width row rather
       than shrinking into two-line buttons. */
    @media (max-width: 1200px) {{
        div.st-key-masthead [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
        div.st-key-masthead [data-testid="stColumn"]:first-child {{ flex: 1 1 100%; }}
        div.st-key-masthead [data-testid="stColumn"]:not(:first-child) {{
            flex: 1 1 150px; min-width: 150px;
        }}
    }}
    div.st-key-generate_plan_btn .stButton > button[data-testid="stBaseButton-primary"] {{
        background: var(--accent-deep) !important;
        border-color: var(--accent-deep) !important;
        color: {c['on_deep']} !important;
    }}
    div.st-key-generate_plan_btn .stButton > button[data-testid="stBaseButton-primary"]:hover {{
        background: var(--accent) !important; border-color: var(--accent) !important;
    }}
    div.st-key-demo_plan_btn .stButton > button {{
        font-weight: 500 !important;
        color: var(--ink-2) !important;
    }}
    div.st-key-week_strip_header {{
        margin-bottom: var(--s-3);
    }}
    div.st-key-week_strip_header [data-testid="stHorizontalBlock"] {{
        align-items: center !important;
    }}
    div.st-key-week_strip_header .am-label {{
        margin-bottom: 0;
    }}
    div.st-key-week_expand_toggle {{
        position: relative;
        width: 26px;
        height: 26px;
        margin-left: auto;
    }}
    .am-week-toggle-icon {{
        display: flex; align-items: center; justify-content: center;
        width: 26px; height: 26px; padding: 0;
        background: var(--surface); border: 1px solid var(--line);
        border-radius: var(--r-sm); color: var(--ink-2);
        transition: border-color .16s ease, background .16s ease, color .16s ease;
    }}
    div.st-key-week_expand_toggle:hover .am-week-toggle-icon {{
        border-color: var(--accent); background: {c['accent_soft']}; color: {c['accent_deep']};
    }}
    div.st-key-week_expand_toggle > [data-testid="stElementContainer"]:has(.stButton) {{
        position: absolute; inset: 0; z-index: 2;
    }}
    div.st-key-week_expand_toggle .stButton {{ height: 100%; margin: 0; padding: 0; }}
    div.st-key-week_expand_toggle .stButton > button {{
        width: 26px; height: 26px; min-height: 26px;
        opacity: 0; padding: 0 !important; margin: 0 !important;
        border: none !important; box-shadow: none !important;
        cursor: pointer;
    }}
    div.st-key-week_expand_toggle:has(button:focus-visible) .am-week-toggle-icon {{
        outline: 2px solid var(--accent); outline-offset: 2px;
    }}
    .am-rule {{ height: 1px; background: var(--line); margin: var(--s-4) 0; }}

    /* ---------- section headings ------------------------------------------ */
    .am-label {{
        display: flex; align-items: baseline; gap: var(--s-2);
        font-size: var(--t-lg); font-weight: 600; color: var(--ink);
        letter-spacing: -.015em; line-height: 1.25;
        margin: 0 0 var(--s-3);
    }}
    section[data-testid="stSidebar"] .am-label {{
        font-size: var(--t-md); margin: 0 0 var(--s-2);
    }}
    .am-label span {{
        font-size: var(--t-sm); font-weight: 400; color: var(--ink-3);
        letter-spacing: 0;
    }}
    div.st-key-meal_plan_section .am-label-meal {{
        margin-top: 0;
    }}
    /* Match other section titles; extra room when a notice sits right above. */
    [data-testid="stLayoutWrapper"]:has(> div.st-key-meal_plan_section) {{
        margin-top: var(--s-3);
    }}
    [data-testid="stElementContainer"]:has(.am-note)
        + [data-testid="stLayoutWrapper"]:has(> div.st-key-meal_plan_section) {{
        margin-top: var(--s-5);
    }}

    /* ---------- week strip ------------------------------------------------ */
    div[class*="st-key-daycard-"] {{
        position: relative;
        min-height: {DAY_CARD_HEIGHT_COLLAPSED};
        gap: 0 !important;
    }}
    div[class*="st-key-daycard-"]:has(.am-day:not(.am-day-collapsed)) {{
        min-height: {DAY_CARD_HEIGHT};
    }}
    /* The button is a transparent hit layer over the whole card, so the card --
       not just its title -- is the click target. The element container has to be
       the positioned box; `inset` on the inner .stButton would resolve against
       it and stack the hit layer below the card instead of over it. */
    div[class*="st-key-daycard-"] > [data-testid="stElementContainer"]:has(.stButton) {{
        position: absolute; inset: 0; z-index: 2;
    }}
    div[class*="st-key-daycard-"] .stButton {{ height: 100%; }}
    div[class*="st-key-daycard-"] .stButton > button {{
        width: 100%; height: {DAY_CARD_HEIGHT_COLLAPSED};
        opacity: 0; background: transparent !important;
        border: none !important; box-shadow: none !important; padding: 0 !important;
        cursor: pointer;
    }}
    div[class*="st-key-daycard-"]:has(.am-day:not(.am-day-collapsed)) .stButton > button {{
        height: {DAY_CARD_HEIGHT};
    }}
    div[class*="st-key-daycard-"]:has(button:focus-visible) .am-day {{
        outline: 2px solid var(--accent); outline-offset: 2px;
    }}

    .am-day {{
        display: flex; flex-direction: column; gap: var(--s-1);
        height: {DAY_CARD_HEIGHT_COLLAPSED}; overflow: hidden;
        background: var(--surface); border: 1px solid var(--line);
        border-radius: var(--r-md); padding: var(--s-3);
        transition: border-color .16s ease, transform .16s ease, height .2s ease;
    }}
    .am-day:not(.am-day-collapsed) {{
        height: {DAY_CARD_HEIGHT};
    }}
    .am-day-collapsed {{
        justify-content: center;
    }}
    div[class*="st-key-daycard-"]:hover .am-day {{
        border-color: var(--accent); transform: translateY(-1px);
    }}
    .am-day-on {{
        background: var(--accent-deep); border-color: var(--accent-deep);
        box-shadow: 0 2px 4px rgba(20,40,35,.10), 0 14px 26px -18px rgba(20,40,35,.55);
    }}
    div[class*="st-key-daycard-"]:hover .am-day-on {{ border-color: var(--accent-deep); }}
    .am-day-name {{
        font-family: {FONT_MONO}; font-size: var(--t-micro); font-weight: 600;
        letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3);
    }}
    /* Two-line box whether the name wraps or not, and the meta/burn pair
       pinned to the bottom -- so the seven cards read as one row, not seven
       independently-flowing columns. */
    .am-day-act {{
        display: flex; align-items: flex-start; gap: var(--s-2);
        font-size: var(--t-base); font-weight: 600; color: var(--ink);
        line-height: 1.3; margin-top: var(--s-1);
        min-height: 2.4em; overflow: hidden;
    }}
    .am-day-act .am-i {{ margin-top: 2px; }}
    .am-day-meta {{
        font-size: var(--t-xs); line-height: 1.45; color: var(--ink-2);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        flex-shrink: 0;
    }}
    /* Seven columns get narrow fast. Below this width the duration alone keeps
       the meta on one line; the intensity is still in the energy chain below and
       in the card's accessible name. */
    @media (max-width: 1400px) {{
        .am-day-int {{ display: none; }}
    }}
    .am-day-burn {{
        font-family: {FONT_MONO}; font-size: var(--t-xs); font-weight: 600;
        color: var(--accent); margin-top: auto; white-space: nowrap;
    }}
    .am-day-on .am-day-name {{ color: {c['on_deep_2']}; }}
    .am-day-on .am-day-act {{ color: {c['on_deep']}; }}
    .am-day-on .am-day-meta {{ color: {c['on_deep_2']}; }}
    .am-day-on .am-day-burn {{ color: {c['on_deep_3']}; }}

    /* ---------- energy chain ---------------------------------------------- */
    .am-chain {{
        display: flex; align-items: stretch; gap: var(--s-4); flex-wrap: wrap;
        background: var(--surface); border: 1px solid var(--line);
        border-radius: var(--r-md); padding: var(--s-4) var(--s-5);
        max-width: 100%; box-sizing: border-box;
    }}
    .am-step {{ display: flex; flex-direction: column; gap: 2px; justify-content: center; min-width: 96px; }}
    .am-step-lab {{
        font-size: var(--t-xs); font-weight: 600; color: var(--ink-3);
    }}
    .am-step-val {{
        font-family: {FONT_SERIF}; font-size: var(--t-lg); font-weight: 600;
        color: var(--ink); line-height: 1.1;
    }}
    .am-step-sub {{
        display: flex; align-items: center; flex-wrap: wrap;
        gap: var(--s-1) var(--s-4);
        font-size: var(--t-xs); color: var(--ink-2);
    }}
    /* One session per part, so several of them read as a list rather than as
       one run-on line. Several parts stack instead of running wide: side by
       side they push the goal and target steps onto a second row, and a chain
       that wraps mid-equation stops reading as one. */
    .am-step-part {{ display: inline-flex; align-items: center; gap: var(--s-1); }}
    .am-step-sub:has(.am-step-part + .am-step-part) {{
        flex-direction: column; align-items: flex-start; gap: 2px;
    }}
    .am-arrow {{
        display: flex; align-items: center; color: var(--ink-3);
        font-size: var(--t-md); font-weight: 500;
    }}
    .am-step-target {{
        background: {c['accent_soft']}; border: 1px solid {c['accent']};
        border-radius: var(--r-sm); padding: var(--s-2) var(--s-4);
        margin-left: auto; gap: var(--s-1);
        flex-shrink: 1; min-width: 0;
    }}
    .am-step-target .am-step-lab {{ color: {c['accent_deep']}; }}
    .am-step-target .am-step-val {{ font-size: var(--t-xl); color: {c['accent_deep']}; }}
    .am-step-target .am-step-sub {{ color: {c['accent_deep']}; opacity: .85; }}
    .am-plus {{ color: var(--accent); }}
    .am-minus {{ color: {c['ochre']}; }}

    /* ---------- plan summary + meter -------------------------------------- */
    .am-sum {{
        background: var(--surface); border: 1px solid var(--line);
        border-radius: var(--r-md); padding: var(--s-4) var(--s-5);
        max-width: 100%; box-sizing: border-box;
    }}
    .am-sum-top {{ display: flex; align-items: baseline; gap: var(--s-3); flex-wrap: wrap; }}
    .am-sum-big {{
        font-family: {FONT_SERIF}; font-size: var(--t-xl); font-weight: 600;
        color: var(--ink); line-height: 1;
    }}
    .am-sum-of {{ font-size: var(--t-sm); color: var(--ink-2); }}
    .am-sum-chip {{
        margin-left: auto; font-family: {FONT_MONO}; font-size: var(--t-xs); font-weight: 600;
        border-radius: var(--r-pill); padding: var(--s-1) var(--s-3);
    }}
    .am-chip-ok {{ background: {c['accent_soft']}; color: {c['accent_deep']}; border: 1px solid {c['accent']}; }}
    .am-chip-warn {{ background: {c['ochre_soft']}; color: {c['ochre']}; border: 1px solid {c['ochre']}; }}
    .am-meter {{
        height: 6px; border-radius: var(--r-pill); background: {c['surface_2']};
        margin: var(--s-3) 0; overflow: hidden;
    }}
    /* scaleX, not width: the bar animates on the compositor and never asks
       the summary row to re-lay-out mid-transition. */
    .am-meter-fill {{
        width: 100%; height: 100%; border-radius: var(--r-pill);
        background: var(--accent); transform-origin: left center;
        transition: transform .4s cubic-bezier(.16,1,.3,1);
    }}
    .am-meter-over {{ background: {c['ochre']}; }}
    .am-sum-foot {{
        display: flex; gap: var(--s-6); flex-wrap: wrap;
        font-size: var(--t-xs); color: var(--ink-2);
    }}
    .am-sum-foot b {{ font-family: {FONT_MONO}; color: var(--ink); font-weight: 600; }}

    /* ---------- meal cards ------------------------------------------------ */
    .am-meal {{
        background: var(--surface); border: 1px solid var(--line);
        border-radius: var(--r-md); padding: var(--s-4) var(--s-5);
        margin-bottom: var(--s-3);
    }}
    .am-meal-head {{
        display: flex; align-items: center; gap: var(--s-2);
        border-bottom: 1px solid var(--line-soft);
        padding-bottom: var(--s-2); margin-bottom: var(--s-2);
    }}
    .am-meal-name {{
        font-family: {FONT_SERIF}; font-size: var(--t-md); font-weight: 600; color: var(--ink);
    }}
    .am-meal-kcal {{
        margin-left: auto; font-family: {FONT_MONO}; font-size: var(--t-sm);
        font-weight: 600; color: var(--accent);
    }}
    .am-food {{ display: flex; align-items: baseline; gap: var(--s-3); padding: var(--s-1) 0; }}
    .am-food + .am-food {{ border-top: 1px solid var(--line-soft); }}
    .am-food-name {{ font-size: var(--t-base); color: var(--ink); flex: 1; min-width: 0; }}
    .am-food-g {{ font-family: {FONT_MONO}; font-size: var(--t-xs); color: var(--ink-2); white-space: nowrap; }}
    .am-food-kcal {{
        font-family: {FONT_MONO}; font-size: var(--t-sm); font-weight: 600; color: var(--ink);
        white-space: nowrap; min-width: 62px; text-align: right;
    }}
    .am-src {{
        font-family: {FONT_MONO}; font-size: var(--t-xs); color: var(--ink-3);
        white-space: nowrap; min-width: 92px; text-align: right;
    }}
    .am-src-warn {{ color: {c['ochre']}; font-weight: 600; }}

    /* ---------- empty state ----------------------------------------------- */
    .am-empty {{
        border: 1px solid var(--line); border-radius: var(--r-md);
        background: var(--surface); padding: var(--s-6) var(--s-7);
    }}
    .am-empty-h {{
        font-family: {FONT_SERIF}; font-size: var(--t-lg); font-weight: 600;
        color: var(--ink); margin-bottom: var(--s-2);
    }}
    .am-empty-p {{
        font-size: var(--t-sm); color: var(--ink-2);
        margin-bottom: var(--s-5);
    }}
    .am-flow {{
        display: flex; align-items: center; gap: var(--s-2);
        flex-wrap: wrap; list-style: none; margin: 0; padding: 0;
    }}
    .am-flow li {{ display: flex; align-items: center; flex-shrink: 0; }}
    .am-flow-step {{
        display: flex; align-items: center; gap: var(--s-1);
        color: var(--ink-2); white-space: nowrap; flex-shrink: 0;
    }}
    .am-flow-step b {{ font-size: var(--t-sm); font-weight: 600; color: var(--ink); }}
    .am-flow-step span {{
        font-size: var(--t-xs); color: var(--ink-3); white-space: nowrap;
    }}
    .am-flow-on b, .am-flow-on span, .am-flow-on {{ color: var(--accent); }}
    .am-flow-arrow {{ color: var(--ink-3); opacity: .6; display: flex; }}

    /* ---------- notices + footer ------------------------------------------ */
    .am-note {{
        display: flex; align-items: center; gap: var(--s-2);
        border: 1px solid {c['ochre']}; background: {c['ochre_soft']};
        border-radius: var(--r-sm); padding: var(--s-3) var(--s-4);
        font-size: var(--t-sm); color: {c['ochre']}; margin-top: var(--s-3);
    }}
    .am-note b {{ font-weight: 600; }}
    .am-foot {{
        border-top: 1px solid var(--line); margin-top: var(--s-7); padding-top: var(--s-4);
        display: flex; gap: var(--s-6); flex-wrap: wrap;
        font-size: var(--t-xs); color: var(--ink-3);
    }}
    .am-foot b {{ color: var(--ink-2); font-weight: 600; }}

    /* ---------- hints ------------------------------------------------------ */
    .am-hint {{
        display: flex; align-items: baseline; gap: var(--s-1);
        font-size: var(--t-sm); color: var(--ink-2); line-height: 1.45;
    }}

    /* ---------- buttons (outside the day cards) ---------------------------- */
    .stButton > button {{
        border-radius: var(--r-sm); font-weight: 600; font-size: var(--t-sm);
        border: 1px solid var(--line);
        background: var(--surface); color: var(--ink);
        padding: var(--s-2) var(--s-4); min-height: 38px;
        transition: background .16s ease, border-color .16s ease, color .16s ease;
    }}
    /* A button's label belongs on one line; Streamlit wraps it inside its own
       markdown paragraph, so the rule has to reach that too. */
    .stButton > button, .stButton > button p, .stButton > button div {{ white-space: nowrap; }}
    .stButton > button:hover {{
        border-color: var(--accent); color: {c['accent_deep']}; background: {c['accent_soft']};
    }}
    .stButton > button[data-testid="stBaseButton-primary"] {{
        background: var(--accent-deep) !important; color: {c['on_deep']} !important;
        border-color: var(--accent-deep) !important;
    }}
    .stButton > button[data-testid="stBaseButton-primary"]:hover {{ background: var(--accent) !important; }}
    .stButton > button:disabled {{
        background: {c['surface_2']} !important; color: var(--ink-3) !important;
        border-color: var(--line) !important; cursor: not-allowed;
    }}

    /* ---------- inputs ----------------------------------------------------- */
    .stNumberInput input, .stTextInput input, [data-baseweb="select"] > div {{
        border-radius: var(--r-sm) !important; background: var(--surface) !important;
        font-size: var(--t-base) !important;
    }}
    div[data-testid="stNumberInput"] button {{ display: none !important; }}
    div[data-testid="stNumberInput"] input[type="number"] {{ -moz-appearance: textfield !important; }}
    div[data-testid="stNumberInput"] input[type="number"]::-webkit-outer-spin-button,
    div[data-testid="stNumberInput"] input[type="number"]::-webkit-inner-spin-button {{
        -webkit-appearance: none !important; margin: 0 !important;
    }}
    section[data-testid="stSidebar"] label p {{
        font-size: var(--t-sm) !important; color: var(--ink-2);
    }}

    @media (prefers-color-scheme: dark) {{
        body, .stApp {{ background-color: var(--paper) !important; color: var(--ink) !important; }}
    }}
    """
