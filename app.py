import streamlit as st
import pandas as pd
import re

# --- 1. 데이터 로드 및 전처리 함수 ---
def process_timetable_data(uploaded_file):
    """
    업로드된 CSV 파일을 읽고 Streamlit 앱에 맞게 데이터를 전처리합니다.
    - 불필요한 행과 열을 제거합니다.
    - Multi-index 헤더를 단일 헤더로 정리합니다.
    - 교사 이름에서 괄호와 숫자를 제거합니다.
    - 빈 데이터를 정리합니다.
    """
    try:
        # 두 번째 행부터 헤더로 인식하고, 첫 번째 데이터 행은 4번째 줄부터 시작
        df = pd.read_csv(uploaded_file, header=[1, 2], skipinitialspace=True)

        # A. 컬럼 이름 재구성
        new_columns = []
        # 기본 정보 컬럼 (연번, 교과, 부서, 교사, 담임)
        for i in range(5):
            new_columns.append(df.columns[i][1])

        # 시간표 컬럼 (월1, 월2, ..., 금7)
        current_day = ''
        for col in df.columns[5:]:
            day = col[0] if 'Unnamed' not in col[0] else current_day
            period = col[1]
            new_columns.append(f"{day}{period}")
            current_day = day
        
        df.columns = new_columns
        
        # B. 데이터 정제
        # '연번' 컬럼이 비어있는 불필요한 행 제거
        df.dropna(subset=['연번'], inplace=True)
        # '연번'을 정수형으로 변환
        df['연번'] = df['연번'].astype(int)
        
        # 교사 이름에서 괄호와 시수 정보 제거 (예: "천민정(16)" -> "천민정")
        df['교사'] = df['교사'].apply(lambda x: re.match(r'^[가-힣]+', str(x)).group(0) if re.match(r'^[가-힣]+', str(x)) else x)
        
        # 결측값(NaN)을 빈 문자열로 대체
        df.fillna('', inplace=True)
        
        return df

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
        st.warning("올바른 형식의 CSV 파일을 업로드했는지 확인해주세요.")
        return None

# --- 2. UI 및 시간표 표시 함수 ---
def display_teacher_timetable(df_filtered):
    """
    필터링된 데이터프레임을 받아 각 교사의 시간표를 보기 좋게 출력합니다.
    """
    if df_filtered.empty:
        st.info("선택한 조건에 해당하는 교사가 없습니다.")
        return

    for _, row in df_filtered.iterrows():
        teacher_name = row['교사']
        subject = row['교과']
        department = row['부서']
        
        st.subheader(f"📘 {teacher_name} 선생님 시간표")
        st.caption(f"소속: {department} | 교과: {subject}")

        # 시간표 데이터를 wide format에서 long format으로 변경하여 표 생성
        days = ['월', '화', '수', '목', '금']
        periods = [str(i) for i in range(1, 8)]
        
        timetable_display = pd.DataFrame(index=[f"{p}교시" for p in periods], columns=days)
        
        for day in days:
            for period in periods:
                col_name = f"{day}{period}"
                if col_name in row and row[col_name]:
                    timetable_display.loc[f"{period}교시", day] = row[col_name]

        # 데이터가 없는 행(모든 요일이 빈 7교시 등) 제거 및 NaN 값 처리
        timetable_display.dropna(how='all', inplace=True)
        timetable_display.fillna('', inplace=True)

        st.table(timetable_display)
        st.markdown("---")


# --- 3. Streamlit 앱 메인 구성 ---

# 페이지 기본 설정
st.set_page_config(page_title="교사 시간표 조회 시스템", layout="wide")

# 제목
st.title("🗓️ 2025학년도 2학기 교사 시간표 조회")

# 파일 업로더
uploaded_file = st.file_uploader("📁 '2025 2학기 교사 전체 시간표(확정).csv' 파일을 업로드하세요.", type="csv")


if uploaded_file is not None:
    # 데이터 로드 및 처리
    df = process_timetable_data(uploaded_file)

    if df is not None:
        st.sidebar.header("🔍 시간표 검색")

        # 검색 방식 선택 (라디오 버튼)
        search_option = st.sidebar.radio(
            "검색 방법을 선택하세요.",
            ('이름으로 검색', '교과 및 부서로 검색')
        )

        filtered_df = pd.DataFrame()

        # 이름으로 검색
        if search_option == '이름으로 검색':
            teacher_list = sorted(df['교사'].unique())
            selected_teacher = st.sidebar.selectbox("선생님 이름을 선택하세요.", teacher_list)
            if selected_teacher:
                filtered_df = df[df['교사'] == selected_teacher]
        
        # 교과 및 부서로 검색
        else:
            subject_list = sorted(df['교과'].dropna().unique())
            department_list = sorted(df['부서'].dropna().unique())

            selected_subjects = st.sidebar.multiselect("교과를 선택하세요. (복수 선택 가능)", subject_list)
            selected_departments = st.sidebar.multiselect("부서를 선택하세요. (복수 선택 가능)", department_list)

            # 필터링 로직
            if not selected_subjects and not selected_departments:
                st.info("조회할 교과 또는 부서를 사이드바에서 선택해주세요.")
                filtered_df = pd.DataFrame() # 빈 데이터프레임
            else:
                query_parts = []
                if selected_subjects:
                    query_parts.append("교과 in @selected_subjects")
                if selected_departments:
                    query_parts.append("부서 in @selected_departments")
                
                query_string = " and ".join(query_parts)
                filtered_df = df.query(query_string)

        # 결과 출력
        display_teacher_timetable(filtered_df)
else:
    st.info("시간표 CSV 파일을 업로드하여 조회를 시작하세요.")
