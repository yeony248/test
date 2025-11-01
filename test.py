import streamlit as st
from datetime import date, timedelta

# --- 페이지 설정 ---
st.set_page_config(
    page_title="최고의 D-day 계산기",
    page_icon="📅",
    layout="centered"
)

# --- 세션 상태 초기화 ---
# 'target_date'와 'dday_title'은 사용자가 설정한 값, 'mode'는 계산 모드
if 'target_date' not in st.session_state:
    st.session_state.target_date = date.today() + timedelta(days=30)
if 'dday_title' not in st.session_state:
    st.session_state.dday_title = "D-day 목표를 설정하세요"
if 'mode' not in st.session_state:
    st.session_state.mode = "D-day 모드 (남은 일수)"

# --- 기능 1: 리셋 함수 ---
def reset_settings():
    """날짜, 제목, 모드를 기본값으로 초기화하는 함수"""
    st.session_state.target_date = date.today() + timedelta(days=30)
    st.session_state.dday_title = "D-day 목표를 설정하세요"
    st.session_state.mode = "D-day 모드 (남은 일수)"
    st.experimental_rerun() # 리셋 후 페이지 새로고침

# --- 사이드바 및 설정 UI ---
with st.sidebar:
    st.header("⚙️ D-day 설정")

    # 기능: D-day 이름/목표 설정
    st.session_state.dday_title = st.text_input(
        "D-day 이름/목표", 
        st.session_state.dday_title,
        key="input_title_key"
    )

    # 기능: 날짜 설정
    st.session_state.target_date = st.date_input(
        "날짜를 선택하세요", 
        st.session_state.target_date, 
        key="input_date_key"
    )

    # 기능: D-day 종류 선택 (카운트 방식)
    st.session_state.mode = st.radio(
        "D-day 계산 모드",
        ["D-day 모드 (남은 일수)", "Day Count 모드 (경과 일수)"],
        key="input_mode_key"
    )

    st.markdown("---")
    
    # 기능: 리셋 기능
    st.button("🔄 설정 초기화 (리셋)", on_click=reset_settings, use_container_width=True)


# --- 메인 페이지 로직 ---
today = date.today()
target_date = st.session_state.target_date

# 날짜 차이 계산 (timedelta 객체)
delta = target_date - today

# --- 결과 출력 ---
st.title("🌟 D-day 계산기")
st.header(st.session_state.dday_title)
st.markdown("---")

if st.session_state.mode == "D-day 모드 (남은 일수)":
    
    # 목표 날짜가 오늘 이후인 경우 (D-day)
    if delta.days >= 0:
        d_day_num = delta.days
        st.subheader(f"D-day까지 :blue[**{d_day_num}**] 일 남았습니다.")
        
        # D-day 당일 (오늘)
        if d_day_num == 0:
            st.success(f"🎉 **D-Day**입니다! 오늘이 바로 :green[{st.session_state.dday_title}] 날짜입니다.")
        else:
            st.info(f"목표 날짜: **{target_date.strftime('%Y년 %m월 %d일')}**")
            
    # 목표 날짜가 오늘 이전인 경우 (D-day가 지났음)
    else:
        d_day_num = abs(delta.days)
        st.error(f"D-day가 :red[**{d_day_num}**] 일 지났습니다. 다음 목표를 설정해보세요!")
        st.info(f"지나간 목표 날짜: **{target_date.strftime('%Y년 %m월 %d일')}**")

elif st.session_state.mode == "Day Count 모드 (경과 일수)":
    
    # 시작 날짜가 오늘 이전인 경우 (Day Count: +N일)
    if delta.days <= 0:
        day_count = abs(delta.days) + 1 # 당일 포함 계산
        st.subheader(f"시작일로부터 :green[**+{day_count}**] 일째입니다.")
        st.info(f"시작 날짜: **{target_date.strftime('%Y년 %m월 %d일')}**")
        
        # 경과 일수 1일째 (오늘 시작)
        if day_count == 1:
            st.success(f"✨ **오늘**이 :green[{st.session_state.dday_title}]의 시작일입니다.")
            
    # 시작 날짜가 오늘 이후인 경우
    else:
        st.warning(f"아직 시작일이 아닙니다. 시작일까지 :orange[**{delta.days}**] 일 남았습니다.")
        st.info(f"시작 예정 날짜: **{target_date.strftime('%Y년 %m월 %d일')}**")

st.markdown("---")
st.caption(f"현재 날짜: {today.strftime('%Y년 %m월 %d일')}")
