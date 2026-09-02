import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # CapFinch post-launch dashboard

    "
        "This sample combines CapFinch's in-store sales history with modeled activity from its new "
        "e-commerce website. It illustrates the measures we will use to monitor commercial "
        "performance after launch.
    """)
    return


@app.cell
def _():
    # Dependencies live in .venv — install with:  .venv/bin/python -m pip install -r requirements.txt
    # (marimo must be launched from that same venv, or it won't see these packages)

    import random
    from itertools import count

    import altair as alt
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
    return alt, count, fake, np, pd, random


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
    N_PRODUCTS = 38  # catalog holds 38 SKUs across 5 categories and 19 subcategories

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
    GIFT_SHIP_RATE = 0.20          # online orders shipped somewhere other than the buyer's address

    # ---- Geography: a boutique's customers cluster near the store (Richmond, VA) ----
    # zip prefixes keep state and zip internally consistent, which Faker alone won't do
    STATE_ZIP_PREFIX = {
        "VA": "232", "MD": "208", "DC": "200", "NC": "275",
        "PA": "191", "NY": "100", "CA": "941", "TX": "787",
    }
    STATE_W = [0.44, 0.12, 0.10, 0.08, 0.06, 0.06, 0.07, 0.07]
    APT_RATE = 0.25  # share of addresses with a unit/suite line

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
        APT_RATE,
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
        GIFT_SHIP_RATE,
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
        STATE_W,
        STATE_ZIP_PREFIX,
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
    ## Address sampling

    Addresses are generated as separate components (`line1` / `line2` / `city` / `state` / `zip`)
    rather than one blob, so location analysis can group by state or zip without parsing.

    Two realism details: customers cluster near the store rather than being spread uniformly over
    all 50 states and territories, and the **zip prefix is derived from the state** — Faker's
    `state_abbr()` and `zipcode()` are independent, so used naively they happily produce a Virginia
    address with a Montana zip.
    """)
    return


