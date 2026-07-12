import os
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, TextClip
from PIL import Image, ImageFilter

class VideoAssemblerTool:
    def __init__(self, font_path="fonts/Prompt-SemiBold.ttf"):
        self.font_path = font_path
        print("🤖 [Tool: VideoAssembler] เปิดใช้งานระบบตัดต่อแบบไร้ Whisper (รันสด ประหยัดพลังงาน)...")

    def create_tiktok_frame(self, square_img_path: str, output_path: str, target_size=(1080, 1920)):
        """ใช้ PIL ขยายภาพทำพื้นหลังเบลอ และแปะภาพจริงไว้ตรงกลาง"""
        with Image.open(square_img_path) as img:
            # 1. ทำพื้นหลังแนวตั้ง 1080x1920 แบบเบลอ
            bg = img.resize((target_size[1], target_size[1]))
            bg = bg.crop(((target_size[1]-target_size[0])//2, 0, (target_size[1]+target_size[0])//2, target_size[1]))
            bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
            bg = bg.point(lambda p: p * 0.7) # ลดความสว่างพื้นหลังลง 30%
            
            # 2. เอาภาพจริงมาจัดขนาดให้อยู่ตรงกลางจอ
            fg_size = 720
            fg = img.resize((fg_size, fg_size))
            
            offset = ((target_size[0] - fg_size) // 2, (target_size[1] - fg_size) // 2 - 100)
            bg.paste(fg, offset)
            bg.save(output_path)

    def assemble_from_scenes(self, scenes_data: list, output_path="final_output.mp4"):
        """
        รับค่าข้อมูลแต่ละฉากมาประกอบร่างพร้อมฝังซับไตเติลรายซีนโดยตรง
        :param scenes_data: list ของ dict เช่น [{"image": "path.jpg", "audio": "path.mp3", "text": "บทพูดตรงนี้"}, ...]
        """
        print(f"🎬 [Tool: VideoAssembler] เริ่มขั้นตอนมัดรวมคลิปและฝังซับไตเติลสไตล์ TikTok...")
        scene_clips = []
        os.makedirs("temp_process", exist_ok=True)

        for idx, scene in enumerate(scenes_data):
            img_path = scene["image"]
            audio_path = scene["audio"]
            sub_text = scene["text"] # ดึงบทพูดต้นฉบับมาใช้โดยตรง ไม่ต้องพึ่ง AI แกะเสียง
            
            # 1. จัด Layout ภาพแนวตั้งสำหรับ TikTok
            tiktok_frame_path = f"temp_process/frame_{idx}.png"
            self.create_tiktok_frame(img_path, tiktok_frame_path)
            
            # 2. โหลดไฟล์เสียงพากย์เพื่อหาความยาวของฉากนั้นๆ
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # 3. สร้างคลิปภาพนิ่งตามความยาวเสียง
            video_clip = ImageClip(tiktok_frame_path).with_duration(duration)
            
            # 4. สร้างกล่องซับไตเติลฝังเข้าไปในฉากนี้โดยตรง (ให้แสดงยาวตั้งแต่ต้นจนจบฉากย่อยนี้)
            txt_clip = TextClip(
                text=sub_text, 
                font=self.font_path, 
                font_size=55, 
                color='yellow', # ตัวหนังสือสีเหลืองยอดฮิตของ TikTok
                stroke_color='black', 
                stroke_width=3.0, 
                method='caption', 
                size=(1080 - 160, None)
            ).with_duration(duration).with_position(('center', 1400)) # จัดวางตำแหน่งใต้ภาพตรงกลางพอดี
            
            # 5. มัดรวม ภาพ + ซับไตเติล + เสียงพากย์ เข้าด้วยกันเป็น "ฉากย่อยที่สมบูรณ์"
            composite_scene = CompositeVideoClip([video_clip, txt_clip]).with_audio(audio_clip)
            scene_clips.append(composite_scene)

        # 6. นำทุกฉากย่อยที่ฝังซับเรียบร้อยแล้วมาต่อชนกันรวดเดียวจบ
        print(f"🚀 กำลังเรนเดอร์วิดีโอตัวเต็มรวดเดียวจบ...")
        final_video = concatenate_videoclips(scene_clips, method="compose")
        final_video.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast",
            threads=4
        )
        print(f"✅ บอทสร้างวิดีโอ TikTok เสร็จสิ้น! ผลลัพธ์อยู่ที่: {output_path}")