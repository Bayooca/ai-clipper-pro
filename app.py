import streamlit as st
import os, yt_dlp, subprocess, re, time
from google import genai

st.set_page_config(page_title="AI Video Clipper Pro", layout="wide")

API_KEY = st.secrets.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

st.title("🎬 مصنع الفيديوهات الذكي (النسخة النهائية)")

yt_url = st.text_input("🔗 ضع رابط يوتيوب هنا:")

if yt_url:
    if st.button("🚀 ابدأ العمل"):
        try:
            with st.status("🛠️ جاري محاولة اختراق الحجب...", expanded=True) as status:
                # حذف أي ملفات قديمة
                if os.path.exists("temp_audio.mp3"): os.remove("temp_audio.mp3")
                
                # إعدادات الهروب الكبير
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'temp_audio.%(ext)s',
                    'no_check_certificate': True,
                    'quiet': False,
                    # استخدام عميل iOS لأنه الأقل حظراً حالياً
                    'extractor_args': {'youtube': {'player_client': ['ios'], 'po_token': ['web+OAb9S...']}},
                    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
                }

                status.write("📡 جاري سحب البيانات بصيغة iOS...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                
                if not os.path.exists("temp_audio.mp3") or os.path.getsize("temp_audio.mp3") < 1000:
                    raise Exception("يوتيوب مازال يحظر السيرفر. جرب تغيير 'المنطقة' في إعدادات Streamlit.")

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
                        cmd = f'ffmpeg -ss {start_t} -to {end_t} -i "$(yt-dlp -g -f \"best\" {yt_url})" -c copy {out_name} -y'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(out_name):
                            with open(out_name, "rb") as f:
                                st.download_button(f"📥 تحميل مقطع {i}", f, file_name=out_name)
                status.update(label="✅ تم بنجاح!", state="complete")
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")
