# -*- coding: utf-8 -*-
"""
Génère la présentation client Agent Meal Prep (10 minutes, entrevue KPMG).

Les diapositives portent une idée par bloc, en une ligne. Tout le détail est
dans les notes du présentateur.

Toutes les positions sont exprimées en pouces et posées explicitement : aucun
placeholder de gabarit n'est utilisé, ce qui évite les chevauchements et les
mises en page « par défaut ».

    python build_deck.py [-o sortie.pptx]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

# --------------------------------------------------------------------------- #
# Thème
# --------------------------------------------------------------------------- #

INK = RGBColor(0x14, 0x20, 0x1D)
INK_SOFT = RGBColor(0x43, 0x52, 0x4E)
MUTED = RGBColor(0x71, 0x81, 0x7C)
LINE = RGBColor(0xD2, 0xDB, 0xD8)
ACCENT = RGBColor(0x0E, 0x6A, 0x5A)
ACCENT_SOFT = RGBColor(0xDF, 0xEE, 0xEA)
BG = RGBColor(0xF1, 0xF4, 0xF3)
SURFACE = RGBColor(0xFF, 0xFF, 0xFF)
FLAG = RGBColor(0x9C, 0x43, 0x21)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ON_ACCENT_SOFT = RGBColor(0xA9, 0xD5, 0xC9)

F_DISPLAY = "Georgia"          # titres
F_BODY = "Segoe UI"            # corps
F_MONO = "Consolas"            # étiquettes, numéros

SW, SH = 13.333, 7.5           # 16:9
MARGIN = 0.75
CONTENT_W = SW - 2 * MARGIN    # 11.833

TITLE_Y = 0.92
EYEBROW_Y = 0.58


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #

def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)
    return prs


def add_slide(prs: Presentation, bg: RGBColor = BG):
    """Diapositive vierge (layout 6 = blank) avec fond plein."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    back = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                  Inches(SW), Inches(SH))
    back.fill.solid()
    back.fill.fore_color.rgb = bg
    back.line.fill.background()
    back.shadow.inherit = False
    return slide


def text(slide, box: Box, runs, *, size=15, color=INK, font=F_BODY, bold=False,
         italic=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         line_spacing=1.22, space_after=0, caps_spacing=None):
    """
    `runs` : str, ou liste de paragraphes. Chaque paragraphe est soit un str,
    soit un dict {text, size, color, bold, italic, font, space_before}.
    """
    if isinstance(runs, str):
        runs = [runs]

    shape = slide.shapes.add_textbox(Inches(box.x), Inches(box.y),
                                     Inches(box.w), Inches(box.h))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0

    for i, item in enumerate(runs):
        spec = {"text": item} if isinstance(item, str) else dict(item)
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.line_spacing = spec.get("line_spacing", line_spacing)
        if spec.get("space_before"):
            para.space_before = Pt(spec["space_before"])
        para.space_after = Pt(spec.get("space_after", space_after))

        run = para.add_run()
        run.text = spec["text"]
        f = run.font
        f.name = spec.get("font", font)
        f.size = Pt(spec.get("size", size))
        f.bold = spec.get("bold", bold)
        f.italic = spec.get("italic", italic)
        f.color.rgb = spec.get("color", color)
        spacing = spec.get("caps_spacing", caps_spacing)
        if spacing:
            f._rPr.set("spc", str(int(spacing * 100)))
    return shape


def eyebrow(slide, label: str, *, x=MARGIN, y=EYEBROW_Y, color=ACCENT, w=None):
    return text(slide, Box(x, y, w or CONTENT_W, 0.24), label.upper(),
                size=10.5, font=F_MONO, color=color, bold=True,
                caps_spacing=1.6)


def title(slide, label: str, *, color=INK, y=TITLE_Y, size=34, w=None):
    return text(slide, Box(MARGIN, y, w or CONTENT_W, 0.85), label,
                size=size, font=F_DISPLAY, color=color, bold=True,
                line_spacing=1.05)


def card(slide, box: Box, *, fill=SURFACE, border=LINE, radius=0.035):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                   Inches(box.x), Inches(box.y),
                                   Inches(box.w), Inches(box.h))
    shape.adjustments[0] = radius
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if border is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = border
        shape.line.width = Pt(0.75)
    shape.shadow.inherit = False
    return shape


