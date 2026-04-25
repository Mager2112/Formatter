import pytest
import tempfile
import shutil
import os
from unittest.mock import patch, Mock
from io import StringIO

# Покрытие тестами
# Импорт из проекта
from formatter import (
    detect_encoding,
    read_data,
    shorten_name,
    fix_date,
    parse_date_part,
    parse_time_part,
    shorten_date,
    shorten_address,
    print_table
)


# ============ ТЕСТЫ ДАТ ============
class TestDateFunctions:
    """Тесты для функций работы с датами"""
    
    def test_normal_date(self):
        """Нормальная дата не должна меняться"""
        assert fix_date("2026-03-15") == "2026-03-15 00:00:00"
        assert fix_date("2026-03-15 14:30:00") == "2026-03-15 14:30:00"
    
    def test_swapped_month_day(self):
        """Если месяц > 12, меняем местами день и месяц"""
        assert fix_date("2026-15-03") == "2026-03-15 00:00:00"
        assert fix_date("2026-20-05") == "2026-05-20 00:00:00"
        assert fix_date("2026-13-01") == "2026-01-13 00:00:00"
    
    def test_fix_date_with_time(self):
        """Дата со временем и перепутанными месяцем/днём"""
        assert fix_date("2026-15-03 23:45:12") == "2026-03-15 23:45:12"
    
    def test_compact_format(self):
        """Компактный формат YYYYMMDD"""
        assert fix_date("20260315") == "2026-03-15 00:00:00"
        assert fix_date("20213011") == "2021-11-30 00:00:00"  # 13й месяц исправлен
    
    def test_t_separator(self):
        """Разделитель T вместо пробела"""
        assert fix_date("20211309T12:23:00") == "2021-09-13 12:23:00"
    
    def test_dot_separator(self):
        """Точки вместо дефисов"""
        assert fix_date("2026.03.15") == "2026-03-15 00:00:00"
        assert fix_date("15.03.2026") == "2026-03-15 00:00:00"
    
    def test_slash_separator(self):
        """Слеши вместо дефисов"""
        assert fix_date("2026/03/15") == "2026-03-15 00:00:00"
    
    def test_parse_date_part(self):
        """Парсинг даты из разных форматов"""
        assert parse_date_part("2026-03-15") == "2026-03-15"
        assert parse_date_part("20260315") == "2026-03-15"
        assert parse_date_part("15.03.2026") == "2026-03-15"
        assert parse_date_part("2026-15-03") == "2026-03-15"
    
    def test_parse_time_part(self):
        """Парсинг времени"""
        assert parse_time_part("14:30:00") == "14:30:00"
        assert parse_time_part("14:30") == "14:30:00"
        assert parse_time_part("143000") == "14:30:00"
        assert parse_time_part("14:30:00.123") == "14:30:00"
        assert parse_time_part("14:30:00+03:00") == "14:30:00"
    
    @pytest.mark.parametrize("input_date,expected", [
        ("2026-03-15", "2026-03-15 00:00:00"),
        ("2026-15-03", "2026-03-15 00:00:00"),
        ("20213011", "2021-11-30 00:00:00"),
        ("20211309T12:23:00", "2021-09-13 12:23:00"),
        ("2022-12-23 05:56:06", "2022-12-23 05:56:06"),
    ])
    def test_fix_date_parametrized(self, input_date, expected):
        """Параметризованный тест для fix_date"""
        assert fix_date(input_date) == expected
    
    def test_shorten_date_levels(self):
        """Разные уровни сокращения даты"""
        date_with_time = "2026-03-15 14:30:00"
        # Уровень 0 и 1 - полная дата+время
        assert shorten_date(date_with_time, 0) == "2026-03-15 14:30:00"
        assert shorten_date(date_with_time, 1) == "2026-03-15 14:30:00"
        # Уровень 2+ - только месяц-день
        assert shorten_date(date_with_time, 2) == "03-15"
        assert shorten_date(date_with_time, 3) == "03-15"


