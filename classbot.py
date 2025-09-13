from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import threading, datetime, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os
import logging

router = APIRouter()

def setup_chrome_options():
    opts = Options()
    
    # Essential options for Render
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--remote-debugging-port=9222")
    opts.add_argument("--single-process")
    opts.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Disable audio/video permissions
    opts.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.sound": 2,
        "profile.default_content_setting_values.notifications": 2
    })
    
    # Binary locations for Render
    opts.binary_location = "/usr/bin/chromium-browser"
    
    return opts

def join_class(class_index=0, duration_seconds=7200):
    print(f"🕒 {datetime.datetime.now().strftime('%H:%M:%S')} - Attempting to join class {class_index + 1}")
    
    try:
        opts = setup_chrome_options()
        
        # Set Chrome driver for Render
        driver_path = "/usr/local/bin/chromedriver"
        service = webdriver.chrome.service.Service(driver_path)
        
        d = webdriver.Chrome(service=service, options=opts)
        w = WebDriverWait(d, 30)  # Increased timeout for Render
        
        # Login
        d.get("https://myclass.lpu.in/")
        username = os.getenv("CLASSBOT_USERNAME")
        password = os.getenv("CLASSBOT_PASSWORD")

        if not username or not password:
            print("❌ Environment variables CLASSBOT_USERNAME or CLASSBOT_PASSWORD not set!")
            return

        # Wait for page to load completely
        time.sleep(5)
        
        # Find and fill username
        username_field = w.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/div/form/div[7]/input[1]')))
        username_field.clear()
        username_field.send_keys(username)
        
        # Find and fill password
        password_field = d.find_element(By.XPATH, '/html/body/div[2]/div/form/div[7]/input[2]')
        password_field.clear()
        password_field.send_keys(password)
        
        # Click login button
        login_button = d.find_element(By.XPATH, '/html/body/div[2]/div/form/div[8]/button')
        login_button.click()

        time.sleep(5)
        
        # Navigate to classes
        class_link = w.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[9]/div/div[1]/div/div/div[1]/div/div[2]/a')))
        class_link.click()
        time.sleep(3)

        # Get classes
        classes = w.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.fc-time-grid-event.fc-event.fc-start.fc-end')))
        
        if len(classes) <= class_index:
            print(f"❌ Class index {class_index} not available. Only {len(classes)} classes found.")
            return
            
        classes[class_index].click()
        time.sleep(2)
        
        # Join class
        join_button = w.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn.btn-primary.btn-block.btn-sm.joinBtn')))
        join_button.click()

        time.sleep(10)  # Wait longer for class to load
        
        # Switch to iframe and join listen only
        w.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frame")))
        listen_button = w.until(EC.element_to_be_clickable((By.XPATH, "//button//span[contains(text(),'Listen only')]")))
        listen_button.click()

        print(f"✅ Joined class {class_index + 1} (listen-only). Staying for {duration_seconds} seconds.")
        
        # Stay in class for the duration
        time.sleep(duration_seconds)

    except Exception as e:
        print(f"❌ Error while joining class {class_index + 1}: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")

    finally:
        try:
            d.quit()
            print("🔒 Browser closed after class.")
        except:
            print("⚠️  Browser already closed or not initialized.")

def schedule_classes(times, class_index=0, duration_seconds=7200):
    while True:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        if current_time in times:
            print(f"⏰ Triggering class {class_index + 1} at {current_time}")
            join_class(class_index, duration_seconds)
            time.sleep(60)  # Avoid multiple triggers in the same minute
        time.sleep(30)  # Check every 30 seconds

@router.post("/start")
async def start_scheduler():
    try:
        def runner():
            # Schedule multiple classes with different times
            schedule_classes(["09:00", "09:01", "09:02"], class_index=0, duration_seconds=7200)
            schedule_classes(["13:00", "13:01", "13:02"], class_index=1, duration_seconds=7200)
            schedule_classes(["15:00", "15:01", "15:02"], class_index=2, duration_seconds=3600)

        # Start scheduler in background thread
        t = threading.Thread(target=runner, daemon=True)
        t.start()
        
        return {
            "status": "started", 
            "message": "Class scheduler is running in background",
            "scheduled_classes": [
                {"index": 0, "times": ["09:00", "09:01", "09:02"], "duration": "2 hours"},
                {"index": 1, "times": ["13:00", "13:01", "13:02"], "duration": "2 hours"},
                {"index": 2, "times": ["15:00", "15:01", "15:02"], "duration": "1 hour"}
            ]
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/status")
async def scheduler_status():
    return {
        "status": "running",
        "message": "ClassBot scheduler is active",
        "environment": "Render" if os.environ.get('RENDER') else "Local"
    }