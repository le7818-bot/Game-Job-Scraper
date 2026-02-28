import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import google.generativeai as genai
import google.api_core.exceptions

# --- 1. AI 세팅 (비밀 금고에서 키 가져오기) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Secrets 설정에서 API 키를 확인해주세요!")

# --- 2. UI 구성 ---
st.set_page_config(page_title="게임 기획 통합 채용 비서", layout="wide")
st.title("💼 게임 기획자 맞춤형 통합 채용 보드")
st.write("6년 차 시스템 기획자님을 위한 맞춤형 분석기입니다.")

st.sidebar.header("🔍 검색 설정")
target_companies = st.sidebar.multiselect(
    "대상 회사를 선택하세요", 
    ["Nexon", "Krafton", "NCSoft", "Smilegate"], 
    default=["Nexon", "Krafton"]
)
analyze_count = st.sidebar.slider("회사당 분석할 공고 개수", 1, 10, 2)

# --- 3. 회사별 수집 설정 ---
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

if st.button("🚀 분석 시작"):
    all_evaluated_jobs = []
    
    for company in target_companies:
        with st.status(f"📡 {company} 정보 수집 중...", expanded=True) as status:
            try:
                # --- [중요] Streamlit Cloud 서버 전용 크롬 설정 ---
                chrome_options = Options()
                chrome_options.add_argument("--headless") 
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                
                driver = webdriver.Chrome(options=chrome_options)
                config = SITE_CONFIG[company]
                
                driver.get(config["url"])
                time.sleep(6)

                job_elements = driver.find_elements(By.CSS_SELECTOR, config["list_selector"])
                temp_jobs = []
                for elem in job_elements[:analyze_count]:
                    try:
                        title = elem.find_element(By.CSS_SELECTOR, config["title_selector"]).text
                        link_elem = elem.find_element(By.CSS_SELECTOR, config["link_selector"])
                        link = link_elem.get_attribute("href")
                        
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
                        
                        # AI 분석 및 자동 재시도
                        while True:
                            try:
                                prompt = f"6년 차 게임 시스템 기획자 관점에서 다음 공고 분석: {jd_text[:3000]}... (첫 줄에 추천 점수 0-100 기재)"
                                response = model.generate_content(prompt)
                                break
                            except google.api_core.exceptions.ResourceExhausted:
                                st.warning("⚠️ 구글 AI 쿨타임 대기 중 (20초)...")
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
    for job in all_evaluated_jobs:
        with st.expander(f"🏆 [{job['score']}점] [{job['company']}] {job['title']}", expanded=False):
            st.write(job['analysis'])
    st.balloons()