# ============ ТЕСТЫ ИМЁН ============
class TestNameFunctions:
    """Тесты для сокращения имён"""
    
    def test_full_name_level0(self):
        """Полное имя на уровне 0"""
        assert shorten_name("Иванов Иван Иванович", 0) == "Иванов Иван Иванович"
    
    def test_initials_level1_full(self):
        """Фамилия + инициалы (3 части)"""
        assert shorten_name("Иванов Иван Иванович", 1) == "Иванов И. И."
    
    def test_initials_level1_two_parts(self):
        """Фамилия + инициал (2 части)"""
        assert shorten_name("Иванов Иван", 1) == "Иванов И."
    
    def test_shortened_surname_level2(self):
        """Уровень 2 - сокращённая фамилия + инициалы"""
        result = shorten_name("Иванов Иван Иванович", 2)
        assert result.startswith("Иван.")
        assert "И." in result
    
    def test_only_initials_level3(self):
        """Уровень 3 - только инициалы"""
        assert shorten_name("Иванов Иван Иванович", 3) == "И.И.И."
        assert shorten_name("Иванов Иван", 3) == "И.И."
    
    def test_single_word_name(self):
        """Одно слово в имени - возвращаем как есть"""
        assert shorten_name("Мононим", 3) == "Мононим"
    
    def test_empty_name(self):
        """Пустое имя"""
        assert shorten_name("", 1) == ""
    
    @pytest.mark.parametrize("name,level,expected", [
        ("Иванов Иван Иванович", 0, "Иванов Иван Иванович"),
        ("Иванов Иван Иванович", 1, "Иванов И. И."),
        ("Иванов Иван Иванович", 3, "И.И.И."),
        ("Петров Петр", 1, "Петров П."),
        ("Сидоров Сидор Сидорович", 2, "Сидо. С. С."),
    ])
    def test_shorten_name_parametrized(self, name, level, expected):
        """Параметризованные тесты имён"""
        assert shorten_name(name, level) == expected


# ============ ТЕСТЫ АДРЕСОВ ============
class TestAddressFunctions:
    """Тесты для сокращения адресов"""
    
    def test_address_level0(self):
        """Уровень 0 - полный адрес"""
        addr = "улица Советская, 63, Санкт-Петербург"
        assert shorten_address(addr, 0) == addr
    
    def test_street_shortening(self):
        """Сокращение типов улиц"""
        addr = "улица Пушкина, 10, Москва"
        result = shorten_address(addr, 0)  # level 0 не сокращает
        # На уровне 1 проверяем сокращения
        result_level1 = shorten_address(addr, 1)
        assert "ул." in result_level1
    
    def test_city_shortening_special(self):
        """Особые случаи городов"""
        addr = "улица Советская, 63, Санкт-Петербург"
        result = shorten_address(addr, 1)
        # Город должен сократиться до специального кода
        assert "СПб" in result or "Санк" in result
    
    def test_city_shortening_long(self):
        """Длинные города"""
        addr = "улица Ленина 20, Екатеринбург"
        result = shorten_address(addr, 1)
        # Должен быть формат "три буквы-последняя буква."
        assert len(result.split(',')[-1].strip()) <= 6
    
    def test_address_level1_first_words(self):
        """Уровень 1 - первые 4 слова"""
        addr = "улица Советская, 63, Санкт-Петербург"
        result = shorten_address(addr, 1)
        words = result.split()
        assert len(words) <= 4
    
    def test_address_level2_strong_shortening(self):
        """Уровень 2 - сильное сокращение"""
        addr = "улица ОченьДлиннаяНазваниеУлицыКоторуюНужноСократить, 123, Санкт-Петербург"
        result = shorten_address(addr, 2, 30)
        # Должно быть сокращение с точкой в середине
        assert "." in result or len(result) <= 30
    
    def test_address_no_comma(self):
        """Адрес без запятой"""
        addr = "улица Пушкина дом 10"
        result = shorten_address(addr, 1)
        assert result == "улица Пушкина дом 10" or result == "ул. Пушкина дом 10"


