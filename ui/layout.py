"""Page configuration and global styling for the Streamlit app."""

import streamlit as st

from ui.theme import GOOGLE_FONTS_URL, SIDEBAR_VIEWPORT_FRACTION, build_global_css

# Streamlit's sidebar Resizable leaves inline width on the section when collapsed;
# CSS !important handles it, but a parent-frame script re-syncs on toggle in case
# layout wrappers keep stale pixel widths from Streamlit's measurement pass.
_LAYOUT_SYNC_JS = f"""
(function () {{
  const doc = document;
  const RATIO = {SIDEBAR_VIEWPORT_FRACTION};
  const VERSION = 'ratio:' + RATIO;
  const SIDEBAR = '[data-testid="stSidebar"]';

  function sidebarWidthPx() {{
    return Math.round(window.innerWidth * RATIO);
  }}

  function sidebarCollapsed() {{
    const sb = doc.querySelector(SIDEBAR);
    return sb && sb.getAttribute('aria-expanded') === 'false';
  }}

  function setImp(el, prop, val) {{
    if (el) el.style.setProperty(prop, val, 'important');
  }}

  function clearImp(el, prop) {{
    if (el) el.style.removeProperty(prop);
  }}

  function syncSidebarStorage(w) {{
    try {{
      localStorage.setItem('sidebarWidth', String(w));
    }} catch (_) {{}}
  }}

  function sync() {{
    const app = doc.querySelector('[data-testid="stAppViewContainer"]');
    if (!app || app.children.length < 2) return;

    const sidebarWrap = app.firstElementChild;
    const mainWrap = app.lastElementChild;
    const sidebar = doc.querySelector(SIDEBAR);
    const stMain = doc.querySelector('[data-testid="stMain"]');
    const collapsed = sidebarCollapsed();
    const w = sidebarWidthPx();

    if (collapsed) {{
      setImp(sidebar, 'width', '0');
      setImp(sidebar, 'min-width', '0');
      setImp(sidebar, 'max-width', '0');
      setImp(sidebar, 'flex', '0 0 0');
      setImp(sidebarWrap, 'width', '0');
      setImp(sidebarWrap, 'min-width', '0');
      setImp(sidebarWrap, 'max-width', '0');
      setImp(sidebarWrap, 'flex', '0 0 0');
    }} else {{
      syncSidebarStorage(w);
      const wpx = w + 'px';
      setImp(sidebar, 'width', wpx);
      setImp(sidebar, 'min-width', wpx);
      setImp(sidebar, 'max-width', wpx);
      setImp(sidebar, 'flex', '0 0 ' + wpx);
      setImp(sidebarWrap, 'width', wpx);
      setImp(sidebarWrap, 'min-width', wpx);
      setImp(sidebarWrap, 'max-width', wpx);
      setImp(sidebarWrap, 'flex', '0 0 ' + wpx);
    }}

    setImp(mainWrap, 'flex', '1 1 0%');
    setImp(mainWrap, 'width', 'auto');
    setImp(mainWrap, 'min-width', '0');
    setImp(mainWrap, 'max-width', '100%');

    if (stMain) {{
      setImp(stMain, 'align-items', 'stretch');
      setImp(stMain, 'width', '100%');
      setImp(stMain, 'max-width', '100%');
      setImp(stMain, 'min-width', '0');
    }}

    doc.querySelectorAll(
      '[data-testid="stMainBlockContainer"], .block-container, [data-testid="stLayoutWrapper"]'
    ).forEach((el) => {{
      el.style.width = '100%';
      el.style.maxWidth = '100%';
    }});
  }}

  function burst() {{
    sync();
    let n = 0;
    const id = window.setInterval(() => {{
      sync();
      n += 1;
      if (n >= 15) window.clearInterval(id);
    }}, 50);
  }}

  // Always sync on each Streamlit rerun (script is re-injected). Only attach
  // listeners once per ratio so edits to SIDEBAR_VIEWPORT_FRACTION take effect.
  sync();
  if (doc.__amLayoutSyncVersion === VERSION) return;
  doc.__amLayoutSyncVersion = VERSION;

  burst();
  window.addEventListener('resize', sync);

  const sb = doc.querySelector(SIDEBAR);
  if (sb) {{
    new MutationObserver(burst).observe(sb, {{
      attributes: true,
      attributeFilter: ['aria-expanded'],
    }});
  }}
}})();
"""


def configure_page() -> None:
    """Set page config, preload the webfonts and inject global CSS.

    Call once at the top of app.py before any other Streamlit code. The font
    <link> tags go in first: an @import alone is unreliable inside a Streamlit
    style block, and a missed font is the difference between the design and a
    default-sans fallback.
    """
    st.set_page_config(
        page_title="AgentMealPrep — activity-aware meal planning",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link rel="stylesheet" href="{GOOGLE_FONTS_URL}">',
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{build_global_css()}</style>", unsafe_allow_html=True)
    with st.container(key="layout_sync"):
        st.html(
            f"<script>{_LAYOUT_SYNC_JS}</script>",
            unsafe_allow_javascript=True,
        )