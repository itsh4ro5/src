import fitz  # PyMuPDF
import os
import re

def process_pdf_watermark(input_file, output_file, watermark_text=None, remove_words=None):
    """
    Ultimate PDF Hacker: Removes Annotations, Auto-Detects Text Watermarks, 
    and applies Custom Branding (Emoji & Rotation Crash Fixed).
    """
    try:
        doc = fitz.open(input_file)
        
        # Regex Patterns
        tag_pattern = re.compile(r"@[a-zA-Z0-9_]+")
        link_pattern = re.compile(r"(?i)(t\.me|telegram\.me|telegram\.dog)/[a-zA-Z0-9_+]+")
        url_pattern = re.compile(r"(?i)https?://[a-zA-Z0-9_.-]+")
        
        promotional_phrases = [
            "Join TG", "JOIN TG", "join tg", "Telegram Channel",
            "Click Here", "Join @", "Join our", "Subscribe", "YouTube"
        ]
        
        for page in doc:
            # =========================================
            # ☢️ THE DEEP SCRUBBER (Layer Removal)
            # =========================================
            annots = page.annots()
            if annots:
                for annot in annots:
                    page.delete_annot(annot)

            # =========================================
            # 🧹 STEP 1, 2, 3: Phrase, Scanner & Custom
            # =========================================
            for phrase in promotional_phrases:
                text_instances = page.search_for(phrase)
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=(1, 1, 1)) 
                    
            words = page.get_text("words") 
            for w in words:
                text = w[4] 
                if tag_pattern.search(text) or link_pattern.search(text) or url_pattern.search(text):
                    rect = fitz.Rect(w[:4]) 
                    page.add_redact_annot(rect, fill=(1, 1, 1))

            if remove_words:
                for word in remove_words:
                    if word.strip():  
                        text_instances = page.search_for(word.strip())
                        for inst in text_instances:
                            page.add_redact_annot(inst, fill=(1, 1, 1))

            page.apply_redactions()
            
            # =========================================
            # 🖋 STEP 4: BUG-FREE BRANDING
            # =========================================
            if watermark_text and str(watermark_text).lower() != "skip":
                # 🔥 FIX 1: Emojis ko filter karo taaki PDF font engine crash na ho (Sirf English Text rakhega)
                clean_watermark = str(watermark_text).encode('ascii', 'ignore').decode('ascii').strip()
                
                if clean_watermark:
                    rect = page.rect
                    x = rect.width / 6
                    y = rect.height / 1.05 # Page ke bottom par place karega
                    f_size = rect.width / 15  
                    
                    # 🔥 FIX 2: rotate=45 hata diya, ab seedha aur clean watermark aayega
                    page.insert_text(
                        fitz.Point(x, y),
                        clean_watermark,
                        fontsize=f_size,
                        color=(0.4, 0.4, 0.4), # Premium Grey Text
                    )
                
        doc.save(output_file, deflate=True, garbage=4)
        doc.close()
        return True
    except Exception as e:
        print(f"PDF Processing Error: {e}")
        return False