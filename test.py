import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException, NoSuchElementException
import time
import google.generativeai as genai

# --- 0. 페이지 기본 설정 (가장 위에 있어야 함) ---
st.set_page_config(page_title="게임사 공고 분석기", layout="wide")

# --- 1. 직무 필터 설정 (주연 기획자 전용) ---
VALID_KEYWORDS = ["시스템", "콘텐츠", "컨텐츠", "UX", "UI", "UI/UX", "기획", "System", "Content", "Planner", "Designer"]
EXCLUDE_KEYWORDS = ["레벨", "Level", "전투", "Combat", "전투디자인", "전투기획", "밸런스", "Balance"]

def is_valid_job(title):
    # 제외 키워드가 하나라도 있으면 탈락
    if any(ex.lower() in title.lower() for ex in EXCLUDE_KEYWORDS):
        return False
    # 유효 키워드가 하나라도 있으면 승인
    return any(kw.lower() in title.lower() for kw in VALID_KEYWORDS)

# --- 2. 환경 설정 및 AI 초기화 ---
def setup_ai():
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if api_key:
        genai.configure(api_key="".join(api_key.split()))
        return genai.GenerativeModel('gemini-2.5-flash')
    return None

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

# --- 3. 회사별 수집 엔진 (수리 완료) ---

def crawl_krafton(driver, count):
    results = []
    driver.get("https://krafton.ai/ko/careers/jobs/")
    time.sleep(3)
    try:
        items = driver.find_elements(By.CLASS_NAME, "job-item")
        found = 0
        for item in items:
            if found >= count: break
            title = item.find_element(By.TAG_NAME, "h3").text
            if not is_valid_job(title): continue # 주연님 직무 아니면 패스
            
            item.click()
            try:
                # [제목 검증] 아테나/룬샷 섞임 방지 로직
                WebDriverWait(driver, 7).until(lambda d: title[:5] in d.find_element(By.CLASS_NAME, "post-title").text)
                content = driver.find_element(By.CLASS_NAME, "post-content").text
                results.append({"company": "Krafton", "title": title, "content": content})
                found += 1
            except: pass
            driver.back()
            time.sleep(1)
    except: pass
    return results

def crawl_ncsoft(driver, count):
    results = []
    try:
        driver.get("https://careers.ncsoft.com/ko/jobs")
        time.sleep(3)
    except UnexpectedAlertPresentException:
        driver.switch_to.alert.accept() # 알럿 자동 차단
    # (NC는 보안상 로컬 테스트를 권장하며, 여기서는 기본 틀만 유지합니다)
    return results

# --- 4. AI 분석 엔진 (100만 점 리포트) ---

def analyze_job(model, job_data):
    prompt = f"""
    너는 10년 차 리드 게임 기획자야. 아래 공고가 '6년 차 시스템/콘텐츠 기획자(주연)'에게 얼마나 적합한지 평가해.
    [공고] {job_data['company']} - {job_data['title']}
    [본문] {job_data['content']}
    
    분석 기준:
    1. 주연 기획자의 강점인 '예외 상황 방지', '논리적 무결성', 'UX/UI 연계' 역량이 필요한가?
    2. 점수는 0~1,000,000점 사이로 산출.
    3. 결과는 [CRITICAL], [STRENGTH], [RISK]를 사용해 날카롭고 개조식으로 작성.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "AI 분석 중 오류가 발생했습니다."

# --- 5. Streamlit UI (이미지 반영) ---

st.title("🛡️ 주연 기획자 전용: 무결성 채용공고 분석기")
st.markdown("> **시스템 / 콘텐츠 / UXUI 기획 직무만 정밀 필터링합니다.**")

with st.sidebar:
    st.header("⚙️ 검색 설정")
    selected_companies = st.multiselect("분석 대상", ["Krafton", "NCSoft", "Smilegate"], default=["Krafton"])
    job_count = st.slider("회사당 유효 공고 수집 개수", 1, 5, 2)

if st.button("🚀 분석 시작"):
    model = setup_ai()
    if not model:
        st.error("Gemini API 키가 설정되지 않았습니다. Secrets 설정을 확인해 주세요!")
    else:
        driver = get_driver()
        all_data = []
        with st.spinner("불필요한 공고(레벨/전투/밸런스)를 걸러내는 중..."):
            if "Krafton" in selected_companies:
                all_data.extend(crawl_krafton(driver, job_count))
            # (다른 회사 추가 시 여기에 루프 배치)
        driver.quit()

        if all_data:
            st.divider()
            for job in all_data:
                with st.expander(f"✨ [{job['company']}] {job['title']}"):
                    st.markdown(analyze_job(model, job))
        else:
            st.warning("현재 주연님의 기준에 맞는 공고가 페이지에 없습니다.")
