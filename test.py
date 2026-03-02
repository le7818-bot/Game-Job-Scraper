import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, NoSuchElementException
import time
import google.generativeai as genai

# --- 1. 유효 직무 필터링 로직 ---
# 주연님이 지정하신 유효 카테고리만 수집 대상에 포함합니다.
VALID_KEYWORDS = ["시스템", "콘텐츠", "컨텐츠", "UX", "UI", "UI/UX", "System", "Content"]
EXCLUDE_KEYWORDS = ["레벨", "Level", "전투", "Combat", "전투디자인", "전투기획"]

def is_valid_job(title):
    # 제외 키워드가 포함되어 있으면 무시
    if any(ex in title for ex in EXCLUDE_KEYWORDS):
        return False
    # 유효 키워드가 하나라도 포함되어 있으면 승인
    return any(kw in title for kw in VALID_KEYWORDS)

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

# --- 3. 회사별 수집 엔진 (수리 및 필터링 적용) ---

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
            
            # 주연님이 원하시는 직무인지 필터링
            if not is_valid_job(title): continue
            
            item.click()
            # [방어 로직] 제목 일치 대기 (낚시 방지)
            try:
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
    # (NC소프트 상세 수집 및 필터링 로직...)
    return results

# --- 4. AI 분석 엔진 (100만 점 리포트) ---

def analyze_job(model, job_data):
    # 주연님의 6년 차 경력과 논리적 설계 역량을 프롬프트에 반영
    prompt = f"""
    너는 10년 차 리드 게임 기획자야. 아래 공고가 '6년 차 시스템 기획자(주연)'에게 얼마나 적합한지 평가해.
    [공고] {job_data['company']} - {job_data['title']}
    [본문] {job_data['content']}
    
    분석 기준:
    1. 주연 기획자의 강점인 '예외 상황 방지', '논리적 무결성', '데이터 구조화' 역량이 필요한 자리인가?
    2. 점수는 0~1,000,000점 사이로 산출해.
    3. 결과는 [CRITICAL], [STRENGTH], [RISK] 머리말을 사용한 날카로운 개조식으로 작성해.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "AI 분석 중 오류가 발생했습니다."

# --- 5. Streamlit UI ---

st.set_page_config(page_title="게임사 공고 분석기", layout="wide")
st.title("🛡️ 주연 기획자 전용: 무결성 채용공고 분석기")
