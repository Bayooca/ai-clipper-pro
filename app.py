import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

# سحب المفتاح
API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات الذكي (نسخة الموبايل)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ جاري تخطي الحجب (وضع الأندرويد)...", expanded=True) as status:
                
                # إعدادات تقليد تطبيق يوتيوب الرسمي على الأندرويد
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'temp_audio.%(ext)s',
                    'quiet': True,
                    'no_check_certificate': True,
                    # السطر السحري: إيهام يوتيوب أننا تطبيق موبايل
                    'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
                    'user_agent': 'com.google.android.youtube/19.29.37 (Linux; U; Android 14; en_US; Pixel 8 Pro) gzip',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    status.write("📡 جاري سحب الصوت...")
                    ydl.download([yt_url])
                
                status.write("🧠 جاري التحليل بـ Gemini...")
                audio_upload = client.files.upload(file="temp_audio.mp3")
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
                        # القص باستخدام نفس بصمة الأندرويد
                        ua = 'com.google.android.youtube/19.29.37 (Linux; U; Android 14; en_US; Pixel 8 Pro) gzip'
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "$(yt-dlp --user-agent "{ua}" -g -f "best" {yt_url})" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                status.update(label="✅ تم بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
