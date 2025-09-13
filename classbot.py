from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import threading, datetime, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

router = APIRouter()

def join_class(class_index=0, duration_seconds=7200):
    print(f"🕒 {datetime.datetime.now().strftime('%H:%M:%S')} - Attempting to join class {class_index + 1}")
    opts = webdriver.ChromeOptions()
    opts.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.sound": 2
    })
    d = webdriver.Chrome(options=opts)
    w = WebDriverWait(d, 20)

    try:
        # Login
        d.get("https://myclass.lpu.in/")
        w.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div/form/div[7]/input[1]'))).send_keys(os.getenv("CLASSBOT_USERNAME"))
        d.find_element(By.XPATH,'/html/body/div[2]/div/form/div[7]/input[2]').send_keys(os.getenv("CLASSBOT_PASSWORD"))
        d.find_element(By.XPATH,'/html/body/div[2]/div/form/div[8]/button').click()

        time.sleep(5)
        w.until(EC.element_to_be_clickable((By.XPATH,'/html/body/div[9]/div/div[1]/div/div/div[1]/div/div[2]/a'))).click()
        time.sleep(3)

        # Get classes
        classes = w.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,'a.fc-time-grid-event.fc-event.fc-start.fc-end')))
        classes[class_index].click()
        time.sleep(2)
        w.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'a.btn.btn-primary.btn-block.btn-sm.joinBtn'))).click()

        time.sleep(5)
        w.until(EC.frame_to_be_available_and_switch_to_it((By.ID,"frame")))
        w.until(EC.element_to_be_clickable((By.XPATH,"//button//span[contains(text(),'Listen only')]"))).click()

        print(f"✅ Joined class {class_index + 1} (listen-only). Staying for {duration_seconds} seconds.")
        time.sleep(duration_seconds)

    finally:
        d.quit()
        print("🔒 Browser closed after class.")

def schedule_classes(times, class_index=0, duration_seconds=7200):
    while True:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        if current_time in times:
            join_class(class_index, duration_seconds)
            time.sleep(60)  # avoid multiple triggers same minute
        time.sleep(5)

# API endpoint
@router.post("/start")
async def start_scheduler():
    try:
        # Run scheduler in background thread
        def runner():
            schedule_classes(["09:00"], class_index=0, duration_seconds=7200)
            schedule_classes(["13:00"], class_index=1, duration_seconds=7200)
            schedule_classes(["15:00"], class_index=2, duration_seconds=3600)

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        return {"status": "started", "message": "Class scheduler is running in background"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
