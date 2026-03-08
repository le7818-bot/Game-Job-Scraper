import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# --- 1. 클라우드용 헤드리스 드라이버 세팅 ---
def setup_driver():
    options = Options()
    options.add_argument('--headless=new') # 화면 없이 백그라운드에서 실행 (클라우드 필수)
    options.add_argument('--no-sandbox') # 리눅스 서버 환경 필수 권한 옵션
    options.add_argument('--disable-dev-shm-usage') # 메모리 초과로 인한 크래시 방지
    options.add_argument('--disable-gpu')
    
    # 넥슨 서버가 봇으로 인식하여 차단하는 것을 막기 위한 User-Agent 위장
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # webdriver_manager 없이 최신 Selenium 자체 기능으로 실행
    driver = webdriver.Chrome(options=options)
    return driver

# --- 2. 넥슨 크롤링 함수 ---
def crawl_nexon(driver, job_limit):
    st.info("📡 넥슨 채용 페이지에 접속 중...")
    driver.get("https://career.nexon.com/kr/recruit/notice")
    
    # 서버 환경에서는 로컬보다 네트워크/렌더링이 느릴 수 있으므로 대기 시간 확보
    time.sleep(3) 
    
    jobs = [] 
    
    # ==========================================
    # 💡 이 아래에 주연님이 작성하셨던 세부 파싱 로직
    # (XPath, find_elements 등)을 그대로 붙여넣어 주세요!
    # ==========================================
    
    # 예시: jobs.append({"title": "시스템 기획자", "link": "..."})
    
    return jobs

# --- 3. UI 및 메인 실행부 ---
st.set_page_config(page_title="Nexon Job Scraper", layout="wide")
st.title("🛡️ 주연 기획자의 넥슨 채용 공고 스크래퍼")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 스크래퍼 설정")
    job_limit = st.number_input("가져올 공고 수 한도", min_value=1, max_value=50, value=10)

if st.button("🚀 크롤링 시작"):
    with st.spinner("클라우드 서버에서 헤드리스 브라우저를 띄우는 중..."):
        driver = None
        try:
            # 1. 드라이버 소환
            driver = setup_driver()
            all_jobs = []
            
            # 2. 크롤링 로직 실행
            all_jobs.extend(crawl_nexon(driver, job_limit))
            
            # 3. 결과 출력
            st.success("데이터 추출 완료!")
            if all_jobs:
                st.dataframe(all_jobs) # 표 형태로 깔끔하게 출력
            else:
                st.warning("조건에 맞는 공고를 찾지 못했거나 파싱 로직 확인이 필요합니다.")
            
        except Exception as e:
            st.error(f"스크래핑 중 에러가 발생했습니다: {e}")
            st.info("💡 에러 로그를 확인하고 XPath나 셀렉터가 변경되지 않았는지 점검해 주세요.")
            
        finally:
            # ★ 시스템 안정성 확보: 에러 여부와 상관없이 무조건 브라우저 닫기
            if driver is not None:
                driver.quit()
