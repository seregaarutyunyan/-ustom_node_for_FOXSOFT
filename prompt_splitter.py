"""
Prompt Splitter - кастомная нода для ComfyUI.

Берёт один большой текст с нумерованными промптами:

    1. сгенерируй ...
    2. сгенерируй ...
    3. ...

и режет его на отдельные промпты. Структуру определяет сама.

Установка: положить файл в  ComfyUI/custom_nodes/  и перезапустить ComfyUI.
Нода появится в меню: Add Node -> text -> prompts -> Prompt Splitter (Auto)
"""

import re

# Сколько выходов-«розеток» у ноды. В ComfyUI число выходов фиксировано,
# поэтому делаем с запасом. Нужно больше - просто поменяй число.
MAX_PROMPTS = 50

# Ловит: "1. текст", "1) текст", "1: текст", "**1.** текст", "Промпт 1: текст", "Prompt 1. текст"
_NUM_RE = re.compile(
    r"^\s*[*#]*\s*(?:промпт|prompt)?\s*(\d+)\s*[.):][*]*\s*(.*)$",
    re.IGNORECASE,
)


def split_prompts(text: str):
    """Режет текст на список промптов."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    items = []
    expected = None

    for line in text.split("\n"):
        m = _NUM_RE.match(line)
        if m:
            n = int(m.group(1))
            # Новый промпт начинается только если номер идёт по порядку.
            # Так "3." внутри текста другого промпта не разрежет его по ошибке.
            if expected is None or n == expected:
                items.append([m.group(2)])
                expected = n + 1
                continue
        # Продолжение предыдущего промпта (многострочные промпты)
        if items:
            items[-1].append(line)

    prompts = [" ".join(p.strip() for p in item if p.strip()).strip() for item in items]
    prompts = [p for p in prompts if p]

    # Запасной вариант: нумерации нет - режем по пустым строкам
    if not prompts:
        blocks = re.split(r"\n\s*\n", text)
        prompts = [" ".join(b.split()) for b in blocks if b.strip()]

    return prompts


class PromptSplitterAuto:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = tuple(["STRING"] * MAX_PROMPTS) + ("STRING", "INT")
    RETURN_NAMES = tuple(f"prompt_{i}" for i in range(1, MAX_PROMPTS + 1)) + (
        "all_prompts_list",
        "count",
    )
    # Предпоследний выход - список (для батч-обработки), остальные - обычные строки
    OUTPUT_IS_LIST = tuple([False] * MAX_PROMPTS) + (True, False)

    FUNCTION = "run"
    CATEGORY = "text/prompts"

    def run(self, text):
        prompts = split_prompts(text)
        count = len(prompts)

        if count > MAX_PROMPTS:
            print(
                f"[PromptSplitter] Найдено {count} промптов, а выходов {MAX_PROMPTS}. "
                f"Лишние доступны только через all_prompts_list. "
                f"Увеличь MAX_PROMPTS в файле."
            )

        slots = prompts[:MAX_PROMPTS]
        slots += [""] * (MAX_PROMPTS - len(slots))  # пустые слоты = пустая строка

        return tuple(slots) + (prompts, count)


NODE_CLASS_MAPPINGS = {"PromptSplitterAuto": PromptSplitterAuto}
NODE_DISPLAY_NAME_MAPPINGS = {"PromptSplitterAuto": "Prompt Splitter (Auto)"}
