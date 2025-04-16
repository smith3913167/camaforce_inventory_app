import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import base64
import altair as alt

# 초기 데이터프레임 생성 또는 세션 상태에서 로드
def init_data():
    if "inventory_df" not in st.session_state:
        st.session_state.inventory_df = pd.DataFrame(columns=[
            "ID", "날짜", "제품명", "컬러", "입출고", "수량"
        ])
        st.session_state.next_id = 1

# 입출고 데이터 추가 함수
def add_record(date, product, color, inout, qty):
    new_row = {
        "ID": st.session_state.next_id,
        "날짜": date,
        "제품명": product,
        "컬러": color,
        "입출고": inout,
        "수량": qty if inout == "입고" else -qty
    }
    st.session_state.inventory_df = pd.concat([
        st.session_state.inventory_df,
        pd.DataFrame([new_row])
    ], ignore_index=True)
    st.session_state.next_id += 1

# 재고 집계 함수
def calculate_stock():
    if st.session_state.inventory_df.empty:
        return pd.DataFrame(columns=["제품명", "컬러", "재고"])
    stock_df = st.session_state.inventory_df.groupby(["제품명", "컬러"])['수량'].sum().reset_index()
    stock_df = stock_df.rename(columns={"수량": "재고"})
    return stock_df

# 수정 함수
def update_record(record_id, new_product, new_color):
    idx = st.session_state.inventory_df.index[st.session_state.inventory_df['ID'] == record_id].tolist()
    if idx:
        st.session_state.inventory_df.at[idx[0], "제품명"] = new_product
        st.session_state.inventory_df.at[idx[0], "컬러"] = new_color

# Streamlit 앱 시작
st.title("CAMAFORCE 입출고 재고 관리")

init_data()

# 입력 폼
with st.form("입출고 등록"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("날짜", value=datetime.today())
        product = st.text_input("제품명")
        color = st.text_input("컬러")
    with col2:
        inout = st.radio("입출고 구분", ["입고", "출고"], horizontal=True)
        qty = st.number_input("수량", min_value=1, step=1)

    submitted = st.form_submit_button("등록")
    if submitted and product and color:
        add_record(date.strftime("%Y-%m-%d"), product, color, inout, qty)
        st.success("입출고 정보가 등록되었습니다.")

# 검색 기능
st.subheader("🔍 제품 검색")
search_term = st.text_input("검색할 제품명 또는 컬러")

filtered_df = st.session_state.inventory_df
if search_term:
    filtered_df = filtered_df[filtered_df["제품명"].str.contains(search_term, case=False) | filtered_df["컬러"].str.contains(search_term, case=False)]

# 수정 기능
st.subheader("✏️ 제품명 및 컬러 수정")
with st.expander("수정할 항목 선택"):
    selected_id = st.selectbox("수정할 ID 선택", st.session_state.inventory_df["ID"].tolist())
    new_product = st.text_input("새 제품명")
    new_color = st.text_input("새 컬러")
    if st.button("수정하기"):
        if new_product and new_color:
            update_record(selected_id, new_product, new_color)
            st.success(f"ID {selected_id} 수정 완료")
        else:
            st.warning("제품명과 컬러를 모두 입력해주세요.")

# 현재 재고표 표시
st.subheader("📦 현재 재고 현황")
stock_df = calculate_stock()
st.dataframe(stock_df, use_container_width=True)

# 전체 입출고 내역 표시
st.subheader("🗂 입출고 내역")
filtered_df["날짜"] = pd.to_datetime(filtered_df["날짜"])
st.dataframe(filtered_df.sort_values("날짜", ascending=False), use_container_width=True)

# 엑셀 다운로드 (csv 대체)
st.subheader("📥 엑셀 다운로드 (CSV 형식)")
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8-sig')

csv_data = convert_df(filtered_df)
st.download_button(
    label="CSV 파일 다운로드",
    data=csv_data,
    file_name='입출고내역.csv',
    mime='text/csv'
)

# 입출고 통계 시각화 (Altair 대체)
st.subheader("📊 입출고 통계 그래프")
graph_df = st.session_state.inventory_df.copy()
graph_df["월"] = pd.to_datetime(graph_df["날짜"]).dt.to_period("M").astype(str)
summary = graph_df.groupby(["월", "입출고"])["수량"].sum().reset_index()

chart = alt.Chart(summary).mark_bar().encode(
    x='월:N',
    y='수량:Q',
    color='입출고:N',
    tooltip=['월', '입출고', '수량']
).properties(
    width=700,
    height=400,
    title="월별 입출고 수량"
)

st.altair_chart(chart, use_container_width=True)