def frame(slide, box: Box, *, border=ACCENT, radius=0.02):
    """Contour pointillé sans remplissage : délimite une frontière logique
    (ici, ce qui se trouve réellement dans core/agent/graph.py)."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                   Inches(box.x), Inches(box.y),
                                   Inches(box.w), Inches(box.h))
    shape.adjustments[0] = radius
    shape.fill.background()
    shape.line.color.rgb = border
    shape.line.width = Pt(1.0)
    shape.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    shape.shadow.inherit = False
    return shape


def badge(slide, x: float, y: float, label: str, *, d=0.42, fill=ACCENT,
          color=WHITE, size=13):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y),
                                   Inches(d), Inches(d))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    shape.shadow.inherit = False
    tf = shape.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = label
    run.font.name = F_MONO
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = color
    return shape


def connector(slide, start, end, *, color=MUTED, width=1.25, arrow=True):
    x1, y1 = start
    x2, y2 = end
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1),
                                      Inches(y1), Inches(x2), Inches(y2))
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    if arrow:
        ln = conn.line._get_or_add_ln()
        tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle",
                                                "w": "med", "len": "med"})
        ln.append(tail)
    return conn


def page_number(slide, n: int, *, color=MUTED):
    text(slide, Box(SW - MARGIN - 1.0, SH - 0.62, 1.0, 0.3), f"{n:02d}",
         size=10, font=F_MONO, color=color, align=PP_ALIGN.RIGHT)


def notes(slide, body: str):
    slide.notes_slide.notes_text_frame.text = body.strip()


def columns(n: int, *, x=MARGIN, total=CONTENT_W, gap=0.4):
    w = (total - gap * (n - 1)) / n
    return [(x + i * (w + gap), w) for i in range(n)]


# --------------------------------------------------------------------------- #
# Diapositives
# --------------------------------------------------------------------------- #

def slide_01_cover(prs):
    slide = add_slide(prs)
    panel = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                   Inches(5.0), Inches(SH))
    panel.fill.solid()
    panel.fill.fore_color.rgb = ACCENT
    panel.line.fill.background()
    panel.shadow.inherit = False

    text(slide, Box(0.85, 1.35, 3.4, 0.24), "PROTOTYPE",
         size=10.5, font=F_MONO, color=ON_ACCENT_SOFT, bold=True,
         caps_spacing=1.6)
    text(slide, Box(0.85, 4.15, 3.6, 2.0),
         [{"text": "Personnalisée."},
          {"text": "Fondée.", "space_before": 4},
          {"text": "Sécuritaire.", "space_before": 4}],
         size=25, font=F_DISPLAY, color=WHITE, italic=True, line_spacing=1.1)

    text(slide, Box(5.85, 2.15, 6.7, 0.26), "ENTREVUE · MISE EN SITUATION",
         size=10.5, font=F_MONO, color=ACCENT, bold=True, caps_spacing=1.6)
    text(slide, Box(5.85, 2.55, 6.9, 1.1), "Agent Meal Prep",
         size=48, font=F_DISPLAY, color=INK, bold=True, line_spacing=1.0)
    text(slide, Box(5.85, 3.75, 6.5, 0.6),
         "Plan alimentaire quotidien, généré par un agent IA.",
         size=17, color=INK_SOFT)
    text(slide, Box(5.85, 4.62, 6.6, 0.3),
         "Streamlit · LangGraph · Gemini › Groq · USDA FoodData Central · SQLite",
         size=11, font=F_MONO, color=MUTED)
    text(slide, Box(5.85, 5.55, 6.5, 0.8),
         [{"text": "Melody Nadeau", "size": 15, "bold": True, "color": INK},
          {"text": "27 août 2026", "size": 13, "color": MUTED,
           "space_before": 3}])

    notes(slide, """
10 minutes, présentation client. Ne pas ouvrir sur la technique.
Annoncer le déroulé : le besoin, la solution, la démo, l'architecture,
les garde-fous, les risques.
Le prototype roule sur le profil imposé dans l'énoncé.
""")
    return slide


def slide_02_besoin(prs):
    slide = add_slide(prs)
    eyebrow(slide, "Votre besoin")
    title(slide, "Ce que vous voulez offrir")

    text(slide, Box(MARGIN, 2.55, 6.6, 2.4),
         "Une entreprise de mieux-être veut offrir à ses employés un plan "
         "alimentaire quotidien, personnalisé et adapté à leur objectif.",
         size=24, color=INK, line_spacing=1.4)

    right = Box(7.95, 2.45, 4.63, 2.6)
    card(slide, right)
    text(slide, Box(right.x + 0.45, right.y + 0.45, right.w - 0.9, 0.24),
         "LE GAP", size=10.5, font=F_MONO, color=FLAG, bold=True,
         caps_spacing=1.6)
    text(slide, Box(right.x + 0.45, right.y + 0.9, right.w - 0.9, 1.4),
         "Aujourd'hui, ça demande un nutritionniste. Pas à l'échelle de "
         "centaines d'employés.",
         size=18, font=F_DISPLAY, color=INK, line_spacing=1.3)

    notes(slide, """
1 minute. Reformuler le besoin de leur point de vue, puis nommer le gap.

À dire, pas écrit sur la diapositive : ce n'est pas un produit grand public,
c'est un service que vous mettez à votre nom, pour des centaines de personnes,
tous les jours.

