"""Personal Subscription Tracker - Streamlit + MySQL."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

import db

st.set_page_config(page_title="Subscription Tracker", page_icon="💳", layout="wide")

CYCLES = ["weekly", "monthly", "quarterly", "yearly"]
STATUSES = ["active", "paused", "cancelled"]
MONTHLY_FACTOR = {"weekly": 52 / 12, "monthly": 1, "quarterly": 1 / 3, "yearly": 1 / 12}


# ---------- Setup ----------
@st.cache_resource
def setup():
    db.init_db()
    return True


try:
    setup()
except Exception as e:
    st.error(f"Could not connect to MySQL: {e}")
    st.info("Check your .env file (DB_HOST, DB_USER, DB_PASSWORD) and make sure MySQL is running.")
    st.stop()


# ---------- Helpers ----------
def next_renewal(start, cycle, today=None):
    today = today or date.today()
    if start >= today:
        return start
    if cycle == "weekly":
        n = -(-(today - start).days // 7)
        return start + timedelta(weeks=n)
    step = {"monthly": 1, "quarterly": 3, "yearly": 12}[cycle]
    months = (today.year - start.year) * 12 + (today.month - start.month)
    n = max(0, months // step * step)
    d = start + relativedelta(months=n)
    while d < today:
        n += step
        d = start + relativedelta(months=n)
    return d


def load_df():
    rows = db.get_subscriptions()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["cost"] = df["cost"].astype(float)
    df["category"] = df["category"].fillna("Uncategorized")
    df["monthly_cost"] = df.apply(lambda r: r["cost"] * MONTHLY_FACTOR[r["billing_cycle"]], axis=1)
    df["next_renewal"] = df.apply(lambda r: next_renewal(r["start_date"], r["billing_cycle"]), axis=1)
    df["days_left"] = df["next_renewal"].apply(lambda d: (d - date.today()).days)
    return df


# ---------- Pages ----------
def page_dashboard():
    st.title("💳 Subscription Dashboard")
    df = load_df()
    if df.empty:
        st.info("No subscriptions yet. Add your first one from the sidebar.")
        return

    active = df[df["status"] == "active"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monthly spend", f"{active['monthly_cost'].sum():,.2f}")
    c2.metric("Yearly spend", f"{active['monthly_cost'].sum() * 12:,.2f}")
    c3.metric("Active subscriptions", len(active))
    c4.metric("Renewing in 7 days", int((active["days_left"] <= 7).sum()))

    left, right = st.columns(2)
    with left:
        st.subheader("Upcoming renewals (30 days)")
        up = active[active["days_left"] <= 30].sort_values("next_renewal")
        if up.empty:
            st.write("Nothing renewing in the next 30 days.")
        else:
            st.dataframe(
                up[["name", "cost", "billing_cycle", "next_renewal", "days_left"]],
                hide_index=True, use_container_width=True,
            )
    with right:
        st.subheader("Monthly spend by category")
        by_cat = active.groupby("category")["monthly_cost"].sum().sort_values(ascending=False)
        if by_cat.empty:
            st.write("No active subscriptions.")
        else:
            st.bar_chart(by_cat)

    st.subheader("🔪 Cancel candidates")
    threshold = st.slider("Flag active subscriptions used this many times or fewer in the last 30 days",
                          0, 10, 2)
    cand = active[active["uses_30d"] <= threshold].copy()
    if cand.empty:
        st.success("Nothing to cancel. You're using everything you pay for.")
    else:
        cand["cost_per_use"] = cand.apply(
            lambda r: round(r["monthly_cost"] / r["uses_30d"], 2) if r["uses_30d"] > 0 else None, axis=1)
        st.dataframe(
            cand[["name", "category", "monthly_cost", "uses_30d", "cost_per_use"]]
            .sort_values("monthly_cost", ascending=False),
            hide_index=True, use_container_width=True,
        )
        st.warning(f"Cancelling all of these would save about {cand['monthly_cost'].sum():,.2f} per month "
                   f"({cand['monthly_cost'].sum() * 12:,.2f} per year).")
        st.caption("Log usage on the 'Log Usage' page so this list stays accurate.")


def page_add():
    st.title("➕ Add Subscription")
    cats = db.get_categories()
    cat_names = [c["name"] for c in cats]
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Name (e.g. Netflix)")
        col1, col2 = st.columns(2)
        category = col1.selectbox("Category", cat_names)
        new_cat = col2.text_input("...or new category (optional)")
        col3, col4, col5 = st.columns(3)
        cost = col3.number_input("Cost", min_value=0.0, step=1.0, format="%.2f")
        cycle = col4.selectbox("Billing cycle", CYCLES, index=1)
        start = col5.date_input("First billing date", value=date.today())
        notes = st.text_input("Notes (optional)")
        submitted = st.form_submit_button("Add subscription")

    if submitted:
        if not name.strip():
            st.error("Please enter a name.")
            return
        if new_cat.strip():
            cat_id = db.get_or_create_category(new_cat)
        else:
            cat_id = next(c["id"] for c in cats if c["name"] == category)
        db.add_subscription(name.strip(), cat_id, cost, cycle, start, notes)
        st.success(f"Added {name.strip()}.")


def page_manage():
    st.title("🛠 Manage Subscriptions")
    df = load_df()
    if df.empty:
        st.info("Nothing to manage yet.")
        return

    st.dataframe(
        df[["id", "name", "category", "cost", "billing_cycle", "status", "next_renewal", "monthly_cost"]],
        hide_index=True, use_container_width=True,
    )

    st.subheader("Edit or delete")
    labels = {int(r["id"]): f"{r['name']} (#{r['id']})" for _, r in df.iterrows()}
    sub_id = st.selectbox("Choose a subscription", list(labels), format_func=lambda i: labels[i])
    row = df[df["id"] == sub_id].iloc[0]

    cats = db.get_categories()
    cat_names = [c["name"] for c in cats]
    cur_cat = row["category"] if row["category"] in cat_names else cat_names[0]

    with st.form("edit_form"):
        name = st.text_input("Name", value=row["name"])
        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", cat_names, index=cat_names.index(cur_cat))
        status = c2.selectbox("Status", STATUSES, index=STATUSES.index(row["status"]))
        c3, c4, c5 = st.columns(3)
        cost = c3.number_input("Cost", min_value=0.0, step=1.0, value=float(row["cost"]), format="%.2f")
        cycle = c4.selectbox("Billing cycle", CYCLES, index=CYCLES.index(row["billing_cycle"]))
        start = c5.date_input("First billing date", value=row["start_date"])
        notes = st.text_input("Notes", value=row["notes"] or "")
        save = st.form_submit_button("Save changes")

    if save:
        cat_id = next(c["id"] for c in cats if c["name"] == category)
        db.update_subscription(int(sub_id), name.strip(), cat_id, cost, cycle, start, status, notes)
        st.success("Saved. Refresh the page to see updated values in the table.")

    confirm = st.checkbox("I want to permanently delete this subscription")
    if st.button("Delete", disabled=not confirm):
        db.delete_subscription(int(sub_id))
        st.success("Deleted. Refresh the page.")


def page_usage():
    st.title("📝 Log Usage")
    df = load_df()
    active = df[df["status"] == "active"] if not df.empty else df
    if active.empty:
        st.info("Add an active subscription first.")
        return

    labels = {int(r["id"]): r["name"] for _, r in active.iterrows()}
    with st.form("usage_form"):
        sub_id = st.selectbox("Which subscription did you use?", list(labels), format_func=lambda i: labels[i])
        used_on = st.date_input("Date", value=date.today())
        ok = st.form_submit_button("Log usage")
    if ok:
        db.log_usage(int(sub_id), used_on)
        st.success(f"Logged use of {labels[sub_id]} on {used_on}.")

    st.subheader("Recent usage")
    recent = db.get_recent_usage()
    if recent:
        st.dataframe(pd.DataFrame(recent), hide_index=True, use_container_width=True)
    else:
        st.write("No usage logged yet.")


# ---------- Navigation ----------
PAGES = {
    "Dashboard": page_dashboard,
    "Add Subscription": page_add,
    "Manage": page_manage,
    "Log Usage": page_usage,
}
choice = st.sidebar.radio("Go to", list(PAGES))
PAGES[choice]()