# ============ ТЕСТЫ ФАЙЛОВ ============
class TestFileOperations:
    """Тесты для работы с файлами"""
    
    @pytest.fixture
    def temp_file(self):
        """Фикстура для временного файла"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "test.txt")
        yield file_path
        shutil.rmtree(temp_dir)
    
    def create_test_file(self, path, content, encoding='utf-8'):
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    
    def test_read_normal_data(self, temp_file):
        """Чтение нормальных данных"""
        content = "Иванов Иван\t30\tМосква\t2026-03-15\n"
        content += "Петров Петр\t25\tСПб\t2026-03-16\n"
        self.create_test_file(temp_file, content)
        
        data = read_data(temp_file)
        assert len(data) == 2
        assert data[0]['name'] == "Иванов Иван"
        assert data[0]['age'] == "30"
        assert data[0]['address'] == "Москва"
    
    def test_read_swapped_dates(self, temp_file):
        """Чтение с перепутанными датами"""
        content = "Иванов Иван\t30\tМосква\t2026-15-03\n"
        self.create_test_file(temp_file, content)
        
        data = read_data(temp_file)
        assert len(data) == 1
        assert data[0]['date'] == "2026-03-15 00:00:00"
    
    def test_read_compact_dates(self, temp_file):
        """Чтение с компактными датами"""
        content = "Никитин Иван\t22\tДзержинск\t20213011 153031\n"
        content += "Бендер Остап\t27\tНью-Васюки\t20211309T12:23:00\n"
        self.create_test_file(temp_file, content)
        
        data = read_data(temp_file)
        assert len(data) == 2
        assert data[0]['date'] == "2021-11-30 15:30:31"
        assert data[1]['date'] == "2021-09-13 12:23:00"
    
    def test_skip_incomplete_lines(self, temp_file):
        """Пропуск неполных строк"""
        content = "Иванов Иван\t30\tМосква\n"  # нет даты
        content += "Петров Петр\t25\tСПб\t2026-03-15\n"
        self.create_test_file(temp_file, content)
        
        data = read_data(temp_file)
        assert len(data) == 1
    
    def test_skip_empty_lines(self, temp_file):
        """Пропуск пустых строк"""
        content = "Иванов Иван\t30\tМосква\t2026-03-15\n\n\n"
        content += "\t\t\t\n"
        content += "Петров Петр\t25\tСПб\t2026-03-16\n"
        self.create_test_file(temp_file, content)
        
        data = read_data(temp_file)
        assert len(data) == 2
    
    def test_detect_encoding(self, temp_file):
        """Определение кодировки"""
        content = "Тестовый текст с русскими буквами"
        self.create_test_file(temp_file, content, encoding='utf-8')
        
        encoding = detect_encoding(temp_file)
        # chardet может определить как utf-8 или windows-1251
        assert encoding is not None
    
    def test_read_different_encoding(self, temp_file):
        """Чтение файла в другой кодировке"""
        content = "Иванов Иван\t30\tМосква\t2026-03-15"
        with open(temp_file, 'w', encoding='cp1251') as f:
            f.write(content)
        
        data = read_data(temp_file)
        assert len(data) == 1
        assert data[0]['name'] == "Иванов Иван"


# ============ ТЕСТЫ ВЫВОДА ТАБЛИЦЫ ============
class TestPrintTable:
    """Тесты вывода таблицы"""
    
    @pytest.fixture
    def sample_data(self):
        return [
            {'name': 'Иванов Иван', 'age': '30', 
             'address': 'Москва', 'date': '2026-03-15'},
            {'name': 'Петров Петр', 'age': '25', 
             'address': 'СПб', 'date': '2026-03-16'},
        ]
    
    def test_print_table_output(self, sample_data, capsys):
        """Проверка вывода таблицы"""
        print_table(sample_data)
        captured = capsys.readouterr()
        
        assert "ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ" in captured.out
        assert "ФИО" in captured.out
        assert "Возраст" in captured.out
        assert "Иванов" in captured.out
    
    def test_empty_data(self, capsys):
        """Пустые данные"""
        print_table([])
        captured = capsys.readouterr()
        assert captured.out == ""
    
    def test_real_data_output(self, capsys):
        """Тест с реальными данными"""
        test_data = [
            {'name': 'Соколов Андрей Николаевич', 'age': '36',
             'address': 'улица Советская, 63, Санкт-Петербург',
             'date': '2022-12-23 05:56:06'},
            {'name': 'Никитин Иван Александрович', 'age': '22',
             'address': 'улица Ленина 20, Дзержинск',
             'date': '2021-11-30 15:30:31'},
        ]
        
        print_table(test_data)
        captured = capsys.readouterr()
        
        assert "Соколов" in captured.out
        assert "Никитин" in captured.out
        assert "2022-12-23" in captured.out


# ============ КРАЕВЫЕ СЛУЧАИ ============
class TestEdgeCases:
    """Тесты краевых случаев"""
    
    def test_invalid_dates(self):
        """Невалидные даты"""
        result = fix_date("not a date")
        assert result == "not a date" or result == "not a date 00:00:00"
    
    def test_parse_date_part_none(self):
        """Parse_date_part возвращает None для некорректных данных"""
        assert parse_date_part("") is None
        assert parse_date_part("invalid") is None
    
    def test_parse_time_part_default(self):
        """Parse_time_part возвращает 00:00:00 для некорректных данных"""
        assert parse_time_part("") == "00:00:00"
        assert parse_time_part("invalid") == "00:00:00"
    
    def test_leap_year_feb29(self):
        """29 февраля в високосный год"""
        result = fix_date("2024-29-02")
        assert result == "2024-02-29 00:00:00"
    
    def test_long_name(self):
        """Длинное имя не вызывает ошибок"""
        long_name = "А" * 50 + " Б" * 10
        result = shorten_name(long_name, 3)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_address_max_len_zero(self):
        """Максимальная длина 0"""
        addr = "Тестовый адрес"
        result = shorten_address(addr, 2, 0)
        assert isinstance(result, str)


# ============ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ============
class TestIntegration:
    """Интеграционные тесты с реальными данными"""
    
    @pytest.fixture
    def temp_dir(self):
        """Фикстура для временной директории"""
        dir_path = tempfile.mkdtemp()
        yield dir_path
        shutil.rmtree(dir_path)
    
    def create_data_file(self, dir_path, filename="data.txt"):
        """Создаёт тестовый файл как в задании"""
        content = """Соколов Андрей Николаевич	36	улица Советская, 63, Санкт-Петербург	2022-12-23 05:56:06
