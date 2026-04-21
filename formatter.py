import shutil
import sys
import os
import argparse
import requests
import chardet
import tempfile
from io import StringIO

def detect_encoding(filename): #### ОПРЕДЕЛЕНИЕ КОДИРОВКИ
    #Определяет кодировку файла
    with open(filename, 'rb') as f:
        raw = f.read(1000000)
        result = chardet.detect(raw)
        return result['encoding'] or 'utf-8'

def read_data(filename): #### ЧТЕНИЕ ФАЙЛА
    data = []
    encoding = detect_encoding(filename)
    print(f"Определена кодировка: {encoding}")
    
    with open(filename, 'r', encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 4:
                fixed_date = fix_date(parts[3])
                data.append({
                    'name': parts[0],
                    'age': parts[1],
                    'address': parts[2],
                    'date': fixed_date
                })
    return data


def shorten_name(name, level): #### СОКРАЩЕНИЕ ИМЕНИ
    parts = name.split()
    if level == 0 or len(parts) < 2:
        return name
    elif level == 1:  # Иванов И. И.
        if len(parts) == 3:
            return f"{parts[0]} {parts[1][0]}. {parts[2][0]}."
        elif len(parts) == 2:
            return f"{parts[0]} {parts[1][0]}."
    elif level == 2:  # Иван. И. И. (фамилия тоже сокращена)
        if len(parts) >= 2:
            short_last = parts[0][:4] + '.' if len(parts[0]) > 4 else parts[0]
            if len(parts) == 3:
                return f"{short_last} {parts[1][0]}. {parts[2][0]}."
            elif len(parts) == 2:
                return f"{short_last} {parts[1][0]}."
    elif level >= 3:  # И.И.И.
        initials = '.'.join(p[0] for p in parts) + '.'
        return initials
    return name

def fix_date(date_str): #### ОТОБРАЖЕНИЕ ДАТЫ И ВРЕМЕНИ
    parts = date_str.split()
    date_part = parts[0]
    time_part = parts[1] if len(parts) > 1 else ""
    
    # Разбираем дату YYYY-MM-DD
    date_components = date_part.split('-')
    if len(date_components) != 3:
        return date_str  # неверный формат — возвращаем как есть
    
    year, month, day = date_components
    
    if int(month) > 12:
        # Меняем местами день и месяц
        month, day = day, month
    
    # Собираем исправленную дату
    fixed_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Возвращаем с временем, если оно было
    if time_part:
        return f"{fixed_date} {time_part}"
    return fixed_date

def shorten_date(date_str, level):
    #Сокращение даты и времени
    parts = date_str.split()
    date_part = parts[0]
    time_part = parts[1] if len(parts) > 1 else ''
    
    if level == 0:
        return date_str  # полная дата + время
    elif level == 1:
        return date_part  # только дата
    elif level >= 2:
        # короткая дата: 22-03-15
        return '-'.join(date_part.split('-')[i] for i in [-2, -1]) if '-' in date_part else date_part
    return date_str

def shorten_address(address, level, max_len=50): #### СОКРАЩЕНИЕ АДРЕСА
    #сокращение
    if level == 0:
        return address
    elif level == 1:
        return address[:max_len-3] + '...' if len(address) > max_len else address
    elif level >= 2:
        # сокращаем с начала и конца
        if len(address) > max_len - 6:
            return address[:max_len//2] + '...' + address[-max_len//2:]
        return address
    return address

def print_table(data):
    #Выводит таблицу с динамическим сокращением и общим заголовком
    if not data:
        return
    
    max_width = shutil.get_terminal_size().columns
    headers = ['ФИО', 'Возраст', 'Адрес', 'Дата рождения']
    table_title = "Таблица пользователей"
    
    # Копируем данные, чтобы не портить оригинал
    working_data = [row.copy() for row in data]
    
    # Пробуем разные уровни сокращения
    for level in range(5):  # от 0 (минимум) до 4 (максимум)
        # Применяем сокращение согласно уровню
        for row in working_data:
            row['name'] = shorten_name(row['name'], level)
            row['date'] = shorten_date(row['date'], level)
            row['address'] = shorten_address(row['address'], level, max_len=30 - level*5)
        
        # Вычисляем ширину
        col_widths = [len(h) for h in headers]
        for row in working_data:
            col_widths[0] = max(col_widths[0], len(row['name']))
            col_widths[1] = max(col_widths[1], len(row['age']))
            col_widths[2] = max(col_widths[2], len(row['address']))
            col_widths[3] = max(col_widths[3], len(row['date']))
        
        total_width = sum(col_widths) + 3 * 3 + 2  # рамки и разделители
        
        if total_width <= max_width or level == 4:  # влезает или уже максимум
            # Выводим общий заголовок таблицы
            title_width = total_width - 2  # ширина без внешних рамок
            if len(table_title) > title_width:
                # Если заголовок не влезает - обрезаем
                table_title_display = table_title[:title_width-3] + '...'
            else:
                table_title_display = table_title.center(title_width)
            
            print('+' + '-' * (total_width - 2) + '+')
            print(f"|{table_title_display}|")
            print('+' + '-' * (total_width - 2) + '+')
            
            # Выводим шапку таблицы с заголовками столбцов
            separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
            print(separator)
            header_row = '| ' + ' | '.join(headers[i].ljust(col_widths[i]) for i in range(4)) + ' |'
            print(header_row)
            print(separator)
            
            # Выводим данные
            for row in working_data:
                data_row = '| ' + ' | '.join(
                    row[col].ljust(col_widths[i]) for i, col in enumerate(['name', 'age', 'address', 'date'])
                ) + ' |'
                print(data_row)
            print(separator)
            break
        
        # Если не влезло и не последний уровень — продолжаем цикл
        # Сбрасываем данные для следующего уровня (снова берём оригинал)
        working_data = [row.copy() for row in data]

if __name__ == '__main__':    
    parser = argparse.ArgumentParser(description='Преобразователь таблиц')
    parser.add_argument('-i', '--input', required=True, help='Путь к файлу или URL')
    args = parser.parse_args()
    filename = args.input
    
    # Проверяем, является ли вход ссылкой
    if filename.startswith(('http://', 'https://')):
        response = requests.get(filename)
        response.encoding = 'utf-8'
        # Сохраняем во временный файл или читаем из строки
        fake_file = StringIO(response.text)
        # Или временно сохранить на диск
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tmp:
            tmp.write(response.text)
            tmp_path = tmp.name
        data = read_data(tmp_path)
        # Удаляем временный файл после чтения
        os.unlink(tmp_path)
    else:
        data = read_data(filename)
    
    print_table(data)