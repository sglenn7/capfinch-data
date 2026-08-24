# CapFinch Data Dictionary

## Introduction

CapFinch is a boutique retail store with a physical location. Today it runs on a Square POS
system and Mailchimp email marketing, and it is launching its **first** e-commerce website with
**no** historical online data. To build and test the analytics/KPI pipeline before launch, we
generate a **synthetic dataset** that imitates what real online-platform data (Shopify / Square
Online / GA4 style) would look like once the site is live.

The dataset is organized around two anchor keys:

- **`transaction_id`** — primary key of `orders`; one row per completed sale (revenue, AOV).
- **`customer_id`** — primary key of `customers`; one row per person (repeat rate, demographics).

These join together via `customer_id`, which is a foreign key inside `orders`. This lets us
analyze the data both per-sale and per-customer.

**Relationship chain**

```
customers ─┬─ sessions ── events
           └─ orders ── order_items ── products
```

---

## Table 1: `customers`

**Purpose:** The people dimension. One row per unique customer (the "who"). Square Customer
Directory equivalent. Anchor for per-person KPIs like repeat purchase rate, age band, and
location. Every order links back to one row here.

| Field | Type | Key | Description | Example |
|---|---|---|---|---|
| `customer_id` | string | PK | Unique, stable ID for one person; reused across all their orders and sessions | `CUST_00042` |
| `email` | string | | Contact address; join key to Mailchimp audience data | `a***@gmail.com` |
| `age` | int | | Customer age in years at signup | `31` |
| `age_band` | string | | Pre-bucketed age group (18-24 / 25-34 / 35-44 / 45+) | `25-34` |
| `gender` | string | | Self-reported gender; optional demographic slice | `F` |
| `state` | string | | Two-letter US state; used for Sales by Location | `VA` |
| `zip` | string | | Postal code; finer location grain than state | `23219` |
| `signup_date` | date | | When the account/email was first created; cohort anchor | `2026-01-15` |
| `acquisition_source` | string | | How the customer first arrived (organic / mailchimp / social / referral) | `mailchimp` |
| `first_order_date` | date | | Date of first purchase; null if never bought | `2026-01-20` |
| `total_orders` | int | | Lifetime completed-order count; ≥2 flags a repeat buyer | `3` |

---

## Table 2: `orders`

**Purpose:** The transaction fact table (the "what was bought, when, for how much"). One row per
completed purchase. Square Payments/Orders equivalent. Source for revenue, AOV, and daily sales.
Header-level only; itemized detail lives in `order_items`.

| Field | Type | Key | Description | Example |
|---|---|---|---|---|
| `transaction_id` | string | PK | Unique ID for one completed order | `TXN_000578` |
| `customer_id` | string | FK → customers | Which customer placed the order | `CUST_00042` |
| `session_id` | string | FK → sessions | Which website visit produced this order | `SESS_09912` |
| `order_date` | timestamp | | Date/time the order was placed; grain for daily KPIs | `2026-03-04 14:22` |
| `order_total` | decimal | | Total order value; equals sum of `order_items.line_total` minus discount | `84.50` |
| `item_count` | int | | Number of units in the order | `2` |
| `payment_method` | string | | Tender type (card / apple_pay / paypal) | `card` |
| `payment_status` | string | | Processor result (authorized / declined); feeds Payment Success Rate | `authorized` |
| `shipping_state` | string | | State the order ships to; may differ from home state | `VA` |
| `discount_amount` | decimal | | Total promo/discount applied; 0 if none | `5.00` |
| `is_first_order` | bool | | True if the customer's first-ever order | `true` |

---

## Table 3: `order_items`

**Purpose:** The line-item detail (the "what products, at what price"). One row per product per
order (Square line_items). Source for top sellers, category mix, price bands, and 80/20 Pareto
analysis.

| Field | Type | Key | Description | Example |
|---|---|---|---|---|
| `order_item_id` | string | PK | Unique ID for one line within one order | `OI_0001923` |
| `transaction_id` | string | FK → orders | Which order this line belongs to | `TXN_000578` |
| `product_id` | string | FK → products | Which product/SKU was purchased | `PROD_0087` |
| `quantity` | int | | Units of this product on the line | `1` |
| `unit_price` | decimal | | Price of one unit at time of sale | `42.25` |
| `line_total` | decimal | | `quantity × unit_price`; summed to `order_total` | `42.25` |

---

## Table 4: `products`

**Purpose:** The product catalog dimension (the "what CapFinch sells"). One row per SKU (Square
Catalog equivalent). Attaches category, price, and margin to each line item; supports Inventory
Sync Accuracy.

| Field | Type | Key | Description | Example |
|---|---|---|---|---|
| `product_id` | string | PK | Unique SKU identifier | `PROD_0087` |
| `product_name` | string | | Human-readable product name | `Linen Scarf` |
| `category` | string | | Product category; used for Category Mix | `Accessories` |
| `price` | decimal | | Current list/selling price | `42.25` |
| `price_band` | string | | Pre-bucketed price tier (<$25 / $25-75 / $75+) | `$25-75` |
| `cost` | decimal | | Unit cost; enables margin and break-even AOV | `18.00` |
| `stock_on_hand` | int | | Current inventory units; feeds Inventory Sync Accuracy | `120` |

---

## Table 5: `sessions`

**Purpose:** The web-traffic layer (the "visits," including browsers who never bought). One row
per site visit. The piece a physical POS lacks; without it Conversion Rate and Cart Abandonment
cannot be computed. Denominator for the funnel.

| Field | Type | Key | Description | Example |
|---|---|---|---|---|
| `session_id` | string | PK | Unique ID for one website visit | `SESS_09912` |
| `customer_id` | string | FK → customers (nullable) | The visitor if known; null = anonymous browser | `CUST_00042` |
| `session_start` | timestamp | | When the visit began; daily grain for traffic KPIs | `2026-03-04 14:05` |
| `device` | string | | Device category (mobile / desktop / tablet) | `mobile` |
| `traffic_source` | string | | What drove the visit (organic / mailchimp / social / referral) | `mailchimp` |
| `landing_page` | string | | First page the visitor hit | `/home` |
| `reached_cart` | bool | | True if visitor added to cart; denominator for abandonment | `true` |
| `converted` | bool | | True if the visit ended in a completed order; numerator for conversion | `true` |

---

## Table 6: `events` (optional)

**Purpose:** The granular funnel log (the "every step a visitor took"), GA4-style. One row per
fired event. Needed only for Event Tracking Coverage and funnel drop-off analysis. The
`reached_cart` / `converted` flags on `sessions` are a lighter substitute.

| Field | Type | Key | Description | Example |
|---|---|---|---|---|
| `event_id` | string | PK | Unique ID for one tracked event | `EVT_0455120` |
| `session_id` | string | FK → sessions | Which visit the event occurred in | `SESS_09912` |
| `event_type` | string | | Funnel step (page_view / product_view / add_to_cart / checkout_start / purchase) | `add_to_cart` |
| `product_id` | string | FK → products (nullable) | Product involved; null for generic page views | `PROD_0087` |
| `event_time` | timestamp | | Exact time the event fired; orders steps within a session | `2026-03-04 14:07` |

---

## Data Integrity Rules

- `orders.order_total` = sum(`order_items.line_total`) − `discount_amount`
- `order_items.line_total` = `quantity × unit_price`
- Every `orders.customer_id` and `orders.session_id` must exist in `customers` / `sessions`
- A session with `converted = true` has exactly one matching row in `orders`
- `customers.total_orders` = count of that customer's rows in `orders`
- Only sessions with `reached_cart = true` count in the abandonment denominator