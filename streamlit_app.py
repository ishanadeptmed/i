"""Metro store earnings — Streamlit app."""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st

# Initialize logging and src path before other local imports
import services.bootstrap  # noqa: F401
from Drug_EDA.exception import customexception, format_error
from services.bootstrap import LOG_FILEPATH, get_logger
from services import auth
from services.files import (
    cleanup_on_logout,
    list_available_periods,
    list_period_files,
    parse_period,
    period_key,
    process_period,
    raw_paths,
    read_file_bytes,
    save_uploaded_file,
    tail_log_file,
)
from services.files import load_merged_csv, load_summary

logger = get_logger("streamlit_app")

st.set_page_config(page_title="Metro Earnings", page_icon="📊", layout="wide")

SESSION_DEFAULTS = {
    "authenticated": False,
    "role": None,
    "email": None,
    "owner_email": None,
    "store_ids": [],
    "page": "login",
}


def init_session() -> None:
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def require_manager() -> bool:
    return bool(st.session_state.get("authenticated") and st.session_state.get("role") == "manager")


def set_manager_session(session: dict) -> None:
    st.session_state.authenticated = True
    st.session_state.role = session["role"]
    st.session_state.email = session["email"]
    st.session_state.owner_email = session["owner_email"]
    st.session_state.store_ids = session["store_ids"]
    st.session_state.page = "upload"
    logger.info("Session started for manager %s", session["email"])


def logout() -> None:
    logger.info("User logout: %s", st.session_state.get("email"))
    try:
        cleanup_on_logout()
    except Exception as exc:
        logger.exception("Logout cleanup failed")
        st.sidebar.error(format_error(exc))
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session()


def sidebar_log_panel() -> None:
    with st.sidebar.expander("Activity log (this session)", expanded=False):
        st.caption(f"Full log file:\n`{LOG_FILEPATH}`")
        st.code(tail_log_file(LOG_FILEPATH), language=None)


def sidebar_nav() -> None:
    sidebar_log_panel()

    if not require_manager():
        return

    st.sidebar.title("Metro Earnings")
    st.sidebar.caption(f"Manager: {st.session_state.email}")
    st.sidebar.caption(f"Stores: {', '.join(st.session_state.store_ids)}")

    pages = {
        "upload": "Upload files",
        "preview": "Preview / download",
        "dashboard": "Dashboard",
    }
    choice = st.sidebar.radio(
        "Navigation",
        options=list(pages.keys()),
        format_func=lambda k: pages[k],
        index=list(pages.keys()).index(st.session_state.get("page", "upload")),
    )
    st.session_state.page = choice

    if st.sidebar.button("Logout", type="primary"):
        logout()
        st.rerun()


def page_login() -> None:
    st.title("Login")
    tab_owner, tab_mgr_signup, tab_mgr_login = st.tabs(
        ["Store owner signup", "Store manager signup", "Store manager login"]
    )

    with tab_owner:
        st.subheader("Store owner signup")
        with st.form("owner_signup"):
            email = st.text_input("Owner email")
            password = st.text_input("Password", type="password")
            store_ids = st.text_input("Store IDs (comma-separated)")
            manager_emails = st.text_input("Manager emails (comma-separated)")
            submitted = st.form_submit_button("Create owner account")
            if submitted:
                try:
                    ok, msg = auth.signup_owner(email, password, store_ids, manager_emails)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                except customexception as exc:
                    logger.exception("Owner signup UI error")
                    st.error(str(exc))
                except Exception as exc:
                    logger.exception("Owner signup unexpected error")
                    st.error(format_error(exc))

    with tab_mgr_signup:
        st.subheader("Store manager signup")
        st.caption("Your email must be listed by a store owner before you can sign up.")
        with st.form("manager_signup"):
            email = st.text_input("Manager email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Create manager account")
            if submitted:
                try:
                    ok, msg = auth.signup_manager(email, password)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                except customexception as exc:
                    logger.exception("Manager signup UI error")
                    st.error(str(exc))
                except Exception as exc:
                    logger.exception("Manager signup unexpected error")
                    st.error(format_error(exc))

    with tab_mgr_login:
        st.subheader("Store manager login")
        with st.form("manager_login"):
            email = st.text_input("Manager email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
            if submitted:
                try:
                    ok, msg, session = auth.login_manager(email, password)
                    if ok and session:
                        set_manager_session(session)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                except customexception as exc:
                    logger.exception("Manager login UI error")
                    st.error(str(exc))
                except Exception as exc:
                    logger.exception("Manager login unexpected error")
                    st.error(format_error(exc))


def page_upload() -> None:
    st.title("Upload files")
    now = datetime.now()
    col_y, col_m = st.columns(2)
    with col_y:
        year = st.selectbox("Year", options=list(range(now.year - 2, now.year + 2)), index=2)
    with col_m:
        month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            format_func=lambda m: datetime(2000, m, 1).strftime("%B"),
            index=now.month - 1,
        )

    st.info(f"Files will be saved under `uploads/raw/{period_key(year, month)}/`")

    paths = raw_paths(year, month)
    existing = {k: os.path.isfile(p) for k, p in paths.items()}
    if any(existing.values()):
        st.caption(
            "Existing files: "
            + ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in existing.items())
        )

    activation = st.file_uploader("Activation Detail Report", type=["csv"])
    cur_callidus = st.file_uploader("curCallidus Report", type=["csv"])
    callidus_detail = st.file_uploader("Callidus Detail Report", type=["csv"])

    if st.button("Save uploaded files", type="secondary"):
        try:
            saved = 0
            uploads = {
                "activation": activation,
                "cur_callidus": cur_callidus,
                "callidus_detail": callidus_detail,
            }
            for key, uploaded in uploads.items():
                if uploaded is not None:
                    save_uploaded_file(uploaded, paths[key])
                    saved += 1
            if saved:
                st.success(f"Saved {saved} file(s) for {period_key(year, month)}.")
            else:
                st.warning("Select at least one file to save.")
        except customexception as exc:
            logger.exception("Save upload failed")
            st.error(str(exc))
        except Exception as exc:
            logger.exception("Save upload unexpected error")
            st.error(format_error(exc))

    if st.button("Process files", type="primary"):
        try:
            ok, msg = process_period(
                year,
                month,
                st.session_state.email,
                st.session_state.store_ids,
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)
        except customexception as exc:
            logger.exception("Process UI error")
            st.error(str(exc))
        except Exception as exc:
            logger.exception("Process unexpected error")
            st.error(format_error(exc))


