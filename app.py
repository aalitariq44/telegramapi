import os
from flask import Flask, jsonify, request
from pyrogram import Client
from pyrogram.raw.types import InputPhoneContact
import asyncio
from functools import wraps

# إنشاء تطبيق Flask
app = Flask(__name__)

# تحميل المتغيرات من البيئة أو القيم الافتراضية
api_id = int(os.environ.get("API_ID", 27121127))
api_hash = os.environ.get("API_HASH", "b550dcd23b25a86124f28ba15a38ad00")
API_KEY = os.environ.get("API_KEY", "your_secret_api_key_here")

# اسم الجلسة (سيقرأ/ينشئ ملف my_account.session في جذر المشروع)
SESSION_NAME = "my_account"

# نقطة صحّة للتأكد من أن السيرفر يعمل
@app.route('/')
def home():
    return "✅ Server is up!", 200

# تزيين لتحقق مفتاح API
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({'success': False, 'message': 'Invalid API key'}), 401
    return decorated_function

# تحويل رقم الهاتف إلى الشكل الدولي (+964 للعراق)
def to_international(phone: str) -> str:
    if phone.startswith("0"):
        return "+964" + phone[1:]
    if not phone.startswith("+"):
        return "+964" + phone
    return phone

# وظيفة إرسال الرسالة بشكل غير متزامن
async def send_message_to_phone(raw_phone, message_text):
    phone = to_international(raw_phone)
    async with Client(SESSION_NAME, api_id=api_id, api_hash=api_hash) as client:
        # استيراد جهة اتصال مؤقتة
        contacts = await client.import_contacts([
            InputPhoneContact(
                client_id=0,
                phone=phone,
                first_name="Temp",
                last_name="Contact"
            )
        ])
        if not contacts.users:
            return False, f"❌ لا يوجد مستخدم على رقم {phone} في تيليجرام."
        user = contacts.users[0]
        try:
            await client.send_message(user.id, message_text)
            return True, f"✅ تم إرسال الرسالة إلى {phone}."
        finally:
            await client.delete_contacts([user.id])

# مساعد لتشغيل الدوال async من دوال sync
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(coro)
    loop.close()
    return result

# نقطة API لإرسال الرسائل
@app.route('/api/send_message', methods=['POST'])
@require_api_key
def api_send_message():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'No JSON data provided'}), 400

    phone = data.get('phone')
    message = data.get('message')
    if not phone or not message:
        return jsonify({'success': False, 'message': 'Phone and message are required'}), 400

    ok, result_msg = run_async(send_message_to_phone(phone, message))
    return jsonify({'success': ok, 'message': result_msg})

# نقطة تشغيل التطبيق
if __name__ == '__main__':
    # استخدم المنفذ المعرّف في البيئة أو 5000
    port = int(os.environ.get("PORT", 5000))
    # استمع على كل الواجهات الخارجية
    app.run(host="0.0.0.0", port=port, debug=True)