Phrase d'ouverture, à dire telle quelle :
« Ce que vos employés reçoivent, c'est un plan qui tient compte de leur
entraînement de la journée, de ce qu'ils acceptent de manger, et sur lequel
vous pouvez mettre votre nom sans prendre de risque. »
""")
    return slide


def slide_03_promesse(prs):
    slide = add_slide(prs)
    eyebrow(slide, "La promesse")
    title(slide, "Trois mots, trois choix de conception")

    items = [
        ("Personnalisée", "Profil, objectif, entraînement, préférences."),
        ("Fondée", "Chaque calorie vient de l'USDA."),
        ("Sécuritaire", "Les garde-fous sont écrits en code."),
    ]
    for (x, w), (head, body) in zip(columns(3), items):
        card(slide, Box(x, 2.45, w, 2.35))
        text(slide, Box(x + 0.42, 2.9, w - 0.84, 0.6), head,
             size=25, font=F_DISPLAY, color=ACCENT, bold=True)
        text(slide, Box(x + 0.42, 3.65, w - 0.84, 0.85), body,
             size=15.5, color=INK_SOFT, line_spacing=1.4)

    notes(slide, """
Définir les deux derniers mots, pas le premier : tout le monde promet
« personnalisé ».

Fondée : chaque calorie vient de la base USDA, le modèle ne fait jamais
l'addition.
Sécuritaire : les règles de sécurité santé sont écrites en Python. Une consigne
dans un prompt se contourne, une vérification en code, non.

Ces deux définitions préparent les diapositives Architecture et Garde-fous.
""")
    return slide


def slide_04_sources(prs):
    slide = add_slide(prs)
    eyebrow(slide, "Orchestration multi-sources")
    title(slide, "D'où viennent les données")

    items = [
        ("SQLite", "Activité du jour", "Change la cible calorique."),
        ("JSON", "Préférences", "Ce qu'ils acceptent de manger."),
        ("API USDA", "Nutrition", "Chiffres vérifiables à la source."),
    ]
    for (x, w), (tag, head, body) in zip(columns(3), items):
        card(slide, Box(x, 2.25, w, 2.75))
        card(slide, Box(x + 0.42, 2.6, 1.62, 0.4), fill=ACCENT_SOFT,
             border=None, radius=0.4)
        text(slide, Box(x + 0.42, 2.70, 1.62, 0.24), tag,
             size=10.5, font=F_MONO, color=ACCENT, bold=True,
             align=PP_ALIGN.CENTER, caps_spacing=1.2)
        text(slide, Box(x + 0.42, 3.3, w - 0.84, 0.45), head,
             size=19, font=F_DISPLAY, color=INK, bold=True)
        text(slide, Box(x + 0.42, 3.95, w - 0.84, 0.75), body,
             size=15, color=INK_SOFT, line_spacing=1.4)

    text(slide, Box(MARGIN, 5.45, CONTENT_W, 0.5),
         "Âge, poids, grandeur, objectif et préférences se modifient dans "
         "l'interface.",
         size=16, color=INK)

    notes(slide, """
Nommer la source ET sa raison d'être.

SQLite : le plan du mardi n'est pas celui du mercredi, l'entraînement de la
journée change la cible.
JSON : un plan que personne ne suit ne vaut rien, c'est une question
d'adhérence.
USDA : des chiffres vérifiables à la source plutôt que des chiffres que le
modèle trouve plausibles.

Le paramétrage est aussi le filet pour la modification de code en direct de la
partie 2.
""")
    return slide


def slide_05_principe(prs):
    slide = add_slide(prs, bg=ACCENT)
    text(slide, Box(1.55, 2.35, 10.2, 0.26), "LE PRINCIPE",
         size=10.5, font=F_MONO, color=ON_ACCENT_SOFT, bold=True,
         caps_spacing=1.6)
    text(slide, Box(1.55, 2.85, 10.2, 2.1),
         [{"text": "Le modèle compose le repas."},
          {"text": "Python vérifie le chiffre.", "space_before": 6}],
         size=40, font=F_DISPLAY, color=WHITE, bold=True, line_spacing=1.12)

    notes(slide, """
Dire cette phrase AVANT la liste des garde-fous, et ajouter à voix haute :
« Ce n'est jamais l'inverse. »

Sinon, une série de vérifications déterministes laisse croire que l'IA est
décorative, et les requis interdisent explicitement une solution uniquement à
base de règles métier.

