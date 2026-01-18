import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات (النسخة العالمية)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ جاري التحميل بتكنولوجيا التخفي...", expanded=True) as status:
                # تنظيف الملفات القديمة
                for f in ["temp_audio.mp3", "video_temp"]:
                    if os.path.exists(f): os.remove(f)
                
                # إعدادات الـ Bypass القصوى
                ydl_opts = {
                    'format': 'best', # سحب أفضل نسخة متاحة (فيديو+صوت) لضمان عدم رفض الطلب
                    'outtmpl': 'video_temp.%(ext)s',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'no_check_certificate': True,
                    # استخدام "عميل التلفزيون" لأنه حالياً الأقل تعرضاً للحظر
                    'extractor_args': {'youtube': {'player_client': ['tv', 'web']}},
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
                }

                status.write("📡 جاري محاولة سحب البيانات من يوتيوب...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                # العثور على الملف المحمل (بأي امتداد mp4 أو webm)
                downloaded_file = None
                for file in os.listdir("."):
                    if file.startswith("video_temp"):
                        downloaded_file = file
                        break
                
                if not downloaded_file or os.path.getsize(downloaded_file) < 1000:
                    raise Exception("يوتيوب حظر السيرفر. جرب تغيير الـ Region في إعدادات Streamlit.")

                status.write("🎵 جاري استخراج الصوت يدوياً...")
                # استخدام FFmpeg لاستخراج الصوت من الفيديو اللي حملناه
                subprocess.run(f'ffmpeg -i "{downloaded_file}" -vn -ab 128k -ar 44100 -y temp_audio.mp3', shell=True)

                status.write("🧠 جاري التحليل بـ Gemini...")
                audio_upload = client.files.upload(path="temp_audio.mp3")
                while audio_upload.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_upload = client.files.get(name=audio_upload.name)

                prompt = "استخرج أفضل 3 لحظات مشوقة واكتب التوقيت [MM:SS - MM:SS]. ابدأ بكلمة CLIP_DATA"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, audio_upload])
                st.write(res.text)

                times = re.findall(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', res.text)
                if times:
                    for i, (start_t, end_t) in enumerate(times, 1):
                        out_name = f"clip_{i}.mp4"
                        # القص من الفيديو المحمل عندنا على السيرفر (أسرع وأضمن)
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "{downloaded_file}" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                status.update(label="✅ تمت العملية بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
