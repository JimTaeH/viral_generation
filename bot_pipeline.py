import requests
from bs4 import BeautifulSoup
import edge_tts
import asyncio
import sys
from core.script_tools import ScriptGeneratorTool, VoiceOptimizerTool, NewsSummarizerTool
from pythainlp.tokenize import sent_tokenize
import os
import shutil
from core.comfy_client import ComfyClient # เพิ่มตัวเชื่อมต่อ Local
from core.video_assembler import VideoAssemblerTool # เวอร์ชันอัปเกรดแนวตั้ง
import time

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
    test_url = "https://www.blognone.com/node/151127"
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

    comfy = ComfyClient() # เรียกใช้เครื่องผลิตภาพ Local
    assembler = VideoAssemblerTool() # เรียกใช้เครื่องตัดต่อ
    
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
    
    # โฟลเดอร์เก็บ Asset ชั่วคราวเพื่อเอาไปมัดรวมกัน
    os.makedirs("assets_output", exist_ok=True)
    scenes_production_list = []

    CORE_CHARACTER_PROMPT = (
    "A highly realistic yet irresistibly adorable orange tabby cat cyborg character, "
    "designed as a lovable futuristic mascot. The cat has incredibly fluffy, soft, "
    "voluminous fur with rich orange tabby stripes, realistic individual hairs, silky texture, "
    "and subtle white accents around the muzzle and chest. Its fur appears touchably soft with "
    "ultra-realistic grooming and natural flow. Talking and acting smile, "
    "front view, close-up portrait shot, looking at camera, distinct facial features, centered composition"
)

    print("\n🔄 [Pipeline] เริ่มวิ่ง Loop ออโตเมชันรายฉากย่อย...")
    for idx, scene in enumerate(script_data.get("scenes", [])):
        scene_num = scene.get('scene_number', idx + 1)
        print(f"\n🎬 --- ลุยงานฉากย่อยที่ {scene_num} ---")
        
        # A. ดึงบทพูดและสั่งปรับแต่งคำทับศัพท์สำหรับ TTS
        raw_voice = scene.get('voice_script', '')
        optimized_voice = voice_tool.optimize_for_tts(raw_voice)
        
        # เจนไฟล์เสียงพากย์เฉพาะฉากนี้
        scene_audio_path = f"assets_output/voice_scene_{scene_num}.mp3"
        communicate = edge_tts.Communicate(text=optimized_voice, voice="th-TH-NiwatNeural", rate="+5%", pitch="+5Hz")
        await communicate.save(scene_audio_path)

        # B. ดึงบทภาพ (Visual Instruction) มาผสมสูตรมัดรวมส่งหา ComfyUI Node 3
        visual_instruction = scene.get('visual_instruction', '')
        final_image_prompt = f"{CORE_CHARACTER_PROMPT}, {visual_instruction}"
        max_retries = 3
        video_success = False
        comfy_video_file = None
        
        for attempt in range(max_retries):
            print(f"🔄 กำลังพยายามเจนวิดีโอฉากที่ {scene_num} (รอบที่ {attempt + 1}/{max_retries})...")
            
            comfy_video_file = comfy.generate_video(
                action_prompt=final_image_prompt, 
                workflow_path="workflow_api.json", 
                node_id="3",
                video_node_id="17"
            )
            
            if comfy_video_file != "FAILED_FACE_NOT_FOUND":
                video_success = True
                break
                
            print("🎲 ภาพสุ่มรอบนี้มุมกล้องไม่ได้องศาตรวจจับหน้าตรง สั่งดึง Seed ใหม่เพื่อสุ่มภาพโครงสร้างใหม่...")
            time.sleep(2) # พักเบรกสั้นๆ ก่อนเคลียร์คิวถัดไป

        if not video_success:
            raise Exception(f"💥 Pipeline ล้มเหลว: ฉากที่ {scene_num} เจนภาพสุ่ม 3 รอบแล้วตรวจไม่พบโครงสร้างใบหน้าตรงเลย")
            
        # คัดลอกวิดีโอย่อยเก็บเข้าคลัง Asset (เมื่อรันรอบที่สมบูรณ์สำเร็จ)
        local_video_path = f"assets_output/video_scene_{scene_num}.mp4"
        shutil.copy(comfy_video_file, local_video_path)
        
        # จัดชุดข้อมูลใส่ลิสต์เพื่อเตรียมส่งให้ตัวตัดต่อมัดรวมฉากย่อย
        scenes_production_list.append({
            "video": local_video_path,
            "audio": scene_audio_path,
            "text": raw_voice
        })

    # 3. ส่งลิสต์เสบียงทั้งหมดไปเข้าเครื่องตัดต่อเรนเดอร์เวอร์ชัน TikTok ท้ายสุด
    if scenes_production_list:
        assembler.assemble_from_scenes(scenes_production_list, output_path="tiktok_viral_output.mp4")

if __name__ == "__main__":
    asyncio.run(main())