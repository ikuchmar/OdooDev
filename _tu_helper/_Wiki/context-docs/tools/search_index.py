# -*- coding: utf-8 -*-
"""
Индекс и логика подсказок/поиска по ключам, алиасам и токенам.
"""

import difflib
from typing import Dict, List, Optional, Set
from models import Section
from utils import normalize_key, tokenize

class SearchIndex:
    """
    Простой индекс:
      - by_key: ключ -> Section (если дубликаты, берём первый)
      - alias_to_key: алиас -> ключ
      - token_to_keys: токен -> множество ключей
      - universe: множество строк (для fuzzy)
    """
    def __init__(self, sections: List[Section]):
        self.by_key: Dict[str, Section] = {}
        self.alias_to_key: Dict[str, str] = {}
        self.token_to_keys: Dict[str, Set[str]] = {}
        self.universe: Set[str] = set()

        for s in sections:
            if s.key not in self.by_key:
                self.by_key[s.key] = s
            self.universe.add(s.key)

            for t in tokenize(s.key):
                self.token_to_keys.setdefault(t, set()).add(s.key)
                self.universe.add(t)

            for a in s.aliases:
                self.alias_to_key[a] = s.key
                self.universe.add(a)
                for t in tokenize(a):
                    self.token_to_keys.setdefault(t, set()).add(s.key)
                    self.universe.add(t)

    def suggest(self, q: str, limit: int = 50) -> List[str]:
        """
        Список КЛЮЧЕЙ для Combobox.
        Порядок: точное → подстроки (ключи/алиасы/токены) → fuzzy, уникально, до limit.
        """
        q = normalize_key(q)
        results: List[str] = []

        if not q:
            return sorted(self.by_key.keys())[:limit]

        # точное
        if q in self.by_key:
            results.append(q)

        # подстроки по ключам
        subs_keys = [k for k in self.by_key if q in k and k not in results]
        subs_keys.sort(key=lambda k: (k.find(q), len(k)))
        results.extend(subs_keys)

        # подстроки по алиасам
        for a, k in self.alias_to_key.items():
            if q in a and k not in results:
                results.append(k)

        # подстроки по токенам
        for t, keys in self.token_to_keys.items():
            if q in t:
                for k in keys:
                    if k not in results:
                        results.append(k)

        # fuzzy
        if len(results) < limit:
            near = difflib.get_close_matches(q, list(self.universe), n=limit, cutoff=0.7)
            for s in near:
                if s in self.by_key and s not in results:
                    results.append(s)
                elif s in self.alias_to_key:
                    k = self.alias_to_key[s]
                    if k not in results:
                        results.append(k)
                elif s in self.token_to_keys:
                    for k in self.token_to_keys[s]:
                        if k not in results:
                            results.append(k)

        return results[:limit]

    def find_best(self, q: str) -> Optional[Section]:
        """
        Лучшая секция под запрос: точное совпадение -> первая из suggest().
        """
        q = normalize_key(q)
        if not q:
            return None
        if q in self.by_key:
            return self.by_key[q]
        sug = self.suggest(q, limit=1)
        if sug:
            return self.by_key.get(sug[0])
        return None
