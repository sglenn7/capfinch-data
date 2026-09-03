"""Render the CapFinch ERD to a standalone SVG.

Usage:
    python render_erd.py [-o erd.svg]

Writes a self-contained SVG with no external dependencies, so it can be pasted
straight into Slides, Docs, Figma, or a README. Keep the schema below in sync
with the data dictionary in README.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

# ---- Layout constants ----
COL_W = 320
ROW_H = 19
HEADER_H = 30
SECTION_H = 17
PAD_X = 12
PORT_GAP = 22          # vertical spacing when several edges share one side
OUTER_X = 1290         # right edge for the drawing canvas
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
LABEL_FONT = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"

INK = "#1f2933"
MUTED = "#7b8794"
LINE = "#9aa5b1"
NULLABLE = "#b44d12"
FACT_FILL = "#e8f0fe"
FACT_STROKE = "#4a7fd4"
DIM_FILL = "#eaf4ec"
DIM_STROKE = "#4f9d69"
LOG_FILL = "#f5eef8"
LOG_STROKE = "#9b6bb0"

# (name, type, key, nullable) — key is "PK", "FK", or ""
TABLES = {
    "customers": {
        "kind": "dim",
        "at": (40, 70),
        "subtitle": "one row per identifiable person",
        "fields": [
            ("customer_id", "string", "PK", False),
            ("email", "string", "", False),
            ("birthdate", "date", "", True),
            ("age", "int", "", True),
            ("age_band", "string", "", True),
            ("gender", "string", "", False),
            ("address_line1", "string", "", False),
            ("address_line2", "string", "", True),
            ("city", "string", "", False),
            ("state", "string", "", False),
            ("zip", "string", "", False),
            ("signup_date", "date", "", False),
            ("acquisition_source", "string", "", False),
            ("first_order_date", "date", "", True),
            ("total_orders", "int", "", False),
        ],
    },
    "sessions": {
        "kind": "log",
        "at": (500, 70),
        "subtitle": "website visits (online only)",
        "fields": [
            ("session_id", "string", "PK", False),
            ("customer_id", "string", "FK", True),
            ("session_start", "timestamp", "", False),
            ("device", "string", "", False),
            ("traffic_source", "string", "", False),
            ("landing_page", "string", "", False),
            ("reached_cart", "bool", "", False),
            ("converted", "bool", "", False),
        ],
    },
    "orders": {
        "kind": "fact",
        "at": (500, 330),
        "subtitle": "one row per sale, both channels",
        "sections": [
            ("shared", [
                ("transaction_id", "string", "PK", False),
                ("customer_id", "string", "FK", True),
                ("channel", "string", "", False),
                ("order_datetime", "timestamp", "", False),
                ("order_date", "date", "", False),
                ("day_of_week", "string", "", False),
                ("hour_of_day", "int", "", False),
                ("subtotal", "decimal", "", False),
                ("discount_amount", "decimal", "", False),
                ("order_total", "decimal", "", False),
                ("item_count", "int", "", False),
                ("payment_method", "string", "", False),
                ("payment_status", "string", "", False),
            ]),
            ("online only", [
                ("session_id", "string", "FK", True),
                ("shipping_address_line1", "string", "", True),
                ("shipping_address_line2", "string", "", True),
                ("shipping_city", "string", "", True),
                ("shipping_state", "string", "", True),
                ("shipping_zip", "string", "", True),
                ("is_gift_ship", "bool", "", True),
                ("shipping_fee", "decimal", "", True),
                ("fulfillment_type", "string", "", True),
                ("promo_code", "string", "", True),
                ("device", "string", "", True),
            ]),
            ("in-store only", [
                ("register_id", "string", "", True),
                ("employee_id", "string", "", True),
                ("entry_method", "string", "", True),
                ("tip_amount", "decimal", "", True),
                ("receipt_type", "string", "", True),
            ]),
        ],
    },
    "order_items": {
        "kind": "fact",
        "at": (960, 330),
        "subtitle": "one row per product per order",
        "fields": [
            ("order_item_id", "string", "PK", False),
            ("transaction_id", "string", "FK", False),
            ("product_id", "string", "FK", False),
            ("quantity", "int", "", False),
            ("unit_price", "decimal", "", False),
            ("line_total", "decimal", "", False),
        ],
    },
    "products": {
        "kind": "dim",
        "at": (960, 560),
        "subtitle": "the catalog, one row per SKU",
        "fields": [
            ("product_id", "string", "PK", False),
            ("product_name", "string", "", False),
            ("category", "string", "", False),
            ("subcategory", "string", "", False),
            ("price", "decimal", "", False),
            ("price_band", "string", "", False),
            ("cost", "decimal", "", False),
            ("stock_on_hand", "int", "", False),
        ],
    },
}

# src, side, port, dst, side, port, cardinality at each end, label, route style
EDGES = [
    ("customers", "right", 0, "sessions", "left", 0, "0..1", "0..N", "browses", "hv"),
    ("customers", "right", 1, "orders", "left", 0, "0..1", "0..N", "places", "hv"),
    ("sessions", "bottom", 0, "orders", "top", 0, "1", "0..1", "converts into", "vh"),
    ("orders", "right", 0, "order_items", "left", 0, "1", "1..N", "contains", "hv"),
    ("products", "top", 0, "order_items", "bottom", 0, "1", "0..N", "sold as", "vh"),
]

PALETTE = {
    "fact": (FACT_FILL, FACT_STROKE),
    "dim": (DIM_FILL, DIM_STROKE),
    "log": (LOG_FILL, LOG_STROKE),
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rows_of(table: dict) -> list:
    """Flatten a table into drawable rows: ('section', name) or ('field', tuple)."""
    if "sections" in table:
        out = []
        for title, fields in table["sections"]:
            out.append(("section", title))
            out.extend(("field", f) for f in fields)
        return out
    return [("field", f) for f in table["fields"]]


def table_height(table: dict) -> int:
    h = HEADER_H
    for kind, _ in rows_of(table):
        h += SECTION_H if kind == "section" else ROW_H
    return h + 8


def anchor(name: str, side: str, port: int = 0) -> tuple[float, float]:
    x, y = TABLES[name]["at"]
    h = table_height(TABLES[name])
    if side in ("left", "right"):
        return (x if side == "left" else x + COL_W), y + HEADER_H + 14 + port * PORT_GAP
    return x + COL_W / 2 + port * PORT_GAP, (y if side == "top" else y + h)


def card_pos(x: float, y: float, side: str) -> tuple[float, float]:
    if side == "right":
        return x + 20, y - 7
    if side == "left":
        return x - 20, y - 7
    if side == "top":
        return x, y - 9
    return x, y + 17


def draw_table(name: str, table: dict) -> list[str]:
    x, y = table["at"]
    fill, stroke = PALETTE[table["kind"]]
    h = table_height(table)
    out = [
        f'<rect x="{x}" y="{y}" width="{COL_W}" height="{h}" rx="8" '
        f'fill="#ffffff" stroke="{stroke}" stroke-width="1.5"/>',
        f'<path d="M{x} {y + 8} a8 8 0 0 1 8 -8 h{COL_W - 16} a8 8 0 0 1 8 8 v{HEADER_H - 8} h-{COL_W} z" '
        f'fill="{fill}"/>',
        f'<text x="{x + PAD_X}" y="{y + 20}" font-family="{LABEL_FONT}" font-size="14" '
        f'font-weight="700" fill="{INK}">{esc(name)}</text>',
        f'<text x="{x + COL_W - PAD_X}" y="{y + 20}" font-family="{LABEL_FONT}" font-size="9.5" '
        f'text-anchor="end" fill="{MUTED}">{esc(table["subtitle"])}</text>',
        f'<line x1="{x}" y1="{y + HEADER_H}" x2="{x + COL_W}" y2="{y + HEADER_H}" '
        f'stroke="{stroke}" stroke-width="1.5"/>',
    ]

    cy = y + HEADER_H
    for kind, item in rows_of(table):
        if kind == "section":
            cy += SECTION_H
            out.append(
                f'<rect x="{x + 1}" y="{cy - SECTION_H + 3}" width="{COL_W - 2}" height="{SECTION_H - 2}" '
                f'fill="#f4f6f8"/>'
            )
            out.append(
                f'<text x="{x + PAD_X}" y="{cy - 3}" font-family="{LABEL_FONT}" font-size="9.5" '
                f'font-weight="600" letter-spacing="0.6" fill="{MUTED}">{esc(item.upper())}</text>'
            )
            continue

        fname, ftype, key, nullable = item
        cy += ROW_H
        colour = NULLABLE if nullable else INK
        weight = "700" if key else "400"
        out.append(
            f'<text x="{x + PAD_X}" y="{cy - 5}" font-family="{FONT}" font-size="11" '
            f'font-weight="{weight}" fill="{colour}">{esc(fname)}</text>'
        )
        out.append(
            f'<text x="{x + COL_W - PAD_X - 24}" y="{cy - 5}" font-family="{FONT}" font-size="10" '
            f'text-anchor="end" fill="{MUTED}">{esc(ftype)}</text>'
        )
        if key:
            badge = "#3b6fb0" if key == "PK" else "#8a6d3b"
            out.append(
                f'<text x="{x + COL_W - PAD_X}" y="{cy - 5}" font-family="{LABEL_FONT}" font-size="9" '
                f'font-weight="700" text-anchor="end" fill="{badge}">{key}</text>'
            )
    return out


def draw_edge(edge) -> list[str]:
    src, s_side, s_port, dst, d_side, d_port, s_card, d_card, label, route = edge
    x1, y1 = anchor(src, s_side, s_port)
    x2, y2 = anchor(dst, d_side, d_port)

    if route == "hv":
        mid = (x1 + x2) / 2
        path = f"M{x1} {y1} H{mid} V{y2} H{x2}"
        lx, ly, at = mid, min(y1, y2) - 9, "middle"
    elif route == "vh":
        mid = (y1 + y2) / 2
        path = f"M{x1} {y1} V{mid} H{x2} V{y2}"
        lx, ly, at = (x1 + x2) / 2, mid - 5, "middle"
    else:  # route around the right-hand column
        path = f"M{x1} {y1} H{OUTER_X} V{y2} H{x2}"
        lx, ly, at = OUTER_X + 8, (y1 + y2) / 2, "start"

    cx1, cy1 = card_pos(x1, y1, s_side)
    cx2, cy2 = card_pos(x2, y2, d_side)

    return [
        f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="1.4"/>',
        f'<circle cx="{x1}" cy="{y1}" r="3" fill="{LINE}"/>',
        f'<circle cx="{x2}" cy="{y2}" r="3" fill="{LINE}"/>',
        f'<text x="{cx1}" y="{cy1}" font-family="{LABEL_FONT}" font-size="10" font-weight="600" '
        f'fill="{INK}" text-anchor="middle">{s_card}</text>',
        f'<text x="{cx2}" y="{cy2}" font-family="{LABEL_FONT}" font-size="10" font-weight="600" '
        f'fill="{INK}" text-anchor="middle">{d_card}</text>',
        f'<text x="{lx}" y="{ly}" font-family="{LABEL_FONT}" font-size="10" fill="{MUTED}" '
        f'text-anchor="{at}">{esc(label)}</text>',
    ]


def build_svg() -> str:
    width = OUTER_X + 130
    height = max(t["at"][1] + table_height(t) for t in TABLES.values()) + 110

    body: list[str] = [
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="40" y="40" font-family="{LABEL_FONT}" font-size="21" font-weight="700" '
        f'fill="{INK}">CapFinch synthetic dataset &#8212; entity relationship diagram</text>',
    ]

    for edge in EDGES:
        body += draw_edge(edge)
    for name, table in TABLES.items():
        body += draw_table(name, table)

    ly = height - 62
    body += [
        f'<text x="40" y="{ly}" font-family="{LABEL_FONT}" font-size="11.5" fill="{MUTED}">'
        f'Cardinality is read at each line end. <tspan fill="{NULLABLE}" font-weight="600">Orange</tspan> '
        f'fields are nullable. Note <tspan font-weight="600">customer_id</tspan> on orders: ~68% of in-store '
        f'and ~12% of online orders have none, so an inner join to customers drops most in-store revenue.</text>',
        f'<text x="40" y="{ly + 18}" font-family="{LABEL_FONT}" font-size="11.5" fill="{MUTED}">'
        f'Shipping fields on orders are a snapshot taken at order time, not a join to the customer&#8217;s '
        f'current address. Sessions exist for online activity only.</text>',
    ]

    for i, (kind, text) in enumerate([("dim", "dimension"), ("fact", "fact"), ("log", "web log")]):
        fill, stroke = PALETTE[kind]
        lx = 40 + i * 110
        body += [
            f'<rect x="{lx}" y="{ly + 28}" width="14" height="12" rx="3" fill="{fill}" stroke="{stroke}"/>',
            f'<text x="{lx + 20}" y="{ly + 38}" font-family="{LABEL_FONT}" font-size="11" '
            f'fill="{MUTED}">{text}</text>',
        ]

    inner = "\n  ".join(body)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n  {inner}\n</svg>\n'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default="erd.svg", help="output path (default: erd.svg)")
    args = parser.parse_args()

    path = Path(args.output)
    path.write_text(build_svg(), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
