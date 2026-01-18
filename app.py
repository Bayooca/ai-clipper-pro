import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

# سحب المفتاح
API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات الذكي (النسخة المضادة للحظر)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ جاري محاولة اختراق الحماية...", expanded=True) as status:
                
                # إعدادات "الضربة القاضية" لتخطي الـ Empty File والـ 403
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'temp_audio.%(ext)s',
                    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
                    'nocheckcertificate': True,
                    'ignoreerrors': False,
                    'logtostderr': True,
                    'quiet': False,
                    'no_warnings': False,
                    'source_address': '0.0.0.0', # إجبار السيرفر على استخدام IPv4 (أهم سطر)
                    'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
                }

                status.write("📡 جاري محاولة سحب البيانات...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                # فحص هل الملف فعلاً فيه بيانات؟
                if not os.path.exists("temp_audio.mp3") or os.path.getsize("temp_audio.mp3") < 1000:
                    st.error("⚠️ يوتيوب أرسل ملفاً فارغاً. جرب تحديث صفحة يوتيوب ونسخ الرابط مجدداً أو استبدال ملف cookies.txt")
                    st.stop()

                status.write("🧠 جاري التحليل بـ Gemini...")
                audio_upload = client.files.upload(path="temp_audio.mp3")
                while audio_upload.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_upload = client.files.get(name=audio_upload.name)

                prompt = "حلل الصوت واستخرج أفضل 3 لحظات. اكتب التوقيت بالصيغة [MM:SS - MM:SS]. ابدأ بكلمة CLIP_DATA"
                res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, audio_upload])
                st.write(res.text)

                times = re.findall(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', res.text)
                if times:
                    for i, (start_t, end_t) in enumerate(times, 1):
                        out_name = f"clip_{i}.mp4"
                        cookie_cmd = "--cookies cookies.txt" if os.path.exists('cookies.txt') else ""
                        # القص باستخدام بروتوكول IPv4 أيضاً
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "$(yt-dlp {cookie_cmd} --force-ipv4 -g -f \"best\" {yt_url})" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                
                status.update(label="✅ تم بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
