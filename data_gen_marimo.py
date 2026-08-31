import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # CapFinch — Synthetic Omnichannel Data Generator

    Builds a small, internally-consistent fake dataset (6 tables) to develop and test the
    analytics / KPI pipeline **before** the e-commerce site launches.

    CapFinch has run a physical store on **Square POS** for a while and is now launching its
    first website, so transactions arrive from two sources. Both land in a **single `orders`
    table** tagged with a `channel` flag, with channel-specific columns left null on the other
    side — the same way Square's Orders API mixes in-store and Square Online sales.

    **Two anchor keys**
    - `transaction_id` — PK of `orders` (one row per completed sale → revenue, AOV)
    - `customer_id` — PK of `customers` (one row per person → repeat rate, demographics).
      **Nullable on `orders`**: most walk-ins are anonymous, and some online buyers check out as guests.

    **Relationship chain**
    ```
    customers ─┬─ sessions ── events          (online only)
               └─ orders ── order_items ── products
    ```

    **Realism rules baked in**
    | Rule | Detail |
    |---|---|
    | Store hours | Open every day 10:00–18:00; no in-store order outside that window |
    | In-store time-of-day | Slow morning, lunch bump, late-afternoon peak |
    | In-store day-of-week | Saturday busiest, Mon/Tue slowest |
    | Online time-of-day | 24/7 with a 19:00–22:00 peak and a 02:00–06:00 trough |
    | Timeline | In-store history predates launch; online orders start on `LAUNCH_DATE` |
    | Identity capture | ~68% of in-store orders anonymous; ~12% of online orders are guests |
    | Payment mix | Cash/gift card only in store; PayPal only online |
    | Basket size | Larger in store, mostly single-item online |

    **KPI targets (funnel metrics are online-only by construction)**
    | Metric | Target |
    |---|---|
    | Conversion rate (online orders / sessions) | ~2% |
    | Cart abandonment (1 − completed/carts) | ~68% |
    | Repeat purchase (customers with ≥2 attributable orders) | ~20% |

    Everything is produced as a pandas `DataFrame` first (no CSV yet). Scale up later by raising
    `N_CUSTOMERS` — the ratios above are preserved. A commented CSV-export cell is at the bottom.
    """)
    return


@app.cell
def _():
    # Dependencies live in .venv — install with:  .venv/bin/python -m pip install -r requirements.txt
    # (marimo must be launched from that same venv, or it won't see these packages)

    import random
    from itertools import count

    import numpy as np
    import pandas as pd
    from faker import Faker

    SEED = 42
    random.seed(SEED)
    np.random.seed(SEED)
    fake = Faker("en_US")
    Faker.seed(SEED)

    pd.set_option("display.max_columns", None)
    print("Libraries ready.")
    return count, fake, np, pd, random


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Config, timeline & KPI targets

    `N_CUSTOMERS` is the single knob for dataset size. Repeat buyers get a 2nd order, so
    *attributable* orders ≈ `N_CUSTOMERS × (1 + repeat_rate)`; anonymous walk-ins and guest
    checkouts are then layered on top to hit the identity-capture rates. Session and cart counts
    are derived from the **online** orders only, so conversion (~2%) and abandonment (~68%) hold
    at any scale.
    """)
    return


