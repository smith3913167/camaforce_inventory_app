import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import base64
import altair as alt
import os
from supabase import create_client, Client

# 🔐 Supabase 설정
SUPABASE_URL = "https://ibotdnvtdlmmcrqtfsgx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlib3RkbnZ0ZGxtbWNycXRmc2d4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTIyNDk3MywiZXhwIjoyMDYwODAwOTczfQ.C2ndSZGaNTeEAdzKTb8X9hr19Rokqy8obqgb33oq0aE"
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
def save_data(row):
    supabase.table("inventory").insert(row).execute()

# 자동 저장 설정
if "autosave" not in st.session_state:
    st.session_state.autosave = True

load_data()

st.title("CAMAFORCE 입출고 재고 관리")

# 탭 UI 구성
tabs = st.tabs(["📦 제품 등록 및 입출고", "📊 재고 현황 및 통계"])

# 첫 번째 탭
with tabs[0]:
    st.subheader("📦 제품 등록")
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
                save_data(new_row)
            st.success("제품이 등록되었습니다.")

# 두 번째 탭: 재고 및 통계
with tabs[1]:
    st.subheader("📦 현재 재고 현황")
    if not st.session_state.inventory_df.empty:
        df = st.session_state.inventory_df.copy()
        df["날짜"] = pd.to_datetime(df["날짜"])

        # 날짜 필터 추가
        min_date, max_date = df["날짜"].min(), df["날짜"].max()
        date_range = st.date_input("조회할 날짜 범위", value=(min_date, max_date))
        if isinstance(date_range, tuple) and len(date_range) == 2:
            df = df[(df["날짜"] >= pd.to_datetime(date_range[0])) & (df["날짜"] <= pd.to_datetime(date_range[1]))]

        # 재고 현황
        stock_df = df.groupby(["날짜", "시리즈명", "제품명", "컬러", "스마트스토어번호"])["수량"].sum().reset_index()
        stock_df = stock_df.rename(columns={"수량": "재고"})

        def highlight_low_stock(val):
            return 'color: red; font-weight: bold;' if isinstance(val, (int, float)) and val < 15 else ''

        styled_stock_df = stock_df.style.applymap(highlight_low_stock, subset=["재고"])
        st.dataframe(styled_stock_df, use_container_width=True)

        st.markdown("\n**📎 스마트스토어 상품 링크 자동 연결:**")
        for _, row in stock_df.iterrows():
            if str(row["스마트스토어번호"]).strip():
                st.markdown(f"[{row['제품명']} ({row['컬러']}) 링크 열기](https://smartstore.naver.com/{row['스마트스토어번호']})")

        # 일간 입출고 흐름 차트
        st.subheader("📈 일간 입출고 흐름")
        flow_df = df.groupby(["날짜", "입출고"])["수량"].sum().reset_index()
        flow_chart = alt.Chart(flow_df).mark_line(point=True).encode(
            x='날짜:T',
            y='수량:Q',
            color='입출고:N',
            tooltip=['날짜', '입출고', '수량']
        ).properties(
            width=700,
            height=400,
            title="일별 입출고 흐름"
        )
        st.altair_chart(flow_chart, use_container_width=True)

        # 월간 입출고 통계
        st.subheader("📊 월별 입출고 비교")
        df["월"] = df["날짜"].dt.to_period("M").astype(str)
        summary = df.groupby(["월", "입출고"])["수량"].sum().reset_index()
        chart = alt.Chart(summary).mark_bar().encode(
            x='월:N',
            y='sum(수량):Q',
            color='입출고:N',
            tooltip=['월', '입출고', '수량']
        ).properties(
            width=700,
            height=400,
            title="월별 입출고 비교"
        )
        st.altair_chart(chart, use_container_width=True)

        # 제품별 누적 재고 리스트
        st.subheader("📋 제품별 누적 재고 리스트")
        item_df = df.groupby(["시리즈명", "제품명", "컬러"]).agg({"수량": "sum"}).reset_index()
        item_df = item_df.rename(columns={"수량": "총재고"})
        item_df["총재고"] = item_df["총재고"].astype(int)
        st.dataframe(item_df, use_container_width=True)

    else:
        st.info("재고 데이터가 없습니다.")