@app.cell
def _(APT_RATE, STATE_W, STATE_ZIP_PREFIX, fake, np, random):
    def sample_address(prefix=""):
        """A US address as separate components. `prefix` namespaces the keys, e.g. 'shipping_'."""
        state = str(np.random.choice(list(STATE_ZIP_PREFIX), p=STATE_W))
        zip_code = f"{STATE_ZIP_PREFIX[state]}{np.random.randint(0, 100):02d}"
        return {
            # building_number + street_name, not street_address() — the latter embeds a unit
            # number, which would collide with address_line2
            f"{prefix}address_line1": f"{fake.building_number()} {fake.street_name()}",
            f"{prefix}address_line2": fake.secondary_address() if random.random() < APT_RATE else None,
            f"{prefix}city": fake.city(),
            f"{prefix}state": state,
            f"{prefix}zip": zip_code,
        }


    def copy_address(row, prefix="shipping_"):
        """Re-key a customer's address onto an order as the shipping address."""
        return {f"{prefix}{f}": row[f"{f}"] for f in
                ("address_line1", "address_line2", "city", "state", "zip")}


    for _ in range(3):
        print(sample_address())
    return copy_address, sample_address


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 4 — `products`  [PK: product_id]
    Built first because orders and order items reference it.

    CapFinch is a boutique carrying 38 SKUs across 5 main categories and 19 subcategories:

    | Category | Subcategory | Price Range |
    |---|---|---|
    | Apparel | Tops, Dresses, Outerwear, Bottoms, Denim | $35–$250 |
    | Accessories | Jewelry (everyday), Jewelry (statement), Handbags, Scarves & wraps, Belts, Sunglasses | $20–$220 |
    | Footwear | Sandals/flats, Boots, Heels | $50–$220 |
    | Home & Gift | Candles, Small home decor, Gift sets | $18–$75 |
    | Beauty/Wellness | Skincare, Fragrance | $20–$95 |

    Prices and costs end in `.99` or round numbers (`.00`). Stock depth is inverse to price — cheap impulse items are stocked deep, high-ticket anchors are stocked thin.
    """)
    return


@app.cell
def _(N_PRODUCTS, pd):
    # (product_name, category, subcategory, price, cost, stock_on_hand)
    CATALOG = [('Ribbed Cotton Knit Tee', 'Apparel', 'Tops', 38.0, 15.0, 24), ('Silk Button-Down Blouse', 'Apparel', 'Tops', 78.0, 31.0, 12), ('Linen Midi Wrap Dress', 'Apparel', 'Dresses', 128.0, 51.0, 8), ('Tiered Floral Maxi Dress', 'Apparel', 'Dresses', 149.99, 60.0, 6), ('Tailored Wool Cardigan', 'Apparel', 'Outerwear', 120.0, 48.0, 6), ('Structured Utility Jacket', 'Apparel', 'Outerwear', 225.0, 90.0, 4), ('Pleated High-Waist Trousers', 'Apparel', 'Bottoms', 88.0, 35.0, 10), ('A-Line Midi Skirt', 'Apparel', 'Bottoms', 68.0, 27.0, 12), ('Straight-Leg Ankle Denim', 'Apparel', 'Denim', 118.0, 47.0, 14), ('Wide-Leg High-Rise Jean', 'Apparel', 'Denim', 139.99, 56.0, 10), ('Gold Vermeil Hoop Earrings', 'Accessories', 'Jewelry (everyday)', 48.0, 19.0, 18), ('Minimalist Chain Necklace', 'Accessories', 'Jewelry (everyday)', 35.0, 14.0, 22), ('Freshwater Pearl Drop Earrings', 'Accessories', 'Jewelry (statement/special occasion)', 85.0, 34.0, 8), ('Chunky Statement Cuff', 'Accessories', 'Jewelry (statement/special occasion)', 98.0, 39.0, 6), ('Leather Crossbody Bag', 'Accessories', 'Handbags', 145.0, 58.0, 8), ('Canvas Carryall Tote', 'Accessories', 'Handbags', 95.0, 38.0, 12), ('Silk Twill Scarf', 'Accessories', 'Scarves & wraps', 58.0, 23.0, 15), ('Cashmere Blend Wrap', 'Accessories', 'Scarves & wraps', 68.0, 27.0, 10), ('Classic Leather Belt', 'Accessories', 'Belts', 45.0, 18.0, 16), ('Woven Waist Belt', 'Accessories', 'Belts', 32.0, 12.0, 18), ('Cat-Eye Acetate Sunglasses', 'Accessories', 'Sunglasses', 65.0, 26.0, 14), ('Classic Aviator Sunglasses', 'Accessories', 'Sunglasses', 48.0, 19.0, 16), ('Leather Slide Sandals', 'Footwear', 'Sandals/flats', 68.0, 27.0, 12), ('Pointed-Toe Ballet Flats', 'Footwear', 'Sandals/flats', 85.0, 34.0, 10), ('Ankle Leather Chelsea Boots', 'Footwear', 'Boots', 165.0, 66.0, 6), ('Suede Tall Riding Boots', 'Footwear', 'Boots', 210.0, 84.0, 4), ('Strappy Block-Heel Pumps', 'Footwear', 'Heels', 98.0, 39.0, 8), ('Classic Kitten Heels', 'Footwear', 'Heels', 88.0, 35.0, 10), ('Soy Wax Signature Candle', 'Home & Gift', 'Candles', 28.0, 11.0, 24), ('Botanical Glass Candle', 'Home & Gift', 'Candles', 34.0, 13.0, 18), ('Speckled Ceramic Vase', 'Home & Gift', 'Small home decor', 42.0, 18.0, 10), ('Brass Picture Frame', 'Home & Gift', 'Small home decor', 35.0, 15.0, 14), ('Self-Care Bath Gift Set', 'Home & Gift', 'Gift sets', 58.0, 26.0, 12), ('Artisanal Tea & Mug Set', 'Home & Gift', 'Gift sets', 45.0, 20.0, 15), ('Hydrating Facial Oil', 'Beauty/Wellness', 'Skincare', 38.0, 13.0, 16), ('Nourishing Botanical Cleanser', 'Beauty/Wellness', 'Skincare', 27.99, 9.0, 20), ('Eau de Parfum Travel Spray', 'Beauty/Wellness', 'Fragrance', 52.0, 18.0, 14), ('Botanical Roll-On Perfume Oil', 'Beauty/Wellness', 'Fragrance', 68.0, 23.0, 12)]

    def price_band(p):
        if p < 50:
            return '<$50'
        if p < 100:
            return '$50-100'
        if p < 200:
            return '$100-200'
        return '$200+'
    products = []
    for _i, (_name, cat, subcat, price, cost, stock) in enumerate(CATALOG[:N_PRODUCTS], start=1):
        products.append({'product_id': f'PROD{_i:04d}', 'product_name': _name, 'category': cat, 'subcategory': subcat, 'price': price, 'price_band': price_band(price), 'cost': cost, 'stock_on_hand': stock})
    products_df = pd.DataFrame(products)
    print(f"{len(products_df)} SKUs across {products_df['category'].nunique()} categories")
    print(f"Units on hand: {products_df['stock_on_hand'].sum()} total, median {int(products_df['stock_on_hand'].median())} per SKU")
    print(products_df.assign(margin=1 - products_df['cost'] / products_df['price']).groupby(['category', 'subcategory']).agg(skus=('product_id', 'count'), low=('price', 'min'), high=('price', 'max'), avg_margin=('margin', 'mean')).round(2).to_string())
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

    These weights drive what gets bought in `order_items`. They are a generator input, not a column
    on `products` — Square's catalog wouldn't export them.
    """)
    return


