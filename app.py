import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

# سحب المفتاح من Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات الذكي (النسخة المستقرة)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ جاري فحص الرابط وسحب الصوت...", expanded=True) as status:
                
                # إعدادات "المرونة القصوى" - يسحب أفضل متاح مهما كان نوعه
                ydl_opts = {
                    'format': 'ba/b', # يسحب أفضل صوت (ba) ولو مفيش يسحب أفضل فيديو (b)
                    'outtmpl': 'temp_audio.%(ext)s',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'no_check_certificate': True,
                    'noplaylist': True,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '128',
                    }],
                }

                status.write("📡 جاري تحميل البيانات من يوتيوب...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                # فحص وجود الملف
                if os.path.exists("temp_audio.mp3") and os.path.getsize("temp_audio.mp3") > 0:
                    status.write("✅ تم تجهيز الصوت بنجاح")
                else:
                    raise Exception("فشل تحميل الملف. يرجى تجربة فيديو آخر.")

                status.write("🧠 جاري تحليل اللحظات المشوقة...")
                audio_upload = client.files.upload(path="temp_audio.mp3")
                while audio_upload.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_upload = client.files.get(name=audio_upload.name)

                prompt = "حلل الصوت واستخرج أفضل 3 لحظات. اكتب التوقيت بالصيغة [MM:SS - MM:SS]. ابدأ بكلمة CLIP_DATA"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, audio_upload])
                st.write(res.text)

                times = re.findall(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', res.text)
                if times:
                    status.write(f"✂️ جاري قص {len(times)} مقاطع...")
                    for i, (start_t, end_t) in enumerate(times, 1):
                        out_name = f"clip_{i}.mp4"
                        # القص المباشر باستخدام أفضل جودة فيديو متاحة
                        cookie_cmd = "--cookies cookies.txt" if os.path.exists('cookies.txt') else ""
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "$(yt-dlp {cookie_cmd} -g -f "best" {yt_url})" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل المقطع {i}", f, file_name=out_name)
                
                status.update(label="✅ تمت العملية بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ حدث خطأ: {str(e)}")
