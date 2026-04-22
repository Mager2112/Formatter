import shutil
import sys
import os
import argparse
import requests
import chardet
import tempfile
import re
from datetime import datetime
from io import StringIO

def detect_encoding(filename): #### ОПРЕДЕЛЕНИЕ КОДИРОВКИ
    with open(filename, 'rb') as f:
        raw = f.read(1000000)
        result = chardet.detect(raw)
        print(f"chardet результат: {result}")
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

def fix_date(date_str):
    """
    Приводит дату (и время) к формату YYYY-MM-DD HH:MM:SS
    Поддерживает различные форматы ввода
    """
    date_str = date_str.strip()
    date_part = ""
    time_part = ""
    
    # 1. Пробуем разделить дату и время (если есть пробел или T)
    if 'T' in date_str:
        parts = date_str.split('T')
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else ""
    elif ' ' in date_str:
        parts = date_str.split()
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else ""
    else:
        # Возможно, только дата или только время
        # Проверяем, похоже ли на время (содержит двоеточия)
        if ':' in date_str:
            time_part = date_str
            date_part = ""
        else:
            date_part = date_str
            time_part = ""
    
    # 2. Разбираем дату
    fixed_date = parse_date_part(date_part) if date_part else ""
    
    # 3. Разбираем время
    fixed_time = parse_time_part(time_part) if time_part else "00:00:00"
    
    # 4. Если дата не распознана, возвращаем исходную строку
    if not fixed_date and date_part:
        return date_str
    
    # 5. Собираем результат
    if fixed_date:
        return f"{fixed_date} {fixed_time}"
    else:
        # Было только время (маловероятно для наших данных)
        return fixed_time


def parse_date_part(date_str):
    """Парсит дату из разных форматов в YYYY-MM-DD"""
    date_str = date_str.strip()
    
    # Удаляем возможные кавычки и пробелы
    date_str = date_str.strip('"\'')
    
    # Список возможных форматов (порядок важен: от более специфичных к общим)
    formats = [
        # ISO с дефисами
        (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', '%Y-%m-%d'),
        # ISO с дефисами и временем (уже отделено)
        (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', '%Y-%m-%d'),
        # Без разделителей YYYYMMDD
        (r'^(\d{4})(\d{2})(\d{2})$', '%Y%m%d'),
        # С точками YYYY.MM.DD
        (r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', '%Y.%m.%d'),
        # Со слешами YYYY/MM/DD
        (r'^(\d{4})/(\d{1,2})/(\d{1,2})$', '%Y/%m/%d'),
        # DD.MM.YYYY (российский формат)
        (r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', '%d.%m.%Y'),
        # DD-MM-YYYY
        (r'^(\d{1,2})-(\d{1,2})-(\d{4})$', '%d-%m-%Y'),
        # DD/MM/YYYY
        (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', '%d/%m/%Y'),
    ]
    
    # Пробуем каждый формат
    for pattern, fmt in formats:
        match = re.match(pattern, date_str)
        if match:
            try:
                # Парсим через datetime для валидации
                dt = datetime.strptime(date_str, fmt)
                year, month, day = dt.year, dt.month, dt.day
                
                # Проверяем, не перепутаны ли день и месяц (месяц > 12)
                if month > 12:
                    # Меняем местами
                    month, day = day, month
                    # Проверяем валидность после обмена
                    try:
                        dt = datetime(year, month, day)
                    except ValueError:
                        # Если дата невалидна, оставляем как есть
                        month, day = day, month
                
                return f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                # Невалидная дата (например, 31 февраля)
                continue
    
    # Если ничего не подошло, пробуем извлечь числа вручную
    numbers = re.findall(r'\d+', date_str)
    if len(numbers) >= 3:
        # Пытаемся угадать: что год, месяц, день
        candidates = []
        
        # Ищем 4-значное число (скорее всего год)
        year_candidates = [n for n in numbers if len(n) == 4]
        if year_candidates:
            year = int(year_candidates[0])
            rest = [int(n) for n in numbers if n != str(year)]
            if len(rest) >= 2:
                month, day = rest[0], rest[1]
                
                # Если месяц > 12, меняем
                if month > 12:
                    month, day = day, month
                
                try:
                    datetime(year, month, day)
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except ValueError:
                    pass
    
    return None


def parse_time_part(time_str):
    """Парсит время из разных форматов в HH:MM:SS"""
    time_str = time_str.strip()
    
    # Убираем миллисекунды и часовые пояса
    time_str = re.sub(r'\.\d+', '', time_str)  # .123
    time_str = re.sub(r'[+-]\d{2}:?\d{2}$', '', time_str)  # +03:00 или +0300
    time_str = re.sub(r'Z$', '', time_str)  # Z в конце
    
    # Форматы времени
    formats = [
        (r'^(\d{2}):(\d{2}):(\d{2})$', '%H:%M:%S'),  # HH:MM:SS
        (r'^(\d{2}):(\d{2})$', '%H:%M'),              # HH:MM
        (r'^(\d{2})(\d{2})(\d{2})$', '%H%M%S'),       # HHMMSS
        (r'^(\d{1,2}):(\d{2})$', '%H:%M'),            # H:MM
    ]
    
    for pattern, fmt in formats:
        match = re.match(pattern, time_str)
        if match:
            try:
                dt = datetime.strptime(time_str, fmt)
                return f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
            except ValueError:
                continue
    
    # Если не распознали, возвращаем 00:00:00
    return "00:00:00"

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

def print_table(data): #### ВЫВЕДЕНИЕ ТАБЛИЦЫ
    if not data:
        return
    
    max_width = shutil.get_terminal_size().columns
    headers = ['ФИО', 'Возраст', 'Адрес', 'Дата рождения']
    table_title = "ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ"
    
    # Копируем данные, чтобы не портить оригинал
    working_data = [row.copy() for row in data]
    
    # разные уровни сокращения
    for level in range(5):  # от 0 (минимум) до 4 (максимум)
        # сокращение согласно уровню
        for row in working_data:
            row['name'] = shorten_name(row['name'], level)
            row['date'] = shorten_date(row['date'], level)
            row['address'] = shorten_address(row['address'], level, max_len=30 - level*5)
        
        # Вычисление ширины
        col_widths = [len(h) for h in headers]
        for row in working_data:
            col_widths[0] = max(col_widths[0], len(row['name']))
            col_widths[1] = max(col_widths[1], len(row['age']))
            col_widths[2] = max(col_widths[2], len(row['address']))
            col_widths[3] = max(col_widths[3], len(row['date']))
        
        total_width = sum(col_widths) + 3 * 3 + 2  # рамки и разделители
        
        if total_width <= max_width or level == 4:  # влезает или уже максимум
            # Выводим общий заголовок таблицы
            title_width = total_width  # ширина без внешних рамок
            if len(table_title) > title_width:
                # Если заголовок не влезает - обрезаем
                table_title_display = table_title[:title_width-3] + '...'
            else:
                table_title_display = table_title.center(title_width)
            
            print('+' + '-' * (total_width) + '+')
            print(f"|{table_title_display}|")
            print('+' + '-' * (total_width) + '+')
            
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

def main():
    # то, что показывается в консолях --help
    parser = argparse.ArgumentParser(description='Преобразователь таблиц. Он из файла с данными может создать таблицу')
    parser.add_argument('-i', '--input', required=True, help='Путь к файлу или URL')
    args = parser.parse_args()
    filename = args.input
    
    # Является ли файл ссылкой
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

if __name__ == '__main__':    
    main()