@app.cell
def _(pd):
    # ---- Scale (raise this to grow every table; KPI ratios are preserved) ----
    N_CUSTOMERS = 15
    N_PRODUCTS = 30  # catalog holds 30 SKUs across 6 categories; lower this to trim it

    # ---- Timeline: in-store history predates the website ----
    TODAY = pd.Timestamp("2026-08-31").normalize()
    HISTORY_START = TODAY - pd.DateOffset(months=18)
    LAUNCH_DATE = (TODAY - pd.DateOffset(months=3)).normalize()  # first possible online order

    # ---- KPI targets ----
    TARGET_CONVERSION = 0.02   # online orders / total sessions
    TARGET_ABANDONMENT = 0.68  # 1 - completed_carts / carts_created
    TARGET_REPEAT = 0.20       # share of customers with >= 2 orders

    # ---- Channel mix & identity capture ----
    P_ONLINE_ATTRIBUTABLE = 0.40  # of known-customer orders, share placed on the website
    INSTORE_ANON_RATE = 0.68      # in-store orders with no customer_id (no receipt captured)
    ONLINE_GUEST_RATE = 0.12      # online orders checked out as a guest
    BIRTHDATE_CAPTURE_RATE = 0.45  # share of customers who actually hand over a birthday

    # ---- Store hours: open daily 10:00-18:00 ----
    STORE_OPEN_HOUR, STORE_CLOSE_HOUR = 10, 18
    INSTORE_HOURS = list(range(STORE_OPEN_HOUR, STORE_CLOSE_HOUR))
    INSTORE_HOUR_W = [0.06, 0.09, 0.12, 0.13, 0.12, 0.15, 0.18, 0.15]  # lunch bump, late-day peak
    INSTORE_DOW_W = [0.10, 0.10, 0.12, 0.13, 0.16, 0.23, 0.16]         # Mon..Sun, Saturday busiest

    # ---- Online traffic shape: 24/7, evening peak, overnight trough ----
    ONLINE_HOURS = list(range(24))
    ONLINE_HOUR_W = [
        0.030, 0.018, 0.010, 0.007, 0.006, 0.008, 0.014, 0.022,  # 00-07
        0.030, 0.035, 0.038, 0.042, 0.055, 0.045, 0.040, 0.040,  # 08-15
        0.042, 0.048, 0.060, 0.085, 0.100, 0.095, 0.070, 0.050,  # 16-23
    ]
    ONLINE_DOW_W = [0.15, 0.13, 0.13, 0.13, 0.14, 0.15, 0.17]

    # ---- Categorical vocabularies ----
    GENDERS = ["female", "male"]
    ACQ_SOURCES = ["organic", "mailchimp", "social", "referral"]
    DEVICES = ["mobile", "desktop", "tablet"]
    DEVICE_W = [0.62, 0.30, 0.08]
    LANDING_PAGES = ["/", "/new-arrivals", "/sale", "/collections/best-sellers", "/product"]
    EVENT_TYPES = ["page_view", "product_view", "add_to_cart", "checkout_start", "purchase"]

    PAYMENT_METHODS = {
        "in_store": (["card_present", "cash", "apple_pay", "gift_card"], [0.60, 0.20, 0.15, 0.05]),
        "online": (["card_not_present", "paypal", "apple_pay"], [0.65, 0.20, 0.15]),
    }
    DECLINE_RATE = {"in_store": 0.02, "online": 0.05}  # card-present rarely fails
    BASKET_SIZE = {
        "in_store": ([1, 2, 3, 4, 5], [0.30, 0.32, 0.20, 0.12, 0.06]),
        "online": ([1, 2, 3], [0.62, 0.28, 0.10]),
    }

    ENTRY_METHODS = ["chip", "tap", "swipe"]
    ENTRY_METHOD_W = [0.50, 0.42, 0.08]
    REGISTERS = ["REG01", "REG02"]
    EMPLOYEES = ["EMP01", "EMP02", "EMP03", "EMP04"]
    PROMO_CODES = ["WELCOME10", "SUMMER5", "MAILCHIMP15"]
    FREE_SHIP_THRESHOLD = 75.0
    SHIPPING_FEE = 6.95

    repeat_customers = round(N_CUSTOMERS * TARGET_REPEAT)
    print(f"Config: {N_CUSTOMERS} customers ({repeat_customers} repeat buyers), {N_PRODUCTS} products")
    print(f"History {HISTORY_START.date()} -> {TODAY.date()}  |  site launched {LAUNCH_DATE.date()}")
    return (
        ACQ_SOURCES,
        BASKET_SIZE,
        BIRTHDATE_CAPTURE_RATE,
        DECLINE_RATE,
        DEVICES,
        DEVICE_W,
        EMPLOYEES,
        ENTRY_METHODS,
        ENTRY_METHOD_W,
        FREE_SHIP_THRESHOLD,
        GENDERS,
        HISTORY_START,
        INSTORE_ANON_RATE,
        INSTORE_DOW_W,
        INSTORE_HOURS,
        INSTORE_HOUR_W,
        LANDING_PAGES,
        LAUNCH_DATE,
        N_CUSTOMERS,
        N_PRODUCTS,
        ONLINE_DOW_W,
        ONLINE_GUEST_RATE,
        ONLINE_HOURS,
        ONLINE_HOUR_W,
        PAYMENT_METHODS,
        PROMO_CODES,
        P_ONLINE_ATTRIBUTABLE,
        REGISTERS,
        SHIPPING_FEE,
        STORE_CLOSE_HOUR,
        STORE_OPEN_HOUR,
        TARGET_ABANDONMENT,
        TARGET_CONVERSION,
        TODAY,
        repeat_customers,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Timestamp sampling

    The single most visible tell of synthetic transaction data is uniformly-spread timestamps.
    `sample_datetime` draws a day weighted by day-of-week, then an hour weighted by time-of-day,
    using a different shape per channel. In-store draws are confined to store hours, and the
    closing hour is tapered because nobody walks in at 17:55.
    """)
    return


@app.cell
def _(
    HISTORY_START,
    INSTORE_DOW_W,
    INSTORE_HOURS,
    INSTORE_HOUR_W,
    ONLINE_DOW_W,
    ONLINE_HOURS,
    ONLINE_HOUR_W,
    STORE_CLOSE_HOUR,
    TODAY,
    np,
    pd,
):
    def _weighted_days(start, end, dow_w):
        days = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq="D")
        w = np.array([dow_w[d.weekday()] for d in days], dtype=float)
        return days, w / w.sum()


    def sample_datetime(channel, start, end):
        """Draw an order timestamp with channel-appropriate day-of-week and time-of-day shape."""
        dow_w = INSTORE_DOW_W if channel == "in_store" else ONLINE_DOW_W
        days, day_p = _weighted_days(start, end, dow_w)
        day = days[np.random.choice(len(days), p=day_p)]

        if channel == "in_store":
            hour_w = np.array(INSTORE_HOUR_W) / sum(INSTORE_HOUR_W)
            hour = int(np.random.choice(INSTORE_HOURS, p=hour_w))
            # taper the closing hour: no walk-ins in the last 15 minutes
            minute = int(np.random.randint(0, 45 if hour == STORE_CLOSE_HOUR - 1 else 60))
        else:
            hour_w = np.array(ONLINE_HOUR_W) / sum(ONLINE_HOUR_W)
            hour = int(np.random.choice(ONLINE_HOURS, p=hour_w))
            minute = int(np.random.randint(0, 60))

        return day + pd.Timedelta(hours=hour, minutes=minute, seconds=int(np.random.randint(0, 60)))


    _demo = pd.Series([sample_datetime("in_store", HISTORY_START, TODAY).hour for _ in range(500)])
    print("In-store hour range:", _demo.min(), "-", _demo.max(), "(store open 10-18)")
    return (sample_datetime,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 4 — `products`  [PK: product_id]
    Built first because orders/order_items and events reference it.

    CapFinch is a gift-and-everyday boutique, so the catalog spans six categories mixing low-ticket
    impulse/gift items with a few higher-ticket anchors:

    | Category | Envelope | What's in it |
    |---|---|---|
    | Stationery | ~$5–40 | Cards, notebooks, pens, planners, washi tape |
    | Home | ~$24–110 | Candles, vases, frames, diffusers, throws |
    | Accessories | ~$18–88 | Jewelry, hats, scarves, small leather goods |
    | Kitchen & Table | ~$12–95 | Mugs, tea towels, boards, salt cellars, kettles |
    | Bath & Body | ~$8–56 | Soap, hand cream, bath salts, lip balm, body oil |
    | Pantry & Treats | ~$6–26 | Honey, chocolate, tea, spiced nuts, jam |

    Each product carries its own narrow price range rather than drawing from the whole category
    envelope — a greeting card should never price out at $38. Prices are then snapped to retail-looking
    endings (`.00` / `.50` / `.95`). Cost ratios vary by category: jewelry and bath carry the best
    margin, pantry food the worst. Stock depth is inverse to price — cheap impulse items are stocked
    deep, high-ticket anchors are stocked thin.
    """)
    return


