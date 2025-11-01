import streamlit as st
import openai
from openai import OpenAI
import os

# 페이지 설정
st.set_page_config(
    page_title="Midjourney Prompt Generator",
    page_icon="🎨",
    layout="wide"
)

# 제목 및 설명
st.title("🎨 Midjourney Prompt Generator")
st.markdown("ChatGPT를 활용한 전문적인 미드저니 프롬프트 생성기")

# 사이드바에 API 키 입력
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("OpenAI API Key", type="password", help="OpenAI API 키를 입력하세요")
    
    st.markdown("---")
    st.markdown("### 📖 사용 방법")
    st.markdown("""
    1. OpenAI API 키 입력
    2. 원하는 이미지 설명 입력
    3. 스타일 및 옵션 선택
    4. '프롬프트 생성' 클릭
    """)
    
    st.markdown("---")
    st.markdown("### 💡 팁")
    st.markdown("""
    - 구체적인 설명일수록 좋습니다
    - 원하는 분위기, 색상, 스타일을 명시하세요
    - 생성된 프롬프트를 미드저니에 바로 사용하세요
    """)

# 메인 컨텐츠
col1, col2 = st.columns([1, 1])

with col1:
    st.header("입력")
    
    # 사용자 입력
    user_input = st.text_area(
        "이미지 설명을 입력하세요",
        height=150,
        placeholder="예: 석양이 지는 해변에서 서핑하는 사람"
    )
    
    # 스타일 옵션
    style_options = st.multiselect(
        "스타일 선택 (선택사항)",
        ["photorealistic", "anime", "digital art", "oil painting", "watercolor", 
         "3D render", "cinematic", "fantasy", "cyberpunk", "minimalist"],
        help="원하는 스타일을 선택하세요"
    )
    
    # 추가 옵션
    with st.expander("🎯 추가 옵션"):
        mood = st.text_input("분위기/무드", placeholder="예: 평화로운, 역동적인, 신비로운")
        lighting = st.text_input("조명", placeholder="예: 자연광, 네온, 황금빛")
        color_palette = st.text_input("색상 팔레트", placeholder="예: 파스텔톤, 비브란트, 모노크롬")
        details = st.text_input("추가 디테일", placeholder="예: 높은 디테일, 매크로 촬영")
    
    # 생성 버튼
    generate_button = st.button("🚀 프롬프트 생성", type="primary", use_container_width=True)

with col2:
    st.header("결과")
    
    if generate_button:
        if not api_key:
            st.error("⚠️ OpenAI API 키를 입력해주세요!")
        elif not user_input:
            st.error("⚠️ 이미지 설명을 입력해주세요!")
        else:
            try:
                # OpenAI 클라이언트 초기화
                client = OpenAI(api_key=api_key)
                
                # 시스템 프롬프트 구성
                system_prompt = """당신은 Midjourney 프롬프트 전문가입니다. 
사용자의 입력을 받아 Midjourney에 최적화된 영어 프롬프트를 생성하세요.

규칙:
1. 명확하고 구체적인 영어 표현 사용
2. 쉼표로 요소들을 구분
3. 스타일, 조명, 분위기, 구도 등을 포함
4. 전문적인 사진/예술 용어 사용
5. 파라미터(--ar, --v 등)는 절대 포함하지 말 것
6. 오직 이미지 설명만 포함
7. 자연스럽고 읽기 쉬운 문장 구조

출력: 프롬프트만 제공하고 다른 설명은 하지 마세요."""

                # 사용자 프롬프트 구성
                user_prompt_parts = [f"이미지 설명: {user_input}"]
                
                if style_options:
                    user_prompt_parts.append(f"스타일: {', '.join(style_options)}")
                if mood:
                    user_prompt_parts.append(f"분위기: {mood}")
                if lighting:
                    user_prompt_parts.append(f"조명: {lighting}")
                if color_palette:
                    user_prompt_parts.append(f"색상: {color_palette}")
                if details:
                    user_prompt_parts.append(f"디테일: {details}")
                
                user_prompt = "\n".join(user_prompt_parts)
                
                # 로딩 표시
                with st.spinner("프롬프트 생성 중..."):
                    # OpenAI API 호출
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    # 결과 추출
                    generated_prompt = response.choices[0].message.content.strip()
                    
                    # 결과 표시
                    st.success("✅ 프롬프트가 생성되었습니다!")
                    
                    # 생성된 프롬프트 표시
                    st.text_area(
                        "생성된 Midjourney 프롬프트",
                        value=generated_prompt,
                        height=200,
                        help="이 프롬프트를 복사하여 Midjourney에서 사용하세요"
                    )
                    
                    # 복사 버튼
                    st.code(generated_prompt, language=None)
                    
                    # 추가 정보
                    st.info("💡 이 프롬프트를 복사하여 Midjourney Discord에서 `/imagine` 명령어와 함께 사용하세요!")
                    
            except openai.AuthenticationError:
                st.error("❌ API 키가 유효하지 않습니다. 올바른 OpenAI API 키를 입력해주세요.")
            except openai.RateLimitError:
                st.error("❌ API 사용 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Made with ❤️ for Midjourney Artists | Powered by OpenAI GPT-4</p>
</div>
""", unsafe_allow_html=True)
