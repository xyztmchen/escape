import re
from collections import OrderedDict
import ast  # 輸入轉陣列
from datetime import datetime
import os
import logging

from openpyxl import load_workbook, Workbook

logging.basicConfig(level=logging.DEBUG)

# 基礎模式（Primitive Patterns）
basic_patterns = {
    "{NUM}": r"\d+",
    "{CH}": r"[一二三四五六七八九十百千萬零○]",
    "{CH_b}": r"[壹貳參肆伍陸柒捌玖拾佰仟萬零]",
    "{u_ROMAN}": r"(?:[IVXLCDM]+)",      # 大寫羅馬數字
    "{l_ROMAN}": r"(?:[ivxlcdm]+)",      # 新增：小寫羅馬數字
    "{u_ALPHA}": r"[A-Z]",               # 排除羅馬字母
    "{l_ALPHA}": r"[a-z]",               # 排除羅馬字母
    "{CIRCLED_NUM}": r"[❶-❿➊-➓]"
}

# 符號組合規則（Symbol Templates）
symbol_templates = [
    "",     # 原始模式（如 "1"）
    ".",    # 1.
    "、",   # 一、
    "-",    # 1-1
    "_",    # 1_1
    "/",
    " ",    # Part 1
    ")",    # 1)
    "）",
    "• ",   # • 1
    "★",    # ★1
    "■",    # ■A
    "§",    # §1
    "#",    # #1
    "~",    # 1
    "▶"     # ▶1
]

# 結構化組合規則（Structural Templates）
structural_templates = [
    "{PATTERN}",                  # 原始
    "{SYMBOL}{PATTERN}",          # 符號前綴（如 ★1）
    "{PATTERN}{SYMBOL}",          # 符號後綴（如 1)）
    "{SYMBOL}{PATTERN}{SYMBOL}",  # 符號包圍（如 -1-）

    "\\({PATTERN}\\)",
    "\\[{PATTERN}\\]",
    "\\（{PATTERN}\\）",
    "\\［{PATTERN}\\］",
    "\\「{PATTERN}\\」",

    "第{PATTERN}章",              # 第1章
    "卷{PATTERN}",               # 卷一
    "Part {PATTERN}",             # Part A
    "Section {PATTERN}",          # Section 1
    "No.{PATTERN}",           # No.1

    "{PATTERN}(?:{SYMBOL}{PATTERN})+"  # 多層級通用模式（如 1.1.1）
]

def is_roman(text):
    """檢查是否為合法羅馬數字（大小寫皆可）"""
    if not isinstance(text, str):
        return False
        
    roman_numerals = r'^[IVXLCDMivxlcdm]+$'
    if not re.fullmatch(roman_numerals, text):
        return False

    # 轉換為大寫統一處理
    upper_text = text.upper()

    # 非法規則列表（每條規則獨立檢查）
    invalid_rules = [
        'VV', 'LL', 'DD',  # 不可重複的字符
        'IL', 'IC', 'ID', 'IM',  # 非法減法組合
        'VX', 'VL', 'VC', 'VD', 'VM',  # V 不能減其他字符
        # 可擴充更多規則...
    ]

    # 檢查是否違反任何規則
    return not any(invalid in upper_text for invalid in invalid_rules)


# 動態生成所有結構模式
def generate_structural_patterns():
    generated_patterns = set()  # 避免重複

    # 遍歷所有基礎模式和符號組合
    for pattern_key in basic_patterns.keys():
        for symbol in symbol_templates:
            for template in structural_templates:
                # 替換模板中的佔位符
                generated = template.replace("{PATTERN}", pattern_key)
                generated = generated.replace("{SYMBOL}", re.escape(symbol))
                generated_patterns.add(generated)

    return sorted(generated_patterns, key=lambda x: len(x), reverse=True)

