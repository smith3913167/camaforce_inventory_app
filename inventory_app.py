import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import base64
import altair as alt
import os

DATA_FILE = "inventory_data.csv"
HISTORY_FILE = "inventory_history.csv"

# CSV에서 데이터 불러오기 또는 초기화
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if not df.empty:
            st.session_state.inventory_df = df
            st.session_state.next_id = df["ID"].max() + 1
        else:
            st.session_state.inventory_df = pd.DataFrame(columns=["ID", "날짜", "카테고리", "시리즈명", "제품명", "특징", "코드", "컬러", "스마트스토어번호", "입출고", "수량", "메모"])
            st.session_state.next_id = 1
    else:
        st.session_state.inventory_df = pd.DataFrame(columns=["ID", "날짜", "카테고리", "시리즈명", "제품명", "특징", "코드", "컬러", "스마트스토어번호", "입출고", "수량", "메모"])
        st.session_state.next_id = 1

# 데이터 저장
def save_data():
    st.session_state.inventory_df.to_csv(DATA_FILE, index=False)

# 수정 이력 저장 함수
def log_history(action, record):
    record["이력"] = action
    history_df = pd.DataFrame([record])
    if os.path.exists(HISTORY_FILE):
        history_df.to_csv(HISTORY_FILE, mode='a', index=False, header=False)
    else:
        history_df.to_csv(HISTORY_FILE, index=False)

# 입출고 데이터 수정 함수
def update_record(record_id, updated_row):
    df = st.session_state.inventory_df
    index = df[df["ID"] == record_id].index
    if not index.empty:
        original = df.loc[index[0]].to_dict()
        log_history("수정 전", original)
        for key in updated_row:
            df.at[index[0], key] = updated_row[key]
        save_data()
        log_history("수정 후", df.loc[index[0]].to_dict())

# 입출고 데이터 삭제 함수
def delete_record(record_id):
    df = st.session_state.inventory_df
    deleted = df[df["ID"] == record_id].iloc[0].to_dict()
    log_history("삭제", deleted)
    st.session_state.last_deleted = deleted
    st.session_state.inventory_df = df[df["ID"] != record_id].reset_index(drop=True)
    save_data()

# 삭제 취소 함수
def undo_delete():
    if "last_deleted" in st.session_state:
        restored = st.session_state.last_deleted
        st.session_state.inventory_df = pd.concat([
            st.session_state.inventory_df,
            pd.DataFrame([restored])
        ], ignore_index=True).sort_values("ID").reset_index(drop=True)
        save_data()
        st.success("삭제 취소 완료")
        del st.session_state.last_deleted

# 기존 내용 불러오기
load_data()

# 레이아웃 좌우 분리
left, right = st.columns([1, 2])

# 왼쪽 영역: 신규 등록 + 수정 삭제
with left:
    st.subheader("✏️ 제품 정보 수정 및 삭제")
    edit_df = st.session_state.inventory_df.copy()
    selected_edit_id = st.selectbox("수정 또는 삭제할 제품 ID", options=edit_df["ID"].tolist())
    edit_row = edit_df[edit_df["ID"] == selected_edit_id].iloc[0]

    with st.form("수정폼"):
        new_date = st.date_input("날짜", value=pd.to_datetime(edit_row["날짜"]))
        new_category = st.text_input("카테고리", value=edit_row["카테고리"])
        new_series = st.text_input("시리즈명", value=edit_row["시리즈명"])
        new_product = st.text_input("제품명", value=edit_row["제품명"])
        new_feature = st.text_input("특징", value=edit_row["특징"])
        new_store_id = st.text_input("스마트스토어 상품번호", value=str(edit_row["스마트스토어번호"]))
        new_code = st.text_input("코드번호", value=str(edit_row["코드"]))
        new_color = st.text_input("컬러", value=edit_row["컬러"])
        new_inout = st.selectbox("입출고", ["입고", "출고"], index=0 if edit_row["입출고"] == "입고" else 1)
        new_qty = st.number_input("수량", min_value=1, step=1, value=abs(int(edit_row["수량"])))
        new_memo = st.text_input("메모", value=edit_row["메모"])

        col3, col4 = st.columns(2)
        with col3:
            if st.form_submit_button("수정하기"):
                update_record(selected_edit_id, {
                    "날짜": new_date.strftime("%Y-%m-%d"),
                    "카테고리": new_category,
                    "시리즈명": new_series,
                    "제품명": new_product,
                    "특징": new_feature,
                    "코드": new_code,
                    "컬러": new_color,
                    "스마트스토어번호": new_store_id,
                    "입출고": new_inout,
                    "수량": new_qty if new_inout == "입고" else -new_qty,
                    "메모": new_memo
                })
                st.success("수정 완료")

        with col4:
            if st.form_submit_button("삭제하기"):
                delete_record(selected_edit_id)
                st.warning("삭제 완료")

    if "last_deleted" in st.session_state:
        if st.button("⏪ 삭제 취소(Undo)"):
            undo_delete()

# 오른쪽 영역: 재고 현황 및 통계
with right:
    st.subheader("📦 재고 현황")
    df = st.session_state.inventory_df.copy()
    if df.empty:
        st.info("등록된 제품이 없습니다.")
    else:
        df["날짜"] = pd.to_datetime(df["날짜"])
        stock_df = df.groupby(["카테고리", "제품명"])["수량"].sum().reset_index()
        stock_df = stock_df.rename(columns={"수량": "재고"})
        st.dataframe(stock_df, use_container_width=True)

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
