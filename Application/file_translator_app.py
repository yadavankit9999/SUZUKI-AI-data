def main():
    import streamlit as st
    import os
    import tempfile
    from pathlib import Path
    from Translator import FileTranslator, detect_language, validate_file_format, SECONDARY_LANG
    import time

    # Page configuration
    st.set_page_config(
        page_title="File Translator - Japanese ↔ English",
        page_icon="🌐",
        layout="wide"
    )

    # Initialize translator
    @st.cache_resource
    def get_translator():
        return FileTranslator()

    translator = get_translator()

    def translate_file(uploaded_file, translation_direction, use_ocr):
        """Handle file translation"""
        
        # Parse translation direction
        if "→" in translation_direction:
            source_lang, target_lang = translation_direction.split(" → ")
        else:
            source_lang, target_lang = translation_direction.split(" to ")
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Update progress
            progress_bar.progress(20)
            status_text.text("Extracting text from file...")
            
            # Extract text
            original_text = translator.extract_text_from_file(tmp_file_path, use_ocr)
            
            if not original_text.strip():
                st.error("No text content found in the file. Try enabling OCR if it's a scanned PDF.")
                os.unlink(tmp_file_path)
                return
            
            # Update progress
            progress_bar.progress(40)
            status_text.text("Translating text...")
            
            # Translate text
            translated_text = translator.translate_text(original_text, source_lang, target_lang)
            
            # Debug: Show translation in the app for troubleshooting
            st.info("**Debug: Translation Preview (first 500 chars):**\n" + translated_text[:500])
            
            # Warn if translation is too similar to original
            if translated_text.strip() == original_text.strip() or len(set(translated_text.strip())) < 10:
                st.warning("⚠️ The translation result is very similar to the original. The translation may have failed. Please check your API key, rate limits, or try again with a smaller file.")
            
            # Update progress
            progress_bar.progress(80)
            status_text.text("Preparing download...")
            
            # Generate output filename
            base_name = Path(uploaded_file.name).stem
            extension = Path(uploaded_file.name).suffix
            output_filename = f"{base_name}_translated_{target_lang}{extension}"
            
            # Save translated file
            output_path = os.path.join(tempfile.gettempdir(), output_filename)
            translator.save_translated_file(tmp_file_path, translated_text, output_path)
            
            # Update progress
            progress_bar.progress(100)
            status_text.text("Translation completed!")
            
            # Clean up
            os.unlink(tmp_file_path)
            
            st.success("✅ Translation completed successfully!")
            
            return {
                'success': True,
                'original_text': original_text,
                'translated_text': translated_text,
                'output_path': output_path
            }
            
        except Exception as e:
            st.error(f"❌ Translation failed: {str(e)}")
            progress_bar.progress(0)
            status_text.text("Translation failed")
            return {
                'success': False,
                'error': str(e)
            }

    def translate_quick_text(text, translation_direction):
        """Handle quick text translation"""
        
        # Parse translation direction
        if "→" in translation_direction:
            source_lang, target_lang = translation_direction.split(" → ")
        else:
            source_lang, target_lang = translation_direction.split(" to ")
        
        try:
            with st.spinner("Translating text..."):
                translated_text = translator.translate_text(text, source_lang, target_lang)
            
            # Display results
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Original Text")
                st.text_area("Original", text, height=200, disabled=True)
            
            with col2:
                st.subheader("Translated Text")
                st.text_area("Translated", translated_text, height=200, disabled=True)
            
            # Copy button
            st.button("📋 Copy Translated Text", on_click=lambda: st.write("Copied to clipboard!"))
            
            st.success("✅ Text translation completed!")
            
        except Exception as e:
            st.error(f"❌ Translation failed: {str(e)}")

    # Main app
    st.title("🌐 File Translator - Japanese ↔ English")
    st.markdown("Translate your documents between Japanese and English with OCR support for PDF files")
    
    # Sidebar for options
    with st.sidebar:
        st.header("Translation Options")
        
        # Secondary language toggle
        secondary_lang = st.selectbox(
            "Secondary Language",
            ["Hindi", "Japanese"],
            index=0 if SECONDARY_LANG == "Hindi" else 1,
            help="Choose the secondary language for translation."
        )
        
        # Translation direction
        translation_direction = st.selectbox(
            "Translation Direction",
            [f"English → {secondary_lang}", f"{secondary_lang} → English"],
            help="Choose the direction of translation"
        )
        
        # OCR option for PDFs
        use_ocr = st.checkbox(
            "Enable OCR for PDF files",
            help="Use OCR to extract text from images in PDF files (slower but more accurate for scanned documents)"
        )
        
        # File format info
        st.markdown("---")
        st.markdown("**Supported Formats:**")
        st.markdown("• PDF (.pdf)")
        st.markdown("• Word (.docx)")
        st.markdown("• Excel (.xlsx)")
        st.markdown("• Text (.txt)")
        
        st.markdown("---")
        st.markdown("**Features:**")
        st.markdown("• OCR for scanned PDFs")
        st.markdown("• Preserves original formatting")
        st.markdown("• High-quality AI translation")
        st.markdown("• Batch processing ready")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Upload Your File")
        uploaded_file = st.file_uploader(
            "Choose a file to translate",
            type=['pdf', 'docx', 'xlsx', 'txt'],
            help="Upload a file to translate"
        )
        # Use session state to persist file and translation
        if 'uploaded_file' not in st.session_state or (uploaded_file and uploaded_file != st.session_state.get('uploaded_file_obj')):
            st.session_state['uploaded_file'] = None
            st.session_state['uploaded_file_obj'] = uploaded_file
            st.session_state['translation_result'] = None
        if uploaded_file is not None and st.button("🚀 Translate File", type="primary"):
            st.session_state['uploaded_file'] = uploaded_file
            st.session_state['translation_result'] = None  # Reset previous result
        if st.session_state.get('uploaded_file') and st.session_state['translation_result'] is None:
            # Do translation and store result
            result = translate_file(st.session_state['uploaded_file'], translation_direction, use_ocr)
            st.session_state['translation_result'] = result
        if st.session_state.get('translation_result'):
            result = st.session_state['translation_result']
            if result.get('success'):
                original_text = result['original_text']
                translated_text = result['translated_text']
                output_path = result['output_path']
                
                # Create unique widget keys
                file_suffix = os.path.basename(st.session_state['uploaded_file'].name) if st.session_state.get('uploaded_file') else ""
                unique_id = str(id(st.session_state['uploaded_file'])) if st.session_state.get('uploaded_file') else str(time.time())
                widget_key_prefix = f"{file_suffix}_{unique_id}"
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Original Text (Preview)")
                    st.text_area("Original", original_text[:500] + "..." if len(original_text) > 500 else original_text, height=200, disabled=True, key=f"original_preview_{widget_key_prefix}")
                with col2:
                    st.subheader("Translated Text (Preview)")
                    st.text_area("Translated", translated_text[:500] + "..." if len(translated_text) > 500 else translated_text, height=200, disabled=True, key=f"translated_preview_{widget_key_prefix}")
                    if st.button("Show Full Preview", key=f"show_full_{widget_key_prefix}"):
                        with st.expander("Full Translated Text", expanded=True):
                            st.text_area("Full Translated Text", translated_text, height=400, disabled=True, key=f"translated_full_{widget_key_prefix}")
                            if st.button("Copy All", key=f"copy_all_{widget_key_prefix}"):
                                # Inject JavaScript to copy the translated text to clipboard
                                st.markdown(f"""
                                    <textarea id='copyArea_{widget_key_prefix}' style='position:absolute; left:-1000px; top:-1000px;'>{translated_text}</textarea>
                                    <script>
                                    function copyToClipboard_{widget_key_prefix}() {{
                                        var copyText = document.getElementById('copyArea_{widget_key_prefix}');
                                        copyText.style.display = 'block';
                                        copyText.select();
                                        document.execCommand('copy');
                                        copyText.style.display = 'none';
                                    }}
                                    copyToClipboard_{widget_key_prefix}();
                                    </script>
                                    <span style='color: green;'>Copied to clipboard!</span>
                                """, unsafe_allow_html=True)
                
                # Only show download if file exists
                if os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        st.download_button(
                            label=f"📥 Download Translated File",
                            data=f.read(),
                            file_name=os.path.basename(output_path),
                            mime=st.session_state['uploaded_file'].type if st.session_state.get('uploaded_file') else 'application/octet-stream',
                            help="Download your translated file",
                            key=f"download_{widget_key_prefix}"
                        )
                else:
                    st.warning("Download file not found. Please re-translate or check for errors.")
            else:
                st.error(f"❌ Translation failed: {result.get('error')}")
    
    with col2:
        st.header("Quick Translation")
        
        # Text input for quick translation
        quick_text = st.text_area(
            "Enter text for quick translation",
            height=200,
            placeholder="Type or paste your text here..."
        )
        
        if quick_text and st.button("Translate Text"):
            translate_quick_text(quick_text, translation_direction)
        
        # Progress and status
        if 'translation_progress' in st.session_state:
            st.progress(st.session_state.translation_progress)
            st.text(st.session_state.translation_status)

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>Powered by Google Gemini AI • Built with Streamlit</p>
            <p>Support for PDF, Word, Excel, and Text files with OCR capabilities</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 