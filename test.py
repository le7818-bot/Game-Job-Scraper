import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
import time
import google.generativeai as genai

# --- 0. 페이지 기본 설정 ---
st.set_page_config(page_title="게임사 공고 분석기", layout="wide")

# --- 1. 직무 필터링 (주연 기획자 맞춤형) ---
VALID_KEYWORDS = ["시스템", "콘텐츠", "컨텐츠", "UX", "UI", "기획", "System", "Content", "Planner"]
EXCLUDE_KEYWORDS = ["레벨", "Level", "전투", "Combat", "밸런스", "Balance"]

def is_valid_job(title):
    if any(ex.lower() in title.lower() for ex in EXCLUDE_KEYWORDS):
        return False
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

# --- 3. 회사별 수집 엔진 ---

def crawl_nexon(driver, count):
    """넥슨: 상세 공고 페이지의 동적 로딩 대응"""
    results = []
    driver.get("https://career.nexon.com/kr/recruit/notice")
    time.sleep(3)
    try:
        # 공고 리스트 대기
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "notice_list")))
        items = driver.find_elements(By.CSS_SELECTOR, ".notice_list li")
        found = 0
        for item in items:
            if found >= count: break
            title = item.find_element(By.CLASS_NAME, "title").text
            if not is_valid_job(title): continue
            
            item.click()
            time.sleep(2)
            # 상세 내용 수집
            content = driver.find_element(By.CLASS_NAME, "notice_view").text
            results.append({"company": "Nexon", "title": title, "content": content})
            found += 1
            driver.back()
            time.sleep(2)
    except: pass
    return results

def crawl_krafton(driver, count):
    """크래프톤: 제목 불일치 낚시 방지 로직"""
    results = []
    driver.get("https://krafton.ai/ko/careers/jobs/")
    time.sleep(3)
    try:
        items = driver.find_elements(By.CLASS_NAME, "job-item")
        found = 0
        for item in items:
            if found >= count: break
            title = item.find_element(By.TAG_NAME, "h3").text
            if not is_valid_job(title): continue
            
            item.click()
            try:
                # 제목 일치 확인 (7초 대기)
                WebDriverWait(driver, 7).until(lambda d: title[:5] in d.find_element(By.CLASS_NAME, "post-title").text)
                content = driver.find_element(By.CLASS_NAME, "post-content").text
                results.append({"company": "Krafton", "title": title, "content": content})
                found += 1
            except: pass
            driver.back()
            time.sleep(1)
    except: pass
    return results

# --- 4. AI 분석 엔진 (100만 점 리포트) ---

def analyze_job(model, job_data):
    # 주연님의 논리적 설계 역량과 데이터 무결성 철학 반영
    prompt = f"""
    너는 10년 차 리드 기획자야. 아래 공고가 '6년 차 시스템 기획자(주연)'에게 얼마나 적합한가?
    [공고] {job_data['company']} - {job_data['title']}
    [내용] {job_data['content']}
    
    분석 가이드:
    1. 주연 기획자의 강점: '예외 상황 방지 기획', '데이터 구조화', 'UX 로직 설계'.
    2. 점수는 0~1,000,000점 사이로 산출.
    3. [CRITICAL], [STRENGTH], [ACTION] 머리말을 사용해 전문적으로 작성.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "AI 분석 중입니다. 잠시만 기다려 주세요."

# --- 5. Streamlit 메인 UI ---

st.title("🛡️ 주연 기획자 전용: 무결성 채용공고 분석기")
st.markdown("> **넥슨 / 크래프톤 / NC소프트의 유효 직무를 정밀 분석합니다.**")

with st.sidebar:
    st.header("⚙️ 분석 설정")
    targets = st.multiselect("대상 회사", ["Nexon", "Krafton", "NCSoft"], default=["Nexon", "Krafton"])
    job_limit = st.slider("회사당 유효 공고 수집 개수", 1, 5, 2)

if st.button("🚀 유효 공고 분석 시작"):
    model = setup_ai()
    if not model:
        st.error("API 키를 확인해 주세요! (Secrets 설정)")
    else:
        driver = get_driver()
        all_jobs = []
        with st.spinner("불필요한 공고를 걸러내며 수집 중입니다..."):
            if "Nexon" in targets:
                all_jobs.extend(crawl_nexon(driver, job_limit))
            if "Krafton" in targets:
                all_jobs.extend(crawl_krafton(driver, job_limit))
            # (NCSoft 등 추가 루프)
        driver.quit()

        if all_jobs:
            for job in all_jobs:
                with st.expander(f"✨ [{job['company']}] {job['title']}"):
                    st.markdown(analyze_job(model, job))
        else:
            st.warning("현재 주연님의 전문 분야(시스템/콘텐츠/UX)에 맞는 공고가 없습니다.")
