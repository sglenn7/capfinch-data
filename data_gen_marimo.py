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
    # CapFinch Online Platform — Synthetic Data Generator

    Builds a small, internally-consistent fake e-commerce dataset (6 tables) to develop and test
    the analytics / KPI pipeline **before** the real store launches.

    **Two anchor keys**
    - `transaction_id` — PK of `orders` (one row per completed sale → revenue, AOV)
    - `customer_id` — PK of `customers` (one row per person → repeat rate, demographics)

    They join via `customer_id` (FK inside `orders`).

    **Relationship chain**
    ```
    customers ─┬─ sessions ── events
               └─ orders ── order_items ── products
    ```

    **KPI targets baked into the generator (by construction)**
    | Metric | Target |
    |---|---|
    | Conversion rate (orders / sessions) | ~2% |
    | Cart abandonment (1 − completed/carts) | ~68% |
    | Repeat purchase (customers with ≥2 orders) | ~20% |

    Everything is produced as a pandas `DataFrame` first (no CSV yet). Scale up later by raising
    `N_CUSTOMERS` — the ratios above are preserved. A commented CSV-export cell is at the bottom.
    """)
    return


@app.cell
def _():
    # If the libraries are not installed, uncomment the next line:
    # %pip install faker pandas numpy
    #h

    import random

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
    return fake, np, pd, random


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Config & KPI targets

    `N_CUSTOMERS` is the single knob for dataset size. Repeat buyers get a 2nd order, so total
    orders ≈ `N_CUSTOMERS × (1 + repeat_rate)`. Session and cart counts are derived from the orders
    so the conversion (~2%) and abandonment (~68%) targets hold at any scale.
    """)
    return


@app.cell
def _():
    # ---- Scale (raise this to grow every table; KPI ratios are preserved) ----
    N_CUSTOMERS = 15
    N_PRODUCTS = 12

    # ---- KPI targets ----
    TARGET_CONVERSION = 0.02   # orders / total sessions
    TARGET_ABANDONMENT = 0.68  # 1 - completed_carts / carts_created
    TARGET_REPEAT = 0.20       # share of customers with >= 2 orders

    # ---- Categorical vocabularies ----
    GENDERS = ["female", "male", "nonbinary"]
    ACQ_SOURCES = ["organic", "mailchimp", "social", "referral"]
    DEVICES = ["mobile", "desktop", "tablet"]
    PAYMENT_METHODS = ["card", "apple_pay", "paypal"]
    LANDING_PAGES = ["/", "/new-arrivals", "/sale", "/collections/best-sellers", "/product"]
    EVENT_TYPES = ["page_view", "product_view", "add_to_cart", "checkout_start", "purchase"]

    repeat_customers = round(N_CUSTOMERS * TARGET_REPEAT)
    print(f"Config: {N_CUSTOMERS} customers ({repeat_customers} repeat buyers), {N_PRODUCTS} products")
    return (
        ACQ_SOURCES,
        DEVICES,
        GENDERS,
        LANDING_PAGES,
        N_CUSTOMERS,
        N_PRODUCTS,
        PAYMENT_METHODS,
        TARGET_ABANDONMENT,
        TARGET_CONVERSION,
        repeat_customers,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 4 — `products`  [PK: product_id]
    Built first because orders/order_items and events reference it.
    """)
    return


@app.cell
def _(N_PRODUCTS, np, pd):
    CATALOG = [('Linen Button Shirt', 'Apparel'), ('Merino Wool Sweater', 'Apparel'), ('Slim Fit Chinos', 'Apparel'), ('Silk Scarf', 'Accessories'), ('Leather Belt', 'Accessories'), ('Canvas Tote Bag', 'Accessories'), ('Suede Loafers', 'Footwear'), ('Leather Sneakers', 'Footwear'), ('Scented Soy Candle', 'Home'), ('Ceramic Mug Set', 'Home'), ('Vitamin C Serum', 'Beauty'), ('Matte Lip Balm', 'Beauty')]

    def price_band(p):
        if p < 25:
            return '<$25'
        if p <= 75:
            return '$25-75'
        return '$75+'
    products = []
    for _i, (_name, cat) in enumerate(CATALOG[:N_PRODUCTS], start=1):
        price = round(np.random.uniform(12, 140), 2)
        products.append({'product_id': f'PROD{_i:04d}', 'product_name': _name, 'category': cat, 'price': price, 'price_band': price_band(price), 'cost': round(price * np.random.uniform(0.4, 0.6), 2), 'stock_on_hand': int(np.random.randint(0, 200))})
    products_df = pd.DataFrame(products)
    products_df
    return (products_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 1 — `customers`  [PK: customer_id]
    `total_orders` is assigned here (repeat buyers get 2). `first_order_date` is left blank now and
    filled in from the actual orders once they exist.
    """)
    return


