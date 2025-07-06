import telebot as tb
from PIL import Image, ImageDraw
from random import randint
import os

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = tb.TeleBot('5127159983:AAEHSG3yGVSbKsoQvZyIVBFy9E2PbCboCE0')

user_state = {}

os.makedirs("images", exist_ok=True)

@bot.message_handler(commands=['start', 'list'])
def handle_commands(message):
    id_ = message.from_user.id
    if message.text == '/start':
        bot.send_message(id_, 'Привет! Я могу обработать твои фото под разными фильтрами.\n'
                              'Отправь мне фото и выбери нужный эффект.\n'
                              'Список эффектов — команда /list')
    elif message.text == '/list':
        bot.send_message(id_, 'Доступные эффекты:\n'
                              '1 — Чёрно-белое\n'
                              '2 — Красный фильтр\n'
                              '3 — Инверсия\n'
                              '4 — Шум')

@bot.message_handler(content_types=['photo'])
def handle_image(message):
    id_ = message.from_user.id
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    img_path = f"images/{id_}.png"
    with open(img_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    user_state[id_] = {"img_path": img_path}

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("1 — Ч/Б", callback_data="effect_1"),
        InlineKeyboardButton("2 — Красный", callback_data="effect_2"),
        InlineKeyboardButton("3 — Инверсия", callback_data="effect_3"),
        InlineKeyboardButton("4 — Шум", callback_data="effect_4")
    ]
    markup.add(*buttons)

    bot.send_message(id_, "Фото получено! Выбери эффект ниже:", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text_input(message):
    id_ = message.from_user.id

    if id_ in user_state and user_state[id_].get("awaiting_noise_input"):
        try:
            factor = int(message.text.strip())
            if not (1 <= factor <= 100):
                raise ValueError

            apply_effect(id_, "effect_4", noise_factor=factor)
            user_state.pop(id_, None)

        except ValueError:
            bot.send_message(id_, "Пожалуйста, введите целое число от 1 до 100.\n"
                                  "Или выбери один из готовых вариантов ниже.")



@bot.callback_query_handler(func=lambda call: call.data.startswith('effect_'))
def handle_effect_callback(call):
    id_ = call.from_user.id
    data = call.data

    if data == "effect_4":
        if id_ in user_state:
            user_state[id_]['awaiting_noise_input'] = True

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Слабый", callback_data="noise_10"),
            InlineKeyboardButton("Средний", callback_data="noise_30"),
            InlineKeyboardButton("Сильный", callback_data="noise_60")
        )
        bot.edit_message_text("Выбери интенсивность шума:\n"
                              "или напиши уровень шума вручную (например, 25)",
                              chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        return

    apply_effect(id_, data)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('noise_'))
def handle_noise_level(call):
    id_ = call.from_user.id
    if id_ not in user_state:
        bot.answer_callback_query(call.id, "Сначала отправь изображение.")
        return

    factor = int(call.data.split("_")[1])
    apply_effect(id_, "effect_4", noise_factor=factor)
    bot.answer_callback_query(call.id)

def apply_effect(id_, effect_code, noise_factor=30):
    img_path = user_state[id_]["img_path"]
    output_path = f"images/{id_}_processed.png"

    image = Image.open(img_path)
    draw = ImageDraw.Draw(image)
    width, height = image.size
    pix = image.load()

    effect = int(effect_code.split("_")[1])

    if effect == 1:
        for i in range(width):
            for j in range(height):
                a, b, c = pix[i, j]
                avg = (a + b + c) // 3
                draw.point((i, j), (avg, avg, avg))

    elif effect == 2:
        depth = 50
        for i in range(width):
            for j in range(height):
                a, b, c = pix[i, j]
                avg = (a + b + c) // 3
                r = min(255, avg + depth * 2)
                g = min(255, avg + depth)
                b = avg
                draw.point((i, j), (r, g, b))

    elif effect == 3:
        for i in range(width):
            for j in range(height):
                a, b, c = pix[i, j]
                draw.point((i, j), (255 - a, 255 - b, 255 - c))

    elif effect == 4:
        for i in range(width):
            for j in range(height):
                rand = randint(-noise_factor, noise_factor)
                a = max(0, min(255, pix[i, j][0] + rand))
                b = max(0, min(255, pix[i, j][1] + rand))
                c = max(0, min(255, pix[i, j][2] + rand))
                draw.point((i, j), (a, b, c))

    image.save(output_path)
    with open(output_path, 'rb') as photo:
        bot.send_photo(id_, photo, caption="Изображение обработано")

    del user_state[id_]

bot.polling(non_stop=True, interval=0)
