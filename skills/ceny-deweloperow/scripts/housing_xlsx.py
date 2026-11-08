"""Bounded, read-only OOXML table reader. No extraction or formula evaluation."""
import io
import posixpath
import re
import zipfile
import zlib
import xml.etree.ElementTree as ET

MAIN = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PACKAGE = '{http://schemas.openxmlformats.org/package/2006/relationships}'
MAX_PART = 16 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_COLUMNS = 256


class XlsxError(ValueError):
    def __init__(self, message, kind='upstream_format'):
        super().__init__(message)
        self.kind = kind


def read_table(raw, max_rows=200000):
    """Return one sheet's header and row dictionaries; values remain strings."""
    consumed = [0]
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise XlsxError('Powtórzone wpisy archiwum XLSX.')

            def xml_part(name):
                info = archive.getinfo(name)
                if info.flag_bits & 1:
                    raise XlsxError('Zaszyfrowane archiwum XLSX jest nieobsługiwane.')
                if info.file_size > MAX_PART:
                    raise XlsxError('Element XLSX przekracza limit 16 MiB po rozpakowaniu.', 'response_too_large')
                consumed[0] += info.file_size
                if consumed[0] > MAX_TOTAL:
                    raise XlsxError('Przekroczony limit 32 MiB rozpakowanych danych XLSX.', 'response_too_large')
                with archive.open(info) as stream:
                    content = stream.read(MAX_PART + 1)
                if len(content) > MAX_PART:
                    raise XlsxError('Element XLSX przekracza limit 16 MiB po rozpakowaniu.', 'response_too_large')
                content = content.decode('utf-8-sig')
                if re.search(r'<!\s*(?:DOCTYPE|ENTITY)', content, re.I):
                    raise XlsxError('DTD i encje XML nie są obsługiwane.')
                return ET.fromstring(content)

            workbook = xml_part('xl/workbook.xml')
            sheets = workbook.findall(MAIN + 'sheets/' + MAIN + 'sheet')
            if len(sheets) != 1:
                raise XlsxError('Obsługiwany XLSX musi zawierać dokładnie jeden arkusz.')
            rels = xml_part('xl/_rels/workbook.xml.rels')
            matches = [rel for rel in rels.findall(PACKAGE + 'Relationship')
                       if rel.get('Id') == sheets[0].get(REL + 'id')]
            if len(matches) != 1 or matches[0].get('TargetMode') == 'External':
                raise XlsxError('Nieprawidłowe odwołanie do arkusza.')
            target = matches[0].get('Target', '')
            path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
            if not path.startswith('xl/worksheets/') or not path.endswith('.xml'):
                raise XlsxError('Nieobsługiwane odwołanie do arkusza.')
            strings = []
            if 'xl/sharedStrings.xml' in names:
                shared = xml_part('xl/sharedStrings.xml')
                for node in shared.findall(MAIN + 'si'):
                    strings.append(''.join(t.text or '' for t in node.iter(MAIN + 't')))
                    if len(strings) > max_rows:
                        raise XlsxError('Za dużo tekstów w XLSX.')
            sheet = xml_part(path)
            table, previous_row = [], 0
            for row in sheet.findall(MAIN + 'sheetData/' + MAIN + 'row'):
                index = row.get('r', '')
                if not index.isdigit() or not previous_row < int(index) <= max_rows + 1:
                    raise XlsxError('Nieprawidłowy lub zbyt duży zakres wierszy XLSX.')
                previous_row = int(index)
                values = []
                for cell in row.findall(MAIN + 'c'):
                    address = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]*)', cell.get('r', ''))
                    if not address or int(address[2]) != previous_row:
                        raise XlsxError('Nieprawidłowy adres komórki XLSX.')
                    column = 0
                    for character in address[1]:
                        column = column * 26 + ord(character) - ord('A') + 1
                    if not len(values) < column <= MAX_COLUMNS:
                        raise XlsxError('Powtórzona komórka lub zbyt dużo kolumn XLSX.')
                    if cell.find(MAIN + 'f') is not None or cell.get('t') in ('e', 'b'):
                        raise XlsxError('Formuły, błędy i wartości logiczne w tabeli XLSX są nieobsługiwane.')
                    value = cell.find(MAIN + 'v')
                    value = value.text or '' if value is not None else ''
                    if cell.get('t') == 's':
                        if not value.isdigit() or int(value) >= len(strings):
                            raise XlsxError('Nieprawidłowy indeks tekstu XLSX.')
                        value = strings[int(value)]
                    elif cell.get('t') == 'inlineStr':
                        inline = cell.find(MAIN + 'is')
                        value = ''.join(t.text or '' for t in inline.iter(MAIN + 't')) if inline is not None else ''
                    values.extend([''] * (column - len(values) - 1))
                    values.append(value)
                while values and values[-1] == '':
                    values.pop()
                if values:
                    table.append(values)
            if not table:
                raise XlsxError('Pusty arkusz XLSX.')
            headers = table[0]
            if len(headers) != len(set(headers)) or any(not value for value in headers):
                raise XlsxError('Puste lub powtórzone nagłówki XLSX.')
            rows = []
            for values in table[1:]:
                if len(values) > len(headers):
                    raise XlsxError('Wiersz XLSX wykracza poza nagłówki.')
                rows.append(dict(zip(headers, values + [''] * (len(headers) - len(values)))))
            return headers, rows
    except XlsxError:
        raise
    except (zipfile.BadZipFile, KeyError, UnicodeError, ET.ParseError, OSError, RuntimeError, NotImplementedError, RecursionError, ValueError, EOFError, zlib.error):
        raise XlsxError('Nieprawidłowy lub nieobsługiwany plik XLSX.')
