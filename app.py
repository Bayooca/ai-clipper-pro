import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

# سحب المفتاح
API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات الذكي (نسخة الهروب من الحظر)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ محاولة الالتفاف على الحماية...", expanded=True) as status:
                
                # إعدادات "الجوكر" لتفادي الملف الفارغ
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'temp_audio.%(ext)s',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'no_check_certificate': True,
                    # السطر السحري: إقناع يوتيوب أننا متصفح "سافاري" على موبايل
                    'extractor_args': {'youtube': {'player_client': ['mweb', 'web_safari']}},
                    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
                }

                status.write("📡 جاري طلب البيانات بصيغة mweb...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                # فحص المساحة - لو لسه صفر هنوقف البرنامج
                if not os.path.exists("temp_audio.mp3") or os.path.getsize("temp_audio.mp3") < 100:
                    st.error("⚠️ يوتيوب مازال يرسل ملفاً فارغاً. جرب رابط فيديو آخر (قناة صغيرة) للتأكد.")
                    st.stop()

                status.write("🧠 جاري التحليل بـ Gemini...")
                audio_upload = client.files.upload(path="temp_audio.mp3")
                while audio_upload.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_upload = client.files.get(name=audio_upload.name)

                prompt = "حلل اللحظات المشوقة واستخرج 3 لحظات. اكتب التوقيت [MM:SS - MM:SS]. ابدأ بكلمة CLIP_DATA"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, audio_upload])
                st.write(res.text)

                times = re.findall(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', res.text)
                if times:
                    for i, (start_t, end_t) in enumerate(times, 1):
                        out_name = f"clip_{i}.mp4"
                        cookie_cmd = "--cookies cookies.txt" if os.path.exists('cookies.txt') else ""
                        # القص المباشر باستخدام رابط البث
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "$(yt-dlp {cookie_cmd} -g -f \"best\" {yt_url})" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                
                status.update(label="✅ تمت العملية!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