@app.cell
def _(N_PRODUCTS, np, pd):
    # (product_name, category, price_low, price_high)
    CATALOG = [('Letterpress Greeting Card', 'Stationery', 5, 8), ('A5 Linen Notebook', 'Stationery', 16, 24), ('Brass Fountain Pen', 'Stationery', 28, 40), ('Weekly Desk Planner', 'Stationery', 18, 28), ('Washi Tape Trio', 'Stationery', 9, 14), ('Soy Wax Candle', 'Home', 26, 38), ('Speckled Ceramic Vase', 'Home', 34, 52), ('Linen Throw Blanket', 'Home', 78, 110), ('Brass Picture Frame', 'Home', 24, 38), ('Reed Diffuser', 'Home', 32, 46), ('Gold Vermeil Hoops', 'Accessories', 48, 72), ('Wool Felt Hat', 'Accessories', 62, 88), ('Silk Twill Scarf', 'Accessories', 54, 78), ('Leather Card Holder', 'Accessories', 34, 48), ('Beaded Bracelet', 'Accessories', 18, 28), ('Stoneware Mug', 'Kitchen & Table', 16, 24), ('Linen Tea Towel', 'Kitchen & Table', 12, 18), ('Olive Wood Board', 'Kitchen & Table', 44, 68), ('Marble Salt Cellar', 'Kitchen & Table', 26, 38), ('Enamel Stovetop Kettle', 'Kitchen & Table', 68, 95), ('Oatmeal Soap Bar', 'Bath & Body', 8, 12), ('Shea Hand Cream', 'Bath & Body', 18, 26), ('Mineral Bath Salts', 'Bath & Body', 22, 32), ('Tinted Lip Balm', 'Bath & Body', 9, 14), ('Neroli Body Oil', 'Bath & Body', 38, 56), ('Wildflower Honey', 'Pantry & Treats', 14, 20), ('Sea Salt Chocolate Bar', 'Pantry & Treats', 6, 10), ('Loose Leaf Tea Tin', 'Pantry & Treats', 18, 26), ('Rosemary Spiced Nuts', 'Pantry & Treats', 9, 14), ('Small-Batch Fig Jam', 'Pantry & Treats', 12, 18)]
    COST_RATIO = {'Stationery': (0.45, 0.55), 'Home': (0.4, 0.5), 'Accessories': (0.32, 0.45), 'Kitchen & Table': (0.45, 0.55), 'Bath & Body': (0.35, 0.48), 'Pantry & Treats': (0.55, 0.68)}

    def price_band(p):
        if p < 25:
            return '<$25'
        if p <= 75:
            return '$25-75'
        return '$75+'

    def retail_price(low, high):
        """Draw in range, then snap to a retail-looking ending."""
        ending = float(np.random.choice([0.0, 0.5, 0.95], p=[0.45, 0.25, 0.3]))
        return round(np.floor(np.random.uniform(low, high)) + ending, 2)

    def stock_depth(p):
        """Small-boutique shelf depth: a handful of cheap impulse items, 1-2 of the anchors."""
        if p < 25:
            return int(np.random.randint(6, 30))
        if p <= 75:
            return int(np.random.randint(3, 14))
        return int(np.random.randint(1, 6))
    products = []
    for _i, (_name, cat, lo, hi) in enumerate(CATALOG[:N_PRODUCTS], start=1):
        price = retail_price(lo, hi)
        products.append({'product_id': f'PROD{_i:04d}', 'product_name': _name, 'category': cat, 'price': price, 'price_band': price_band(price), 'cost': round(price * np.random.uniform(*COST_RATIO[cat]), 2), 'stock_on_hand': stock_depth(price)})
    products_df = pd.DataFrame(products)
    print(f"{len(products_df)} SKUs across {products_df['category'].nunique()} categories")
    print(f"Units on hand: {products_df['stock_on_hand'].sum()} total, median {int(products_df['stock_on_hand'].median())} per SKU")
    print(products_df.assign(margin=1 - products_df['cost'] / products_df['price']).groupby('category').agg(skus=('product_id', 'count'), low=('price', 'min'), high=('price', 'max'), avg_margin=('margin', 'mean')).round(2).to_string())
    # cost as a share of price — jewelry and bath carry the best margin, food the worst
    products_df
    return (products_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Sell-through weights (best sellers)

    Real boutique sales are heavily Pareto — a handful of SKUs drive most units. Picking products
    uniformly would flatten that and make top-seller and 80/20 analysis meaningless, so every SKU gets
    a **popularity weight** built from three things:

    1. **Price elasticity** — cheap impulse items outsell expensive anchors, as `(median_price / price) ** 0.6`
    2. **Hero boost** — a few deliberate best sellers get a multiplier, so the ranking isn't purely
       "cheapest wins" (the gold hoops sell well *despite* being one of the pricier SKUs)
    3. **Taste jitter** — a lognormal wobble so the order isn't perfectly predictable from price

    These weights drive both what gets bought (`order_items`) and what gets browsed (`product_view`
    events). They are a generator input, not a column on `products` — Square's catalog wouldn't
    export them.
    """)
    return


@app.cell
def _(np, products_df):
    # SKUs that sell above what price alone would predict
    HERO_SKUS = {
        "Soy Wax Candle",
        "Letterpress Greeting Card",
        "Stoneware Mug",
        "Shea Hand Cream",
        "Gold Vermeil Hoops",
    }
    PRICE_ELASTICITY = 0.6  # higher = cheap items dominate more
    HERO_BOOST = 3.5

    _w = (products_df["price"].median() / products_df["price"]) ** PRICE_ELASTICITY
    _w = _w * np.where(products_df["product_name"].isin(HERO_SKUS), HERO_BOOST, 1.0)
    _w = _w * np.exp(np.random.normal(0, 0.35, len(products_df)))
    product_weights = (_w / _w.sum()).to_numpy()

    print("Top 8 by expected sell-through")
    print(
        products_df.assign(share=product_weights)
        .nlargest(8, "share")[["product_name", "category", "price", "share"]]
        .assign(share=lambda d: (d["share"] * 100).round(1).astype(str) + "%")
        .to_string(index=False)
    )
    return (product_weights,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 1 — `customers`  [PK: customer_id]
    Only people CapFinch can actually identify (Square Customer Directory / Mailchimp audience).
    `total_orders` is assigned here and counts **attributable** orders only — repeat buyers get 2.
    Anonymous walk-ins never appear in this table. `signup_date` is drawn inside the history
    window so every customer exists before their first order; `first_order_date` is filled in
    from the actual orders once they exist.

    **`birthdate` is optional and is the source of truth for age.** Handing over a birthday is
    opt-in at signup, so only ~45% of customers have one; `age` and `age_band` are derived from it
    and are **null for everyone else**. Any age-based analysis has to cope with that gap rather than
    assume full coverage.
    """)
    return


