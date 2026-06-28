from abb_contracts import CorpusDocument, Language


def select_sample(documents: list[CorpusDocument], limit: int) -> list[CorpusDocument]:
    """Pick up to `limit` documents, round-robin across languages for diversity.

    A naive head slice would over-represent whichever language was crawled first;
    round-robin keeps AZ/RU/EN all present in the committed demo sample.
    """

    if limit <= 0:
        return []

    by_language: dict[Language, list[CorpusDocument]] = {}
    for document in documents:
        by_language.setdefault(document.language, []).append(document)

    languages = sorted(by_language, key=lambda language: language.value)
    selected: list[CorpusDocument] = []
    index = 0
    while len(selected) < limit and any(index < len(by_language[lang]) for lang in languages):
        for lang in languages:
            if index < len(by_language[lang]) and len(selected) < limit:
                selected.append(by_language[lang][index])
        index += 1
    return selected
