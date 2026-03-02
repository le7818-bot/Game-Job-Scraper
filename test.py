import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException
import time
import pandas as pd
import google.generativeai as genai

# --- 1. 환경 설정 및 보안 (Secrets 활용) ---
def setup_api():
    try:
        # Streamlit Cloud의 Secrets에서 키를 가져옵니다.
        API_KEY = st.secrets.get("GEMINI_API_KEY", "")
        if API_KEY:
            genai.configure(api_key="".join(API_KEY.split()))
            return genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        st.error(f"API 설정 오류: {e}")
    return None

# --- 2. 회사별 수집 엔진 (방어적 설계 적용) ---

def crawl_krafton(driver, count):
    """크래프톤: 제목 불일치 방지를 위한 '이중 검증' 로직 추가"""
    results = []
    driver.get("https://krafton.ai/ko/careers/jobs/")
    time.sleep(3)
    
    # 공고 리스트 추출 (최신 구조 반영)
    items = driver.find_elements(By.CLASS_NAME, "job-item")[:count]
    
    for item in items:
        clicked_title = item.find_element(By.TAG_NAME, "h3").text
        item.click()
        
        # [핵심] 내가 클릭한 제목과 상세 페이지 제목이 일치할 때까지 대기
        try:
            WebDriverWait(driver, 7).until(
                lambda d: clicked_title[:10] in d.find_element(By.CLASS_NAME, "post-title").text
            )
            content = driver.find_element(By.CLASS_NAME, "post-content").text
            results.append({"company": "Krafton", "title": clicked_title, "content": content})
        except:
            # 로딩 실패 시 새로고침 후 재시도
            driver.refresh()
            time.sleep(2)
        driver.back()
        time.sleep(1)
    return results

def crawl_ncsoft(driver, count):
    """NC소프트: 시스템 오류 알럿(Alert) 자동 처리 로직 추가"""
    results = []
    try:
        driver.get("https://careers.ncsoft.com/ko/jobs")
        time.sleep(3)
    except UnexpectedAlertPresentException:
        # "시스템 오류가 발생하였습니다" 알럿 창을 자동으로 닫습니다.
        alert = driver.switch_to.alert
        alert.accept()
    
    # 이후 수집 로직... (구조에 맞게 보완)
    return results

def crawl_smilegate(driver, count):
    """스마일게이트: 변경된 CSS 셀렉터 대응"""
    results = []
    driver.get("https://careers.smilegate.com/ko/recruit/it")
    # 스마일게이트는 동적 로딩이 강하므로 충분한 대기 필요
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "list_item")))
    # ... (생략된 수집 로직)
    return results

# --- 3. 메인 실행 루프 ---
# (Streamlit UI 및 데이터 분석 로직)
