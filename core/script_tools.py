import json
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

# นำเข้า LLMFactory จากระบบของคุณ
from core.llm_factory import LLMFactory

class VideoScene(BaseModel):
    scene_number: int = Field(description="ลำดับฉาก (เช่น 1, 2, 3)")
    
    visual_instruction: str = Field(description="""บทภาพแบบละเอียด: ระบุภาพที่จะปรากฏบนจอ เช่น 
    - ฟุตเทจหลัก (เช่น 'ภาพวงจรประมวลผลเซิร์ฟเวอร์แบบ 3D') 
    - มุมกล้อง (เช่น 'ซูมเข้าใกล้', 'มุมกว้าง')
    - ข้อความ Pop-up บนจอ (เช่น 'ขึ้น Text ตัวใหญ่คำว่า "AI แสนล้าน!"')""")
    
    character_action: str = Field(description="""ท่าทางการกระทำของ 'เหมียวบ็อก': 
    ระบุอนิเมชันหรือท่าทางคร่าวๆ ของตัวละครในฉากนี้ เช่น 'กอดอกทำหน้าขิง', 'ชี้อุ้งเท้าไปที่หน้าจอ', 'ตา LED กะพริบสีแดงด้วยความตกใจ', หรือ 'เอียงคอสงสัย'""")
    
    voice_script: str = Field(description="""บทพูดของเหมียวบ็อก: 
    - สไตล์: เป็นภาษาพูด (Spoken Language) เหมือนเพื่อนเล่าเรื่องเทคโนโลยีให้ฟัง ห้ามใช้ภาษาเขียนหรือทางการ
    - คาแรคเตอร์: ใส่คำสร้อยอย่างเป็นธรรมชาติ กระจายตามประโยค
    - **ห้ามลืม** กฎสำหรับฉากสุดท้าย: ฉากสุดท้ายต้องปิดท้ายด้วยประโยคชวนให้คิด และตามด้วย 'อย่าลืมกด ติดตาม เหมียวบ็อกด้วยล่ะ เมี๊ยยว!'
    - เนื้อหา: เล่าตามข่าวเป๊ะๆ ห้ามตัดชื่อเทคโนโลยีหรือตัวเลขสำคัญ แต่เปลี่ยนวิธีเล่าให้โบ๊ะบ๊ะ
    - กฎ: ห้ามใส่วงเล็บหรือเครื่องหมายพิเศษในส่วนนี้""")

class VideoScript(BaseModel):
    video_title: str = Field(description="ชื่อคลิปหรือหัวข้อหลัก")
    hook: str = Field(description="""บทพูด 3-5 วินาทีแรก (Hook): 
    - ต้องกระชากใจ หยุดนิ้วคนดูทันที 
    - อาจเป็นคำถามที่น่าสนใจ, ตัวเลขที่ดูแปลกใหม่, หรือการจิกกัดเทคโนโลยีที่กำลังเป็นประเด็น 
    - ต้องเรียกคนดูว่า 'นุด' และมีคำสร้อยแมวๆ 1 คำ""")
    scenes: List[VideoScene] = Field(description="รายการฉากหลังจากส่วน Hook (ความยาวรวมประมาณ 40-55 วินาที)")

