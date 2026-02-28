import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import google.generativeai as genai
import google.api_core.exceptions

# --- 1. AI 세팅 ---
# ★ 본인의 API 키를 입력하세요
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. UI 구성 ---
st.set_page_config(page_title="게임 기획 통합 채용 비서", layout="wide")
st.title("💼 게임 기획자 맞춤형 통합 채용 보드 (Ver 1.0)")
st.write("넥슨, 크래프톤, 엔씨소프트, 스마일게이트의 공고를 분석하여 6년 차 기획자님께 추천해 드립니다.")

st.sidebar.header("🔍 검색 설정")
# 스마일게이트 추가!
target_companies = st.sidebar.multiselect(
    "대상 회사를 선택하세요", 
    ["Nexon", "Krafton", "NCSoft", "Smilegate"], 
    default=["Nexon", "Krafton"]
)
analyze_count = st.sidebar.slider("회사당 분석할 공고 개수", 1, 10, 2)

# --- 3. 회사별 수집 설정 (스마일게이트 추가) ---
SITE_CONFIG = {
    "Nexon": {
        "url": "https://careers.nexon.com/recruit?jobCategories=3",
        "list_selector": "ul.notice-list > li",
        "title_selector": "h4",
        "link_selector": "a"
    },
    "Krafton": {
        "url": "https://www.krafton.com/careers/jobs/?search_department=GameDesign",
        "list_selector": "li.RecruitList-item",
        "title_selector": "h3.RecruitItemTitle-title",
        "link_selector": "a.RecruitItemTitle-link"
    },
    "NCSoft": {
        "url": "https://careers.ncsoft.com/recruit/list",
        "list_selector": "div.applyListWrap li",
        "title_selector": "p.subject",
        "link_selector": "a.applyDetailBtn"
    },
    "Smilegate": {
        "url": "https://careers.smilegate.com/apply/announce/list",
        "list_selector": "ul.list > li",
        "title_selector": "span.txt_notice",
        "link_selector": "a"
    }
}

if st.button("🚀 선택한 모든 회사 공고 분석 시작"):
    all_evaluated_jobs = []
    
    for company in target_companies:
        with st.status(f"📡 {company} 정보 수집 중...", expanded=True) as status:
            try:
                chrome_options = Options()
            chrome_options.add_argument("--headless") # 화면 없이 실행
            chrome_options.add_argument("--no-sandbox") # 보안 제한 해제 (서버 필수)
            chrome_options.add_argument("--disable-dev-shm-usage") # 메모리 부족 방지
            chrome_options.add_argument("--disable-gpu")
            
            # 서버용 브라우저 실행
            driver = webdriver.Chrome(options=chrome_options)
                config = SITE_CONFIG[company]
                
                driver.get(config["url"])
                time.sleep(6)

                job_elements = driver.find_elements(By.CSS_SELECTOR, config["list_selector"])
                
                temp_jobs = []
                for elem in job_elements[:analyze_count]:
                    try:
                        title = elem.find_element(By.CSS_SELECTOR, config["title_selector"]).text
                        # 스마게는 href가 상대경로일 수 있어 절대경로로 처리
                        link_elem = elem.find_element(By.CSS_SELECTOR, config["link_selector"])
                        link = link_elem.get_attribute("href")
                        
                        # 엔씨소프트는 클릭 방식, 나머지는 직접 접속
                        if company == "NCSoft":
                            temp_jobs.append({"title": title, "elem": link_elem})
                        else:
                            temp_jobs.append({"title": title, "link": link})
                    except: continue

                for job in temp_jobs:
                    try:
                        if company == "NCSoft":
                            job['elem'].click()
                        else:
                            driver.get(job['link'])
                        
                        time.sleep(4)
                        jd_text = driver.find_element(By.TAG_NAME, "body").text
                        
                        # 자동 재시도 로직
                        while True:
                            try:
                                prompt = f"6년 차 게임 시스템 기획자 관점에서 다음 공고 분석: {jd_text[:3000]}... (첫 줄에 추천 점수 0-100 기재)"
                                response = model.generate_content(prompt)
                                break
                            except google.api_core.exceptions.ResourceExhausted:
                                st.warning(f"⚠️ 구글 AI 게이지 충전 중... (20초 대기)")
                                time.sleep(20)
                        
                        try:
                            score = int(''.join(filter(str.isdigit, response.text.split('\n')[0])))
                        except: score = 0
                            
                        all_evaluated_jobs.append({
                            "company": company,
                            "title": job['title'],
                            "score": score,
                            "analysis": response.text
                        })
                        
                        if company == "NCSoft": driver.back()
                        time.sleep(3)
                        
                    except Exception as inner_e:
                        continue

                driver.quit()
                status.update(label=f"✅ {company} 수집 완료!", state="complete")

            except Exception as e:
                st.error(f"{company} 오류: {e}")

    # 통합 점수순 정렬
    all_evaluated_jobs.sort(key=lambda x: x['score'], reverse=True)

    st.divider()
    st.subheader(f"📊 총 {len(all_evaluated_jobs)}개의 공고가 분석되었습니다")

    for job in all_evaluated_jobs:
        # 제목 앞에 회사 이름과 점수를 표시하여 직관적으로 구성
        with st.expander(f"🏆 [{job['score']}점] [{job['company']}] {job['title']}", expanded=False):
            st.write(job['analysis'])
    

    st.balloons()
