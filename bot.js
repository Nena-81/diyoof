const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: false, args: ['--no-sandbox'] }
});

client.on('qr', (qr) => { 
    qrcode.generate(qr, { small: true }); 
});

client.on('ready', () => { 
    console.log('🚀 البوت متصل ومستعد لاستقبال الرسائل!'); 
});

client.on('message', async (msg) => {
    // تجاهل رسائل المجموعات (اختياري)
    if (msg.isGroupMsg) return;

    try {
        // نرسل الطلب للسيرفر مع تعديل الرابط ليتطابق مع app.py
        const response = await axios.post('http://127.0.0.1:8000/whatsapp-webhook', 
            `text=${encodeURIComponent(msg.body)}&phone=${encodeURIComponent(msg.from)}&sender=client`,
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        );
        
        // استلام الرد من البايثون (مطابق لاسم المتغير في app.py وهو bot_reply)
        const replyText = response.data.bot_reply;
        
        console.log('✅ تم استلام الرد من الذكاء الاصطناعي:', replyText);
        
        if (replyText) {
            await msg.reply(replyText);
        }
    } catch (e) {
        console.log('❌ خطأ في الاتصال بالسيرفر:', e.message);
    }
});

client.initialize();