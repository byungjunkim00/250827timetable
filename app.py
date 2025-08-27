import streamlit as st
import pandas as pd
import re
import datetime

# --- 0. 설정 ---
# GitHub 'timetable.csv' 파일의 Raw URL
GITHUB_FILE_URL = "https://raw.githubusercontent.com/byungjunkim00/250827timetable/main/timetable.csv"

# --- 1. 데이터 로드 및 유틸리티 함수 ---
@st.cache_data(ttl=3600)
def load_data_from_github(url):
    """GitHub CSV 파일을 읽고 데이터를 전처리합니다."""
    try:
        df = pd.read_csv(url, header=[1, 2], skipinitialspace=True)
        new_columns = [col[1] for col in df.columns[:5]]
        day_temp = ''
        for col in df.columns[5:]:
            day = col[0] if 'Unnamed' not in col[0] else day_temp
            period = col[1]
            new_columns.append(f"{day}{period}")
            day_temp = day
        df.columns = new_columns
        
        df.dropna(subset=['연번'], inplace=True)
        df['연번'] = df['연번'].astype(int)
        df['교사'] = df['교사'].apply(lambda x: re.match(r'^[가-힣]+', str(x)).group(0) if re.match(r'^[가-힣]+', str(x)) else x)
        df.fillna('', inplace=True)
        return df
    except Exception as e:
        st.error(f"GitHub에서 데이터를 불러오는 데 실패했습니다: {e}")
        return None

def style_timetable(df):
    """[개선] 수업이 있는 셀을 연한 회색으로 강조하는 스타일링 함수"""
    def color_cells(val):
        return 'background-color: #f5f5f5' if val else ''
    return df.style.applymap(color_cells)

# --- 2. 기능별 UI 함수 ---

def display_lunch_members(df):
    """[최종 개선] 요일 및 부서 선택 방식으로 점심 멤버를 조회합니다."""
    with st.expander("🥗 점심 멤버 찾기 (요일/부서 선택)", expanded=True):
        today_weekday = datetime.datetime.today().weekday()
        # 오늘이 주말이면 월요일(0)을 기본값으로 설정
        default_day_index = today_weekday if today_weekday < 5 else 0
        
        col1, col2 = st.columns(2)
        with col1:
            # [개선] 요일 선택 기능 추가
            selected_day = st.selectbox("요일 선택", ['월', '화', '수', '목', '금'], index=default_day_index)
        
        df_with_dept = df[df['부서'] != '']
        all_departments = sorted(df_with_dept['부서'].unique())
        
        with col2:
            selected_dept = st.selectbox("부서 선택", all_departments, index=None, placeholder="부서를 선택하여 조회하세요...")

        if selected_dept:
            target_column = f"{selected_day}4"
            dept_df = df[df['부서'] == selected_dept]
            
            available = dept_df[dept_df[target_column] == '']['교사'].tolist()
            busy = dept_df[dept_df[target_column] != '']['교사'].tolist()

            c1, c2 = st.columns(2)
            with c1:
                st.metric(f"✅ {selected_dept} 점심 가능", f"{len(available)}명")
                if available: st.caption(" | ".join(available))
            with c2:
                st.metric(f"❌ {selected_dept} 수업 중", f"{len(busy)}명")
                if busy: st.caption(" | ".join(busy))

def display_combined_timetable(df_filtered):
    """[개선] 공통 공강 시간 강조 및 수업 시간 음영 처리를 적용합니다."""
    st.subheader("👨‍🏫 종합 시간표 (공통 공강 찾기)")
    st.info("공통 공강은 ✅, 수업이 있는 시간은 옅은 회색(⬜)으로 표시됩니다.")
    
    days = ['월', '화', '수', '목', '금']
    periods = [f"{i}교시" for i in range(1, 8)]
    combined_df = pd.DataFrame(index=periods, columns=days)
    for day in days:
        for i, period_name in enumerate(periods):
            col_name = f"{day}{i+1}"
            if col_name in df_filtered.columns:
                is_all_free = (df_filtered[col_name] == '').all()
                combined_df.loc[period_name, day] = "✅ 공통 공강" if is_all_free else "수업"
    
    styled_df = combined_df.replace("수업", "").style.applymap(lambda val: 'background-color: #f5f5f5' if not str(val).startswith('✅') and val else '')
    st.dataframe(styled_df)

