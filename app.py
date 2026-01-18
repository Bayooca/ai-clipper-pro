import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات (نسخة تخطي التنسيق)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ جاري البحث عن تنسيق متاح...", expanded=True) as status:
                if os.path.exists("temp_audio.mp3"): os.remove("temp_audio.mp3")
                
                # إعدادات بتجيب أي حاجة شغالة (Video + Audio) وتحولها
                ydl_opts = {
                    'format': 'best', # سحب أفضل نسخة مدمجة (أضمن طريقة)
                    'outtmpl': 'temp_video.%(ext)s',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'no_check_certificate': True,
                    'quiet': False,
                    # استخدام متصفح ويب عادي (Chrome) بدل iOS
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                }

                status.write("📡 جاري محاولة سحب البيانات...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                # تحويل الفيديو المسحوب لصوت MP3 يدوياً عشان نضمن الجودة لـ Gemini
                status.write("🎵 جاري استخراج الصوت...")
                video_file = [f for f in os.listdir('.') if f.startswith('temp_video')][0]
                subprocess.run(f'ffmpeg -i "{video_file}" -q:a 0 -map a temp_audio.mp3 -y', shell=True)

                if os.path.exists("temp_audio.mp3"):
                    status.write("✅ تم تجهيز الصوت للتحليل")
                else:
                    raise Exception("فشل استخراج الصوت. يوتيوب حظر هذا التنسيق أيضاً.")

                status.write("🧠 جاري التحليل بـ Gemini...")
                audio_upload = client.files.upload(path="temp_audio.mp3")
                while audio_upload.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_upload = client.files.get(name=audio_upload.name)

                prompt = "استخرج أفضل 3 لحظات واكتب التوقيت [MM:SS - MM:SS]. ابدأ بكلمة CLIP_DATA"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, audio_upload])
                st.write(res.text)

                times = re.findall(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', res.text)
                if times:
                    for i, (start_t, end_t) in enumerate(times, 1):
                        out_name = f"clip_{i}.mp4"
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "{video_file}" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                status.update(label="✅ تم بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
