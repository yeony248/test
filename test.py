import streamlit as st
import time
from datetime import datetime, timedelta

# -------------------------------------------------------------------
# 1. 세션 상태(Session State) 초기화
# -------------------------------------------------------------------
# 스트림릿은 스크립트를 위에서 아래로 재실행하므로,
# 타이머의 상태를 'st.session_state'에 저장해야 합니다.

# 'timer_active': 타이머가 현재 실행 중인지 (True/False)
if 'timer_active' not in st.session_state:
    st.session_state.timer_active = False

# 'end_time': 타이머가 종료되어야 하는 정확한 시간
if 'end_time' not in st.session_state:
    st.session_state.end_time = None

# 'notified': 알림이 이미 표시되었는지 (True/False)
# (타이머 종료 후 재실행 시 알림이 반복되는 것을 방지)
if 'notified' not in st.session_state:
    st.session_state.notified = False

# -------------------------------------------------------------------
# 2. 콜백 함수 (버튼 로직)
# -------------------------------------------------------------------

def start_timer(minutes):
    """타이머 시작 콜백"""
    st.session_state.timer_active = True
    st.session_state.end_time = datetime.now() + timedelta(minutes=minutes)
    st.session_state.notified = False  # 새 타이머 시작 시 알림 상태 초기화

def reset_timer():
    """타이머 초기화 콜백"""
    st.session_state.timer_active = False
    st.session_state.end_time = None
    st.session_state.notified = False

# -------------------------------------------------------------------
# 3. UI 레이아웃
# -------------------------------------------------------------------

st.title("👨‍💻 Streamlit Timer")
st.write("스트림릿 세션 상태를 활용한 타이머입니다.")

# 3-1. 시간 설정 버튼 (가로 정렬)
cols = st.columns(4)
with cols[0]:
    st.button("3분", on_click=start_timer, args=(3,), use_container_width=True)
with cols[1]:
    st.button("5분", on_click=start_timer, args=(5,), use_container_width=True)
with cols[2]:
    st.button("10분", on_click=start_timer, args=(10,), use_container_width=True)
with cols[3]:
    st.button("15분", on_click=start_timer, args=(15,), use_container_width=True)

# 3-2. 초기화 버튼
st.button("초기화 (Reset)", on_click=reset_timer, use_container_width=True)

st.divider()

# 3-3. 타이머 및 알림 표시 영역
# st.empty()를 사용하여 이 영역만 동적으로 업데이트합니다.
timer_placeholder = st.empty()
notification_placeholder = st.empty()

# -------------------------------------------------------------------
# 4. 메인 타이머 로직
# -------------------------------------------------------------------

if st.session_state.timer_active:
    # 타이머가 활성화된 경우
    
    # 남은 시간 계산
    remaining_time = st.session_state.end_time - datetime.now()
    
    if remaining_time.total_seconds() > 0:
        # 4-1. 시간이 남았을 때
        
        # 남은 시간(분, 초) 계산
        mins, secs = divmod(int(remaining_time.total_seconds()), 60)
        timer_display = f"{mins:02d}:{secs:02d}"
        
        # st.metric을 사용해 시간 표시
        timer_placeholder.metric("⏳ 남은 시간", timer_display)
        
        # 1초 대기. 
        # 중요: 이 sleep 중 '초기화' 버튼이 눌리면
        # Streamlit이 sleep을 중단하고 스크립트를 재실행합니다.
        time.sleep(1)
        
        # 스크립트 마지막에 도달했으므로 1초 후 자동 재실행
        st.experimental_rerun() 
        # (참고: 최신 Streamlit은 st.rerun()이지만, 
        #  호환성을 위해 experimental_rerun()도 유효합니다.)

    else:
        # 4-2. 시간 만료
        timer_placeholder.metric("⏳ 남은 시간", "00:00")
        
        # 알림을 아직 안 띄웠다면
        if not st.session_state.notified:
            notification_placeholder.success("⏰ 시간이 만료되었습니다!")
            st.balloons()
            st.session_state.notified = True  # 알림 상태 변경

        # 타이머 상태 비활성화
        st.session_state.timer_active = False

else:
    # 5. 타이머가 비활성 상태일 때
    timer_placeholder.metric("⏳ 남은 시간", "00:00")
    
    # 만약 '초기화'가 아닌 '만료'로 인해 비활성화된 것이라면
    # 알림 메시지를 유지합니다.
    if st.session_state.notified:
        notification_placeholder.success("⏰ 시간이 만료되었습니다!")
