import requests
from bs4 import BeautifulSoup
import edge_tts
import asyncio
import re
import sys
from langchain_core.prompts import ChatPromptTemplate
# นำเข้า LLMFactory จากไฟล์ที่มีอยู่ในโปรเจกต์
from core.llm_factory import LLMFactory
from core.script_tools import ScriptGeneratorTool, VoiceOptimizerTool
from core.video_assembler import VideoAssemblerTool

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
# 2. ฟังก์ชันให้ AI สรุปและเขียนสคริปต์ (ใช้ LLMFactory)
# ==========================================
def generate_script(news_text, provider="google", model_name="gemini-1.5-flash"):
    print(f"🤖 [2/3] เจ้าเหมียวไซบอร์กกำลังเขียนสคริปต์ด้วย {provider} ({model_name})...")
    
    # 2.1 สร้าง LLM อินสแตนซ์ผ่าน LLMFactory
    try:
        llm = LLMFactory.create_llm(
            provider=provider, 
            model_name=model_name,
            temperature=0.1
        )
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการโหลด LLM: {e}")
        return None

    # 2.2 สร้าง Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "คุณคือ 'เจ้าเหมียวไซบอร์ก' ครีเอเตอร์สายเทคโนโลยีบน TikTok คาแรคเตอร์: ฉลาด กวนนิดๆ เรียกคนดูว่า 'นุด' (มนุษย์)"),
        ("user", """จงอ่านข่าวเทคโนโลยีต่อไปนี้ และสรุปเป็นสคริปต์วิดีโอ TikTok ความยาว 45 วินาที
        
        เนื้อหาข่าว: {news_text}
        
        กฎสำคัญ:
        1. เขียนเฉพาะ "คำพูด" ที่จะให้ออกเสียงเท่านั้น ห้ามใส่วงเล็บอธิบายภาพ ห้ามใส่สัญลักษณ์พิเศษ ห้ามใส่ [ดนตรี] หรือ [เอฟเฟกต์]
        2. เปิดคลิปด้วย Hook ที่ดึงดูดใจ
        3. เล่าเนื้อหาให้กระชับ เข้าใจง่าย
        4. ปิดท้ายด้วยการบอกให้กดติดตามช่อง 'เจ้าเหมียวไซบอร์ก'
        """)
    ])

    # 2.3 รัน Chain ด้วย LCEL Syntax
    try:
        chain = prompt | llm
        response = chain.invoke({"news_text": news_text})
        
        # ทำความสะอาดข้อความ ลบพวกเครื่องหมาย *, # 
        clean_script = re.sub(r'[*#]', '', response.content)
        return clean_script
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการรัน LangChain: {e}")
        return None

# ==========================================
# 3. ฟังก์ชันแปลงสคริปต์เป็นเสียงพากย์ (Edge TTS)
# ==========================================
async def generate_voice(script_text, output_filename="output_voice.mp3"):
    print("🎙️ [3/3] กำลังสร้างเสียงพากย์...")
    
    # เสียง NiwatNeural (ผู้ชาย) หรือ PremwadeeNeural (ผู้หญิง)
    voice = "th-TH-NiwatNeural" 
    
    communicate = edge_tts.Communicate(script_text, voice)
    await communicate.save(output_filename)
    print(f"✅ สำเร็จ! บันทึกไฟล์เสียงไว้ที่: {output_filename}")

# ==========================================
# Main Execution
# ==========================================
async def main():
    test_url = "https://www.blognone.com/node/151045" 
    news_content = scrape_news(test_url)
    if not news_content:
        return
        
    # 1. เรียกใช้งาน Script Generator Tool
    script_tool = ScriptGeneratorTool(provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct")
    voice_tool = VoiceOptimizerTool(provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct")
    script_data = script_tool.generate_plan(news_content)
    
    if script_data:
        # แยกบทพูดแบบดิบออกมา
        raw_voice = script_tool.get_voice_script(script_data)
        print(f"\n[📝 บทพูดดิบ]\n{raw_voice}")
        
        # --- Step 2: ปรับแต่งสคริปต์บทพูดสำหรับ TTS ---
        optimized_voice = voice_tool.optimize_for_tts(raw_voice)
        print(f"\n[✨ บทพูดที่ปรับแต่งแล้ว (ทับศัพท์ + จัดวรรค)]\n{optimized_voice}")
        
        # แสดงบทภาพสำหรับนำไปใช้งานต่อ
        visual_guide = script_tool.get_visual_script(script_data)
        print(f"\n[🎬 แผนงานบทภาพ]\n{visual_guide}")
        
        # --- Step 3: ส่งไปสร้างเสียงพากย์จริง ---
        # ตรงนี้ใช้ optimized_voice ส่งเข้า Edge TTS
        await generate_voice(optimized_voice, "final_voice.mp3")

if __name__ == "__main__":
    asyncio.run(main())