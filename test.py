import streamlit as st
from datetime import date, timedelta
import uuid # 고유 ID 생성을 위해 사용

# --- 페이지 설정 ---
st.set_page_config(
    page_title="궁극의 D-day 관리 시스템",
    page_icon="🗓️",
    layout="wide" # 여러 D-day를 보여주기 위해 wide 레이아웃 사용
)

# --- 세션 상태 초기화 ---
# 'dday_list'는 모든 D-day 객체를 저장하는 핵심 리스트입니다.
if 'dday_list' not in st.session_state:
    st.session_state.dday_list = []
    
# 'edit_id'는 현재 편집 중인 D-day의 ID를 저장합니다.
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None
    

# --- D-day 계산 및 표시 함수 ---
def calculate_and_display_dday(dday_item):
    """
    개별 D-day 아이템을 계산하고 스트림릿에 표시하는 함수
    """
    today = date.today()
    target_date = dday_item['date']
    delta = target_date - today
    
    st.subheader(f"✨ {dday_item['title']}")
    
    # Day Count 모드 (과거)
    if delta.days < 0:
        day_count = abs(delta.days) + 1 # 당일 포함 계산
        st.metric(label=f"시작일로부터 경과 일수 (+1일은 오늘 포함)", 
                  value=f"+{day_count} 일", 
                  delta=f"시작일: {target_date.strftime('%Y년 %m월 %d일')}",
                  delta_color="off") # delta_color를 off로 설정해 색상 변화를 막음
        st.caption(f"이벤트가 이미 시작되었어요. 벌써 {day_count}일째!")

    # D-day 당일 (오늘)
    elif delta.days == 0:
        st.metric(label="오늘의 카운트", value="D-DAY", delta="🎉 바로 오늘입니다!", delta_color="inverse")
        st.balloons() # D-day 당일 풍선 효과 추가

    # D-day 모드 (미래)
    else:
        d_day_num = delta.days
        st.metric(label="남은 D-day", 
                  value=f"D-{d_day_num} 일", 
                  delta=f"목표일: {target_date.strftime('%Y년 %m월 %d일')}")
        
        # 주차 정보 표시 (추가 기능)
        weeks_left = d_day_num // 7
        st.caption(f"약 {weeks_left}주 남았습니다.")
        
    st.markdown("---")


# --- 콜백 함수: D-day 관리 ---

def add_dday():
    """새로운 D-day를 리스트에 추가"""
    # 임시 변수에 저장된 값 사용
    new_title = st.session_state.new_title or "새 D-day"
    new_date = st.session_state.new_date or date.today() + timedelta(days=7)
    
    new_dday = {
        'id': str(uuid.uuid4()), # 고유 ID 부여
        'title': new_title,
        'date': new_date
    }
    st.session_state.dday_list.append(new_dday)
    # 입력 필드 초기화
    st.session_state.new_title = "" 
    st.session_state.new_date = date.today() + timedelta(days=7)
    st.rerun()

def start_edit(dday_id):
    """특정 D-day를 편집 모드로 전환"""
    st.session_state.edit_id = dday_id

def delete_dday(dday_id):
    """특정 D-day를 리스트에서 삭제"""
    st.session_state.dday_list = [d for d in st.session_state.dday_list if d['id'] != dday_id]
    st.rerun()

def save_edit(dday_id, new_title, new_date):
    """편집된 내용을 저장하고 편집 모드를 종료"""
    for d in st.session_state.dday_list:
        if d['id'] == dday_id:
            d['title'] = new_title
            d['date'] = new_date
            break
    st.session_state.edit_id = None
    st.rerun()

def cancel_edit():
    """편집 모드 취소"""
    st.session_state.edit_id = None
    st.rerun()


# --- 메인 UI 구성 ---
st.title("🗓️ 궁극의 D-day 관리 시스템 (D-day/Day Count 모드)")
st.markdown("---")

# --- 1. 새 D-day 추가 폼 (사이드바) ---
with st.sidebar:
    st.header("➕ 새로운 D-day 추가")
    
    # 입력 필드 (콜백 함수에서 사용하기 위해 key 지정)
    st.text_input("목표 이름/제목", key='new_title', value="새 D-day")
    st.date_input("목표 날짜", key='new_date', value=date.today() + timedelta(days=7))
    
    # 추가 버튼
    st.button("✅ D-day 추가하기", on_click=add_dday, use_container_width=True)

    st.markdown("---")
    
    # 전체 리셋 기능 (모든 D-day 삭제)
    if st.button("🗑️ 모든 D-day 초기화", use_container_width=True):
        st.session_state.dday_list = []
        st.session_state.edit_id = None
        st.rerun()


# --- 2. D-day 목록 표시 및 편집 UI (메인 화면) ---
if not st.session_state.dday_list:
    st.info("➕ 사이드바에서 새로운 D-day를 추가해 보세요!")
else:
    st.header("📋 나의 D-day 목록")
    
    # 각 D-day를 컬럼에 배치하여 더 넓은 화면에 보기 좋게 표시
    cols = st.columns(3) # 한 줄에 최대 3개 표시
    
    for index, dday_item in enumerate(st.session_state.dday_list):
        col = cols[index % 3] # 0, 1, 2, 0, 1, 2 순서로 컬럼 할당
        
        with col:
            # 현재 항목이 편집 중인 경우 (edit_id와 일치)
            if st.session_state.edit_id == dday_item['id']:
                
                st.markdown("### ✏️ D-day 편집")
                
                # 편집 폼
                edited_title = st.text_input("제목 수정", dday_item['title'], key=f"edit_title_{dday_item['id']}")
                edited_date = st.date_input("날짜 수정", dday_item['date'], key=f"edit_date_{dday_item['id']}")
                
                # 저장/취소 버튼
                save_col, cancel_col = st.columns(2)
                with save_col:
                    st.button("💾 저장", 
                              on_click=save_edit, 
                              args=(dday_item['id'], edited_title, edited_date), 
                              key=f"save_{dday_item['id']}", 
                              use_container_width=True)
                with cancel_col:
                    st.button("❌ 취소", 
                              on_click=cancel_edit, 
                              key=f"cancel_{dday_item['id']}", 
                              use_container_width=True)
                st.markdown("---")

            # 편집 중이 아닌 경우 (일반 표시)
            else:
                calculate_and_display_dday(dday_item)
                
                # 편집/삭제 버튼
                edit_col, delete_col = st.columns(2)
                with edit_col:
                    st.button("⚙️ 편집", 
                              on_click=start_edit, 
                              args=(dday_item['id'],), 
                              key=f"edit_{dday_item['id']}",
                              use_container_width=True)
                with delete_col:
                    st.button("🗑️ 삭제", 
                              on_click=delete_dday, 
                              args=(dday_item['id'],), 
                              key=f"delete_{dday_item['id']}",
                              use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True) # 항목 간 간격