@app.cell
def _(np, products_df):
    # SKUs that sell above what price alone would predict
    HERO_SKUS = {
        "Soy Wax Signature Candle",
        "Gold Vermeil Hoop Earrings",
        "Silk Button-Down Blouse",
        "Hydrating Facial Oil",
        "Leather Crossbody Bag",
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
    sample_address,
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
        customers.append({'customer_id': f'CUST{_i:04d}', 'email': fake.unique.email(), 'birthdate': birthdate, 'age': age, 'age_band': age_band(age), 'gender': random.choice(GENDERS), **sample_address(), 'signup_date': _signup.date(), 'acquisition_source': random.choice(ACQ_SOURCES), 'first_order_date': pd.NaT, 'total_orders': order_counts[_i - 1]})
    customers_df = pd.DataFrame(customers)
    customers_df['birthdate'] = pd.to_datetime(customers_df['birthdate'])
    customers_df['age'] = customers_df['age'].astype('Int64')
    have_bday = customers_df['birthdate'].notna().sum()
    print(f'{have_bday}/{len(customers_df)} customers have a birthday on file ({have_bday / len(customers_df):.0%}) — age/age_band are null for the rest')
    print(f"Top states: {customers_df['state'].value_counts().head(4).to_dict()}")
    customers_df  # default / billing address  # filled after orders are built
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
    GIFT_SHIP_RATE,
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
    copy_address,
    count,
    customers_df,
    np,
    pd,
    product_weights,
    products_df,
    random,
    sample_address,
    sample_datetime,
):
    order_rows, oi_rows, sess_rows = ([], [], [])
    order_counter, session_counter = (count(1), count(1))
    product_ids = products_df['product_id'].tolist()
    price_lookup = products_df.set_index('product_id')['price'].to_dict()
    SHIP_FIELDS = ['shipping_address_line1', 'shipping_address_line2', 'shipping_city', 'shipping_state', 'shipping_zip']

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
        row = {'transaction_id': tid, 'customer_id': customer['customer_id'] if customer is not None else None, 'channel': channel, 'order_datetime': when, 'order_date': when.date(), 'day_of_week': when.day_name(), 'hour_of_day': when.hour, 'subtotal': subtotal, 'discount_amount': discount, 'item_count': total_qty, 'payment_method': method, 'payment_status': 'declined' if declined else 'authorized', 'session_id': None, **{f: None for f in SHIP_FIELDS}, 'is_gift_ship': None, 'shipping_fee': None, 'fulfillment_type': None, 'promo_code': None, 'device': None, 'register_id': None, 'employee_id': None, 'entry_method': None, 'tip_amount': None, 'receipt_type': None}
        if channel == 'online':
            sid = f'SESS{next(session_counter):06d}'
            fulfillment = str(np.random.choice(['ship', 'pickup_in_store'], p=[0.85, 0.15]))
            free_ship = fulfillment == 'pickup_in_store' or subtotal >= FREE_SHIP_THRESHOLD
            device = str(np.random.choice(DEVICES, p=DEVICE_W))
            gift = customer is None or random.random() < GIFT_SHIP_RATE
            ship_to = sample_address('shipping_') if gift else copy_address(customer)
            row.update({'session_id': sid, **ship_to, 'is_gift_ship': gift, 'shipping_fee': 0.0 if free_ship else SHIPPING_FEE, 'fulfillment_type': fulfillment, 'promo_code': random.choice(PROMO_CODES) if discount > 0 else None, 'device': device})
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
    orders_df['is_gift_ship'] = orders_df['is_gift_ship'].astype('boolean')
    order_items_df = pd.DataFrame(oi_rows)
    online_mask = orders_df['channel'] == 'online'
    print(f'orders={len(orders_df)}  order_items={len(order_items_df)}')
    print(orders_df['channel'].value_counts().to_string())
    print(f'anonymous in-store={n_anon_instore}  guest online={n_guest_online}')
    print(f"online orders run {orders_df.loc[online_mask, 'order_date'].min()} -> {orders_df.loc[online_mask, 'order_date'].max()}")  # in-store-only
    print(f"shipped to an address other than the buyer's: {int(orders_df['is_gift_ship'].sum())} of {online_mask.sum()}")
    # Pass 1 — attributable orders. The channel split is allocated exactly rather than drawn
    # per order, so the mix still holds at small N.
    # Pass 2 — anonymous walk-ins and guest checkouts, sized to hit the identity-capture rates
    # object dtype would make `~is_gift_ship` invert to ints rather than negate
    # rows are date-sorted, so every online order sits at the tail — preview both channels
    pd.concat([orders_df[~online_mask].head(6), orders_df[online_mask].head(6)])  # gift orders ship somewhere other than the buyer's own address  # a digital receipt is what links a walk-in to a customer record
    return order_items_df, orders_df, sess_rows, session_counter


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
    ## Dataset checks
    Confirm the five DataFrames, verify the KPI targets, and assert the numeric, channel, and
    timing rules hold — including that no in-store order lands outside store hours and no online
    order predates launch.
    """)
    return


@app.cell
def _(
    LAUNCH_DATE,
    STATE_ZIP_PREFIX,
    STORE_CLOSE_HOUR,
    STORE_OPEN_HOUR,
    TODAY,
    customers_df,
    np,
    order_items_df,
    orders_df,
    pd,
    products_df,
    sessions_df,
):
    tables = {'customers': customers_df, 'orders': orders_df, 'order_items': order_items_df, 'products': products_df, 'sessions': sessions_df}
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
    print('\nShip-to states (online)')
    print(online['shipping_state'].value_counts().to_string())
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
    online_only = ['session_id', 'shipping_address_line1', 'shipping_city', 'shipping_state', 'shipping_zip', 'shipping_fee', 'fulfillment_type', 'device']
    # --- Best sellers / Pareto ---
    instore_only = ['register_id', 'employee_id', 'tip_amount', 'receipt_type']
    assert instore[online_only].isna().all().all()
    assert online[instore_only].isna().all().all()
    assert online['session_id'].notna().all()
    assert online['session_id'].isin(sessions_df['session_id']).all()
    assert sessions_df.loc[sessions_df['session_id'].isin(online['session_id']), 'converted'].all()
    assert int(sessions_df['converted'].sum()) == len(online)
    for df_, state_col, zip_col in [(customers_df, 'state', 'zip'), (online, 'shipping_state', 'shipping_zip')]:
        assert df_.apply(lambda r: r[zip_col].startswith(STATE_ZIP_PREFIX[r[state_col]]), axis=1).all()
    known_direct = online[online['customer_id'].notna() & ~online['is_gift_ship']]
    merged = known_direct.merge(customers_df, on='customer_id', suffixes=('', '_cust'))
    assert (merged['shipping_address_line1'] == merged['address_line1']).all()
    assert (merged['shipping_zip'] == merged['zip']).all()
    assert instore['hour_of_day'].between(STORE_OPEN_HOUR, STORE_CLOSE_HOUR - 1).all()
    assert (online['order_datetime'] >= LAUNCH_DATE).all()
    # --- Integrity checks ---
    assert (orders_df['order_datetime'] <= TODAY + pd.Timedelta(days=1)).all()
    assert (customers_df['total_orders'] == orders_df['customer_id'].value_counts().reindex(customers_df['customer_id']).values).all()
    # channel exclusivity
    # addresses: state/zip agree, and non-gift orders ship to the buyer's address on file
    # timing rules
    print('\nIntegrity checks passed: money, FKs, channel exclusivity, addresses, store hours, and launch date all consistent.')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Executive KPI summary

    Funnel measures use website sessions and online orders only. Sales, product, and customer
    measures include both online and in-store activity unless stated otherwise.
    """)
    return


