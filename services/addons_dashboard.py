"""Streamlit Add-ons Dashboard (graphs + drilldowns) for ingestion output."""

from __future__ import annotations

import pandas as pd
import streamlit as st


# =========================
# 1. Year-wise Revenue
# =========================
# def plot_yearly_revenue(df: pd.DataFrame, date_col: str | None = None):
#     st.subheader("📊 1. Year-wise Revenue")

#     if date_col and date_col in df.columns:
#         df = df.copy()
#         df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
#         df["year"] = df[date_col].dt.year

#         revenue_year = (
#             df.groupby("year", as_index=False)["Compensation"]
#             .sum()
#             .sort_values("year")
#         )

#         st.bar_chart(revenue_year, x="year", y="Compensation")

#     else:
#         st.warning("No valid date column provided. Showing total summary only.")
#         st.metric("Total Revenue", float(df["Compensation"].sum()))

def plot_yearly_revenue(df: pd.DataFrame, date_col: str | None = None):
    st.subheader("📊 1. Year-wise Revenue")
    
    if date_col and date_col in df.columns:
        try:
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df["year"] = df[date_col].dt.year
            
            # Remove rows without valid year
            df_valid = df[df["year"].notna()]
            
            if df_valid.empty:
                st.warning("Could not extract years from date column.")
                st.metric("Total Revenue", float(df["Compensation"].sum()))
                return
            
            revenue_year = (
                df_valid.groupby("year", as_index=False)["Compensation"]
                .sum()
                .sort_values("year")
            )
            
            if len(revenue_year) > 0:
                st.bar_chart(revenue_year, x="year", y="Compensation")
            else:
                st.warning("No revenue data grouped by year.")
                st.metric("Total Revenue", float(df["Compensation"].sum()))
                
        except Exception as e:
            st.error(f"Error processing dates: {str(e)}")
            st.metric("Total Revenue", float(df["Compensation"].sum()))
    else:
        st.warning("No valid date column provided. Showing total summary only.")
        st.metric("Total Revenue", float(df["Compensation"].sum()))

# =========================
# 2. Revenue by Store
# =========================
def plot_store_revenue(df: pd.DataFrame):
    st.subheader("🏬 2. Revenue by Store")

    revenue_store = (
        df.groupby("storeid", as_index=False)["Compensation"]
        .sum()
        .sort_values("Compensation", ascending=False)
    )

    st.dataframe(revenue_store)

    st.bar_chart(revenue_store, x="storeid", y="Compensation")


# =========================
# 3. Chargeback Serial List
# =========================
def show_chargebacks(df: pd.DataFrame):
    st.subheader("🚨 3. Serial List with Chargebacks")

    chargeback_df = df[df["Chargeback"].notna()].copy()

    if chargeback_df.empty:
        st.success("No chargebacks found 🎉")
        return

    chargeback_df = chargeback_df[
        ["storeid", "serial", "Compensation", "Rebate", "Chargeback"]
    ]

    st.dataframe(chargeback_df, use_container_width=True)


# =========================
# MASTER WRAPPER
# =========================
def render_dashboard(df: pd.DataFrame, date_col: str | None = None):
    """
    Call this from Streamlit app after ingestion.
    """
    st.title("📦 Add-ons Analytics Dashboard")

    plot_yearly_revenue(df, date_col=date_col)
    st.divider()

    plot_store_revenue(df)
    st.divider()

    show_chargebacks(df)