@app.cell
def _(
    ACQ_SOURCES,
    GENDERS,
    N_CUSTOMERS,
    fake,
    np,
    pd,
    random,
    repeat_customers,
):
    def age_band(a):
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
    customers = []
    for _i in range(1, N_CUSTOMERS + 1):
        age = int(np.random.randint(18, 66))
        customers.append({'customer_id': f'CUST{_i:04d}', 'email': fake.unique.email(), 'age': age, 'age_band': age_band(age), 'gender': random.choice(GENDERS), 'state': fake.state_abbr(), 'zip': fake.zipcode(), 'signup_date': fake.date_between(start_date='-2y', end_date='-30d'), 'acquisition_source': random.choice(ACQ_SOURCES), 'first_order_date': pd.NaT, 'total_orders': order_counts[_i - 1]})
    customers_df = pd.DataFrame(customers)
    customers_df  # filled after orders are built
    return (customers_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Tables 2 & 3 — `orders` and `order_items`
    Each order expands from a customer's `total_orders`. Line items drive `order_total` (= sum of
    `line_total`) and `item_count`. Every order also creates its **converting session** so the
    funnel stays consistent.
    """)
    return


@app.cell
def _(
    DEVICES,
    LANDING_PAGES,
    PAYMENT_METHODS,
    customers_df,
    np,
    pd,
    products_df,
    random,
):
    order_rows, oi_rows, sess_rows = ([], [], [])
    order_seq = _sess_seq = 0
    product_ids = products_df['product_id'].tolist()
    price_lookup = products_df.set_index('product_id')['price'].to_dict()
    for _, cust in customers_df.iterrows():
        n = int(cust['total_orders'])
        base = pd.to_datetime(cust['signup_date']) + pd.Timedelta(days=int(np.random.randint(1, 60)))
        dates = sorted(base + pd.to_timedelta(np.random.randint(0, 400, size=n), unit='D'))
        for k in range(n):
            order_seq += 1
            _sess_seq += 1
            tid = f'TXN{order_seq:05d}'
            sid = f'SESS{_sess_seq:06d}'
            order_dt = pd.to_datetime(dates[k]) + pd.Timedelta(minutes=int(np.random.randint(2, 40)))
            n_items = int(np.random.randint(1, 5))
            chosen = np.random.choice(product_ids, size=n_items, replace=False)
            order_total, total_qty = (0.0, 0)
            for pid in chosen:
                qty = int(np.random.randint(1, 4))  # line items
                unit = float(price_lookup[pid])
                line = round(qty * unit, 2)
                order_total += line
                total_qty += qty
                oi_rows.append({'order_item_id': f'OI{len(oi_rows) + 1:06d}', 'transaction_id': tid, 'product_id': str(pid), 'quantity': qty, 'unit_price': unit, 'line_total': line})
            order_total = round(order_total, 2)
            order_rows.append({'transaction_id': tid, 'customer_id': cust['customer_id'], 'session_id': sid, 'order_date': order_dt, 'order_total': order_total, 'item_count': total_qty, 'payment_method': random.choice(PAYMENT_METHODS), 'payment_status': np.random.choice(['authorized', 'declined'], p=[0.95, 0.05]), 'shipping_state': cust['state'], 'discount_amount': round(order_total * np.random.choice([0, 0.05, 0.1], p=[0.7, 0.2, 0.1]), 2), 'is_first_order': k == 0})
            sess_rows.append({'session_id': sid, 'customer_id': cust['customer_id'], 'session_start': order_dt - pd.Timedelta(minutes=int(np.random.randint(3, 30))), 'device': random.choice(DEVICES), 'traffic_source': cust['acquisition_source'], 'landing_page': random.choice(LANDING_PAGES), 'reached_cart': True, 'converted': True})
    orders_df = pd.DataFrame(order_rows)
    order_items_df = pd.DataFrame(oi_rows)
    print(f'orders={len(orders_df)}  order_items={len(order_items_df)}')
    orders_df  # converting session tied to this order
    return order_items_df, orders_df, product_ids, sess_rows


@app.cell
def _(order_items_df):
    # order_items preview
    order_items_df.head(15)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Table 5 — `sessions`  [PK: session_id]
    The converting sessions already exist (one per order). Here we add **abandoned-cart** and
    **browse-only** sessions so the totals hit conversion ~2% and abandonment ~68%:

    - `total_carts = orders / (1 − 0.68)` → abandoned = carts − orders
    - `total_sessions = orders / 0.02` → browse-only = sessions − carts

    Some non-converting sessions are anonymous (`customer_id = None`).
    """)
    return


