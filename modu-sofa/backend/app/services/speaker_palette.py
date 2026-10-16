PALETTE = [
    "#B0124F",
    "#1D4ED8",
    "#15803D",
    "#A04A06",
    "#6D28D9",
    "#0E7490",
    "#B91C1C",
    "#4D7C0F",
    "#9D174D",
    "#1E40AF",
]


def color_for(index: int) -> str:
    return PALETTE[index % len(PALETTE)]


def code_for(index: int) -> str:
    return f"SPEAKER_{index + 1:02d}"