Le LLM compose : aliments, portions, structure du repas.
Python encadre : cible calorique, exclusions, totaux, conformité.
""")
    return slide


def slide_06_profil(prs):
    slide = add_slide(prs)
    eyebrow(slide, "Démonstration")
    title(slide, "Le profil que vous nous avez donné")

    metrics = [("45", "ans", 42), ("100 kg", "220 lb", 36),
               ("196 cm", "6 pi 5 po", 36), ("Perte de poids", "objectif", 24)]
    for (x, w), (value, label, size) in zip(columns(4, gap=0.35), metrics):
        card(slide, Box(x, 2.35, w, 1.85))
        text(slide, Box(x + 0.3, 2.75, w - 0.6, 0.85), value,
             size=size, font=F_DISPLAY, color=ACCENT, bold=True,
             align=PP_ALIGN.CENTER, line_spacing=1.0)
        text(slide, Box(x + 0.3, 3.68, w - 0.6, 0.3), label.upper(),
             size=10.5, font=F_MONO, color=MUTED, bold=True,
             align=PP_ALIGN.CENTER, caps_spacing=1.4)

    band = Box(MARGIN, 4.75, CONTENT_W, 1.3)
    card(slide, band, fill=ACCENT_SOFT, border=None)
    text(slide, Box(band.x + 0.55, band.y + 0.35, band.w - 1.1, 0.26),
         "SQLITE · ACTIVITÉ DU JOUR", size=10.5, font=F_MONO, color=ACCENT,
         bold=True, caps_spacing=1.6)
    text(slide, Box(band.x + 0.55, band.y + 0.75, band.w - 1.1, 0.4),
         "Elle ajuste la cible calorique avant la génération.",
         size=18, color=INK)

    notes(slide, """
Dire les chiffres à voix haute : 45 ans, 100 kg, 196 cm, perte de poids.
« C'est exactement le profil que vous nous avez donné. »

Montrer l'activité du jour : type, durée, intensité, calories dépensées.

Annoncer la cible AVANT de générer, en déroulant la chaîne à voix haute :
métabolisme de base (Mifflin-St Jeor) 1 922 → base sédentaire × 1,2 = 2 306
→ + activité du jour → déficit de 500 kcal (ou 25 % du TDEE, le plus petit)
→ cible ≈ 1 806 kcal + activité, plancher de 1 200 kcal.
Revérifier ces chiffres en lançant l'app le jour même.

Pendant la génération : l'agent appelle lui-même l'outil USDA, recherche puis
lecture nutritionnelle, en boucle.

Le moment qui convainc : ajouter un aliment du plan en « non aimé »,
régénérer, montrer qu'il a disparu.

