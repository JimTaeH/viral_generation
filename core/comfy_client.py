import json
import requests
import time
import os
import shutil

class ComfyClient:
    def __init__(self, server_address="127.0.0.1:8188", comfy_output_dir=None):
        self.server_address = server_address
        # ระบุพาธโฟลเดอร์ output ของ ComfyUI ของคุณ (ปรับเปลี่ยนตามตำแหน่งจริงในเครื่อง)
        self.comfy_output_dir = comfy_output_dir or r"D:\ComfyUI_windows_portable\ComfyUI\output"

    def generate_image(self, action_prompt: str, workflow_path="workflow_api.json", node_id="3") -> str:
        """ส่ง Prompt สั่งงานไปยัง ComfyUI และดึงพาธไฟล์ภาพที่เจนเสร็จกลับมา"""
        print(f"🎨 [ComfyUI] กำลังยิงคำสั่งภาพไปยัง Node #{node_id}...")
        
        # 1. โหลดโครงสร้างไฟล์ API JSON
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
            
        # 2. ใส่ Text Prompt เข้าไปที่ Node ID 3 ตามที่เซตไว้
        workflow[node_id]["inputs"]["text"] = action_prompt
        
        # 3. ยิงเข้า Queue สั่งเรนเดอร์
        payload = {"prompt": workflow}
        try:
            response = requests.post(f"http://{self.server_address}/prompt", json=payload)
            res_json = response.json()
            prompt_id = res_json["prompt_id"]
        except Exception as e:
            raise Exception(f"❌ ไม่สามารถเชื่อมต่อกับ ComfyUI ได้ (เปิดทิ้งไว้หรือยัง?): {e}")

        # 4. วนลูปเช็กประวัติ (Polling) รอจนกว่าภาพจะคำนวณเสร็จ
        print("⏳ กำลังประมวลผลภาพบนการ์ดจอ Local ของคุณ...")
        while True:
            history_url = f"http://{self.server_address}/history/{prompt_id}"
            history_res = requests.get(history_url).json()
            
            if prompt_id in history_res:
                # เจนเสร็จแล้ว! ดึงชื่อไฟล์ภาพออกมา
                outputs = history_res[prompt_id]["outputs"]
                for node_key in outputs:
                    if "images" in outputs[node_key]:
                        filename = outputs[node_key]["images"][0]["filename"]
                        full_path = os.path.join(self.comfy_output_dir, filename)
                        return full_path
            time.sleep(1) # นอนรอ 1 วินาทีก่อนเช็กซ้ำ