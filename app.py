from flask import Flask, jsonify, request
from pyrogram import Client
from pyrogram.raw.types import InputPhoneContact
import asyncio
from functools import wraps

app = Flask(__name__)

api_id = 27121127
api_hash = "b550dcd23b25a86124f28ba15a38ad00"
API_KEY = "your_secret_api_key_here"  # تغيير هذا المفتاح إلى مفتاح سري خاص بك

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if (api_key and api_key == API_KEY):
            return f(*args, **kwargs)
        return jsonify({'success': False, 'message': 'Invalid API key'}), 401
    return decorated_function

def to_international(phone: str) -> str:
    if phone.startswith("0"):
        return "+964" + phone[1:]
    if not phone.startswith("+"):
        return "+964" + phone
    return phone

async def send_message_to_phone(raw_phone, message_text):
    phone = to_international(raw_phone)
    async with Client("my_account", api_id=api_id, api_hash=api_hash) as app:
        contacts = await app.import_contacts([
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
            await app.send_message(user.id, message_text)
            return True, f"✅ تم إرسال الرسالة إلى {phone}."
        finally:
            await app.delete_contacts([user.id])

async def init_session():
    try:
        async with Client("my_account", api_id=api_id, api_hash=api_hash) as app:
            await app.get_me()
            return True
    except:
        return False

def run_async(func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(func)
    loop.close()
    return result

@app.route('/api/send_message', methods=['POST'])
@require_api_key
def api_send_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No JSON data provided'}), 400
        
        phone = data.get('phone')
        message = data.get('message')
        
        if not phone or not message:
            return jsonify({'success': False, 'message': 'Phone and message are required'}), 400
        
        ok, result_msg = run_async(send_message_to_phone(phone, message))
        return jsonify({'success': ok, 'message': result_msg})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    # Check if session exists
    if not run_async(init_session()):
        print("Please run 'python -m pyrogram' first to create a session.")
        print("You will need to enter your phone number and the verification code.")
        exit(1)
    
    app.run(debug=True)