Filet : le bouton « Demo plan » recharge un plan déjà généré, sans réseau.
Vérifier aussi quel jour de la semaine tombe l'entrevue, l'activité change.
""")
    return slide


def slide_07_architecture(prs):
    slide = add_slide(prs)
    eyebrow(slide, "Schéma d'architecture")
    title(slide, "Le schéma est le graphe")

    # --- Entrées : deux sources locales, puis le calcul déterministe -------- #
    sources = [("SQLite", "Activité du jour", 2.44),
               ("JSON", "Préférences", 3.55)]
    for tag, label, y in sources:
        card(slide, Box(0.75, y, 2.35, 0.95))
        text(slide, Box(1.05, y + 0.22, 1.85, 0.24), tag,
             size=10.5, font=F_MONO, color=ACCENT, bold=True,
             caps_spacing=1.4)
        text(slide, Box(1.05, y + 0.52, 1.95, 0.3), label,
             size=14, color=INK)

    card(slide, Box(3.45, 2.44, 2.45, 0.95))
    text(slide, Box(3.75, 2.66, 1.95, 0.28), "plan_generator",
         size=13, bold=True, color=INK)
    text(slide, Box(3.75, 2.98, 1.95, 0.28), "cible kcal · Python",
         size=10.5, font=F_MONO, color=MUTED)

    connector(slide, (3.10, 2.92), (3.41, 2.92))
    connector(slide, (3.10, 4.03), (3.40, 3.26))
    connector(slide, (5.90, 2.85), (6.56, 2.85))

    # --- Le graphe lui-même ------------------------------------------------ #
    gx, gw = 6.30, 6.28
    frame(slide, Box(gx, 1.98, gw, 4.54))
    text(slide, Box(gx + 0.30, 2.12, 3.4, 0.24), "core/agent/graph.py",
         size=10.5, font=F_MONO, color=ACCENT, bold=True, caps_spacing=1.0)

    ix, iw = 6.60, 2.69
    jx = 9.59
    full_w = 5.68

    def node(x, y, w, head, sub, *, accent=False):
        card(slide, Box(x, y, w, 0.82 if accent else 0.72),
             fill=ACCENT_SOFT if accent else SURFACE,
             border=None if accent else LINE)
        text(slide, Box(x + 0.16, y + (0.18 if accent else 0.13),
                        w - 0.32, 0.28), head,
             size=13, bold=True, color=INK, align=PP_ALIGN.CENTER)
        text(slide, Box(x + 0.16, y + (0.48 if accent else 0.42),
                        w - 0.32, 0.26), sub,
             size=10, font=F_MONO,
             color=ACCENT if accent else MUTED, align=PP_ALIGN.CENTER)

    # Rangée 1 : la boucle d'outils.
    node(ix, 2.52, iw, "agent", "LLM · ≤ 15 tours", accent=True)
    node(jx, 2.52, iw, "tools · usda_tool + cache", "search › nutrition")
    connector(slide, (ix + iw, 2.74), (jx - 0.04, 2.74))
    connector(slide, (jx, 3.12), (ix + iw + 0.04, 3.12))

    # Rangée 2 : la sortie structurée, puis le recalcul déterministe.
    node(ix, 3.62, iw, "collect_proposal", "PlanPropose · Pydantic")
    node(jx, 3.62, iw, "resolve_recompute", "totaux re-dérivés")
    connector(slide, (7.95, 3.34), (7.95, 3.58))
    text(slide, Box(6.66, 3.37, 1.20, 0.20), "submit_plan",
         size=9, font=F_MONO, color=MUTED)
    connector(slide, (ix + iw, 3.98), (jx - 0.04, 3.98))

    # Rangée 3 : la vérification, sur toute la largeur.
    node(ix, 4.62, full_w, "validate_guardrails",
         "G1 cible ±10 %  ·  G2 exclusions  ·  G-exists")
    connector(slide, (10.94, 4.34), (10.94, 4.58))

    # --- Les quatre issues : le mécanisme d'escalade ------------------------ #
    outcomes = [("conforme", "plan affiché", ACCENT, WHITE, ON_ACCENT_SOFT),
                ("non conforme", "reprise, 2×", SURFACE, INK, MUTED),
                ("écart léger", "grammes ajustés", SURFACE, INK, MUTED),
                ("sinon", "dégradé visible", SURFACE, FLAG, MUTED)]
    ow, ogap = 1.30, 0.16
    for i, (head, sub, fill, head_color, sub_color) in enumerate(outcomes):
        x = ix + i * (ow + ogap)
        card(slide, Box(x, 5.62, ow, 0.68), fill=fill,
             border=None if fill is ACCENT else LINE)
        text(slide, Box(x + 0.08, 5.75, ow - 0.16, 0.25), head,
             size=11, bold=True, color=head_color, align=PP_ALIGN.CENTER)
        text(slide, Box(x + 0.08, 6.02, ow - 0.16, 0.24), sub,
             size=9, font=F_MONO, color=sub_color, align=PP_ALIGN.CENTER)
        connector(slide, (x + ow / 2, 5.34), (x + ow / 2, 5.58))

    # La 2e issue renvoie à l'agent : la boucle de garde-fous est fermée.
    retry_x = ix + 1 * (ow + ogap)
    connector(slide, (retry_x, 5.94), (6.45, 5.94), arrow=False)
    connector(slide, (6.45, 5.94), (6.45, 3.15), arrow=False)
    connector(slide, (6.45, 3.15), (6.56, 3.15))

    text(slide, Box(MARGIN, 6.62, 10.4, 0.26),
         "Adaptateur LLM unique · Gemini primaire, Groq en repli · "
         "bascule par variable d'environnement",
         size=11, font=F_MONO, color=MUTED)

    # --- Le message qui porte ---------------------------------------------- #
    card(slide, Box(0.75, 4.90, 5.15, 1.62), fill=ACCENT_SOFT, border=None)
    text(slide, Box(1.15, 5.10, 4.35, 0.24), "AVANT TOUT APPEL AU MODÈLE",
         size=10.5, font=F_MONO, color=ACCENT, bold=True, caps_spacing=1.6)
    text(slide, Box(1.15, 5.42, 4.35, 0.62),
         "La cible calorique est calculée en Python. Le modèle la reçoit, "
         "il ne la décide pas.",
         size=15.5, color=INK, line_spacing=1.35)
    text(slide, Box(1.15, 6.10, 4.35, 0.30),
         "BMR › ×1,2 › +MET › −500 max › plancher 1 200",
         size=10, font=F_MONO, color=ACCENT)

    notes(slide, """
Livrable explicitement exigé : composantes, interactions, flux de données.
Le document d'architecture détaillé sert de laissé-sur-table et de support pour
la partie technique de 25 minutes.

Suivre le flux du doigt, de gauche à droite :

1. Deux sources locales entrent : l'activité du jour (SQLite) et les
   préférences (JSON).
2. plan_generator calcule la cible calorique en Python : Mifflin-St Jeor, base
   sédentaire × 1,2, MET de l'activité du jour, déficit plafonné, plancher
   1 200 kcal. Insister : c'est une ENTRÉE du modèle, jamais une sortie.
3. Le cadre pointillé, c'est le graphe lui-même. Il porte le nom du fichier :
   core/agent/graph.py a exactement cette forme, ce n'est pas un dessin fait
   après coup.
4. agent ⇄ tools : la boucle d'appels d'outils, plafonnée à 15 tours. Au 16e,
   l'appel à submit_plan est forcé par tool_choice — le modèle ne peut pas
   boucler indéfiniment.