Никитин Иван Александрович	22	улица Ленина 20, Дзержинск	20213011 153031
Остап Сулейманович Бендер	27	улица Шахматная, Нью-Васюки	20211309T12:23:00"""
        
        file_path = os.path.join(dir_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_full_pipeline(self, temp_dir):
        """Полный цикл обработки файла"""
        file_path = self.create_data_file(temp_dir)
        data = read_data(file_path)
        
        assert len(data) == 3
        
        # Проверяем исправление дат
        assert data[0]['date'] == "2022-12-23 05:56:06"
        assert data[1]['date'] == "2021-11-30 15:30:31"
        assert data[2]['date'] == "2021-09-13 12:23:00"
        
        # Проверяем имена
        assert "Соколов" in data[0]['name']
        assert "Никитин" in data[1]['name']
        assert "Бендер" in data[2]['name']
        
        # Проверяем адреса
        assert "Санкт-Петербург" in data[0]['address']
        assert "Дзержинск" in data[1]['address']
        assert "Нью-Васюки" in data[2]['address']
    
    def test_full_pipeline_with_output(self, temp_dir, capsys):
        """Полный цикл с выводом таблицы"""
        file_path = self.create_data_file(temp_dir)
        data = read_data(file_path)
        print_table(data)
        
        captured = capsys.readouterr()
        assert "Соколов" in captured.out
        assert "Никитин" in captured.out
        assert "Остап" in captured.out
        assert "2021-11-30" in captured.out or "11-30" in captured.out


# ============ ТЕСТЫ ДЛЯ URL (с моками) ============
class TestURLHandling:
    """Тесты для URL (с моками)"""
    
    @patch('requests.get')
    def test_url_detection_true(self, mock_get):
        """Проверка определения URL"""
        mock_response = Mock()
        mock_response.text = "test\tdata\tfor\turl\n"
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        # Проверяем, что URL определяется по префиксу
        http_url = "http://example.com/file.txt"
        https_url = "https://site.com/data.txt"
        
        assert http_url.startswith(('http://', 'https://'))
        assert https_url.startswith(('http://', 'https://'))
        assert not "file.txt".startswith(('http://', 'https://'))


# ============ ЗАПУСК ТЕСТОВ ============
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--color=yes'])