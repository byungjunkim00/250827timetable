import streamlit as st
import pandas as pd
import re

# --- 0. 설정 ---
# 🚨 중요: 이 URL을 본인의 GitHub 'timetable.csv' 파일의 'Raw' URL로 변경하세요.
# 예: https://raw.githubusercontent.com/사용자이름/저장소이름/main/timetable.csv
GITHUB_FILE_URL = "https://raw.githubusercontent.com/byungjunkim00/250827timetable/timetable.csv" 

# --- 1. 데이터 로드 및 전처리 함수 ---
@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱
def load_data_from_github(url):
    """
    GitHub에 있는 CSV 파일을 읽고 앱에 맞게 데이터를 전처리합니다.
    - 불필요한 행과 열을 제거하고, 헤더를 정리합니다.
    - 교사 이름에서 괄호와 숫자를 제거합니다.
    """
    try:
        # header=[1, 2]를 통해 2, 3번째 줄을 Multi-index 헤더로 지정
        df = pd.read_csv(url, header=[1, 2], skipinitialspace=True)

        # A. 컬럼 이름 재구성 (요일 + 교시)
        new_columns = [col[1] for col in df.columns[:5]] # 기본 정보 컬럼
        day_temp = ''
        for col in df.columns[5:]:
            day = col[0] if 'Unnamed' not in col[0] else day_temp
            period = col[1]
            new_columns.append(f"{day}{period}")
            day_temp = day
        df.columns = new_columns
        
        # B. 데이터 정제
        df.dropna(subset=['연번'], inplace=True) # 연번 없는 행 제거
        df['연번'] = df['연번'].astype(int)
        df['교사'] = df['교사'].apply(lambda x: re.match(r'^[가-힣]+', str(x)).group(0) if re.match(r'^[가-힣]+', str(x)) else x)
        df.fillna('', inplace=True)
        return df

    except Exception as e:
        st.error(f"GitHub에서 데이터를 불러오는 데 실패했습니다: {e}")
        st.error("입력한 URL이 'Raw' 형태인지 확인해주세요.")
        return None

# --- 2. UI 및 시간표 표시 함수 ---

def display_combined_timetable(df_filtered):
    """
    [기능 2] 선택된 모든 교사의 공통 공강 시간을 보여주는 종합 시간표를 생성합니다.
    """
    st.subheader("👨‍🏫 종합 시간표 (공통 공강 찾기)")
    st.info("선택된 모든 선생님들의 공통 공강 시간을 ✅ 로 표시합니다.")

    days = ['월', '화', '수', '목', '금']
    periods = [str(i) for i in range(1, 8)]
    combined_df = pd.DataFrame(index=[f"{p}교시" for p in periods], columns=days)

    for day in days:
        for period in periods:
            col_name = f"{day}{period}"
            if col_name in df_filtered.columns:
                # 해당 시간의 모든 선생님 수업이 비어있는지('') 확인
                is_all_free = (df_filtered[col_name] == '').all()
                combined_df.loc[f"{period}교시", day] = "공강 ✅" if is_all_free else "수업 중 ❌"

    combined_df.dropna(how='all', inplace=True)
    st.table(combined_df)

def display_availability_filter(df_filtered):
    """
    [기능 3] 특정 요일, 특정 교시에 수업이 있는/없는 교사를 필터링하여 보여줍니다.
    """
    with st.expander(" 특정 시간 가능/불가능 교사 찾기"):
        col1, col2 = st.columns(2)
        with col1:
            selected_day = st.selectbox("요일 선택", ['월', '화', '수', '목', '금'], key="day_filter")
        with col2:
            selected_period = st.selectbox("교시 선택", [f"{i}교시" for i in range(1, 8)], key="period_filter")
        
        target_period = selected_period.replace("교시", "")
        target_column = f"{selected_day}{target_period}"

        if target_column in df_filtered.columns:
            # 수업이 없는 교사: 해당 컬럼 값이 빈 문자열인 경우
            available_teachers = df_filtered[df_filtered[target_column] == '']['교사'].tolist()
            # 수업이 있는 교사: 해당 컬럼 값이 비어있지 않은 경우
            unavailable_teachers = df_filtered[df_filtered[target_column] != '']['교사'].tolist()

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**✅ {selected_day}요일 {selected_period}에 수업이 없는 선생님**")
                if available_teachers:
                    st.write(" | ".join(available_teachers))
                else:
                    st.write("-")
            
            with col2:
                st.write(f"**❌ {selected_day}요일 {selected_period}에 수업이 있는 선생님**")
                if unavailable_teachers:
                    st.write(" | ".join(unavailable_teachers))
                else:
                    st.write("-")

def display_teacher_timetable(df_filtered):
    """
    필터링된 각 교사의 개별 시간표를 출력합니다.
    """
    st.subheader("📘 개별 시간표 상세 보기")
    for _, row in df_filtered.iterrows():
        teacher_name, subject, department = row['교사'], row['교과'], row['부서']
        st.markdown(f"**{teacher_name} 선생님** ({department} | {subject})")
        
        days = ['월', '화', '수', '목', '금']
        periods = [str(i) for i in range(1, 8)]
        timetable = pd.DataFrame(index=[f"{p}교시" for p in periods], columns=days)
        
        for day in days:
            for period in periods:
                col_name = f"{day}{period}"
                if col_name in row and row[col_name]:
                    timetable.loc[f"{period}교시", day] = row[col_name]

        timetable.dropna(how='all', inplace=True)
        timetable.fillna('', inplace=True)
        st.table(timetable)

# --- 3. Streamlit 앱 메인 구성 ---

st.set_page_config(page_title="교사 시간표 조회 시스템", layout="wide")
st.title("🗓️ 2025학년도 2학기 교사 시간표 조회")

# 데이터 로드
df = load_data_from_github(GITHUB_FILE_URL)

if df is not None:
    st.sidebar.header("🔍 시간표 검색")
    search_option = st.sidebar.radio("검색 방법", ('교과 및 부서로 검색', '이름으로 검색'))

    filtered_df = pd.DataFrame()

    if search_option == '이름으로 검색':
        teacher_list = sorted(df['교사'].unique())
        selected_teachers = st.sidebar.multiselect("선생님 이름을 선택하세요 (복수 선택 가능)", teacher_list)
        if selected_teachers:
            filtered_df = df[df['교사'].isin(selected_teachers)]
    else: # 교과 및 부서로 검색
        subject_list = sorted(df['교과'].dropna().unique())
        department_list = sorted(df['부서'].dropna().unique())
        
        selected_subjects = st.sidebar.multiselect("교과 선택", subject_list)
        selected_departments = st.sidebar.multiselect("부서 선택", department_list)
        
        if selected_subjects or selected_departments:
            query_parts = []
            if selected_subjects: query_parts.append("교과 in @selected_subjects")
            if selected_departments: query_parts.append("부서 in @selected_departments")
            filtered_df = df.query(" and ".join(query_parts))

    # 검색 결과 표시
    if not filtered_df.empty:
        # 1. 종합 시간표 (2명 이상 선택 시)
        if len(filtered_df) > 1:
            display_combined_timetable(filtered_df)
            st.markdown("---")

        # 2. 특정 시간 가능/불가능 교사 찾기
        display_availability_filter(filtered_df)
        st.markdown("---")
        
        # 3. 개별 시간표
        display_teacher_timetable(filtered_df)
    else:
        st.info("조회할 조건을 사이드바에서 선택해주세요.")
else:
    st.warning("데이터를 불러올 수 없습니다. 코드의 GitHub URL을 확인해주세요.")