def page_preview() -> None:
    st.title("Preview / download")
    try:
        periods = list_available_periods()
        if not periods:
            st.warning("No data yet. Upload and process files first.")
            return

        period = st.selectbox("Period", periods)

        files = list_period_files(period)
        if files:
            st.subheader("Download")
            for label, path in files:
                data = read_file_bytes(path)
                if data:
                    st.download_button(
                        label=f"Download {label}",
                        data=data,
                        file_name=os.path.basename(path),
                        key=f"dl_{label}_{period}",
                    )

        st.subheader("Raw previews")
        raw_dir_files = [(l, p) for l, p in files if l.startswith("raw/")]
        for label, path in raw_dir_files:
            if path.endswith(".csv"):
                try:
                    df = pd.read_csv(path, nrows=200, encoding="latin1")
                    st.markdown(f"**{label}**")
                    st.dataframe(df, use_container_width=True)
                except Exception as exc:
                    logger.exception("Preview failed for %s", label)
                    st.error(f"Could not preview {label}: {format_error(exc)}")

        st.subheader("Processed preview")
        merged = load_merged_csv(period)
        if merged is not None:
            st.dataframe(merged.head(200), use_container_width=True)
        else:
            st.info("No processed merged file for this period.")

        summary = load_summary(period)
        if summary:
            st.subheader("Summary JSON")
            st.json(summary)
    except customexception as exc:
        logger.exception("Preview page error")
        st.error(str(exc))
    except Exception as exc:
        logger.exception("Preview page unexpected error")
        st.error(format_error(exc))


def page_dashboard() -> None:
    st.title("Monthly earnings dashboard")
    try:
        periods = list_available_periods()
        proc_periods = [p for p in periods if load_summary(p) is not None]
        if not proc_periods:
            st.warning("No processed data yet. Upload files and run Process on the Upload page.")
            return

        period = st.selectbox("Period", proc_periods)
        summary = load_summary(period)
        merged = load_merged_csv(period)

        if not summary:
            st.error("Summary not found for this period.")
            return

        c1, c2, c3 = st.columns(3)
        c1.metric("Total compensation", f"${summary['total_compensation']:,.2f}")
        c2.metric("Activations", summary["activation_count"])
        c3.metric("Chargebacks", summary["chargeback_count"])

        if merged is not None and not merged.empty:
            by_store = merged.groupby("storeid")["Compensation"].sum().reset_index()
            st.subheader("Compensation by store")
            st.bar_chart(by_store, x="storeid", y="Compensation")

            st.subheader("Top activations by compensation")
            top = merged.nlargest(20, "Compensation")
            st.dataframe(top, use_container_width=True)
        else:
            by_store_records = summary.get("by_store", [])
            if by_store_records:
                st.subheader("Compensation by store")
                st.bar_chart(
                    pd.DataFrame(by_store_records),
                    x="storeid",
                    y="Compensation",
                )
        logger.info("Dashboard rendered for period %s", period)
    except customexception as exc:
        logger.exception("Dashboard page error")
        st.error(str(exc))
    except Exception as exc:
        logger.exception("Dashboard page unexpected error")
        st.error(format_error(exc))


def main() -> None:
    logger.info("App starting")
    init_session()
    sidebar_nav()

    if not require_manager():
        page_login()
        return

    page = st.session_state.get("page", "upload")
    if page == "upload":
        page_upload()
    elif page == "preview":
        page_preview()
    elif page == "dashboard":
        page_dashboard()
    else:
        page_upload()


if __name__ == "__main__":
    main()
