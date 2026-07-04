import requests
from bs4 import BeautifulSoup
import edge_tts
import asyncio
import re
import sys
from langchain_core.prompts import ChatPromptTemplate
# นำเข้า LLMFactory จากไฟล์ที่มีอยู่ในโปรเจกต์
from core.llm_factory import LLMFactory
from core.script_tools import ScriptGeneratorTool, VoiceOptimizerTool, NewsSummarizerTool
from core.video_assembler import VideoAssemblerTool
from pythainlp.tokenize import sent_tokenize

# ตั้งค่า encoding ของ stdout/stderr ให้รองรับ UTF-8 เพื่อป้องกันข้อผิดพลาดเวลาแสดงผลอีโมจิใน Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ==========================================
# 1. ฟังก์ชันดึงเนื้อหาข่าวจาก URL
# ==========================================
def scrape_news(url):
    print("🌐 [1/3] กำลังดึงข้อมูลจาก URL...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        paragraphs = []
        # 1. ดึงข้อมูลจากแท็ก <p> ปกติ
        for p in soup.find_all('p'):
            p_text = p.get_text().strip()
            if p_text and p_text not in paragraphs:
                paragraphs.append(p_text)
                
        # 2. ดึงจาก Next.js/React Server Components script tags ที่อาจแฝง HTML แบบ escaped (เช่น \u003cp\u003e)
        for script in soup.find_all('script'):
            if script.string:
                script_text = script.string
                if '\\u003cp' in script_text or '\\u003cdiv' in script_text:
                    unescaped = script_text.replace('\\u003c', '<').replace('\\u003e', '>').replace('\\u0026', '&').replace('\\"', '"')
                    sub_soup = BeautifulSoup(unescaped, 'html.parser')
                    for p in sub_soup.find_all('p'):
                        p_text = p.get_text().strip()
                        if p_text and p_text not in paragraphs:
                            paragraphs.append(p_text)
                            
        text = " ".join(paragraphs)
        if not text:
            # ดึงข้อความดิบทั้งหมดของเว็บเป็นทางเลือกสุดท้าย
            text = soup.get_text(separator=' ', strip=True)
            
        return text[:3000] # ตัดมาแค่ 3000 ตัวอักษรเพื่อคุมจำนวน Token
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        return None

# ==========================================
# 3. ฟังก์ชันแปลงสคริปต์เป็นเสียงพากย์ (Edge TTS)
# ==========================================
async def generate_voice(script_text, output_filename="output_voice.mp3"):
    print("🎙️ [3/3] กำลังสร้างเสียงพากย์...")
    
    # เสียง NiwatNeural (ผู้ชาย) หรือ PremwadeeNeural (ผู้หญิง)
    voice = "th-TH-NiwatNeural" 
    
    communicate = edge_tts.Communicate(
        text=script_text, 
        voice=voice, 
        rate="+5%", 
        pitch="+5Hz", 
        volume="+0%"
    )
    await communicate.save(output_filename)
    print(f"✅ สำเร็จ! บันทึกไฟล์เสียงไว้ที่: {output_filename}")

# ==========================================
# Main Execution
# ==========================================
async def main():
    test_url = "https://www.blognone.com/node/151057"
    news_content = scrape_news(test_url)
    if not news_content:
        return
        
    # 1. เรียกใช้งาน Script Generator Tool
    script_tool = ScriptGeneratorTool(provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct")
    voice_tool = VoiceOptimizerTool(provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct")
    summarizer = NewsSummarizerTool(provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct")

    # script_tool = ScriptGeneratorTool(provider="google", model_name="gemini-3.5-flash")
    # voice_tool = VoiceOptimizerTool(provider="google", model_name="gemini-3.5-flash")
    # summarizer = NewsSummarizerTool(provider="google", model_name="gemini-3.5-flash")
    
    clean_text = summarizer.summarize(news_content)
    script_data = script_tool.generate_plan(clean_text)
    
    if script_data:
        # แยกบทพูดแบบดิบออกมา
        raw_voice = script_tool.get_voice_script(script_data)
        print(f"\n[📝 บทพูดดิบ]\n{raw_voice}")
        
        # --- Step 2: ปรับแต่งสคริปต์บทพูดสำหรับ TTS ---
        optimized_voice = voice_tool.optimize_for_tts(raw_voice)
        print(f"\n[✨ บทพูดที่ปรับแต่งแล้ว (ทับศัพท์ + จัดวรรค)]\n{optimized_voice}")
        optimized_sentences = sent_tokenize(optimized_voice, engine="crfcut")
        structured_script = " ".join(optimized_sentences) # รวมกลับเพื่อส่งให้ LLM หรือจะวนลูปจัดการทีละประโยคก็ได้
        
        # แสดงบทภาพสำหรับนำไปใช้งานต่อ
        production_guide = script_tool.get_production_script(script_data)
        print("\n🎬 --- แผนการผลิต (ภาพ + ท่าทาง + เสียง) ---")
        print(production_guide)

        script_tool.save_to_markdown(script_data, "final_script_meowbox.md")
        
        # --- Step 3: ส่งไปสร้างเสียงพากย์จริง ---
        # ตรงนี้ใช้ optimized_voice ส่งเข้า Edge TTS
        await generate_voice(structured_script, "final_voice.mp3")

if __name__ == "__main__":
    asyncio.run(main())