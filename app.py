import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

# سحب المفتاح
API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات الذكي")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ جاري فحص الرابط وسحب البيانات...", expanded=True) as status:
                
                # إعدادات "الجوكر" - بتجيب أفضل صوت متاح مهما كانت صيغته
                ydl_opts = {
                    'format': 'bestaudio/best', # السطر المنقذ: هات أفضل المتاح
                    'outtmpl': 'temp_audio.%(ext)s',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'no_check_certificate': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
                }

                status.write("📡 جاري محاولة التحميل...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                # فحص مساحة الملف للتأكد إنه مش فاضي
                if os.path.exists("temp_audio.mp3") and os.path.getsize("temp_audio.mp3") > 0:
                    status.write(f"✅ تم سحب الصوت بنجاح ({round(os.path.getsize('temp_audio.mp3')/1024/1024, 2)} MB)")
                else:
                    raise Exception("الملف الناتج فارغ، يوتيوب رفض إرسال البيانات لهذا التنسيق.")

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
                        # القص باستخدام رابط البث المباشر مع التنسيق التلقائي
                        cookie_cmd = "--cookies cookies.txt" if os.path.exists('cookies.txt') else ""
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "$(yt-dlp {cookie_cmd} -g -f \"best\" {yt_url})" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                
                status.update(label="✅ تمت العملية بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
            st.info("نصيحة: إذا استمر الخطأ، جرب رابط فيديو آخر (قناة مختلفة) للتأكد من أن الحظر ليس شاملاً للسيرفر.")