5. collect_proposal : la sortie du modèle est validée contre un schéma Pydantic
   (PlanPropose). Un plan mal formé n'entre jamais dans la suite du graphe.
6. resolve_recompute : chaque total est recalculé depuis l'USDA, jamais repris
   du modèle. Un fdc_id inventé est collecté ici, pas silencieusement ignoré.
7. validate_guardrails décide, et il n'y a que quatre issues : conforme, on
   affiche ; non conforme, l'agent reprend, deux fois maximum ; écart léger,
   les grammes sont rééchelonnés automatiquement ; sinon, le plan est affiché
   en mode dégradé AVEC l'avertissement à l'écran.

C'est le mécanisme d'escalade, et il est fermé : aucun chemin ne mène à un plan
non conforme affiché en silence.

Si on demande la sortie en erreur (rate_limited, timeout, api_error,
invalid_output) : elle part de agent et de collect_proposal, elle est volontai-
rement absente d'ici pour ne pas surcharger — elle est sur la diapositive
Robustesse.

Portabilité, à dire ici : un seul adaptateur LLM, Gemini en primaire, Groq en
repli, une variable d'environnement pour basculer. Azure OpenAI est un
changement de configuration, pas une réécriture. Cette phrase prépare le bloc
Microsoft de la fin.
""")
    return slide


def slide_08_gardefous(prs):
    slide = add_slide(prs)
    eyebrow(slide, "Garde-fous santé")
    title(slide, "Les règles de sécurité sont dans le code")

    items = [
        ("1", "Plancher de 1 200 kcal", "Déficit plafonné à 500 kcal."),
        ("2", "Aliments non aimés", "Retirés en Python, pas par le modèle."),
        ("3", "Totaux recalculés", "Reconstruits depuis l'USDA."),
        ("4", "Avis médical", "Disclaimer sous chaque plan."),
    ]
    cols = columns(2, gap=0.4)
    rows = [2.35, 4.35]
    for i, (num, head, body) in enumerate(items):
        x, w = cols[i % 2]
        y = rows[i // 2]
        card(slide, Box(x, y, w, 1.75))
        badge(slide, x + 0.42, y + 0.42, num)
        text(slide, Box(x + 1.02, y + 0.45, w - 1.44, 0.4), head,
             size=18, font=F_DISPLAY, color=INK, bold=True)
        text(slide, Box(x + 1.02, y + 1.0, w - 1.44, 0.5), body,
             size=14.5, color=INK_SOFT, line_spacing=1.35)

    text(slide, Box(MARGIN, 6.35, CONTENT_W, 0.28),
         "Neuf au total (G1–G8 + vérification d'existence des aliments). "
         "Les quatre ci-dessus sont ceux qui modifient le plan affiché.",
         size=12, color=MUTED)

    notes(slide, """
Il y en a neuf. N'en dire que quatre : les dix prennent trois minutes et noient
les plus forts.

Détail de chacun :
1. Le déficit ne dépasse jamais 500 kcal ni 25 % de la dépense quotidienne, et
   le plancher de 1 200 kcal ne cède pas.
2. L'application retire elle-même les aliments non aimés ; elle ne demande pas
   au modèle de le faire à sa place.
3. Chaque total est reconstruit à partir des données USDA, aliment par aliment.
4. La mention de non-responsabilité apparaît sous chaque plan, et le modèle la
   reçoit aussi dans ses consignes.

En réserve pour les questions : bornes de plausibilité sur les entrées,
assainissement des préférences avant le prompt, profil non transmis au LLM,
cache USDA, deux tentatives maximum, signalement d'un plan non conforme.
""")
    return slide


def slide_09_robustesse(prs):
    slide = add_slide(prs)
    eyebrow(slide, "Robustesse")
    title(slide, "Ce qui tient quand quelque chose échoue")

    items = [
        ("Erreurs API",
         [{"text": "Quatre codes explicites, aucune exception levée."},
          {"text": "not_found · rate_limited · timeout · api_error",
           "font": F_MONO, "size": 11.5, "color": MUTED, "space_before": 3}]),
        ("Aliments introuvables", "Rejetés, jamais ignorés."),
        ("Entrées utilisateur", "Validées et bornées."),
    ]
    y = 2.35
    for head, body in items:
        card(slide, Box(MARGIN, y, 6.75, 1.15))
        text(slide, Box(MARGIN + 0.42, y + 0.22, 5.9, 0.32), head,
             size=16, bold=True, color=INK)
        text(slide, Box(MARGIN + 0.42, y + 0.6, 5.9, 0.46), body,
             size=14, color=INK_SOFT)
        y += 1.30

    right = Box(7.95, 2.35, 4.63, 2.75)
    card(slide, right, fill=ACCENT, border=None)
    text(slide, Box(right.x + 0.45, right.y + 0.45, right.w - 0.9, 0.26),
         "VOTRE CONTRAINTE", size=10.5, font=F_MONO, color=ON_ACCENT_SOFT,
         bold=True, caps_spacing=1.6)
    text(slide, Box(right.x + 0.45, right.y + 0.9, right.w - 0.9, 0.8),
         "1 000 requêtes / heure",
         size=23, font=F_DISPLAY, color=WHITE, bold=True, line_spacing=1.1)
    text(slide, Box(right.x + 0.45, right.y + 1.85, right.w - 0.9, 0.6),
         "Cache local des appels USDA.",
         size=15, color=ON_ACCENT_SOFT)

    text(slide, Box(MARGIN, 5.95, CONTENT_W, 0.4),
         "Le profil de santé de vos employés n'est jamais transmis au modèle.",
         size=16, color=INK, bold=True)

    notes(slide, """
