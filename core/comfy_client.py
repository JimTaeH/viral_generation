import json
import requests
import time
import os
import shutil

class ComfyClient:
    def __init__(self, server_address="127.0.0.1:8188", comfy_output_dir=None):
        self.server_address = server_address
        # ระบุพาธโฟลเดอร์ output ของ ComfyUI (ปรับเปลี่ยนตามตำแหน่งจริงในเครื่อง)
        self.comfy_output_dir = comfy_output_dir or r"D:\ComfyUI_windows_portable\ComfyUI\output"

    def generate_image(self, action_prompt: str, workflow_path="workflow_api.json", node_id="3") -> str:
        """ส่ง Prompt สั่งงานไปยัง ComfyUI และดึงพาธไฟล์ภาพที่เจนเสร็จกลับมา"""
        print(f"🎨 [ComfyUI] กำลังยิงคำสั่งภาพไปยัง Node #{node_id}...")
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
            
        workflow[node_id]["inputs"]["text"] = action_prompt
        
        payload = {"prompt": workflow}
        try:
            response = requests.post(f"http://{self.server_address}/prompt", json=payload)
            res_json = response.json()
            prompt_id = res_json["prompt_id"]
        except Exception as e:
            raise Exception(f"❌ ไม่สามารถเชื่อมต่อกับ ComfyUI ได้ (เปิดทิ้งไว้หรือยัง?): {e}")

        print("⏳ กำลังประมวลผลภาพบนการ์ดจอ Local ของคุณ...")
        while True:
            history_url = f"http://{self.server_address}/history/{prompt_id}"
            history_res = requests.get(history_url).json()
            
            if prompt_id in history_res:
                outputs = history_res[prompt_id]["outputs"]
                for node_key in outputs:
                    if "images" in outputs[node_key]:
                        filename = outputs[node_key]["images"][0]["filename"]
                        full_path = os.path.join(self.comfy_output_dir, filename)
                        return full_path
            time.sleep(1)

    def generate_video(self, action_prompt: str, workflow_path="workflow_api.json", node_id="3", video_node_id="17") -> str:
        """ส่ง Prompt สั่งงานไปยัง ComfyUI และดึงพาธไฟล์วิดีโอแอนิเมชันที่เจนเสร็จกลับมา"""
        print(f"🎬 [ComfyUI] กำลังยิงคำสั่งประมวลผลวิดีโอ LivePortrait ไปยัง Node #{node_id}...")
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
            
        # 1. ป้อนคำสั่งฉากย่อยราย Loop
        workflow[node_id]["inputs"]["text"] = action_prompt
        
        # 2. บังคับใช้การตั้งค่าที่เราพิสูจน์แล้วว่าผ่านและไม่เกิดกล่องดำทับหน้าน้องแมว
        if "24" in workflow:
            workflow["24"]["inputs"]["detection_threshold"] = 0.1
            workflow["24"]["inputs"]["onnx_device"] = "CUDA"
        if "18" in workflow:
            workflow["18"]["inputs"]["precision"] = "fp32"
        if "20" in workflow:
            workflow["20"]["inputs"]["stitching"] = False

        payload = {"prompt": workflow}
        try:
            response = requests.post(f"http://{self.server_address}/prompt", json=payload)
            res_json = response.json()
            prompt_id = res_json["prompt_id"]
        except Exception as e:
            raise Exception(f"❌ ไม่สามารถเชื่อมต่อกับ ComfyUI ได้: {e}")

        print("⏳ กำลังเรนเดอร์แอนิเมชันขยับปากน้องแมวรายฉากย่อย...")
        while True:
            history_url = f"http://{self.server_address}/history/{prompt_id}"
            history_res = requests.get(history_url).json()
            
            if prompt_id in history_res:
                job_history = history_res[prompt_id]
                status = job_history.get("status", {})

                if status.get("status_str") == "error":
                    # ระบบแกะรอยหาข้อความ Error จริงจากชั้นข้อความภายใน ComfyUI
                    real_error_msg = "พบข้อผิดพลาดที่ไม่ทราบสาเหตุใน Workflow"
                    messages = status.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, list) and len(msg) > 1 and msg[0] == "execution_error":
                            err_details = msg[1]
                            real_error_msg = (
                                f"Node {err_details.get('node_id')} ({err_details.get('node_type')}): "
                                f"{err_details.get('exception_message')}"
                            )
                            break
                    
                    print(f"❌ [ComfyUI Error ตัวจริง] {real_error_msg}")
                    return "FAILED_FACE_NOT_FOUND"
                    
                outputs = job_history["outputs"]
                
                # พยายามดึงชื่อไฟล์จาก Node วิดีโอหลัก (Node 17)
                if video_node_id in outputs:
                    node_out = outputs[video_node_id]
                    filename = None
                    if "gifs" in node_out:
                        filename = node_out["gifs"][0]["filename"]
                    elif "filenames" in node_out:
                        filename = node_out["filenames"][0]
                    
                    if filename:
                        return os.path.join(self.comfy_output_dir, filename)
                
                # ระบบสแกนหาไฟล์วิดีโอสำรอง
                for node_key, node_out in outputs.items():
                    if "gifs" in node_out:
                        return os.path.join(self.comfy_output_dir, node_out["gifs"][0]["filename"])
                    elif "filenames" in node_out:
                        return os.path.join(self.comfy_output_dir, node_out["filenames"][0])
                        
            time.sleep(1)