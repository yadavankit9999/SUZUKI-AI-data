def main():
    import streamlit as st
    import tempfile
    import os
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    import shutil
    import glob

    # Supported formats for Google API Docs
    SUPPORTED_FORMATS = ['pdf', 'docx', 'txt', 'html']

    TRANSLATE_URL = 'https://translate.google.com/?sl=en&tl=hi&op=docs'

    st.set_page_config(
        page_title="File Translator (Google API)",
        page_icon="🌐",
        layout="wide"
    )

    st.title("🌐 File Translator (Google API)")
    st.markdown("Translate your documents between English and Hindi using Google API feature.")

    with st.sidebar:
        st.header("Translation Options")
        st.markdown("**Supported Formats:**")
        st.markdown("• PDF (.pdf)")
        st.markdown("• Word (.docx)")
        st.markdown("• Text (.txt)")
        st.markdown("• HTML (.html)")
        st.markdown("---")
        st.markdown("**Features:**")
        st.markdown("• Uses Google API translation")
        st.markdown("• Preserves much of the original formatting")
        st.markdown("• No API key required")

    uploaded_file = st.file_uploader(
        "Choose a file to translate",
        type=SUPPORTED_FORMATS,
        help="Upload a file to translate using Google API"
    )

    if uploaded_file is not None:
        if st.button("🚀 Translate File", type="primary"):
            with st.spinner("Translating via Google API (this may take up to a minute)..."):
                # Save uploaded file to temp
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                # Create a unique temp download directory
                download_dir = tempfile.mkdtemp()
                # Set up Selenium headless Chrome
                chrome_options = Options()
                chrome_options.add_argument('--headless')  # Try with this commented out!
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
                prefs = {
                    "download.default_directory": download_dir,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True
                }
                chrome_options.add_experimental_option("prefs", prefs)
                driver = webdriver.Chrome(options=chrome_options)
                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
                    """
                })
                try:
                    driver.get(TRANSLATE_URL)
                    # Wait for the file input to appear
                    upload_input = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//input[@type="file"]'))
                    )
                    upload_input.send_keys(tmp_file_path)
                    # Wait for the "Translate" button to be clickable
                    translate_btn = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Translate")]'))
                    )
                    translate_btn.click()
                    # Wait for translation to finish (look for download button)
                    download_btn = WebDriverWait(driver, 60).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(), "Download translation")]]'))
                    )
                    download_btn.click()
                    # Wait for a new file to appear in the download directory
                    timeout = 60
                    poll_interval = 1
                    elapsed = 0
                    downloaded_file = None
                    while elapsed < timeout:
                        files = glob.glob(os.path.join(download_dir, '*'))
                        if files:
                            # Get the most recent file
                            downloaded_file = max(files, key=os.path.getctime)
                            # Check if file is still being written
                            if os.path.getsize(downloaded_file) > 0:
                                break
                        time.sleep(poll_interval)
                        elapsed += poll_interval
                    if not downloaded_file or not os.path.exists(downloaded_file):
                        st.error("❌ Downloaded file not found. Translation may have failed.")
                    else:
                        ext = os.path.splitext(uploaded_file.name)[1].lower()
                        output_filename = os.path.splitext(uploaded_file.name)[0] + '_translated' + ext
                        st.success("✅ Translation completed successfully!")
                        with open(downloaded_file, 'rb') as f:
                            st.download_button(
                                label=f"📥 Download Translated File",
                                data=f.read(),
                                file_name=output_filename,
                                mime=uploaded_file.type,
                                help="Download your translated file"
                            )
                except Exception as e:
                    st.error(f"❌ Translation failed: {str(e)}")
                finally:
                    driver.quit()
                    os.unlink(tmp_file_path)
                    shutil.rmtree(download_dir, ignore_errors=True) 