Les requis font deux catégories distinctes : garde-fous = sécurité santé,
robustesse = erreurs API, aliments introuvables, validation des entrées.
Les présenter séparément fait cocher deux cases au lieu d'une.

Détail :
- Quatre codes d'erreur explicites (not_found, rate_limited, timeout,
  api_error) ; les outils ne lèvent jamais d'exception vers l'agent.
- Si le modèle invente un identifiant d'aliment, l'application le rejette au
  lieu de l'ignorer : un plan faux ne doit pas avoir l'air conforme.
- Bornes de plausibilité sur l'âge, le poids, la grandeur ; préférences
  nettoyées avant d'entrer dans le prompt.

Le cache n'est pas un détail d'implémentation, c'est la réponse à une
contrainte que le client a écrite lui-même dans l'énoncé.
""")
    return slide


def slide_10_risques(prs):
    slide = add_slide(prs)
    eyebrow(slide, "Lucidité")
    title(slide, "Les risques, et ce qu'on en a fait")

    c1, c2, c3 = 0.75, 4.15, 8.75
    w1, w2, w3 = 3.10, 4.30, 3.833

    heads = [(c1, w1, "RISQUE", FLAG), (c2, w2, "CE QU'ON A FAIT", ACCENT),
             (c3, w3, "EN PRODUCTION", MUTED)]
    for x, w, label, tint in heads:
        text(slide, Box(x + 0.30, 2.20, w - 0.6, 0.24), label,
             size=10.5, font=F_MONO, color=tint, bold=True, caps_spacing=1.6)

    rows = [
        ("Diabète, grossesse, TCA",
         "Avis de non-responsabilité sous chaque plan, et dans les consignes "
         "données au modèle.",
         "Dépistage à l'inscription, escalade vers un professionnel."),
        ("Métabolisme estimé sans le sexe biologique",
         "Constante neutre : écart de ± 83 kcal, sous la marge d'erreur de la "
         "formule elle-même.",
         "Champ optionnel, avec consentement explicite."),
        ("Le modèle peut se tromper",
         "Aucun chiffre du modèle n'atteint l'écran : totaux recalculés, mode "
         "dégradé visible.",
         "Journalisation des écarts, revue humaine sur échantillon."),
        ("Activité non répertoriée",
         "MET générique selon l'intensité, et l'application le dit à l'écran.",
         "Référentiel élargi, calendrier modifiable par l'employé."),
    ]

    y = 2.58
    for risk, done, next_step in rows:
        card(slide, Box(MARGIN, y, CONTENT_W, 0.85))
        text(slide, Box(c1 + 0.30, y + 0.18, w1 - 0.60, 0.52), risk,
             size=13.5, bold=True, color=INK, line_spacing=1.3)
        text(slide, Box(c2 + 0.20, y + 0.18, w2 - 0.40, 0.52), done,
             size=13, color=INK_SOFT, line_spacing=1.3)
        text(slide, Box(c3 + 0.20, y + 0.18, w3 - 0.40, 0.52), next_step,
             size=13, color=MUTED, line_spacing=1.3)
        y += 0.94

    text(slide, Box(MARGIN, 6.42, CONTENT_W, 0.3),
         "Limites assumées du prototype : quatre macronutriments, base "
         "sédentaire fixe à × 1,2, un seul utilisateur.",
         size=12.5, color=MUTED)

    notes(slide, """
Les requis demandent d'identifier ET de justifier les risques. Justifier veut
dire deux choses : pourquoi on l'a accepté, et ce qu'on ferait en production.
D'où les trois colonnes — c'est un registre de risques, pas une liste de
regrets.

Ne pas lire les douze cases. Prendre la ligne 1 et la ligne 3, et dire :

« Le risque le plus sérieux, c'est la personne diabétique ou enceinte. Le
prototype ne la dépiste pas ; l'avis de non-responsabilité couvre, mais en
production ce cas doit être escaladé vers un professionnel, pas absorbé par
l'agent. »

« Le risque le plus prévisible, c'est que le modèle se trompe. C'est celui
qu'on a fermé : aucun chiffre venant du modèle n'atteint l'écran. »

