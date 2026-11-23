#!/usr/bin/env python3
"""Converte classes Tailwind literais de um SFC Vue para os tokens do ADR 0007.

Uso: python3 scripts/tw-tokens.py <ficheiro.vue> [...]   (escreve no lugar; imprime contagens)

Só mexe no <template> e nas linhas `@apply` do <style> — nunca no <script>.
Regras (os tokens invertem sozinhos no escuro, por isso os pares `dark:` saem):
  dark:*                      → removido
  gray|slate|zinc-N           → neutral-N
  bg-white                    → bg-surface
  indigo|violet|purple-N      → primary-N
  qualquer outro dark:*       → removido
  bg-{verde|vermelho|azul|âmbar}-50/100 → bg-{success|danger|info|warning}/10|15
  text-{…}-500/600/700        → text-{success|danger|info|warning}
Ver EV-0054 (primeira utilização) e CLAUDE.md §6.
"""
import re
import sys

SEMANTIC = {
    "green": "success",
    "emerald": "success",
    "red": "danger",
    "rose": "danger",
    "blue": "info",
    "sky": "info",
    "yellow": "warning",
    "amber": "warning",
    "orange": "warning",
}
VARIANT = r"(?:(?:hover|focus|group-hover|active|disabled|placeholder|focus-within|sm|md|lg|xl|group-hover/[\w-]+):)*"
TOKEN_RE = re.compile(
    r"(?<![\w:/-])("
    + VARIANT
    + r")(dark:"
    + VARIANT
    + r")?([a-z]+(?:-[a-z]+)*)-(gray|slate|zinc|white|indigo|violet|purple|green|emerald|red|rose|blue|sky|yellow|amber|orange)(?:-(\d{2,3}))?(/\d+)?(?![\w-])"
)


def convert_token(m, counts):
    variants, dark, util, color, shade, alpha = m.groups()
    if dark:
        counts["dark_removed"] += 1
        return ""
    alpha = alpha or ""
    if color in ("gray", "slate", "zinc") and shade:
        counts["neutral"] += 1
        return f"{variants}{util}-neutral-{shade}{alpha}"
    if color == "white" and util == "bg":
        counts["surface"] += 1
        return f"{variants}bg-surface{alpha}"
    if color in ("indigo", "violet", "purple") and shade:
        counts["primary"] += 1
        return f"{variants}{util}-primary-{shade}{alpha}"
    if color in SEMANTIC and shade:
        sem = SEMANTIC[color]
        n = int(shade)
        if util == "bg" and n <= 100 and not alpha:
            counts["semantic"] += 1
            return f"{variants}bg-{sem}/{10 if n == 50 else 15}"
        if util in ("text", "border") and 400 <= n <= 700:
            counts["semantic"] += 1
            return f"{variants}{util}-{sem}{alpha}"
    return m.group(0)


DARK_ANY_RE = re.compile(r'(?<![\w:/-])dark:[^\s"\'`]+')


def convert_classes(text, counts):
    out = TOKEN_RE.sub(lambda m: convert_token(m, counts), text)
    # Qualquer `dark:` que sobre (cores fora da lista, ring, shadow…) também sai:
    # o par claro, já convertido para token, serve os dois temas.
    out, n = DARK_ANY_RE.subn("", out)
    counts["dark_removed"] += n
    return out


def process(path):
    src = open(path, encoding="utf-8").read()
    counts = {"dark_removed": 0, "neutral": 0, "surface": 0, "primary": 0, "semantic": 0}
    t_start = src.find("<template>")
    t_end = src.rfind("</template>")
    s_start = src.find("<script")
    st_start = src.find("<style")
    if t_start == -1 or t_end == -1:
        return counts
    template = src[t_start:t_end]

    def fix_attr(m):
        new = convert_classes(m.group(2), counts)
        if m.group(1) == 'class="':
            # Atributo estático: só classes separadas por espaço — normalizar é seguro.
            new = re.sub(r"\s{2,}", " ", new).strip()
        else:
            # :class é JavaScript: só se colapsa o duplo espaço deixado pela remoção,
            # nunca se mexe em espaços junto às aspas (concatenações de classes).
            new = re.sub(r"(?<=\w) {2,}(?=\w)", " ", new)
        return f'{m.group(1)}{new}"'

    template = re.sub(r'(\bclass="|:class=")([^"]*)"', fix_attr, template)
    out = src[:t_start] + template + src[t_end:]
    if st_start != -1 and st_start > s_start:
        st_start = out.find("<style")
        head, style = out[:st_start], out[st_start:]
        style = re.sub(
            r"(@apply\s+)([^;]+);",
            lambda m: m.group(1)
            + re.sub(r"\s{2,}", " ", convert_classes(m.group(2), counts)).strip()
            + ";",
            style,
        )
        out = head + style
    open(path, "w", encoding="utf-8").write(out)
    return counts


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f, process(f))
