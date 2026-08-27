"""Design tokens shared across all UI components."""

COLORS = {
    "paper": "#f3f6f5",
    "surface": "#ffffff",
    "surface_2": "#eef2f1",
    "ink": "#16211e",
    "ink_2": "#4b5a56",
    "line": "#d7e0dd",
    "line_strong": "#b9c7c3",
    "accent": "#138572",
    "accent_ink": "#084036",
    "accent_soft": "#e0eeeb",
    "ochre": "#8a6412",
    "ochre_soft": "#f5eedd",
    "danger": "#9d3a2d",
    "danger_soft": "#f7e6e2",
}

RADIUS = "6px"
SHADOW = "0 1px 2px rgba(20,40,35,.05), 0 8px 24px -16px rgba(20,40,35,.28)"

FONT_SANS = "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif"
FONT_MONO = "'IBM Plex Mono', ui-monospace, monospace"
FONT_SERIF = "'Newsreader', Georgia, serif"

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap"
)


def build_global_css() -> str:
    """Return the <style> block injected once by ui/layout.py.

    Includes:
    - Google Fonts import
    - Streamlit overrides (padding, background, font)
    - Custom component classes (chips, badges, stat cards, day pills)
    """
    css = f"""
    @import url('{GOOGLE_FONTS_URL}');

    /* Base styles */
    body, .stApp {{
        background-color: {COLORS['paper']};
        font-family: {FONT_SANS};
        color: {COLORS['ink']};
    }}

    /* Remove Streamlit default padding */
    .block-container {{
        padding-top: 1rem;
        padding-left: 3rem;
        padding-right: 3rem;
        padding-bottom: 1rem;
    }}

   section[data-testid="stSidebar"] {{
        width: 400px !important;
    }}

    /* Primary button styling */
    .stButton > button {{
        background-color: {COLORS['accent']};
        color: {COLORS['surface']};
        border: none;
        border-radius: {RADIUS};
        font-weight: 600;
        padding: 0.5rem 1rem;
    }}

    .stButton > button:hover {{
        background-color: {COLORS['accent_ink']};
    }}

    .stButton > button[data-testid="stBaseButton-primary"] {{
        background-color: {COLORS['accent_ink']} !important;
        color: {COLORS['surface']} !important;
        border-color: {COLORS['accent_ink']} !important;
    }}

    /* Day selector pill styling */
    .day-pill-active {{
        background-color: {COLORS['accent']};
        color: {COLORS['surface']};
        border-radius: {RADIUS};
    }}

    /* Chip styling (preferences) */
    .chip {{
        display: inline-block;
        background-color: {COLORS['surface_2']};
        border: 1px solid {COLORS['line']};
        border-radius: 20px;
        padding: 0.4rem 0.8rem;
        margin-right: 0.5rem;
        margin-bottom: 1.5rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: {COLORS['ink']};
    }}

    .chip-accent {{
        background-color: {COLORS['accent_soft']};
        border-color: {COLORS['accent']};
        color: {COLORS['accent_ink']};
    }}

    .chip-danger {{
        background-color: {COLORS['danger_soft']};
        border-color: {COLORS['danger']};
        color: {COLORS['danger']};
    }}

    /* Badge styling (guardrails, food sources) */
    .badge-ok {{
        display: inline-block;
        background-color: {COLORS['accent_soft']};
        border: 1px solid {COLORS['accent']};
        border-radius: {RADIUS};
        padding: 0.25rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: {COLORS['accent_ink']};
    }}

    .badge-warn {{
        display: inline-block;
        background-color: {COLORS['ochre_soft']};
        border: 1px solid {COLORS['ochre']};
        border-radius: {RADIUS};
        padding: 0.25rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: {COLORS['ochre']};
    }}

    /* Stat card styling */
    .stat-card {{
        border: 1px solid {COLORS['line']};
        border-radius: {RADIUS};
        padding: 1rem;
        background-color: {COLORS['surface']};
        box-shadow: {SHADOW};
        text-align: center;
    }}

    .stat-card-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {COLORS['accent']};
    }}

    .stat-card-label {{
        font-size: 0.875rem;
        color: {COLORS['ink_2']};
        margin-top: 0.5rem;
    }}

    /* Text input styling */
    .stTextInput > div > div > input {{
        border-radius: {RADIUS};
    }}

    /* Number input styling */
    .stNumberInput > div > div > input {{
        border-radius: {RADIUS};
    }}

    div[data-testid="stNumberInput"] button {{
        display: none !important;
    }}

    div[data-testid="stNumberInput"] input[type="number"]::-webkit-outer-spin-button,
    div[data-testid="stNumberInput"] input[type="number"]::-webkit-inner-spin-button {{
        -webkit-appearance: none !important;
        margin: 0 !important;
    }}
    div[data-testid="stNumberInput"] input[type="number"] {{
        -moz-appearance: textfield !important;
    }}

    /* Selectbox styling */
    .stSelectbox > div > div > select {{
        border-radius: {RADIUS};
    }}

    /* Make the header blend with the page background instead of showing
       as a visible empty bar. Keeps the sidebar open/close button intact
       and clickable — only its background/shadow are removed. */
    header[data-testid="stHeader"] {{
        background-color: transparent !important;
        box-shadow: none !important;
    }}

    """
    return css