Les limites du prototype sont en bas de page, en petit, volontairement : elles
sont des choix de périmètre, pas des angles morts.

Réserve pour les 25 minutes : pourquoi LangGraph plutôt qu'une chaîne (la
vérification doit pouvoir renvoyer à l'agent), pourquoi Mifflin-St Jeor
(constantes citées dans core/nutrition/constants.py), comment c'est testé
(pytest sur nutrition, garde-fous, graphe, client USDA), le passage vers Azure,
la péremption du cache.
""")
    return slide


def slide_11_cloture(prs):
    slide = add_slide(prs, bg=ACCENT)

    text(slide, Box(MARGIN + 0.80, 1.15, 10.0, 0.26), "CE QUI RESTE",
         size=10.5, font=F_MONO, color=ON_ACCENT_SOFT, bold=True,
         caps_spacing=1.6)
    text(slide, Box(MARGIN + 0.80, 1.60, 10.4, 1.4),
         [{"text": "Un agent qui compose librement,"},
          {"text": "dans des limites qu'il ne peut pas franchir.",
           "space_before": 6}],
         size=33, font=F_DISPLAY, color=WHITE, bold=True, line_spacing=1.14)

    stats = [("3 sources", "orchestrées à chaque génération"),
             ("9 garde-fous", "écrits en code, pas en prompt"),
             ("0 chiffre", "du modèle affiché à l'écran")]
    for (x, w), (value, label) in zip(columns(3), stats):
        card(slide, Box(x, 3.55, w, 1.45), fill=SURFACE, border=None)
        text(slide, Box(x + 0.42, 3.88, w - 0.84, 0.55), value,
             size=27, font=F_DISPLAY, color=ACCENT, bold=True,
             line_spacing=1.0)
        text(slide, Box(x + 0.42, 4.50, w - 0.84, 0.32), label,
             size=13, color=INK_SOFT)

    text(slide, Box(MARGIN + 0.80, 5.42, 10.4, 0.26), "LA SUITE",
         size=10.5, font=F_MONO, color=ON_ACCENT_SOFT, bold=True,
         caps_spacing=1.6)
    text(slide, Box(MARGIN + 0.80, 5.78, 10.6, 0.4),
         "Pilote sur un groupe  ·  validation humaine dans le graphe  ·  "
         "bascule vers Azure OpenAI par variable d'environnement",
         size=15, color=WHITE)

    text(slide, Box(MARGIN + 0.80, 6.60, 10.6, 0.32),
         "Melody Nadeau  ·  Vos questions",
         size=13.5, color=ON_ACCENT_SOFT)

    notes(slide, """
Diapositive de clôture, 20 secondes. Ne pas la lire mot à mot.

La phrase du haut est celle qu'on veut qu'ils retiennent : le modèle est libre
de composer, mais il est enfermé dans des limites qu'il ne peut pas franchir.
C'est ça, la valeur : ce n'est pas « une IA qui fait des menus », c'est une IA
sur laquelle le client peut mettre son nom.

Les trois chiffres se disent à voix haute, dans cet ordre, en s'arrêtant sur le
dernier : « zéro chiffre venant du modèle n'est affiché à l'écran ».

« La suite » existe pour montrer qu'on sait ce que la mise en production
demande — et la mention Azure OpenAI ouvre volontairement le bloc Microsoft de
la fin de l'entrevue.

Terminer à 10:00 pile. Le respect du temps fait partie de l'évaluation.
Enchaîner : « Je peux entrer dans le code quand vous voulez. »
""")
    return slide


# --------------------------------------------------------------------------- #

# Diapositives sur fond ACCENT : le numéro de page y prend une teinte claire.
BUILDERS = [
    slide_01_cover, slide_02_besoin, slide_03_promesse, slide_04_sources,
    slide_05_principe, slide_06_profil, slide_07_architecture,
    slide_08_gardefous, slide_09_robustesse, slide_10_risques,
    slide_11_cloture,
]

# Diapositives sur fond ACCENT : le numéro de page y prend une teinte claire.
ACCENT_BG_SLIDES = (slide_05_principe, slide_11_cloture)


def build(out_path: Path) -> Path:
    prs = new_deck()
    for number, builder in enumerate(BUILDERS, start=1):
        slide = builder(prs)
        if number > 1:                      # pas de numéro sur la couverture
            page_number(slide, number,
                        color=ON_ACCENT_SOFT
                        if builder in ACCENT_BG_SLIDES else MUTED)
    prs.core_properties.title = "Agent Meal Prep — présentation client"
    prs.core_properties.author = "Melody Nadeau"
    prs.save(str(out_path))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output",
                        default="Agent_Meal_Prep_presentation.pptx")
    args = parser.parse_args()
    path = build(Path(args.output).resolve())
    print(f"Écrit : {path}")


if __name__ == "__main__":
    main()