@app.cell
def _(
    alt,
    customers_df,
    mo,
    order_items_df,
    orders_df,
    pd,
    products_df,
    sessions_df,
):
    online_orders = orders_df[orders_df["channel"] == "online"].copy()
    authorized_orders = orders_df[orders_df["payment_status"] == "authorized"].copy()
    product_sales = (
        order_items_df.merge(products_df, on="product_id", how="left")
        .groupby(["product_id", "product_name", "category", "price_band"], as_index=False)
        .agg(units=("quantity", "sum"), revenue=("line_total", "sum"))
    )
    conversion_rate = len(online_orders) / len(sessions_df)
    carts_created = int(sessions_df["reached_cart"].sum())
    cart_abandonment = 1 - sessions_df["converted"].sum() / carts_created
    average_order_value = authorized_orders["order_total"].mean()
    repeat_purchase_rate = (customers_df["total_orders"] >= 2).mean()
    top_sku_count = max(1, round(len(products_df) * 0.20))
    revenue_concentration = product_sales.nlargest(top_sku_count, "revenue")["revenue"].sum() / product_sales["revenue"].sum()

    def make_chart(spec):
        return mo.ui.altair_chart(spec.properties(width="container", height=280))

    cards = mo.md(
        f"""<div style="display:grid;grid-template-columns:repeat(4,minmax(145px,1fr));gap:12px;margin:12px 0 24px;">
    <div style="border:1px solid #d8dee8;border-top:4px solid #176b87;padding:14px;"><strong>Conversion rate</strong><br><span style="font-size:1.7rem;">{conversion_rate:.1%}</span><br><small>Target: 1.5% to 2.0%</small></div>
    <div style="border:1px solid #d8dee8;border-top:4px solid #d27d2d;padding:14px;"><strong>Average order value</strong><br><span style="font-size:1.7rem;">${average_order_value:,.0f}</span><br><small>Authorized orders</small></div>
    <div style="border:1px solid #d8dee8;border-top:4px solid #176b87;padding:14px;"><strong>Cart abandonment</strong><br><span style="font-size:1.7rem;">{cart_abandonment:.1%}</span><br><small>Target: 70% or lower</small></div>
    <div style="border:1px solid #d8dee8;border-top:4px solid #d27d2d;padding:14px;"><strong>Repeat purchase rate</strong><br><span style="font-size:1.7rem;">{repeat_purchase_rate:.1%}</span><br><small>Target: 20% or higher</small></div>
    </div>"""
    )

    funnel_data = pd.DataFrame({"stage": ["All sessions", "Reached cart", "Completed purchase"], "count": [len(sessions_df), carts_created, int(sessions_df["converted"].sum())]})
    funnel_chart = make_chart(alt.Chart(funnel_data).mark_bar(color="#176b87").encode(
        x=alt.X("count:Q", title="Sessions"),
        y=alt.Y("stage:N", sort=["All sessions", "Reached cart", "Completed purchase"], title=None),
        tooltip=[alt.Tooltip("stage:N", title="Stage"), alt.Tooltip("count:Q", title="Sessions", format=",")],
    ).properties(title="Website funnel"))

    price_band_data = product_sales.groupby("price_band", as_index=False).agg(revenue=("revenue", "sum"), units=("units", "sum"))
    price_chart = make_chart(alt.Chart(price_band_data).mark_bar(color="#d27d2d").encode(
        x=alt.X("price_band:N", title="Price band", sort=["<$50", "$50-100", "$100-200", "$200+"]),
        y=alt.Y("revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0f")),
        tooltip=[alt.Tooltip("price_band:N", title="Price band"), alt.Tooltip("revenue:Q", title="Revenue", format="$,.2f"), alt.Tooltip("units:Q", title="Units sold", format=",")],
    ).properties(title="Revenue by price band"))

    top_sellers = product_sales.nlargest(10, "revenue").sort_values("revenue")
    top_sellers_chart = make_chart(alt.Chart(top_sellers).mark_bar(color="#176b87").encode(
        x=alt.X("revenue:Q", title="Revenue", axis=alt.Axis(format="$,.0f")),
        y=alt.Y("product_name:N", sort=None, title=None),
        tooltip=[alt.Tooltip("product_name:N", title="Product"), alt.Tooltip("units:Q", title="Units sold", format=","), alt.Tooltip("revenue:Q", title="Revenue", format="$,.2f")],
    ).properties(title="Top 10 products by revenue"))

    category_data = product_sales.groupby("category", as_index=False).agg(revenue=("revenue", "sum"))
    category_data["share"] = category_data["revenue"] / category_data["revenue"].sum()
    category_chart = make_chart(alt.Chart(category_data).mark_arc(innerRadius=55).encode(
        theta="revenue:Q",
        color=alt.Color("category:N", title="Category", scale=alt.Scale(range=["#176b87", "#d27d2d", "#5b9a6f", "#b4506d", "#6a7892"])),
        tooltip=[alt.Tooltip("category:N", title="Category"), alt.Tooltip("revenue:Q", title="Revenue", format="$,.2f"), alt.Tooltip("share:Q", title="Revenue share", format=".1%")],
    ).properties(title="Category mix by revenue"))

    age_orders = authorized_orders.dropna(subset=["customer_id"]).merge(customers_df[["customer_id", "age_band"]], on="customer_id", how="left").dropna(subset=["age_band"])
    age_data = age_orders.groupby("age_band", as_index=False).agg(orders=("transaction_id", "count"), aov=("order_total", "mean"))
    age_chart = make_chart(alt.Chart(age_data).mark_bar(color="#5b9a6f").encode(
        x=alt.X("age_band:N", title="Age band", sort=["18-24", "25-34", "35-44", "45+"]),
        y=alt.Y("aov:Q", title="Average order value", axis=alt.Axis(format="$,.0f")),
        tooltip=[alt.Tooltip("age_band:N", title="Age band"), alt.Tooltip("orders:Q", title="Orders", format=","), alt.Tooltip("aov:Q", title="AOV", format="$,.2f")],
    ).properties(title="Customer value by age band"))

    location_data = online_orders.groupby("shipping_state", dropna=True, as_index=False).agg(orders=("transaction_id", "count"), revenue=("order_total", "sum")).sort_values("revenue", ascending=False)
    location_chart = make_chart(alt.Chart(location_data).mark_bar(color="#b4506d").encode(
        x=alt.X("shipping_state:N", title="Shipping state"),
        y=alt.Y("revenue:Q", title="Online revenue", axis=alt.Axis(format="$,.0f")),
        tooltip=[alt.Tooltip("shipping_state:N", title="State"), alt.Tooltip("orders:Q", title="Orders", format=","), alt.Tooltip("revenue:Q", title="Revenue", format="$,.2f")],
    ).properties(title="Online sales by shipping state"))

    pricing_view = mo.vstack([price_chart, mo.md("**Price elasticity:** not available yet. It requires product-level price changes and enough history to compare demand before and after each change.")])
    products_view = mo.vstack([top_sellers_chart, category_chart, mo.md(f"**Revenue concentration:** the top {top_sku_count} products, 20% of the catalog, contribute **{revenue_concentration:.1%}** of item revenue.")])
    customers_view = mo.vstack([age_chart, location_chart, mo.md("Age analysis excludes customers without a recorded birthdate. Location is based on online shipping destinations.")])
    mo.vstack([cards, mo.ui.tabs({"Funnel": funnel_chart, "Pricing": pricing_view, "Products": products_view, "Customers": customers_view})])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Explore the data

    Each tab represents one part of the business. Use the table controls to browse, sort, and
    filter the sample records.
    """)
    return


@app.cell
def _(customers_df, mo, order_items_df, orders_df, products_df, sessions_df):
    table_views = {
        "Customers": mo.ui.table(customers_df, page_size=10, pagination=True, label="Customers"),
        "Orders": mo.ui.table(orders_df, page_size=10, pagination=True, label="Orders"),
        "Order items": mo.ui.table(order_items_df, page_size=10, pagination=True, label="Order items"),
        "Products": mo.ui.table(products_df, page_size=10, pagination=True, label="Products"),
        "Website sessions": mo.ui.table(sessions_df, page_size=10, pagination=True, label="Website sessions"),
    }
    mo.ui.tabs(table_views)
    return


if __name__ == "__main__":
    app.run()
