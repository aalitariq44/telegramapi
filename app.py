import os
import logging
from flask import Flask, jsonify, request
from pyrogram import Client
from pyrogram.raw.types import InputPhoneContact
import asyncio
from functools import wraps

# إعداد اللوقينغ لعرض أي خطأ عند التشغيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إنشاء تطبيق Flask
app = Flask(__name__)

# قراءة المتغيرات من البيئة (Fallback لقيمك المحلية)
API_ID = int(os.environ.get("API_ID", 27121127))
API_HASH = os.environ.get("API_HASH", "b550dcd23b25a86124f28ba15a38ad00")
API_KEY = os.environ.get("API_KEY", "your_secret_api_key_here")

# اسم ملف الجلسة (my_account.session) في جذر المشروع
SESSION_NAME = "my_account"

# نقطة صحّة
@app.route("/", methods=["GET"])
def health():
    return "✅ Server is up!", 200

# Decorator للتحقق من مفتاح API
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not key or key != API_KEY:
            return jsonify({"success": False, "message": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated

# تحويل رقم الهاتف إلى التنسيق الدولي للعراق
def to_international(phone: str) -> str:
    if phone.startswith("0"):
        return "+964" + phone[1:]
    if not phone.startswith("+"):
        return "+964" + phone
    return phone

# الدالة غير المتزامنة لإرسال الرسالة
async def send_message(raw_phone: str, text: str):
    phone = to_international(raw_phone)
    async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH) as tg:
        contacts = await tg.import_contacts([
            InputPhoneContact(client_id=0, phone=phone, first_name="Temp", last_name="Contact")
        ])
        if not contacts.users:
            return False, f"❌ لا يوجد مستخدم على رقم {phone} في تيليجرام."
        user = contacts.users[0]
        try:
            await tg.send_message(user.id, text)
            return True, f"✅ تم الإرسال إلى {phone}."
        finally:
            await tg.delete_contacts([user.id])

# Helper لتشغيل الكوروتين من داخل دالة عادية
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# نقطة النهاية لإرسال الرسائل
@app.route("/api/send_message", methods=["POST"])
@require_api_key
def api_send_message():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "No JSON data provided"}), 400

    phone = data.get("phone")
    message = data.get("message")
    if not phone or not message:
        return jsonify({"success": False, "message": "Phone and message are required"}), 400

    ok, msg = run_async(send_message(phone, message))
    return jsonify({"success": ok, "message": msg}), (200 if ok else 500)

# نقطة تشغيل التطبيق
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask on port {port}")
    # لا تستخدم debug=True على Railway
    app.run(host="0.0.0.0", port=port, debug=False)
