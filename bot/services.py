import base64
import json
from typing import Dict, Any


def parse_payload(raw: str) -> Dict[str, str]:
    if not raw:
        return {}
    if "|" not in raw and "=" not in raw:
        try:
            raw = base64.urlsafe_b64decode(raw + "==").decode("utf-8")
        except Exception:
            return {}
    out = {}
    for part in raw.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def score_lead(a: Dict[str, Any]) -> tuple[int, str]:
    score = 0
    if a.get("keys") == "На руках":
        score += 15
    score += {"до 2 мес": 25, "2–4": 15, "4–6": 8, "позже": 3}.get(a.get("deadline"), 0)
    score += 10 if a.get("priority") in {"Контроль", "Дизайн", "Минимум участия"} else 6 if a.get("priority") == "Бюджет" else 0
    score += {"Баланс (середина рынка)": 15, "Без компромиссов": 15, "Оптимально": 8, "Пока не понимаю": 5}.get(a.get("budget_level"), 0)
    if a.get("ready_call") == "Да":
        score += 20
    t = "Hot" if score >= 70 else "Warm" if score >= 40 else "Cold"
    return score, t


def summary_from_answers(a: Dict[str, Any]) -> str:
    return (
        f"Ключи: {a.get('keys','—')}; Цель: {a.get('purpose','—')}; Объект: {a.get('object_type','—')}; "
        f"Состояние: {a.get('state','—')}; Площадь: {a.get('area_m2','—')} м²; Комнаты: {a.get('rooms','—')}; "
        f"Срок: {a.get('deadline','—')}; Приоритет: {a.get('priority','—')}; Бюджет: {a.get('budget_level','—')}"
    )


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