# 智能分段標註函式
def mark_hierarchical_pattern(text):
    if not isinstance(text, str):
        return None
        
    # 優先檢查羅馬數字
    if is_roman(text):
        return '{u_ROMAN}' if text.isupper() else '{l_ROMAN}'

    # 處理括號包裹的情況，如 "(1.1.1)"
    bracket_match = re.fullmatch(r'^\((.+)\)$', text)
    if bracket_match:
        inner_text = bracket_match.group(1)
        inner_marked = mark_hierarchical_pattern(inner_text)
        if inner_marked:
            return f"\\({inner_marked}\\)"

    # 合併數字多層級判斷（支持 . - _ 三種分隔符）
    if re.fullmatch(r'^([\d一二三四五六七八九十百千萬零○壹貳參肆伍陸柒捌玖拾佰仟萬]+)(?:[.\-_/、]([\d一二三四五六七八九十百千萬零○壹貳參肆伍陸柒捌玖拾佰仟萬]+))+$', text):
        separator_match = re.search(r'[.\-_/、]', text)
        if separator_match:
            separator = separator_match.group()
            parts = text.split(separator)

            # 智能判斷每個部分的類型
            marked_parts = []
            for part in parts:
                if re.fullmatch(r'^\d+$', part):
                    marked_parts.append('{NUM}')
                elif re.fullmatch(r'^[一二三四五六七八九十百千萬零○]+$', part):
                    marked_parts.append('{CH}')
                elif re.fullmatch(r'^[壹貳參肆伍陸柒捌玖拾佰仟萬零]+$', part):
                    marked_parts.append('{CH_b}')
                else:
                    marked_parts.append('{UNKNOWN}')

            return separator.join(marked_parts)

    # 處理字母-數字混合多層級（如 A.1.1 或 B-2-3）
    if re.fullmatch(r'^[A-Za-z](?:[.\-_]\d+)+$', text):
        separator_match = re.search(r'[.\-_]', text)
        if separator_match:
            separator = separator_match.group()
            parts = text.split(separator)
            prefix = '{u_ALPHA}' if parts[0].isupper() else '{l_ALPHA}'
            return prefix + separator + separator.join(['{NUM}'] * (len(parts)-1))

    return None

# 將結構樣式中的標籤取代為對應的正則
def expand_pattern(pattern):
    for key, regex in basic_patterns.items():
        pattern = pattern.replace(key, regex)
    return "^" + pattern + "$"  # 精確比對整個字串

# 檢查項目編號錯誤
def check_item_error(types, levels):
    errors = []
    hierarchy_stack = []
    last_level_idx = -1
    
    for i, item_type in enumerate(types):
        if item_type not in levels:
            errors.append("不符合任何已定義的階層模式")
            continue
            
        curr_level_idx = levels.index(item_type)
        
        # 檢查層級是否正確
        if curr_level_idx > last_level_idx + 1:
            errors.append(f"層級跳躍錯誤 (從{last_level_idx}跳到{curr_level_idx})")
        elif curr_level_idx <= last_level_idx:
            # 層級退回，檢查是否合理
            while hierarchy_stack and hierarchy_stack[-1][0] >= curr_level_idx:
                hierarchy_stack.pop()
                
            if hierarchy_stack and hierarchy_stack[-1][0] != curr_level_idx - 1:
                errors.append("層級關係錯誤")
            else:
                errors.append("")  # 正確
        else:
            errors.append("")  # 正確
        
        # 更新狀態
        hierarchy_stack.append((curr_level_idx, i))
        last_level_idx = curr_level_idx
        
    return errors

# 只分析 Excel 檔案，獲取階層設定
def analyze_excel_file(file_path):
    try:
        logging.info(f"分析 Excel 檔案: {file_path}")
        
        # 讀取 Excel 檔案
        wb = load_workbook(file_path)
        ws = wb.active

        # 取出第一欄作為 samples，跳過空值
        samples = []
        for row in ws.iter_rows(min_row=1, max_col=1):
            cell_value = row[0].value
            if cell_value is not None:
                samples.append(cell_value)
        
        if not samples:
            return [], "檔案中沒有找到項目編號資料"
            
        logging.info(f"找到 {len(samples)} 個項目編號")
        
        # 判斷所有編號類型
        types = []
        structure_patterns = generate_structural_patterns()
        
        for sample in samples:
            # 先檢查是否為多層級模式
            hierarchical_mark = mark_hierarchical_pattern(sample)
            if hierarchical_mark:
                types.append(hierarchical_mark)
                continue

            # 原有模式匹配
            matched = False
            for pattern in structure_patterns:
                regex = expand_pattern(pattern)
                if re.match(regex, str(sample)):
                    types.append(pattern)
                    matched = True
                    break
            if not matched:
                types.append(None)  # 不符合任何 pattern
        
        # 取得編號階層
        levels = list(OrderedDict.fromkeys(filter(None, types)))
        
        logging.info(f"識別到的階層: {levels}")
        
        return levels, None
        
    except Exception as e:
        logging.error(f"分析 Excel 檔案時發生錯誤: {e}", exc_info=True)
        return [], f"分析失敗: {str(e)}"


