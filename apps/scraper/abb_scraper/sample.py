from abb_contracts import CorpusDocument, Language, Segment


def select_sample(documents: list[CorpusDocument], limit: int) -> list[CorpusDocument]:
    """Pick up to `limit` documents, round-robin across (language, segment) buckets.

    A naive head slice would over-represent whichever language/segment was crawled
    first (e.g. all-AZ, or all-`other` root SEO pages). Round-robin across both
    axes keeps AZ/RU/EN *and* individuals/business/about/other present in the
    committed demo sample, so segment-filtered retrieval has something to show.
    """

    if limit <= 0:
        return []

    by_bucket: dict[tuple[Language, Segment], list[CorpusDocument]] = {}
    for document in documents:
        by_bucket.setdefault((document.language, document.segment), []).append(document)

    buckets = sorted(by_bucket, key=lambda key: (key[0].value, key[1].value))
    selected: list[CorpusDocument] = []
    index = 0
    while len(selected) < limit and any(index < len(by_bucket[bucket]) for bucket in buckets):
        for bucket in buckets:
            if index < len(by_bucket[bucket]) and len(selected) < limit:
                selected.append(by_bucket[bucket][index])
        index += 1
    return selected