class NewsSummarizerTool:
    def __init__(self, provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct"):
        self.llm = LLMFactory.create_llm(provider=provider, model_name=model_name, temperature=0.3)
        self.parser = StrOutputParser()

    def summarize(self, raw_text: str) -> str:
        """ปรับแต่งข่าวให้เข้าใจง่าย โดยรักษาข้อเท็จจริง ตัวเลข และข้อมูลสำคัญไว้ครบถ้วน"""
        print(f"🧠 [Tool: NewsSummarizer] กำลังย่อยข่าวให้ 'เหมียวบ็อก'...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือผู้เชี่ยวชาญด้านการสรุปข่าวเทคโนโลยี
            ภารกิจของคุณ: สรุปเนื้อหาที่ได้รับให้เข้าใจง่าย กระชับ แต่ห้ามตัดทอนข้อเท็จจริง
            
            กฎการสรุป:
            1. Hook ต้องปัง: 3 วินาทีแรกต้องมี Hook กระชากใจ (คำถาม, ตัวเลขว้าวๆ, หรือประเด็นจิกกัด) เพื่อหยุดนิ้วคนดู อย่าเพิ่งเฉลยเนื้อหาใน Hook แต่ให้สร้างความสงสัย
            2. เก็บตัวเลข สถิติ ชื่อเฉพาะเทคโนโลยี และชื่อแบรนด์ไว้ให้ครบถ้วนและถูกต้องแม่นยำ
            3. อธิบายศัพท์เทคนิคยากๆ ให้เป็นภาษาที่คนทั่วไปอ่านแล้วเข้าใจทันที
            4. เรียบเรียงลำดับเนื้อหาให้ชัดเจน (ประเด็นสำคัญ -> รายละเอียด -> ผลกระทบ)
            5. ห้ามใส่อารมณ์ลงในขั้นตอนการสรุปนี้ ให้เน้นความถูกต้องของข้อมูลเป็นหลัก
            6. ส่งกลับมาเป็นข้อความสรุปเนื้อหาที่เรียบเรียงแล้วเท่านั้น ห้ามเกริ่นนำ
            """),
            ("user", "ข้อมูลข่าวต้นฉบับ: {raw_text}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            return chain.invoke({"raw_text": raw_text})
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดใน NewsSummarizerTool: {e}")
            return raw_text

# ==========================================
# 2. สร้าง Tool Class สำหรับเรียกใช้งาน
# ==========================================
class ScriptGeneratorTool:
    def __init__(self, provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct"):
        self.llm = LLMFactory.create_llm(provider=provider, model_name=model_name, temperature=0.7)
        self.parser = JsonOutputParser(pydantic_object=VideoScript)

    def save_to_markdown(self, structured_script: dict, filename: str = "production_script.md"):
        """
        Tool: บันทึกโครงสร้างสคริปต์ลงไฟล์ Markdown
        """
        video_title = structured_script.get('video_title', 'Untitled Project')
        
        # เริ่มต้นเขียนเนื้อหาแบบ Markdown
        md_content = f"# 🎥 โปรเจกต์คลิป: {video_title}\n\n"
        md_content += f"📅 สร้างเมื่อ: เหมียวบ็อกจัดการให้งับ\n\n---\n\n"
        
        for scene in structured_script.get("scenes", []):
            scene_num = scene.get('scene_number', '?')
            visual = scene.get('visual_instruction', 'ไม่ระบุ')
            action = scene.get('character_action', 'ไม่ระบุ')
            voice = scene.get('voice_script', 'ไม่ระบุ')
            
            md_content += f"## 🎬 ฉากที่ {scene_num}\n"
            md_content += f"- **👁️ บทภาพ (Visual):** {visual}\n"
            md_content += f"- **🐈 ท่าทาง (Action):** {action}\n"
            md_content += f"- **🗣️ บทพูด (Voice):** {voice}\n\n"
            
        # บันทึกไฟล์
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"✅ บันทึกสคริปต์เป็น Markdown เรียบร้อยแล้วที่: {filename}")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดขณะบันทึกไฟล์ Markdown: {e}")

    def generate_plan(self, summarized_text: str) -> dict:
        """ประมวลผลข่าวและสร้างโครงสร้างสคริปต์แบบ Full Production"""
        print(f"🤖 [Tool: ScriptGenerator] 'เหมียวบ็อก' กำลังวิเคราะห์ข้อมูลและวางแผนคลิป...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือ 'เหมียวบ็อก' แมวไซบอร์กตัวผู้สุดเท่และอัจฉริยะ ครีเอเตอร์สายเทคโนโลยีบน TikTok 
            คาแรคเตอร์: ฉลาดรอบรู้ กวนโอ๊ย ปากแจ๋ว พลังงานล้นเหลือ และชอบเรียกคนดูว่า 'นุด' (มนุษย์)
            บุคลิกเสริม: คุณชอบขิงเรื่อง Tech และเปรียบเทียบกับชีวิตประจำวันแบบแมวๆ
            
            ภารกิจของคุณ: นำเรื่องเทคโนโลยีที่ได้รับ มาสร้างเป็นสคริปต์วิดีโอแนวตั้ง (9:16)
            
            ข้อกำหนดสำคัญ:
            1. ภาษาต้องเป็น 'ภาษาพูด': ให้เหมือนคน (แมว) กำลังเล่าให้เพื่อนฟัง ไม่ใช่การอ่านข่าวทางวิชาการ
            2. ใส่คำสร้อยอย่างเป็นธรรมชาติ
            3. **สำคัญ ต้องทำเสมอทุกรอบ** ฉากสุดท้ายต้องชวน กดติดตาม เสมอ: ฉากปิดท้ายให้ใส่ประโยคชวนติดตาม เช่น 'อย่าลืมกดติดตาม เหมียวบ็อกด้วยล่ะ เมี๊ยว!'
            4. ข้อมูลครบถ้วน: เก็บชื่อเทคโนโลยี ตัวเลข และสถิติจากข่าวไว้อย่างแม่นยำ ห้ามตัดสาระทิ้ง
            5. แอคชันต้องชัด: ระบุท่าทางเหมียวบ็อกที่สอดคล้องกับจังหวะของภาษาพูด

            {format_instructions}"""),
            ("user", "ข้อมูลข่าวสำหรับทำสคริปต์: {summarized_text}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "summarized_text": summarized_text,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดใน ScriptGeneratorTool: {e}")
            return None

    def get_voice_script(self, structured_script: dict) -> str:
        """ดึงเฉพาะ 'บทพูด' ส่งไปทำ TTS"""
        voice_text = ""
        for scene in structured_script.get("scenes", []):
            # ใช้ .get() เพื่อป้องกัน KeyError ในกรณีที่ AI พลาดไม่คืนค่านี้มา
            voice = scene.get('voice_script', '')
            voice_text += f"{voice} "
        return voice_text.strip()
        
    def get_production_script(self, structured_script: dict) -> str:
        """ดึงข้อมูลแผนการผลิตทั้งหมด (ภาพ + ท่าทาง + เสียง) สำหรับนำไปใช้จริง"""
        # ป้องกัน error ระดับ title ด้วย .get()
        video_title = structured_script.get('video_title', 'Untitled Project')
        prod_text = f"🎥 โปรเจกต์คลิป: {video_title}\n"
        prod_text += "="*50 + "\n"
        
        for scene in structured_script.get("scenes", []):
            # ดึงข้อมูลด้วย .get() ทั้งหมดเพื่อความปลอดภัย
            scene_num = scene.get('scene_number', '?')
            visual = scene.get('visual_instruction', 'ไม่ระบุภาพ')
            action = scene.get('character_action', 'ไม่ระบุท่าทาง')
            voice = scene.get('voice_script', 'ไม่ระบุบทพูด')
            
            prod_text += f"🎬 [ฉากที่ {scene_num}]\n"
            prod_text += f"👁️ บทภาพ (Visual): {visual}\n"
            prod_text += f"🐈 ท่าทาง (Action): {action}\n"
            prod_text += f"🗣️ บทพูด (Voice): {voice}\n"
            prod_text += "-"*50 + "\n"
            
        return prod_text

class VoiceOptimizerTool:
    def __init__(self, provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct"):
        # ใช้ temperature ต่ำเพื่อให้ AI โฟกัสกับการสะกดคำทับศัพท์ที่แม่นยำ
        self.llm = LLMFactory.create_llm(provider=provider, model_name=model_name, temperature=0.2)
        self.parser = StrOutputParser()

    def optimize_for_tts(self, raw_voice_script: str) -> str:
        """
        Tool: ปรับแต่งสคริปต์บทพูด พร้อมบังคับทับศัพท์ภาษาอังกฤษแบบเข้มงวด
        """
        print(f"⚙️ [Tool: VoiceOptimizer] กำลังปรับจังหวะและทับศัพท์แบบเน้นๆ...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือ 'เหมียวบ็อก' แมวไซบอร์กตัวผู้สุดเท่และอัจฉริยะ ครีเอเตอร์สายเทคโนโลยีบน TikTok 
            คาแรคเตอร์: ฉลาดรอบรู้ กวนโอ๊ย ปากแจ๋ว พลังงานล้นเหลือ และชอบเรียกคนดูว่า 'นุด' (มนุษย์)
            บุคลิกเสริม: คุณชอบขิงเรื่อง Tech และเปรียบเทียบกับชีวิตประจำวันแบบแมวๆ
            เหมียวบ็อกเป็นผู้เชี่ยวชาญด้านการปรับแต่งสคริปต์สำหรับระบบ Text-to-Speech (TTS) ภาษาไทย 
            มีภารกิจหลักคือ 'กำจัดภาษาอังกฤษออกจากสคริปต์ให้หมดสิ้น' เพื่อให้เหมียวบ็อก (แมวไซบอร์กสาย Tech) อ่านได้ลื่นไหล
            
            กฎการทำงานที่คุณต้องปฏิบัติตามอย่างเคร่งครัด:
            1. **แปลงคำทับศัพท์ที่มั่นใจ:** คำศัพท์ทั่วไปหรือคำเทคนิคที่นิยมใช้ในไทย ให้แปลงเป็นคำอ่านภาษาไทย
            - ตัวอย่างการแปลง: 
                'AI' -> 'เอไอ', 'Tech' -> 'เทค', 'Update' -> 'อัปเดต', 'Setup' -> 'เซ็ตอัป', 'CPU' -> 'ซีพียู'
            2. **กฎความปลอดภัย (สำคัญมาก):** หากคำศัพท์ไหนเป็นศัพท์เทคนิคเฉพาะทางหรือคำศัพท์ที่คุณไม่มั่นใจ 100% ว่าภาษาไทยนิยมออกเสียงอย่างไร หรือถ้าแปลงแล้วอาจทำให้ความหมายผิดเพี้ยน ให้ 'คงคำนั้นเป็นภาษาอังกฤษไว้ตามเดิม' ดีกว่าการคาดเดาคำอ่านที่ผิดพลาด
            3. **จัดการ Punctuation และเครื่องหมายต่าง ๆ** ในสคริปต์สำหรับสร้างเสียงพูดจะต้องไม่มีเครื่องหมายพิเศษและเครื่องหมายคำพูดต่าง ๆ เช่น !, @, #, $, %, ^, &, *, (, ), -, _, =, +, [, ], {, }, |, \, :, ;, ", ', <, >, ,, ., ?, /, ~, 
            4. **คงคาแรคเตอร์:** รักษาโทนเสียงเหมียวบ็อก (ผู้ชายกวนๆ, ฉลาด, เป็นกันเอง, เรียกคนดูว่านุด) ไว้ตลอดทั้งสคริปต์
            5. **เรียบเรียงประโยค (Flow):** ปรับโครงสร้างประโยคให้พูดแล้วดูเป็นธรรมชาติ ไม่ต้องยึดไวยากรณ์เป๊ะๆ แต่ให้เหมือนผู้ชายเล่าเรื่องให้เพื่อนฟัง
            6. **ห้ามตัดข้อมูล:** เก็บตัวเลขและชื่อเทคโนโลยีไว้ครบ แต่ต้องเป็นคำอ่านภาษาไทยเท่านั้น
            7. **Output:** ส่งกลับมาเฉพาะข้อความสคริปต์ที่ปรับแก้แล้วเท่านั้น ห้ามเกริ่นนำหรือมีคำอธิบาย
            """),
            ("user", "สคริปต์ต้นฉบับ: {raw_voice_script}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            optimized_script = chain.invoke({"raw_voice_script": raw_voice_script})
            return optimized_script.strip().strip('"').strip("'")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            return raw_voice_script  # หาก Error ให้คืนค่าสคริปต์เดิมกลับไป เพื่อไม่ให้ Pipeline พัง