def display_availability_filter(df_filtered):
    """특정 시간에 수업이 있는/없는 교사를 필터링합니다."""
    with st.expander("🕒 특정 시간 가능/불가능 교사 찾기"):
        # ... (이전과 동일)
        col1, col2 = st.columns(2)
        day = col1.selectbox("요일 선택", ['월', '화', '수', '목', '금'], key="day_filter")
        period = col2.selectbox("교시 선택", [f"{i}교시" for i in range(1, 8)], key="period_filter")
        target_col = f"{day}{period.replace('교시', '')}"
        if target_col in df_filtered.columns:
            available = df_filtered[df_filtered[target_col] == '']['교사'].tolist()
            unavailable = df_filtered[df_filtered[target_col] != '']['교사'].tolist()
            c1, c2 = st.columns(2)
            c1.metric(f"✅ {day} {period} **가능**", f"{len(available)}명")
            if available: c1.caption(" | ".join(available))
            c2.metric(f"❌ {day} {period} **불가능**", f"{len(unavailable)}명")
            if unavailable: c2.caption(" | ".join(unavailable))

def display_teacher_timetable(df_filtered):
    """[개선] 수업 시간을 음영 처리하여 개별 시간표를 출력합니다."""
    st.subheader("📘 개별 시간표 상세 보기")
    st.info("수업이 있는 시간은 옅은 회색(⬜)으로 표시됩니다.")
    for _, row in df_filtered.iterrows():
        st.markdown(f"**{row['교사']} 선생님** ({row['부서']} | {row['교과']})")
        days, periods = ['월', '화', '수', '목', '금'], [f"{i}교시" for i in range(1, 8)]
        timetable = pd.DataFrame(index=periods, columns=days)
        for day in days:
            for i, period in enumerate(periods):
                col_name = f"{day}{i+1}"
                if col_name in row: timetable.loc[period, day] = row[col_name]
        st.dataframe(style_timetable(timetable.fillna('')))

# --- 3. Streamlit 앱 메인 구성 ---
st.set_page_config(page_title="교사 시간표 조회 시스템", layout="wide")
st.title("🗓️ 2025학년도 2학기 교사 시간표")

df = load_data_from_github(GITHUB_FILE_URL)

if df is not None:
    display_lunch_members(df)
    st.markdown("---")
    
    st.sidebar.header("🔍 시간표 검색")
    sort_option = st.sidebar.radio("교사 명단 정렬", ("연번 순", "가나다 순"), horizontal=True)
    search_option = st.sidebar.radio("검색 방법", ('교과 및 부서로 검색', '이름으로 검색'))
    
    filtered_df = pd.DataFrame()
    if search_option == '이름으로 검색':
        teacher_list = sorted(df['교사'].unique()) if sort_option == '가나다 순' else df['교사'].unique().tolist()
        teachers = st.sidebar.multiselect("선생님 선택", teacher_list)
        if teachers: filtered_df = df[df['교사'].isin(teachers)]
    else:
        subjects = st.sidebar.multiselect("교과 선택", sorted(df['교과'].dropna().unique()))
        departments = st.sidebar.multiselect("부서 선택", sorted(df['부서'].dropna().unique()))
        
        # [개선] 1차 필터링 후 세부 교사 선택 기능
        if subjects or departments:
            q_parts = []
            if subjects: q_parts.append("교과 in @subjects")
            if departments: q_parts.append("부서 in @departments")
            pre_filtered_df = df.query(" and ".join(q_parts))
            
            if not pre_filtered_df.empty:
                st.sidebar.markdown("---")
                st.sidebar.write("명단에서 포함할 교사를 선택하세요:")
                
                teachers_from_filter = pre_filtered_df['교사'].unique().tolist()
                final_selected_teachers = []
                for teacher in teachers_from_filter:
                    if st.sidebar.checkbox(teacher, value=True, key=f"cb_{teacher}"):
                        final_selected_teachers.append(teacher)
                
                if final_selected_teachers:
                    filtered_df = pre_filtered_df[pre_filtered_df['교사'].isin(final_selected_teachers)]
    
    if not filtered_df.empty:
        st.header("🔎 검색 결과")
        if len(filtered_df) > 1:
            display_combined_timetable(filtered_df)
            st.markdown("---")
        display_availability_filter(filtered_df)
        st.markdown("---")
        display_teacher_timetable(filtered_df)
    else:
        st.info("사이드바에서 조회할 조건을 선택해주세요.")
else:
    st.warning("데이터를 불러올 수 없습니다. 코드의 GitHub URL을 확인하거나 새로고침 해보세요.")
