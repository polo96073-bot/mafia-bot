import telebot
import random
import threading
import time

TOKEN = "BOT_TOKENINGIZ"
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
        "phase": "lobby",
        "votes": {},
        "kill": None,
        "save": None,
        "check": None
    }

    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("🎮 Qo‘shilish", callback_data="join"))

    bot.send_message(chat_id,
                     "🎭 MAFIA BOSHLANDI!\n⏳ 55 soniya join",
                     reply_markup=kb)

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

    bot.send_message(chat_id, "🌙 O‘yin boshlandi!")

    for uid, role in assigned.items():
        bot.send_message(uid, f"🎭 ROL: {role}")

    night_phase(chat_id)


# ================= NIGHT =================
def night_phase(chat_id):
    game = games[chat_id]
    game["phase"] = "night"
    game["votes"] = {}

    alive = game["alive"]

    mafia = [u for u, r in game["roles"].items() if r == "Mafia" and u in alive]

    civ = [u for u in alive if u not in mafia]

    game["kill"] = random.choice(civ) if civ else None
    game["save"] = random.choice(alive) if alive else None
    game["check"] = random.choice(alive) if alive else None

    bot.send_message(chat_id, "🌙 Tun... hamma uxlaydi")

    time.sleep(10)

    resolve_night(chat_id)


# ================= NIGHT RESULT =================
def resolve_night(chat_id):
    game = games[chat_id]

    kill = game["kill"]
    save = game["save"]
    check = game["check"]

    msg = "🌙 TUN NATIJASI:\n"

    # Mafia kill + Doctor save
    if kill and kill != save:
        if kill in game["alive"]:
            game["alive"].remove(kill)
        msg += f"💀 O‘ldi: {kill}\n"
    else:
        msg += "🛡 Hech kim o‘lmadi\n"

    # Komissar check
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

    kb = telebot.types.InlineKeyboardMarkup()

    for uid in game["alive"]:
        kb.add(telebot.types.InlineKeyboardButton(
            f"🗳 {uid}", callback_data=f"vote_{uid}"
        ))

    bot.send_message(chat_id,
                     "☀️ KUNDUZ!\nVote qiling (20s)",
                     reply_markup=kb)

    time.sleep(20)

    resolve_day(chat_id)


# ================= VOTE =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("vote_"))
def vote(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    game = games.get(chat_id)
    if not game:
        return

    if game["phase"] != "day":
        return
             target = int(call.data.split("_")[1])
    game["votes"][user_id] = target

    bot.answer_callback_query(call.id, "Vote qabul qilindi")


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

    mafia = [u for u, r in game["roles"].items()
             if r == "Mafia" and u in game["alive"]]

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
