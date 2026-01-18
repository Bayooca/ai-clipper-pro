import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات (النسخة المضادة لـ Bot Detection)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ محاولة تخطي فحص الروبوت...", expanded=True) as status:
                if os.path.exists("temp_audio.mp3"): os.remove("temp_audio.mp3")
                
                # إعدادات الهروب من فحص "Sign in to confirm"
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'temp_audio.%(ext)s',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'no_check_certificate': True,
                    # السطر السحري: إيهام يوتيوب أننا متصفح سفاري على آيفون (أقل حماية)
                    'extractor_args': {'youtube': {'player_client': ['web_safari'], 'po_token': ['web+OAb9S...']}},
                    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
                }

                status.write("📡 جاري محاولة سحب الصوت بصيغة Safari...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                if os.path.exists("temp_audio.mp3") and os.path.getsize("temp_audio.mp3") > 1000:
                    status.write("✅ نجحنا في سحب الصوت!")
                else:
                    raise Exception("يوتيوب مازال يطلب تسجيل الدخول. الكوكيز غير صالحة.")

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
                        cookie_cmd = "--cookies cookies.txt" if os.path.exists('cookies.txt') else ""
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "$(yt-dlp {cookie_cmd} -g -f \"best\" {yt_url})" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                status.update(label="✅ تم بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