@app.cell
def _(
    ACQ_SOURCES,
    BIRTHDATE_CAPTURE_RATE,
    GENDERS,
    HISTORY_START,
    N_CUSTOMERS,
    TODAY,
    fake,
    np,
    pd,
    random,
    repeat_customers,
):
    def age_band(a):
        if a is None:
            return None
        if a <= 24:
            return '18-24'
        if a <= 34:
            return '25-34'
        if a <= 44:
            return '35-44'
        return '45+'
    order_counts = [2] * repeat_customers + [1] * (N_CUSTOMERS - repeat_customers)
    random.shuffle(order_counts)
    # order-count per customer: repeat buyers get 2 orders, everyone else gets 1
    signup_window = (TODAY - pd.Timedelta(days=30) - HISTORY_START).days
    customers = []
    for _i in range(1, N_CUSTOMERS + 1):
        if random.random() < BIRTHDATE_CAPTURE_RATE:
            birthdate = fake.date_between(start_date='-66y', end_date='-18y')
            age = int((TODAY.date() - birthdate).days // 365.25)
        else:
            birthdate, age = (None, None)  # birthday is opt-in at signup, so most customers have no age on file
        _signup = HISTORY_START + pd.Timedelta(days=int(np.random.randint(0, signup_window)))
        customers.append({'customer_id': f'CUST{_i:04d}', 'email': fake.unique.email(), 'birthdate': birthdate, 'age': age, 'age_band': age_band(age), 'gender': random.choice(GENDERS), 'state': fake.state_abbr(), 'zip': fake.zipcode(), 'signup_date': _signup.date(), 'acquisition_source': random.choice(ACQ_SOURCES), 'first_order_date': pd.NaT, 'total_orders': order_counts[_i - 1]})
    customers_df = pd.DataFrame(customers)
    customers_df['birthdate'] = pd.to_datetime(customers_df['birthdate'])
    customers_df['age'] = customers_df['age'].astype('Int64')
    have_bday = customers_df['birthdate'].notna().sum()
    print(f'{have_bday}/{len(customers_df)} customers have a birthday on file ({have_bday / len(customers_df):.0%}) — age/age_band are null for the rest')
    customers_df  # filled after orders are built
    return (customers_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Tables 2 & 3 — `orders` and `order_items`
    One `orders` row per completed sale from **either** channel, distinguished by `channel`.
    Channel-specific columns stay null on the other side:

    - **online only** — `session_id`, `shipping_state`, `shipping_zip`, `shipping_fee`,
      `fulfillment_type`, `promo_code`, `device`
    - **in-store only** — `register_id`, `employee_id`, `entry_method`, `tip_amount`, `receipt_type`

    Money: `order_total = subtotal − discount_amount + shipping_fee`, where `subtotal` is the sum
    of the order's `order_items.line_total`.

    Orders are built in two passes: first the attributable ones expanded from each customer's
    `total_orders`, then anonymous walk-ins and guest checkouts layered on top to hit the
    identity-capture rates. Only online orders create a converting session.
    """)
    return


@app.cell
def _(
    ACQ_SOURCES,
    BASKET_SIZE,
    DECLINE_RATE,
    DEVICES,
    DEVICE_W,
    EMPLOYEES,
    ENTRY_METHODS,
    ENTRY_METHOD_W,
    FREE_SHIP_THRESHOLD,
    HISTORY_START,
    INSTORE_ANON_RATE,
    LANDING_PAGES,
    LAUNCH_DATE,
    ONLINE_GUEST_RATE,
    PAYMENT_METHODS,
    PROMO_CODES,
    P_ONLINE_ATTRIBUTABLE,
    REGISTERS,
    SHIPPING_FEE,
    TODAY,
    count,
    customers_df,
    fake,
    np,
    pd,
    product_weights,
    products_df,
    random,
    sample_datetime,
):
    order_rows, oi_rows, sess_rows = ([], [], [])
    order_counter, session_counter = (count(1), count(1))
    product_ids = products_df['product_id'].tolist()
    price_lookup = products_df.set_index('product_id')['price'].to_dict()

    def build_order(customer, channel, when):
        """One order plus its line items. `customer` is None for a walk-in or guest checkout."""
        tid = f'TXN{next(order_counter):05d}'
        sizes, size_p = BASKET_SIZE[channel]
        n_items = min(int(np.random.choice(sizes, p=size_p)), len(product_ids))
        chosen = np.random.choice(product_ids, size=n_items, replace=False, p=product_weights)
        subtotal, total_qty = (0.0, 0)
        for pid in chosen:
            qty = int(np.random.randint(1, 3 if channel == 'online' else 4))
            unit = float(price_lookup[pid])
            line = round(qty * unit, 2)
            subtotal += line
            total_qty += qty
            oi_rows.append({'order_item_id': f'OI{len(oi_rows) + 1:06d}', 'transaction_id': tid, 'product_id': str(pid), 'quantity': qty, 'unit_price': unit, 'line_total': line})
        subtotal = round(subtotal, 2)
        methods, method_p = PAYMENT_METHODS[channel]
        method = str(np.random.choice(methods, p=method_p))
        declined = method != 'cash' and random.random() < DECLINE_RATE[channel]
        discount = round(subtotal * np.random.choice([0, 0.05, 0.1], p=[0.7, 0.2, 0.1]), 2)
        row = {'transaction_id': tid, 'customer_id': customer['customer_id'] if customer is not None else None, 'channel': channel, 'order_datetime': when, 'order_date': when.date(), 'day_of_week': when.day_name(), 'hour_of_day': when.hour, 'subtotal': subtotal, 'discount_amount': discount, 'item_count': total_qty, 'payment_method': method, 'payment_status': 'declined' if declined else 'authorized', 'session_id': None, 'shipping_state': None, 'shipping_zip': None, 'shipping_fee': None, 'fulfillment_type': None, 'promo_code': None, 'device': None, 'register_id': None, 'employee_id': None, 'entry_method': None, 'tip_amount': None, 'receipt_type': None}
        if channel == 'online':
            sid = f'SESS{next(session_counter):06d}'
            fulfillment = str(np.random.choice(['ship', 'pickup_in_store'], p=[0.85, 0.15]))
            free_ship = fulfillment == 'pickup_in_store' or subtotal >= FREE_SHIP_THRESHOLD
            device = str(np.random.choice(DEVICES, p=DEVICE_W))
            row.update({'session_id': sid, 'shipping_state': customer['state'] if customer is not None else fake.state_abbr(), 'shipping_zip': customer['zip'] if customer is not None else fake.zipcode(), 'shipping_fee': 0.0 if free_ship else SHIPPING_FEE, 'fulfillment_type': fulfillment, 'promo_code': random.choice(PROMO_CODES) if discount > 0 else None, 'device': device})
            sess_rows.append({'session_id': sid, 'customer_id': row['customer_id'], 'session_start': when - pd.Timedelta(minutes=int(np.random.randint(3, 30))), 'device': device, 'traffic_source': customer['acquisition_source'] if customer is not None else random.choice(ACQ_SOURCES), 'landing_page': random.choice(LANDING_PAGES), 'reached_cart': True, 'converted': True})
        else:
            row.update({'register_id': random.choice(REGISTERS), 'employee_id': random.choice(EMPLOYEES), 'entry_method': None if method == 'cash' else str(np.random.choice(ENTRY_METHODS, p=ENTRY_METHOD_W)), 'tip_amount': 0.0 if random.random() < 0.9 else round(subtotal * 0.05, 2), 'receipt_type': random.choice(['email', 'sms']) if customer is not None else random.choice(['printed', 'none'])})
        row['order_total'] = round(subtotal - discount + (row['shipping_fee'] or 0.0), 2)  # cash never declines
        return row
    attributable = [cust for _, cust in customers_df.iterrows() for _ in range(int(cust['total_orders']))]
    n_attr_online = round(len(attributable) * P_ONLINE_ATTRIBUTABLE)
    attr_channels = ['online'] * n_attr_online + ['in_store'] * (len(attributable) - n_attr_online)
    random.shuffle(attr_channels)
    for cust, channel in zip(attributable, attr_channels):
        _signup = pd.Timestamp(cust['signup_date'])
        window_start = max(_signup, LAUNCH_DATE) if channel == 'online' else max(_signup, HISTORY_START)
        order_rows.append(build_order(cust, channel, sample_datetime(channel, window_start, TODAY)))
    n_attr_instore = len(attributable) - n_attr_online
    n_anon_instore = round(n_attr_instore * INSTORE_ANON_RATE / (1 - INSTORE_ANON_RATE))
    n_guest_online = round(n_attr_online * ONLINE_GUEST_RATE / (1 - ONLINE_GUEST_RATE))
    for _ in range(n_anon_instore):
        order_rows.append(build_order(None, 'in_store', sample_datetime('in_store', HISTORY_START, TODAY)))
    for _ in range(n_guest_online):
        order_rows.append(build_order(None, 'online', sample_datetime('online', LAUNCH_DATE, TODAY)))  # online-only
    orders_df = pd.DataFrame(order_rows).sort_values('order_datetime').reset_index(drop=True)
    order_items_df = pd.DataFrame(oi_rows)
    print(f'orders={len(orders_df)}  order_items={len(order_items_df)}')
    print(orders_df['channel'].value_counts().to_string())
    print(f'anonymous in-store={n_anon_instore}  guest online={n_guest_online}')
    print(f"online orders run {orders_df.loc[orders_df['channel'] == 'online', 'order_date'].min()} -> {orders_df.loc[orders_df['channel'] == 'online', 'order_date'].max()}")
    # Pass 1 — attributable orders. The channel split is allocated exactly rather than drawn
    # per order, so the mix still holds at small N.
    # Pass 2 — anonymous walk-ins and guest checkouts, sized to hit the identity-capture rates
    # rows are date-sorted, so every online order sits at the tail — preview both channels
    pd.concat([orders_df[orders_df['channel'] == 'in_store'].head(8), orders_df[orders_df['channel'] == 'online'].head(8)])  # in-store-only  # a digital receipt is what links a walk-in to a customer record
    return order_items_df, orders_df, product_ids, sess_rows, session_counter


@app.cell
def _(order_items_df):
    # order_items preview
    order_items_df.head(15)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 5 — `sessions`  [PK: session_id]
    Website visits only — a POS has no equivalent, which is exactly why the funnel KPIs need this
    table. The converting sessions already exist (one per **online** order). Here we add
    **abandoned-cart** and **browse-only** sessions so the online funnel hits conversion ~2% and
    abandonment ~68%:

    - `total_carts = online_orders / (1 − 0.68)` → abandoned = carts − online orders
    - `total_sessions = online_orders / 0.02` → browse-only = sessions − carts

    All sessions fall on or after `LAUNCH_DATE`, and some are anonymous (`customer_id = None`).
    In-store orders are deliberately excluded from both sides of the conversion ratio.
    """)
    return


@app.cell
def _(
    ACQ_SOURCES,
    DEVICES,
    DEVICE_W,
    LANDING_PAGES,
    LAUNCH_DATE,
    TARGET_ABANDONMENT,
    TARGET_CONVERSION,
    TODAY,
    customers_df,
    np,
    orders_df,
    pd,
    random,
    sample_datetime,
    sess_rows,
    session_counter,
):
    n_online_orders = int((orders_df["channel"] == "online").sum())
    total_carts = round(n_online_orders / (1 - TARGET_ABANDONMENT))
    abandoned_carts = max(total_carts - n_online_orders, 0)
    total_sessions = round(n_online_orders / TARGET_CONVERSION)
    browse_sessions = max(total_sessions - total_carts, 0)

    cust_ids = customers_df["customer_id"].tolist()


    def make_session(reached_cart, converted):
        # ~40% of non-converting traffic is a known customer, the rest is anonymous
        cust_id = random.choice(cust_ids) if random.random() < 0.4 else None
        return {
            "session_id": f"SESS{next(session_counter):06d}",
            "customer_id": cust_id,
            "session_start": sample_datetime("online", LAUNCH_DATE, TODAY),
            "device": str(np.random.choice(DEVICES, p=DEVICE_W)),
            "traffic_source": random.choice(ACQ_SOURCES),
            "landing_page": random.choice(LANDING_PAGES),
            "reached_cart": reached_cart,
            "converted": converted,
        }


    for _ in range(abandoned_carts):
        sess_rows.append(make_session(reached_cart=True, converted=False))
    for _ in range(browse_sessions):
        sess_rows.append(make_session(reached_cart=False, converted=False))

    sessions_df = pd.DataFrame(sess_rows).sort_values("session_start").reset_index(drop=True)
    print(f"sessions={len(sessions_df)}  carts={total_carts}  abandoned={abandoned_carts}  browse={browse_sessions}")
    sessions_df.head(15)
    return (sessions_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Back-fill `first_order_date`
    Now that orders exist, set each customer's first order date from their earliest **attributable**
    order, across both channels. This is the single source of truth for first-purchase / cohort
    analysis — there is no `is_first_order` flag on `orders`, since it is derivable from here and
    would be misleading anyway while most in-store sales are anonymous.
    """)
    return


@app.cell
def _(customers_df, orders_df, pd):
    first_orders = orders_df.dropna(subset=["customer_id"]).groupby("customer_id")["order_datetime"].min()
    customers_df["first_order_date"] = pd.to_datetime(customers_df["customer_id"].map(first_orders)).dt.date
    customers_df
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 6 — `events`  [PK: event_id]
    Funnel detail per session. Every session gets a `page_view` + some `product_view`s; sessions
    that reached the cart add `add_to_cart` → `checkout_start`, and converters end with `purchase`.
    """)
    return


@app.cell
def _(np, pd, product_ids, product_weights, sessions_df):
    event_rows = []


    def add_event(session, etype, t, pid=None):
        event_rows.append({
            "event_id": f"EVT{len(event_rows) + 1:07d}",
            "session_id": session["session_id"],
            "event_type": etype,
            "product_id": pid,
            "event_time": t,
        })


    def viewed_product():
        return str(np.random.choice(product_ids, p=product_weights))


    for _, s in sessions_df.iterrows():
        t = pd.to_datetime(s["session_start"])
        add_event(s, "page_view", t)

        for _ in range(int(np.random.randint(1, 4))):
            t += pd.Timedelta(seconds=int(np.random.randint(20, 180)))
            add_event(s, "product_view", t, viewed_product())

        if s["reached_cart"]:
            t += pd.Timedelta(seconds=int(np.random.randint(20, 120)))
            add_event(s, "add_to_cart", t, viewed_product())
            t += pd.Timedelta(seconds=int(np.random.randint(20, 120)))
            add_event(s, "checkout_start", t)
            if s["converted"]:
                t += pd.Timedelta(seconds=int(np.random.randint(20, 120)))
                add_event(s, "purchase", t)

    events_df = pd.DataFrame(event_rows)
    print(f"events={len(events_df)}")
    events_df.head(15)
    return (events_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Overview, KPI check & integrity
    Confirm the six DataFrames, verify the KPI targets, and assert the numeric, channel, and
    timing rules hold — including that no in-store order lands outside store hours and no online
    order predates launch.
    """)
    return


@app.cell
def _(
    LAUNCH_DATE,
    STORE_CLOSE_HOUR,
    STORE_OPEN_HOUR,
    TODAY,
    customers_df,
    events_df,
    np,
    order_items_df,
    orders_df,
    pd,
    products_df,
    sessions_df,
):
    tables = {'customers': customers_df, 'orders': orders_df, 'order_items': order_items_df, 'products': products_df, 'sessions': sessions_df, 'events': events_df}
    print('Table shapes')
    for _name, df in tables.items():
        print(f'  {_name:12s} rows={len(df):5d}  cols={len(df.columns)}')
    instore = orders_df[orders_df['channel'] == 'in_store']
    online = orders_df[orders_df['channel'] == 'online']
    conversion = len(online) / len(sessions_df)
    carts = int(sessions_df['reached_cart'].sum())
    abandonment = 1 - sessions_df['converted'].sum() / carts
    repeat = (customers_df['total_orders'] >= 2).mean()
    print('\nKPIs (actual vs target)')
    print(f'  Conversion rate : {conversion:6.2%}  (target ~2%, online orders / sessions)')
    print(f'  Cart abandonment: {abandonment:6.2%}  (target ~68%)')
    print(f'  Repeat purchase : {repeat:6.2%}  (target ~20%)')
    print('\nChannel profile')
    print(f"  In-store : {len(instore):4d} orders  AOV ${instore['order_total'].mean():7.2f}  anonymous {instore['customer_id'].isna().mean():.0%}")
    # --- KPI check (funnel metrics are online-only) ---
    print(f"  Online   : {len(online):4d} orders  AOV ${online['order_total'].mean():7.2f}  guest {online['customer_id'].isna().mean():.0%}")
    sales = order_items_df.merge(products_df, on='product_id').groupby(['product_name', 'category']).agg(units=('quantity', 'sum'), revenue=('line_total', 'sum')).sort_values('units', ascending=False)
    top_share = sales['revenue'].head(round(len(products_df) * 0.2)).sum() / sales['revenue'].sum()
    print('\nTop 8 sellers by units')
    print(sales.head(8).round(2).to_string())
    print(f'\n  Top 20% of SKUs = {top_share:.0%} of revenue (Pareto check)')
    print(f'  SKUs with zero sales: {len(products_df) - len(sales)}')
    print('\nCategory mix by revenue')
    print((sales.groupby('category')['revenue'].sum() / sales['revenue'].sum()).sort_values(ascending=False).round(3).to_string())
    assert (order_items_df['line_total'] == (order_items_df['quantity'] * order_items_df['unit_price']).round(2)).all()
    recon = order_items_df.groupby('transaction_id')['line_total'].sum().round(2)
    by_tid = orders_df.set_index('transaction_id').loc[recon.index]
    assert np.allclose(recon.values, by_tid['subtotal'].values)
    assert np.allclose(by_tid['order_total'].values, (by_tid['subtotal'] - by_tid['discount_amount'] + by_tid['shipping_fee'].fillna(0.0)).round(2).values)
    assert orders_df['customer_id'].dropna().isin(customers_df['customer_id']).all()
    assert order_items_df['product_id'].isin(products_df['product_id']).all()
    # --- Best sellers / Pareto ---
    online_only = ['session_id', 'shipping_state', 'shipping_zip', 'shipping_fee', 'fulfillment_type', 'device']
    instore_only = ['register_id', 'employee_id', 'tip_amount', 'receipt_type']
    assert instore[online_only].isna().all().all()
    assert online[instore_only].isna().all().all()
    assert online['session_id'].notna().all()
    assert online['session_id'].isin(sessions_df['session_id']).all()
    assert sessions_df.loc[sessions_df['session_id'].isin(online['session_id']), 'converted'].all()
    assert int(sessions_df['converted'].sum()) == len(online)
    assert instore['hour_of_day'].between(STORE_OPEN_HOUR, STORE_CLOSE_HOUR - 1).all()
    assert (online['order_datetime'] >= LAUNCH_DATE).all()
    assert (orders_df['order_datetime'] <= TODAY + pd.Timedelta(days=1)).all()
    assert (customers_df['total_orders'] == orders_df['customer_id'].value_counts().reindex(customers_df['customer_id']).values).all()
    # --- Integrity checks ---
    # channel exclusivity
    # timing rules
    print('\nIntegrity checks passed: money, FKs, channel exclusivity, store hours, and launch date all consistent.')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Export to CSV (optional)
    Everything lives as DataFrames above. Uncomment to write them to a `data/` folder when ready.
    """)
    return


@app.cell
def _():
    # import os
    # os.makedirs("data", exist_ok=True)
    # for name, df in tables.items():
    #     df.to_csv(f"data/{name}.csv", index=False)
    # print("Wrote:", ", ".join(f"data/{n}.csv" for n in tables))
    return


if __name__ == "__main__":
    app.run()