# 處理 Excel 檔案
def process_excel_file(file_path, custom_levels=None):
    try:
        logging.info(f"處理 Excel 檔案: {file_path}")
        
        # 讀取 Excel 檔案
        wb = load_workbook(file_path)
        ws = wb.active

        # 取出第一欄作為 samples，跳過空值
        samples = []
        for row in ws.iter_rows(min_row=1, max_col=1):
            cell_value = row[0].value
            if cell_value is not None:
                samples.append(cell_value)
        
        if not samples:
            return None, "檔案中沒有找到項目編號資料"
            
        logging.info(f"找到 {len(samples)} 個項目編號")
        
        # 判斷所有編號類型
        types = []
        structure_patterns = generate_structural_patterns()
        
        for sample in samples:
            # 先檢查是否為多層級模式
            hierarchical_mark = mark_hierarchical_pattern(sample)
            if hierarchical_mark:
                types.append(hierarchical_mark)
                continue

            # 原有模式匹配
            matched = False
            for pattern in structure_patterns:
                regex = expand_pattern(pattern)
                if re.match(regex, str(sample)):
                    types.append(pattern)
                    matched = True
                    break
            if not matched:
                types.append(None)  # 不符合任何 pattern
        
        # 使用傳入的自定義階層，或者探測到的階層
        levels = []
        if custom_levels:
            levels = custom_levels
        else:
            # 取得編號階層
            levels = list(OrderedDict.fromkeys(filter(None, types)))
                
        logging.info(f"識別到的階層: {levels}")
        
        # 生成新編號
        result = []
        errors = []  # 儲存錯誤信息
        
        if levels:
            tmp = [0] * len(levels)
            index_prev = 0
            
            for item_type in types:
                if item_type is None or item_type not in levels:
                    result.append("")
                    errors.append("不符合任何已定義的階層模式")
                    continue
                    
                index = levels.index(item_type)

                if index < index_prev:
                    for i in range(index + 1, len(tmp)):
                        tmp[i] = 0
                tmp[index] += 1
                formatted_num = '.'.join(f'{num:02}' for num in tmp[:index+1])
                num = re.sub(r'(\.00)+$', '', formatted_num)
                num2 = 'd' + num
                result.append(num2)
                index_prev = index
                errors.append("")  # 暫時無錯誤
                
        # 額外檢查項目編號順序和結構錯誤
        detailed_errors = check_item_error(types, levels)
        for i in range(len(errors)):
            if i < len(detailed_errors) and not errors[i]:
                errors[i] = detailed_errors[i]
                
        # 建立新的 Excel 檔案
        new_wb = Workbook()
        new_ws = new_wb.active
        
        # 複製原始資料並加入新欄位
        row_idx = 1
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            new_row = list(row)
            # 插入生成的編號
            if i < len(result):
                new_row.insert(0, result[i])
                # 添加錯誤提醒欄
                new_row.append(errors[i])
            new_ws.append(new_row)
            row_idx += 1
        
        # 儲存新 Excel 檔案
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_dir = "static/outputs"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"output_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, output_filename)
        new_wb.save(output_path)
        
        logging.info(f"處理完成，輸出為 {output_path}")
        return output_filename, None
        
    except Exception as e:
        logging.error(f"處理 Excel 檔案時發生錯誤: {e}", exc_info=True)
        return None, f"處理失敗: {str(e)}"