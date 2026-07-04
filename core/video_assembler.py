import os
import whisper
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from moviepy.video.fx import Loop

class VideoAssemblerTool:
    def __init__(self, font_path="fonts/Prompt-SemiBold.ttf"):
        """
        เครื่องมือสำหรับประกอบวิดีโอ (เสียง + ภาพ + ซับไตเติล)
        :param font_path: พาธของไฟล์ฟอนต์ภาษาไทย (ต้องมีไฟล์ฟอนต์ในเครื่อง)
        """
        self.font_path = font_path
        print("🤖 [Tool: VideoAssembler] กำลังโหลด AI Model สำหรับทำซับไตเติล (Whisper)...")
        # โหลดโมเดล Whisper (ใช้ 'base' หรือ 'small' เพื่อความรวดเร็ว)
        self.whisper_model = whisper.load_model("base")

    def generate_subtitles_data(self, audio_path: str) -> list:
        """ใช้ Whisper ถอดเสียงเป็นข้อความพร้อม Timestamp (Start/End)"""
        print(f"🎧 กำลังแกะซับไตเติลจากไฟล์เสียง: {audio_path}")
        result = self.whisper_model.transcribe(audio_path, language="th")
        return result['segments']

    def create_subtitle_clips(self, segments: list, video_size: tuple) -> list:
        """แปลงข้อมูล Timestamp เป็น TextClip ของ MoviePy"""
        clips = []
        video_width, video_height = video_size
        
        for segment in segments:
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()

            # สร้าง Clip ตัวหนังสือ
            try:
                txt_clip = TextClip(
                    text, 
                    font=self.font_path, 
                    fontsize=60, 
                    color='white', 
                    stroke_color='black', 
                    stroke_width=2.5,
                    method='caption',
                    size=(video_width - 100, None) # เว้นขอบซ้ายขวา
                )
                
                # จัดตำแหน่งให้อยู่ตรงกลางค่อนไปด้านล่าง (ตามสไตล์ TikTok)
                txt_clip = (txt_clip
                            .set_position(('center', video_height * 0.65))
                            .set_start(start_time)
                            .set_end(end_time))
                
                clips.append(txt_clip)
            except Exception as e:
                print(f"⚠️ ไม่สามารถสร้าง TextClip ได้: {e}")
                
        return clips

    def assemble(self, audio_path: str, bg_video_path: str, output_path: str = "final_output.mp4"):
        """ประกอบร่างทุกอย่างเข้าด้วยกันและเรนเดอร์เป็น .mp4"""
        print(f"🎬 [Tool: VideoAssembler] เริ่มขั้นตอนการประกอบวิดีโอ...")
        
        if not os.path.exists(bg_video_path):
            print(f"❌ ไม่พบไฟล์วิดีโอพื้นหลัง: {bg_video_path}")
            return

        # 1. โหลดไฟล์เสียงและวิดีโอ
        audio_clip = AudioFileClip(audio_path)
        bg_clip = VideoFileClip(bg_video_path)

        # 2. ปรับความยาววิดีโอพื้นหลังให้เท่ากับเสียงพากย์
        if bg_clip.duration < audio_clip.duration:
            # ถ้ายาวไม่พอ ให้วนลูป
            bg_clip = loop(bg_clip, duration=audio_clip.duration)
        else:
            # ถ้ายาวเกิน ให้ตัดออก
            bg_clip = bg_clip.subclip(0, audio_clip.duration)

        # 3. ยัดเสียงพากย์เข้าไปในวิดีโอ
        bg_clip = bg_clip.set_audio(audio_clip)

        # 4. สร้างซับไตเติล
        subtitle_segments = self.generate_subtitles_data(audio_path)
        sub_clips = self.create_subtitle_clips(subtitle_segments, bg_clip.size)

        # 5. ซ้อนซับไตเติลลงบนวิดีโอ
        final_video = CompositeVideoClip([bg_clip] + sub_clips)

        # 6. เรนเดอร์ไฟล์วิดีโอ
        print(f"🚀 กำลังเรนเดอร์วิดีโอไปยัง: {output_path}")
        final_video.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast", 
            threads=4
        )
        print(f"✅ ประกอบวิดีโอเสร็จสมบูรณ์! ไฟล์อยู่ที่: {output_path}")