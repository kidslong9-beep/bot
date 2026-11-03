BLACK-STARS PRO — Telegram referral bot

LOCAL RUN
1. Python 3.11+ o'rnating.
2. .env.example nusxasini .env deb nomlang.
3. .env ichiga BotFather tokenini kiriting.
4. Terminal:
   pip install -r requirements.txt
   python bot.py
5. Botga /start, admin akkauntidan /admin yuboring.

ADMIN
- ADMIN_ID .env ichida 8868281662.
- Kanal qo'shishdan oldin botni kanalga administrator qiling.
- Admin paneldan menyu nomini uz/ru/en tillarida o'zgartiring.
- Har bir menyuga Telegram sticker biriktirish mumkin.
- Stars to'lovi qo'lda: Starsni Telegram orqali yuborgach, admin "To'landi"ni bosadi.

RENDER DEPLOY
1. ZIPni oching, ichidagi fayllarni GitHub repository rootiga yuklang.
2. Render > New > Background Worker > GitHub repository.
3. Build Command: pip install -r requirements.txt
4. Start Command: python bot.py
5. Environment Variables:
   BOT_TOKEN = BotFather token
   ADMIN_ID = 8868281662
   INITIAL_CHANNEL = @websayt_yaratamz
   REWARD_REFERRALS = 100
   REWARD_STARS = 300
   DB_PATH = /var/data/blackstars.db
6. Render Background Worker uchun Persistent Disk qo'shing:
   Mount Path: /var/data
   Size: mos keladigan disk hajmi.
   Disk bo'lmasa SQLite ma'lumotlari deploy/restartda yo'qolishi mumkin.

MUHIM
- Har bir majburiy kanalga botni administrator qiling.
- Telegram oddiy reply keyboard tugmalarining fon rangini bot orqali o'zgartirishga ruxsat bermaydi.
  Rang mavzusi emoji bezagi sifatida ishlaydi.
- Bot Stars'ni avtomatik yubormaydi. Admin 300 Stars'ni qo'lda yuboradi va keyin statusni belgilaydi.
- Bu kodni ommaviy ishga tushirishdan oldin test bot/kanalda sinang.
- .env faylini hech qachon GitHub'ga yuklamang.
