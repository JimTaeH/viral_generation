import os
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, TextClip, VideoFileClip
from PIL import Image, ImageFilter

class VideoAssemblerTool:
    def __init__(self, font_path="fonts/Prompt-SemiBold.ttf"):
        self.font_path = font_path
        print("🤖 [Tool: VideoAssembler] เปิดใช้งานระบบจัดวาง Layout วิดีโอแนวตั้งเคลื่อนไหวสำหรับ TikTok...")

    def create_blurred_background(self, square_img_path: str, output_path: str, target_size=(1080, 1920)):
        """ใช้ PIL ขยายภาพเฟรมแรกทำพื้นหลังเบลอ 1080x1920"""
        with Image.open(square_img_path) as img:
            bg = img.resize((target_size[1], target_size[1]))
            bg = bg.crop(((target_size[1]-target_size[0])//2, 0, (target_size[1]+target_size[0])//2, target_size[1]))
            bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
            bg = bg.point(lambda p: p * 0.7) # ลดความสว่างพื้นหลังลง 30%
            bg.save(output_path)

    def assemble_from_scenes(self, scenes_data: list, output_path="final_output.mp4"):
        """
        รับค่าข้อมูลแต่ละฉากที่เป็นไฟล์วิดีโอแอนิเมชันมามัดรวมพร้อมฝังซับไตเติลรายซีน
        :param scenes_data: list ของ dict เช่น [{"video": "path.mp4", "audio": "path.mp3", "text": "บทพูดตรงนี้"}, ...]
        """
        print(f"🎬 [Tool: VideoAssembler] เริ่มขั้นตอนมัดรวมคลิป LivePortrait วิดีโอและฝังซับไตเติลสไตล์ TikTok...")
        scene_clips = []
        os.makedirs("temp_process", exist_ok=True)

        for idx, scene in enumerate(scenes_data):
            video_path = scene["video"]
            audio_path = scene["audio"]
            sub_text = scene["text"]
            
            # 1. โหลดคลิปวิดีโอเหลี่ยมที่เจนมาจาก ComfyUI และโหลดเสียงพากย์ฉากนั้นๆ
            raw_video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # ปรับความยาวของแอนิเมชันให้พอดีกัปความยาวเสียงพากย์ (ภาพจะค้างเฟรมสุดท้ายให้หากวิดีโอสั้นกว่าเสียง)
            animated_clip = raw_video_clip.with_duration(duration)
            
            # สเกลขนาดหน้าต่างแมวขยับตรงกลางจอให้เป็น 720x720 ตามดีไซน์เดิม
            animated_clip = animated_clip.resized(width=720, height=720)
            
            # 2. ถ่ายรูปเฟรมแรกของวิดีโอส่งไปเข้า PIL ทำพื้นหลังแนวตั้งแบบเบลอ (ทำสถิติดาวน์โหลดเรนเดอร์ไวมาก)
            temp_frame_path = f"temp_process/temp_frame_{idx}.png"
            raw_video_clip.save_frame(temp_frame_path, t=0)
            
            bg_frame_path = f"temp_process/bg_{idx}.png"
            self.create_blurred_background(temp_frame_path, bg_frame_path)
            
            # 3. สร้างคลิปพื้นหลังนิ่งยาวตามความยาวเสียงพากย์ฉากย่อย
            bg_clip = ImageClip(bg_frame_path).with_duration(duration)
            
            # 4. จัดตำแหน่งจัดวางวิดีโอหน้าเคลื่อนไหวตรงกลางเยื้องบน (x=180, y=500 ของจอ 1080x1920)
            animated_clip = animated_clip.with_position((180, 500))
            
            # 5. สร้างกล่องข้อความซับไตเติลสีเหลืองขอบดำด้านล่าง
            txt_clip = TextClip(
                text=sub_text, 
                font=self.font_path, 
                font_size=55, 
                color='yellow', 
                stroke_color='black', 
                stroke_width=3.0, 
                method='caption', 
                size=(1080 - 160, None)
            ).with_duration(duration).with_position(('center', 1400))
            
            # 6. ซ้อนเลเยอร์: พื้นหลังเบลอ + วิดีโอแมวขยับตรงกลาง + ข้อความซับ + ใส่เสียงพากย์ประจำฉาก
            composite_scene = CompositeVideoClip([bg_clip, animated_clip, txt_clip]).with_audio(audio_clip)
            scene_clips.append(composite_scene)

        # 7. นำทุกเซ็ตวิดีโอฉากย่อยมาร้อยต่อชนกันเป็นเนื้อเดียว
        print(f"🚀 กำลังเรนเดอร์วิดีโอแอนิเมชันแนวตั้งตัวเต็มรวดเดียวจบ...")
        final_video = concatenate_videoclips(scene_clips, method="compose")
        final_video.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast",
            threads=4
        )
        
        # ปิดทรัพยากรเคลียร์แรมระบบ
        for c in scene_clips:
            c.close()
        final_video.close()
        print(f"✅ บอทสร้างวิดีโอแนวตั้งแบบเคลื่อนไหวสำเร็จ! ผลลัพธ์อยู่ที่: {output_path}")