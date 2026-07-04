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
    - ข้อความ Pop-up บนจอ (เช่น 'ขึ้น Text ตัวใหญ่คำว่า \"AI แสนล้าน!\"')""")
    
    character_action: str = Field(description="""ท่าทางการกระทำของ 'เหมียวบ็อก': 
    ระบุอนิเมชันหรือท่าทางคร่าวๆ ของตัวละครในฉากนี้ เช่น 'กอดอกทำหน้าขิง', 'ชี้อุ้งเท้าไปที่หน้าจอ', 'ตา LED กะพริบสีแดงด้วยความตกใจ', หรือ 'เอียงคอสงสัย'""")
    
    voice_script: str = Field(description="""บทพูดของเหมียวบ็อก: 
    - สไตล์: ฉลาด กวนนิดๆ เป็นกันเอง เรียกคนดูว่า 'นุด' 
    - เนื้อหา: ต้องดึงสถิติ ตัวเลข ข้อมูลเชิงลึก หรือชื่อเฉพาะจากข่าวต้นฉบับมาใส่ให้ครบถ้วน ห้ามตัดทอนสาระสำคัญออกเด็ดขาด เปลี่ยนแค่วิธีการเล่าให้ฟังสนุกขึ้น
    - กฎ: ห้ามใส่วงเล็บหรือเครื่องหมายพิเศษในส่วนนี้""")

class VideoScript(BaseModel):
    video_title: str = Field(description="ชื่อคลิปหรือหัวข้อหลัก")
    scenes: List[VideoScene] = Field(description="รายการฉากทั้งหมดในคลิป (ความยาวรวมประมาณ 45-60 วินาที)")

# ==========================================
# 2. สร้าง Tool Class สำหรับเรียกใช้งาน
# ==========================================
class ScriptGeneratorTool:
    def __init__(self, provider="typhoon", model_name="typhoon-v2.5-30b-a3b-instruct"):
        self.llm = LLMFactory.create_llm(provider=provider, model_name=model_name, temperature=0.7)
        self.parser = JsonOutputParser(pydantic_object=VideoScript)

    def generate_plan(self, news_text: str) -> dict:
        """ประมวลผลข่าวและสร้างโครงสร้างสคริปต์แบบ Full Production"""
        print(f"🤖 [Tool: ScriptGenerator] 'เหมียวบ็อก' กำลังวิเคราะห์ข้อมูลและวางแผนคลิป...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือ 'เหมียวบ็อก' แมวไซบอร์กสุดล้ำ ครีเอเตอร์สายเทคโนโลยีบน TikTok 
            คาแรคเตอร์: ฉลาดรอบรู้ กวนนิดๆ ขี้เล่น และชอบเรียกคนดูว่า 'นุด' (มนุษย์)
            
            ภารกิจของคุณ: นำข่าวเทคโนโลยีที่ได้รับ มาสร้างเป็นสคริปต์วิดีโอแนวตั้ง (9:16)
            
            ข้อกำหนดสำคัญ:
            1. ข้อมูลต้องแน่น: ห้ามสรุปจนเนื้อหาหาย เก็บตัวเลข สถิติ และชื่อเทคโนโลยีสำคัญไว้ให้ครบ
            2. ภาพต้องชัด: อธิบายบทภาพให้ละเอียดจนคนตัดต่อเห็นภาพตรงกัน
            3. แอคชันต้องมี: กำหนดท่าทางของ 'เหมียวบ็อก' ให้สอดคล้องกับอารมณ์ของบทพูดในฉากนั้นๆ
            
            {format_instructions}"""),
            ("user", "ข้อมูลข่าวสำหรับทำสคริปต์: {news_text}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "news_text": news_text,
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
        Tool: ปรับแต่งสคริปต์บทพูด แปลงคำอังกฤษเป็นไทยทับศัพท์ และจัดช่องไฟ
        """
        print(f"⚙️ [Tool: VoiceOptimizer] กำลังแปลงคำศัพท์และจัดจังหวะการพูด...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """คุณคือผู้เชี่ยวชาญด้านการปรับแต่งสคริปต์สำหรับระบบ Text-to-Speech (TTS) ภาษาไทย
            
            หน้าที่ของคุณคือ ปรับแก้สคริปต์บทพูดที่ได้รับมาตามกฎต่อไปนี้อย่างเคร่งครัด:
            1. แปลงคำศัพท์ภาษาอังกฤษทั้งหมด ให้เป็นคำอ่านภาษาไทยแบบทับศัพท์ที่ถูกต้อง (เช่น 'AI' เปลี่ยนเป็น 'เอ-ไอ', 'Smart Home' เปลี่ยนเป็น 'สมาร์ทโฮม', 'Apple' เปลี่ยนเป็น 'แอปเปิล')
            2. จัดวรรคตอนให้ถูกต้อง เติมเว้นวรรค ( ) หรือเครื่องหมายจุลภาค (,) ในจุดที่ควรหยุดหายใจ เพื่อให้บอทอ่านแล้วมีจังหวะเป็นธรรมชาติ ไม่พูดติดกันเป็นพืด
            3. ห้ามตัดเนื้อหาเดิมทิ้ง และรักษาอารมณ์ของประโยคสไตล์ 'เจ้าเหมียวไซบอร์ก' ไว้ตามเดิม
            4. ส่งกลับมาเฉพาะข้อความสคริปต์ที่ปรับแก้แล้วเท่านั้น ห้ามมีคำอธิบายหรือข้อความเกริ่นนำใดๆ
            """),
            ("user", "สคริปต์ต้นฉบับ: {raw_voice_script}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            optimized_script = chain.invoke({"raw_voice_script": raw_voice_script})
            # ทำความสะอาดเผื่อ AI หลุดมี Quote ติดมา
            return optimized_script.strip().strip('"').strip("'")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดใน VoiceOptimizerTool: {e}")
            return raw_voice_script  # หาก Error ให้คืนค่าสคริปต์เดิมกลับไป เพื่อไม่ให้ Pipeline พัง