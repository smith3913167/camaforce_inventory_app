import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import base64
import altair as alt
import os
from supabase import create_client, Client

# 🔐 Supabase 설정 (여기에 본인의 프로젝트 URL과 서비스 키 입력)
SUPABASE_URL = https://ibotdnvtdlmmcrqtfsgx.supabase.co
SUPABASE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlib3RkbnZ0ZGxtbWNycXRmc2d4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTIyNDk3MywiZXhwIjoyMDYwODAwOTczfQ.C2ndSZGaNTeEAdzKTb8X9hr19Rokqy8obqgb33oq0aE
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Supabase에서 데이터 불러오기
def load_data():
    response = supabase.table("inventory").select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df = df.sort_values("id")
        st.session_state.inventory_df = df
        st.session_state.next_id = df["id"].max() + 1
    else:
        st.session_state.inventory_df = pd.DataFrame(columns=["id", "날짜", "카테고리", "시리즈명", "제품명", "특징", "코드", "컬러", "스마트스토어번호", "입출고", "수량", "메모"])
        st.session_state.next_id = 1

# Supabase에 데이터 저장
def save_data():
    latest = st.session_state.inventory_df.iloc[-1].to_dict()
    supabase.table("inventory").insert(latest).execute()

# 자동 저장
if "autosave" not in st.session_state:
    st.session_state.autosave = True

load_data()

st.title("CAMAFORCE 입출고 재고 관리")

# 탭 UI 구성
tabs = st.tabs(["📦 제품 등록 및 입출고", "📊 재고 현황 및 통계"])

# 첫 번째 탭: 제품 등록 및 입출고
with tabs[0]:
    with st.expander("➕ 제품 신규 등록", expanded=True):
        with st.form("register_form"):
            r_date = st.date_input("날짜", value=datetime.today())
            r_category = st.text_input("카테고리")
            r_series = st.text_input("시리즈명")
            r_product = st.text_input("제품명")
            r_feature = st.text_input("특징")
            r_code = st.text_input("코드번호")
            r_color = st.text_input("컬러")
            r_store = st.text_input("스마트스토어 상품번호")
            r_inout = st.radio("입출고", ["입고", "출고"], horizontal=True)
            r_qty = st.number_input("수량", min_value=1, step=1)
            r_memo = st.text_input("메모")
            submitted = st.form_submit_button("등록")

            if submitted:
                new_row = {
                    "id": int(st.session_state.next_id),
                    "날짜": r_date.strftime("%Y-%m-%d"),
                    "카테고리": r_category,
                    "시리즈명": r_series,
                    "제품명": r_product,
                    "특징": r_feature,
                    "코드": r_code,
                    "컬러": r_color,
                    "스마트스토어번호": r_store,
                    "입출고": r_inout,
                    "수량": r_qty if r_inout == "입고" else -r_qty,
                    "메모": r_memo
                }
                st.session_state.inventory_df = pd.concat([
                    st.session_state.inventory_df,
                    pd.DataFrame([new_row])
                ], ignore_index=True)
                st.session_state.next_id += 1
                if st.session_state.autosave:
                    save_data()
                st.success("제품이 등록되었습니다.")

    with st.expander("📥 등록된 제품 입고/출고 등록", expanded=True):
        if not st.session_state.inventory_df.empty:
            grouped = st.session_state.inventory_df.groupby(["시리즈명", "제품명", "컬러"])["수량"].sum().reset_index()
            product_options = grouped.apply(lambda row: f"{row['시리즈명']} - {row['제품명']} ({row['컬러']})", axis=1).tolist()
            selected_product = st.selectbox("제품 선택", product_options)

            if selected_product:
                selected = grouped.iloc[product_options.index(selected_product)]
                with st.form("inout_form"):
                    io_date = st.date_input("날짜", value=datetime.today(), key="inout_date")
                    io_inout = st.radio("입출고", ["입고", "출고"], horizontal=True, key="inout_type")
                    io_qty = st.number_input("수량", min_value=1, step=1, key="inout_qty")
                    io_memo = st.text_input("메모", key="inout_memo")
                    submit_io = st.form_submit_button("입출고 등록")

                    if submit_io:
                        new_io = {
                            "id": int(st.session_state.next_id),
                            "날짜": io_date.strftime("%Y-%m-%d"),
                            "카테고리": '',
                            "시리즈명": selected["시리즈명"],
                            "제품명": selected["제품명"],
                            "특징": '',
                            "코드": '',
                            "컬러": selected["컬러"],
                            "스마트스토어번호": '',
                            "입출고": io_inout,
                            "수량": io_qty if io_inout == "입고" else -io_qty,
                            "메모": io_memo
                        }
                        st.session_state.inventory_df = pd.concat([
                            st.session_state.inventory_df,
                            pd.DataFrame([new_io])
                        ], ignore_index=True)
                        st.session_state.next_id += 1
                        if st.session_state.autosave:
                            save_data()
                        st.success("입출고 정보가 등록되었습니다.")