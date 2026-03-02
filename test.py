import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException
import time
import google.generativeai as genai

# --- 0. 페이지 기본 설정 ---
st.set_page_config(page_title="채용공고 분석기", layout="wide")

# --- 1. 직무 필터링 (시스템/콘텐츠/UXUI 전용) ---
VALID_KEYWORDS = ["시스템", "콘텐츠", "컨텐츠", "UX", "UI", "기획", "System", "Content", "Planner", "Designer"]
EXCLUDE_KEYWORDS = ["레벨", "Level", "전투", "Combat", "전투디자인", "전투기획", "밸런스", "Balance"]

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
    # 최신 헤드리스 모드 및 안정성 강화 옵션
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # [추가] 네트워크 및 메모리 안정화 필살기
    options.add_argument("--disable-extensions")
    options.add_argument("--dns-prefetch-disable")  # DNS 에러(ERR_NAME_NOT_RESOLVED) 방지
    options.add_argument("--remote-debugging-port=9222") # 포트 충돌 방지
    
    # 스트림릿 서버 설치 경로 강제 지정 (이전 로그의 버전 충돌 해결용)
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    from selenium.webdriver.chrome.service import Service
    # packages.txt로 설치된 chromedriver 경로 강제 지정
    service = Service("/usr/bin/chromedriver")
    
    try:
        return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        st.error(f"브라우저 초기화 실패: {e}")
        return None

# --- 3. 회사별 수집 엔진 (필터링 및 방어 로직 적용) ---

def crawl_nexon(driver, count):
    results = []
    driver.get("https://career.nexon.com/kr/recruit/notice")
    time.sleep(3)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "notice_list")))
        items = driver.find_elements(By.CSS_SELECTOR, ".notice_list li")
        found = 0
        for item in items:
            if found >= count: break
            title = item.find_element(By.CLASS_NAME, "title").text
            if not is_valid_job(title): continue # 직무 필터링
            
            item.click()
            time.sleep(2)
            content = driver.find_element(By.CLASS_NAME, "notice_view").text
            results.append({"company": "Nexon", "title": title, "content": content})
            found += 1
            driver.back()
            time.sleep(1)
    except: pass
    return results

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
            if not is_valid_job(title): continue # 직무 필터링
            
            item.click()
            try:
                # [방어] 상세 페이지 제목 검증 로직 (낚시 방지)
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
    # 시스템 기획서 명세 수준의 분석 프롬프트 (데이터 무결성 및 예외 처리 강조)
    prompt = f"""
    너는 10년 차 리드 기획자야. 아래 공고가 '6년 차 시스템 기획자'에게 얼마나 적합한지 평가해.
    [공고] {job_data['company']} - {job_data['title']}
    [본문] {job_data['content']}
    
    분석 기준:
    1. '논리적 설계', '예외 상황 방지 기획', '데이터 구조화' 역량이 요구되는가?
    2. 점수는 0~1,000,000점 사이로 산출.
    3. [CRITICAL], [STRENGTH], [RISK]를 사용해 날카롭고 전문적으로 작성.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "AI 분석 중 오류가 발생했습니다."

# --- 5. Streamlit 메인 UI ---

st.title("🛡️ 채용공고 무결성 분석기")
st.markdown("> **시스템 / 콘텐츠 / UXUI 기획 직무만 정밀 수집합니다.**")

with st.sidebar:
    st.header("⚙️ 검색 설정")
    targets = st.multiselect("대상 회사", ["Nexon", "Krafton", "NCSoft"], default=["Nexon", "Krafton"])
    job_limit = st.slider("회사당 유효 공고 수집 개수", 1, 5, 2)

if st.button("🚀 분석 시작"):
    model = setup_ai()
    if not model:
        st.error("API 키가 없습니다. Secrets 설정을 확인해 주세요!")
    else:
        driver = get_driver()
        all_jobs = []
        with st.spinner("불필요한 공고를 걸러내며 수집 중입니다..."):
            if "Nexon" in targets:
                all_jobs.extend(crawl_nexon(driver, job_limit))
            if "Krafton" in targets:
                all_jobs.extend(crawl_krafton(driver, job_limit))
        driver.quit()

        if all_jobs:
            for job in all_jobs:
                with st.expander(f"✨ [{job['company']}] {job['title']}"):
                    st.markdown(analyze_job(model, job))
        else:
            st.warning("현재 필터 조건에 맞는 공고가 페이지에 없습니다.")

