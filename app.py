import streamlit as st
import pandas as pd
import re
import datetime

# --- 0. 설정 ---
# GitHub 'timetable.csv' 파일의 Raw URL
GITHUB_FILE_URL = "https://raw.githubusercontent.com/byungjunkim00/250827timetable/main/timetable.csv"

# 각 교시별 시간 정보 (시작, 종료)
PERIOD_TIMES = {
    '1교시': (datetime.time(8, 30), datetime.time(9, 20)),
    '2교시': (datetime.time(9, 30), datetime.time(10, 20)),
    '3교시': (datetime.time(10, 30), datetime.time(11, 20)),
    '4교시': (datetime.time(11, 30), datetime.time(12, 20)),
    '5교시': (datetime.time(13, 20), datetime.time(14, 10)),
    '6교시': (datetime.time(14, 20), datetime.time(15, 10)),
    '7교시': (datetime.time(15, 20), datetime.time(16, 10)),
}

# --- 1. 데이터 로드 및 유틸리티 함수 ---
@st.cache_data(ttl=3600)
def load_data_from_github(url):
    """GitHub CSV 파일을 읽고 데이터를 전처리합니다."""
    try:
        df = pd.read_csv(url, header=[1, 2], skipinitialspace=True)
        # 컬럼 이름 재구성
        new_columns = [col[1] for col in df.columns[:5]]
        day_temp = ''
        for col in df.columns[5:]:
            day = col[0] if 'Unnamed' not in col[0] else day_temp
            period = col[1]
            new_columns.append(f"{day}{period}")
            day_temp = day
        df.columns = new_columns
        
        # 데이터 정제
        df.dropna(subset=['연번'], inplace=True)
        df['연번'] = df['연번'].astype(int)
        df['교사'] = df['교사'].apply(lambda x: re.match(r'^[가-힣]+', str(x)).group(0) if re.match(r'^[가-힣]+', str(x)) else x)
        df.fillna('', inplace=True)
        return df
    except Exception as e:
        st.error(f"GitHub에서 데이터를 불러오는 데 실패했습니다: {e}")
        st.error("URL이 정확한지, GitHub 저장소가 'Public' 상태인지 확인해주세요.")
        return None

def get_current_period():
    """현재 시간을 기준으로 지금이 몇 요일 몇 교시인지 반환합니다."""
    now = datetime.datetime.now()
    current_time = now.time()
    weekday = now.weekday()
    
    weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금'}
    current_day = weekday_map.get(weekday)
    
    if not current_day:
        return None, None

    for period, (start_time, end_time) in PERIOD_TIMES.items():
        if start_time <= current_time <= end_time:
            return current_day, period
    return current_day, None # 현재 요일이지만 수업 시간이 아님

# --- 2. 기능별 UI 함수 ---

def display_lunch_members(df):
    """[개선] 오늘의 4교시 수업 여부에 따라 점심 멤버를 부서별로 나란히 조회합니다."""
    st.header("🥗 오늘의 점심 멤버 찾기")
    today_weekday = datetime.datetime.today().weekday()
    weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금'}

    if today_weekday not in weekday_map:
        st.success("오늘은 주말입니다. 즐거운 주말 보내세요! 🎉")
        return

    today_kor = weekday_map[today_weekday]
    st.info(f"오늘은 **{today_kor}요일**입니다. 4교시 수업 여부에 따른 부서별 선생님 명단입니다.")
    target_column = f"{today_kor}4"

    # 점심 가능/불가 그룹 생성
    free_groups = df[df[target_column] == ''].groupby('부서')['교사'].apply(list).to_dict()
    busy_groups = df[df[target_column] != ''].groupby('부서')['교사'].apply(list).to_dict()
    
    # 전체 부서 목록을 기준으로 정렬하여 UI 일관성 유지
    all_departments = sorted(list(set(free_groups.keys()) | set(busy_groups.keys())))
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("✅ 4교시 점심 가능")
        for dept in all_departments:
            if dept in free_groups:
                with st.container(border=True):
                    st.markdown(f"**{dept}**")
                    st.text(" | ".join(free_groups[dept]))
    with col2:
        st.subheader("❌ 4교시 수업 중")
        for dept in all_departments:
            if dept in busy_groups:
                with st.container(border=True):
                    st.markdown(f"**{dept}**")
                    st.text(" | ".join(busy_groups[dept]))

def display_combined_timetable(df_filtered):
    """[개선] 공통 공강 시간만 강조하여 표시하는 종합 시간표를 생성합니다."""
    st.subheader("👨‍🏫 종합 시간표 (공통 공강 찾기)")
    st.info("선택된 모든 선생님들의 공통 공강 시간을 ✅ 로 표시합니다.")
    
    days = ['월', '화', '수', '목', '금']
    periods = [f"{i}교시" for i in range(1, 8)]
    combined_df = pd.DataFrame(index=periods, columns=days)

    for day in days:
        for i, period_name in enumerate(periods):
            col_name = f"{day}{i+1}"
            if col_name in df_filtered.columns:
                is_all_free = (df_filtered[col_name] == '').all()
                combined_df.loc[period_name, day] = "✅ 공통 공강" if is_all_free else ""
    st.table(combined_df.fillna(""))

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


def display_teacher_timetable(df_filtered, current_day, current_period):
    """[개선] 현재 시간을 기준으로 시간표를 강조하여 개별 시간표를 출력합니다."""
    st.subheader("📘 개별 시간표 상세 보기")
    
    def highlight_current_time(df):
        style_df = pd.DataFrame('', index=df.index, columns=df.columns)
        if current_day in style_df.columns and current_period in style_df.index:
            style_df.loc[current_period, current_day] = 'background-color: #FFFACD; color: black; font-weight: bold;'
        return style_df

    for _, row in df_filtered.iterrows():
        st.markdown(f"**{row['교사']} 선생님** ({row['부서']} | {row['교과']})")
        days = ['월', '화', '수', '목', '금']
        periods = [f"{i}교시" for i in range(1, 8)]
        timetable = pd.DataFrame(index=periods, columns=days)
        for day in days:
            for i, period in enumerate(periods):
                col_name = f"{day}{i+1}"
                if col_name in row:
                    timetable.loc[period, day] = row[col_name]
        
        timetable.fillna('', inplace=True)
        st.dataframe(timetable.style.apply(highlight_current_time, axis=None))


# --- 3. Streamlit 앱 메인 구성 ---
st.set_page_config(page_title="교사 시간표 조회 시스템", layout="wide")
st.title("🗓️ 2025학년도 2학기 교사 시간표")

df = load_data_from_github(GITHUB_FILE_URL)
current_day, current_period = get_current_period() # 현재 시간 정보 가져오기

if df is not None:
    display_lunch_members(df)
    st.markdown("---")

    st.sidebar.header("🔍 시간표 검색")
    # [개선] 교사 명단 정렬 옵션
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
        if subjects or departments:
            q_parts = []
            if subjects: q_parts.append("교과 in @subjects")
            if departments: q_parts.append("부서 in @departments")
            filtered_df = df.query(" and ".join(q_parts))
    
    if not filtered_df.empty:
        st.header("🔎 검색 결과")
        if len(filtered_df) > 1:
            display_combined_timetable(filtered_df)
            st.markdown("---")
        display_availability_filter(filtered_df)
        st.markdown("---")
        display_teacher_timetable(filtered_df, current_day, current_period) # 현재 시간 정보 전달
    else:
        st.info("사이드바에서 조회할 조건을 선택해주세요.")
else:
    st.warning("데이터를 불러올 수 없습니다. 코드의 GitHub URL을 확인하거나 새로고침 해보세요.")
