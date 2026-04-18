"""
src/font_groups.py
------------------
Thematic grouping of fonts for Symbol Mosaic rendering.

Each font file in assets/fonts/ is assigned to exactly ONE group.
Groups were chosen based on visual family, not just language:
  A = CJK scripts (dense, rhythmic tiles — good for portraits)
  B = Ancient & Exotic scripts (hieroglyphs, cuneiform, runes — "manuscript" aesthetic)
  C = Symbols & Geometric (math, arrows, piktograms — abstract mosaics)
  D = Latin Clean (sans/serif, also Monospace — readable, "editorial")
  E = Decorative / Display (horror, comic, vintage — "poster" effect)
  F = Handwriting / Script (calligraphy, casual — romantic aesthetic)

The filter is applied in TypoEngine.__init__() based on the groups
selected in the GUI. Files not listed here are silently skipped
(allows adding new fonts without breaking the app).
"""

FONT_GROUPS = {
    "A_cjk": [
        "NotoSansJP-Regular.ttf",
        "NotoSerifJP-Regular.ttf",
        "NotoSansSC-Regular.ttf",
        "NotoSerifSC-Regular.ttf",
        "NotoSerifTC-Regular.ttf",
        "NotoSerifKR-Regular.ttf",
        "SawarabiMincho-Regular.ttf",
        "ShipporiMinchoB1-Regular.ttf",
        "NanumMyeongjo-Regular.ttf",
        "YujiBoku-Regular.ttf",
        "YujiHentaiganaAkebono-Regular.ttf",
        "Chokokutai-Regular.ttf",
        "MPLUS1p-Regular.ttf",
    ],
    "B_ancient": [
        "NotoSansEgyptianHieroglyphs-Regular.ttf",
        "NotoSansAnatolianHieroglyphs-Regular.ttf",
        "NotoSansCuneiform-Regular.ttf",
        "NotoSansPhoenician-Regular.ttf",
        "NotoSansOldPersian-Regular.ttf",
        "NotoSansOldNorthArabian-Regular.ttf",
        "NotoSansLinearA-Regular.ttf",
        "NotoSansLinearB-Regular.ttf",
        "NotoSansCarian-Regular.ttf",
        "NotoSansCypriot-Regular.ttf",
        "NotoSansMeroitic-Regular.ttf",
        "NotoSansUgaritic-Regular.ttf",
        "NotoSansRunic-Regular.ttf",
        "NotoSansBhaiksuki-Regular.ttf",
        "NotoSansVai-Regular.ttf",
        "NotoSansBamum-Regular.ttf",
        "NotoSansBatak-Regular.ttf",
        "NotoSansBuginese-Regular.ttf",
        "NotoSansLimbu-Regular.ttf",
        "NotoSansNushu-Regular.ttf",
        "NotoSansOlChiki-Regular.ttf",
        "NotoSansRejang-Regular.ttf",
        "NotoSansThaana-Regular.ttf",
        "NotoSansSyriacWestern-Regular.ttf",
        # Ogham, Deseret, Shavian — pobrane jako część rodziny Noto
        "NotoSansOgham-Regular.ttf",
        "NotoSansDeseret-Regular.ttf",
        "NotoSansShavian-Regular.ttf",
    ],
    "C_symbols": [
        "NotoSansMath-Regular.ttf",
        "NotoSansSymbols-Regular.ttf",
        "NotoSansSymbols2-Regular.ttf",
        "NotoEmoji-Regular.ttf",
        "NotoMusic-Regular.ttf",
        "NotoSansMayanNumerals-Regular.ttf",
        "Yarndings12Charted-Regular.ttf",
        "Yarndings20-Regular.ttf",
        "Yarndings20Charted-Regular.ttf",
    ],
    "D_latin_clean": [
        "NotoSans-Regular.ttf",
        "NotoSans_Condensed-Regular.ttf",
        "NotoSans_ExtraCondensed-Regular.ttf",
        "NotoSans_SemiCondensed-Regular.ttf",
        "AbhayaLibre-Regular.ttf",
        "FrankRuhlLibre-Regular.ttf",
        "Amiri-Regular.ttf",
        "Almarai-Regular.ttf",
        "Tajawal-Regular.ttf",
        "ReemKufi-Regular.ttf",
        "Krub-Regular.ttf",
        "Niramit-Regular.ttf",
        "Itim-Regular.ttf",
        # Monospace fonts (Piotr requested).
        # IBM Plex Mono: full weight family (Thin → Bold) + Italics.
        # All variants in one group — they're the same visual family,
        # different weights give the matcher finer density granularity.
        "IBMPlexMono-Thin.ttf",
        "IBMPlexMono-ThinItalic.ttf",
        "IBMPlexMono-ExtraLight.ttf",
        "IBMPlexMono-ExtraLightItalic.ttf",
        "IBMPlexMono-Light.ttf",
        "IBMPlexMono-LightItalic.ttf",
        "IBMPlexMono-Regular.ttf",
        "IBMPlexMono-Italic.ttf",
        "IBMPlexMono-Medium.ttf",
        "IBMPlexMono-MediumItalic.ttf",
        "IBMPlexMono-SemiBold.ttf",
        "IBMPlexMono-SemiBoldItalic.ttf",
        "IBMPlexMono-Bold.ttf",
        "IBMPlexMono-BoldItalic.ttf",
        # JetBrains Mono and Inconsolata: variable fonts (single file, all weights).
        "JetBrainsMono-VariableFont_wght.ttf",
        "Inconsolata-VariableFont_wdth,wght.ttf",
        "SpaceMono-Regular.ttf",
    ],
    "E_decorative": [
        "Creepster-Regular.ttf",
        "Eater-Regular.ttf",
        "Monoton-Regular.ttf",
        "Matemasie-Regular.ttf",
        "Danfo-Regular-VariableFont_ELSH.ttf",
        "Ole-Regular.ttf",
        "Splash-Regular.ttf",
        "Rubik80sFade-Regular.ttf",
        "RubikPuddles-Regular.ttf",
        "AreYouSerious-Regular.ttf",
        "BitcountPropDouble-Regular.ttf",
        "BitcountPropDouble_Cursive-Regular.ttf",
        "BitcountPropDouble_Roman-Regular.ttf",
        "EduAUVICWANTDots-Regular.ttf",
    ],
    "F_handwriting": [
        "AguafinaScript-Regular.ttf",
        "Allura-Regular.ttf",
        "DancingScript-Regular.ttf",
        "LoveLight-Regular.ttf",
        "MrDafoe-Regular.ttf",
        "NothingYouCouldDo-Regular.ttf",
        "PinyonScript-Regular.ttf",
        "ReenieBeanie-Regular.ttf",
        "RockSalt-Regular.ttf",
        "RugeBoogie-Regular.ttf",
        "Sacramento-Regular.ttf",
        "Tangerine-Regular.ttf",
        "Zeyada-Regular.ttf",
        "NanumPenScript-Regular.ttf",
        "Amita-Regular.ttf",
    ],
    # Fallback — also used for NotoSerifSinhala family which doesn't fit elsewhere
    "G_uncategorized": [
        "NotoSerifSinhala-Regular.ttf",
        "NotoSerifSinhala_Condensed-Regular.ttf",
        "NotoSerifSinhala_ExtraCondensed-Regular.ttf",
        "NotoSerifSinhala_SemiCondensed-Regular.ttf",
        "NotoSansArabic-Regular.ttf",
        "NotoSansArabic_Condensed-Regular.ttf",
        "NotoSansArabic_ExtraCondensed-Regular.ttf",
        "NotoSansArabic_SemiCondensed-Regular.ttf",
        "NotoSansBengali-Regular.ttf",
        "NotoSansBengali_Condensed-Regular.ttf",
        "NotoSansBengali_ExtraCondensed-Regular.ttf",
        "NotoSansBengali_SemiCondensed-Regular.ttf",
    ],
}

# Human-readable labels for GUI
GROUP_LABELS = {
    "A_cjk":           "CJK (Chinese/Japanese/Korean)",
    "B_ancient":       "Ancient & Exotic Scripts",
    "C_symbols":       "Symbols & Geometric",
    "D_latin_clean":   "Latin Clean (Sans/Serif/Mono)",
    "E_decorative":    "Decorative / Display",
    "F_handwriting":   "Handwriting / Script",
    "G_uncategorized": "Other (Arabic, Bengali, Sinhala)",
}


def get_font_group(font_filename: str) -> str | None:
    """Return the group key for a given font filename, or None if unmapped."""
    for group_key, files in FONT_GROUPS.items():
        if font_filename in files:
            return group_key
    return None


def get_fonts_for_groups(selected_groups: list[str]) -> set[str]:
    """Return a set of font filenames belonging to any of the selected groups.

    If selected_groups is empty or contains "all", return all mapped fonts.
    """
    if not selected_groups or "all" in selected_groups:
        all_fonts = set()
        for files in FONT_GROUPS.values():
            all_fonts.update(files)
        return all_fonts

    result = set()
    for group_key in selected_groups:
        if group_key in FONT_GROUPS:
            result.update(FONT_GROUPS[group_key])
    return result
