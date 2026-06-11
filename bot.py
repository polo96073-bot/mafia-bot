import telebot
import random
import threading
import time

TOKEN = "8878908631:AAHxlALJDFGG_vUVVv-e7McSGAYIgo-SypY"

bot = telebot.TeleBot(TOKEN)

games = {}

ROLES = ["Mafia", "Don", "Komissar", "Doctor",
         "Civil", "Civil", "Civil", "Civil"]


# ================= START =================
@bot.message_handler(commands=['startgame'])
def start_game(message):
    chat_id = message.chat.id

    games[chat_id] = {
        "players": [],
        "alive": [],
        "roles": {},
        "votes": {},
        "phase": "lobby",
        "mafia_target": None,
        "doctor_save": None,
        "komissar_check": None
    }

    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("🎮 Qo‘shilish", callback_data="join"))

    bot.send_message(
        chat_id,
        "🎭 MAFIA BOSHLANDI!\n\n🎮 Qo‘shilish tugmasi\n⏳ 55 soniya",
        reply_markup=kb
    )

    threading.Thread(target=lobby_timer, args=(chat_id,)).start()


# ================= JOIN =================
@bot.callback_query_handler(func=lambda c: c.data == "join")
def join(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    game = games.get(chat_id)
    if not game:
        return

    if user_id not in game["players"]:
        game["players"].append(user_id)

    bot.answer_callback_query(call.id, "Qo‘shildingiz")


# ================= LOBBY =================
def lobby_timer(chat_id):
    time.sleep(55)

    game = games.get(chat_id)
    if not game:
        return

    players = game["players"]

    if len(players) < 4:
        bot.send_message(chat_id, "❌ Kamida 4 o‘yinchi kerak")
        del games[chat_id]
        return

    random.shuffle(players)
    roles = random.sample(ROLES, len(players))
    assigned = dict(zip(players, roles))

    game["roles"] = assigned
    game["alive"] = players.copy()
    game["phase"] = "night"

    bot.send_message(chat_id, "🌙 TUN BOSHLANDI!")

    for uid, role in assigned.items():
        try:
            bot.send_message(uid, f"🎭 ROLINGIZ: {role}")
        except:
            pass

    night_phase(chat_id)


# ================= NIGHT ACTIONS =================
def night_phase(chat_id):
    game = games[chat_id]
    game["votes"] = {}

    alive = game["alive"]

    mafia = [u for u, r in game["roles"].items() if r == "Mafia" and u in alive]
    civ = [u for u in alive if u not in mafia]

    game["mafia_target"] = random.choice(civ) if civ else None
    game["doctor_save"] = random.choice(alive) if alive else None
    game["komissar_check"] = random.choice(alive) if alive else None

    bot.send_message(chat_id, "🌙 Tun davom etmoqda...")

    time.sleep(10)

    resolve_night(chat_id)


# ================= NIGHT RESULT =================
def resolve_night(chat_id):
    game = games[chat_id]

    kill = game["mafia_target"]
    save = game["doctor_save"]

    msg = "🌙 TUN NATIJASI:\n"

    if kill and kill != save:
        if kill in game["alive"]:
            game["alive"].remove(kill)
        msg += f"💀 O‘ldi: {kill}\n"
    else:
        msg += "🛡 Hech kim o‘lmadi\n"

    # Komissar check
    check = game["komissar_check"]
    if check:
        role = game["roles"].get(check)
        msg += f"🕵 Komissar tekshirdi: {check} → {role}\n"

    bot.send_message(chat_id, msg)

    if check_win(chat_id):
        return

    day_phase(chat_id)


# ================= DAY =================
def day_phase(chat_id):
    game = games[chat_id]
    game["phase"] = "day"
    game["votes"] = {}

    bot.send_message(chat_id,
                     "☀️ KUNDUZ!\n\nOvoz berish: user_id yozing\n⏳ 20 soniya")

    time.sleep(20)

    resolve_day(chat_id)


# ================= VOTE =================
@bot.message_handler(func=lambda m: True)
def vote(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    game = games.get(chat_id)
    if not game:
        return

    if game["phase"] != "day":
        return

    try:
        target = int(message.text)
    except:
        return

    if target in game["alive"]:
        game["votes"][user_id] = target
        # ================= DAY RESULT =================
def resolve_day(chat_id):
    game = games[chat_id]

    votes = game["votes"]

    if votes:
        count = {}

        for v in votes.values():
            count[v] = count.get(v, 0) + 1

        lynch = max(count, key=count.get)

        if lynch in game["alive"]:
            game["alive"].remove(lynch)
            bot.send_message(chat_id, f"⚖ OSILDI: {lynch}")
    else:
        bot.send_message(chat_id, "⚖ Hech kim vote qilmadi")

    if check_win(chat_id):
        return

    night_phase(chat_id)


# ================= WIN =================
def check_win(chat_id):
    game = games[chat_id]

    mafia = [u for u, r in game["roles"].items() if r == "Mafia" and u in game["alive"]]
    civ = [u for u in game["alive"] if u not in mafia]

    if not mafia:
        bot.send_message(chat_id, "🏆 CIVILIANS YUTDI!")
        del games[chat_id]
        return True

    if len(mafia) >= len(civ):
        bot.send_message(chat_id, "🏆 MAFIA YUTDI!")
        del games[chat_id]
        return True

    return False


# ================= RUN =================
bot.polling(none_stop=True)