@app.cell
def _(
    ACQ_SOURCES,
    DEVICES,
    LANDING_PAGES,
    TARGET_ABANDONMENT,
    TARGET_CONVERSION,
    customers_df,
    fake,
    orders_df,
    pd,
    random,
    sess_rows,
    sess_seq,
):
    n_orders = len(orders_df)
    total_carts = round(n_orders / (1 - TARGET_ABANDONMENT))
    abandoned_carts = max(total_carts - n_orders, 0)
    total_sessions = round(n_orders / TARGET_CONVERSION)
    browse_sessions = max(total_sessions - total_carts, 0)
    cust_ids = customers_df['customer_id'].tolist()

    def make_session(reached_cart, converted):
        global sess_seq
        _sess_seq += 1
        cust_id = random.choice(cust_ids) if random.random() < 0.4 else None
        return {'session_id': f'SESS{_sess_seq:06d}', 'customer_id': cust_id, 'session_start': pd.to_datetime(fake.date_time_between(start_date='-1y', end_date='now')), 'device': random.choice(DEVICES), 'traffic_source': random.choice(ACQ_SOURCES), 'landing_page': random.choice(LANDING_PAGES), 'reached_cart': reached_cart, 'converted': converted}
    for _ in range(abandoned_carts):  # ~40% of non-converting traffic is a known customer, the rest is anonymous
        sess_rows.append(make_session(reached_cart=True, converted=False))
    for _ in range(browse_sessions):
        sess_rows.append(make_session(reached_cart=False, converted=False))
    sessions_df = pd.DataFrame(sess_rows).sort_values('session_start').reset_index(drop=True)
    print(f'sessions={len(sessions_df)}  carts={total_carts}  abandoned={abandoned_carts}  browse={browse_sessions}')
    sessions_df.head(15)
    return (sessions_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Back-fill `first_order_date`
    Now that orders exist, set each customer's first order date from their earliest order.
    """)
    return


@app.cell
def _(customers_df, orders_df, pd):
    first_orders = orders_df.groupby("customer_id")["order_date"].min()
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
def _(np, pd, product_ids, random, sessions_df):
    event_rows = []


    def add_event(session, etype, t, pid=None):
        event_rows.append({
            "event_id": f"EVT{len(event_rows) + 1:07d}",
            "session_id": session["session_id"],
            "event_type": etype,
            "product_id": pid,
            "event_time": t,
        })


    for _, s in sessions_df.iterrows():
        t = pd.to_datetime(s["session_start"])
        add_event(s, "page_view", t)

        for _ in range(int(np.random.randint(1, 4))):
            t += pd.Timedelta(seconds=int(np.random.randint(20, 180)))
            add_event(s, "product_view", t, random.choice(product_ids))

        if s["reached_cart"]:
            t += pd.Timedelta(seconds=int(np.random.randint(20, 120)))
            add_event(s, "add_to_cart", t, random.choice(product_ids))
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
    Confirm the six DataFrames, verify the KPI targets, and assert the numeric relationships hold.
    """)
    return


@app.cell
def _(
    customers_df,
    events_df,
    np,
    order_items_df,
    orders_df,
    products_df,
    sessions_df,
):
    tables = {'customers': customers_df, 'orders': orders_df, 'order_items': order_items_df, 'products': products_df, 'sessions': sessions_df, 'events': events_df}
    print('Table shapes')
    for _name, df in tables.items():
        print(f'  {_name:12s} rows={len(df):5d}  cols={len(df.columns)}')
    conversion = len(orders_df) / len(sessions_df)
    carts = int(sessions_df['reached_cart'].sum())
    abandonment = 1 - sessions_df['converted'].sum() / carts
    repeat = (customers_df['total_orders'] >= 2).mean()
    print('\nKPIs (actual vs target)')
    print(f'  Conversion rate : {conversion:6.2%}  (target ~2%)')
    print(f'  Cart abandonment: {abandonment:6.2%}  (target ~68%)')
    print(f'  Repeat purchase : {repeat:6.2%}  (target ~20%)')
    assert (order_items_df['line_total'] == (order_items_df['quantity'] * order_items_df['unit_price']).round(2)).all()
    # --- KPI check ---
    recon = order_items_df.groupby('transaction_id')['line_total'].sum().round(2)
    assert np.allclose(recon.values, orders_df.set_index('transaction_id').loc[recon.index, 'order_total'].values)
    assert orders_df['customer_id'].isin(customers_df['customer_id']).all()
    assert order_items_df['product_id'].isin(products_df['product_id']).all()
    # --- Integrity checks ---
    print('\nIntegrity checks passed: line totals, order totals, and FK references all consistent.')
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

