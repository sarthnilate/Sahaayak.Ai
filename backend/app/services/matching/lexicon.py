"""
Phase 5: Versioned normalisation and cross-lingual concept lexicon.
Maps equivalent terms across English, Hindi, Marathi, and Hinglish.
Strictly deterministic and unit-testable.
"""

import re
import unicodedata
from typing import Dict, List, Set

LEXICON_VERSION = "1.0.0"

# Stopwords to remove before concept extraction (English, Hindi, Marathi)
STOPWORDS = {
    # English
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "by", "for", "with",
    "about", "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "and", "or", "but", "if", "because", "as", "until", "while", "of", "it",
    # Hindi / Hinglish
    "hai", "hain", "tha", "thi", "the", "ke", "ki", "ka", "ko", "se", "me", "mein",
    "par", "aur", "ya", "bhi", "yeh", "woh", "kar", "raha", "rahi", "rahe", "ho",
    "gaya", "gayi", "gaye", "kuch", "bahut", "bohot", "pe", "h", "thaa",
    "है", "हैं", "था", "थी", "थे", "के", "की", "का", "को", "से", "में", "पर",
    "और", "या", "भी", "यह", "वह", "कर", "रहा", "रही", "रहे", "हो", "गया", "गई", "गए",
    # Marathi
    "ahe", "aahe", "hota", "hoti", "hote", "chya", "cha", "chi", "che", "ani",
    "tar", "pan", "khup", "madhe", "var", "un",
    "आहे", "आहेत", "होता", "होती", "होते", "च्या", "चा", "ची", "चे", "आणि", "तर", "पण", "खूप", "मध्ये", "वर"
}

# Versioned Concept Equivalence Dictionary
# Maps language-specific terms/synonyms to a canonical CONCEPT_KEY
EQUIVALENCE_MAP: Dict[str, str] = {
    # WATER
    "water": "CONCEPT_WATER",
    "waterlogging": "CONCEPT_FLOOD",
    "waterlogged": "CONCEPT_FLOOD",
    "flooded": "CONCEPT_FLOOD",
    "flooding": "CONCEPT_FLOOD",
    "flood": "CONCEPT_FLOOD",
    "inundated": "CONCEPT_FLOOD",
    "inundation": "CONCEPT_FLOOD",
    "paani": "CONCEPT_WATER",
    "pani": "CONCEPT_WATER",
    "pania": "CONCEPT_WATER",
    "paanee": "CONCEPT_WATER",
    "jal": "CONCEPT_WATER",
    "neer": "CONCEPT_WATER",
    "jalbharav": "CONCEPT_FLOOD",
    "jalbhrav": "CONCEPT_FLOOD",
    "jalmay": "CONCEPT_FLOOD",
    "paniyat": "CONCEPT_FLOOD",
    "budale": "CONCEPT_FLOOD",
    "duba": "CONCEPT_FLOOD",
    "dooba": "CONCEPT_FLOOD",
    "पानी": "CONCEPT_WATER",
    "पाणी": "CONCEPT_WATER",
    "जल": "CONCEPT_WATER",
    "नीर": "CONCEPT_WATER",
    "जलभराव": "CONCEPT_FLOOD",
    "पूर": "CONCEPT_FLOOD",
    "पाण्यात": "CONCEPT_FLOOD",
    "बुडालं": "CONCEPT_FLOOD",
    "बुडाले": "CONCEPT_FLOOD",
    "जलमय": "CONCEPT_FLOOD",
    "डूब": "CONCEPT_FLOOD",
    "डूबा": "CONCEPT_FLOOD",

    # ROAD / THOROUGHFARE
    "road": "CONCEPT_ROAD",
    "street": "CONCEPT_ROAD",
    "lane": "CONCEPT_ROAD",
    "highway": "CONCEPT_ROAD",
    "avenue": "CONCEPT_ROAD",
    "rasta": "CONCEPT_ROAD",
    "raste": "CONCEPT_ROAD",
    "marg": "CONCEPT_ROAD",
    "sadak": "CONCEPT_ROAD",
    "galli": "CONCEPT_ROAD",
    "रस्ता": "CONCEPT_ROAD",
    "रस्ते": "CONCEPT_ROAD",
    "मार्ग": "CONCEPT_ROAD",
    "सड़क": "CONCEPT_ROAD",
    "सडक": "CONCEPT_ROAD",
    "गल्ली": "CONCEPT_ROAD",

    # BLOCKED / OBSTRUCTED
    "blocked": "CONCEPT_BLOCKED",
    "jammed": "CONCEPT_BLOCKED",
    "closed": "CONCEPT_BLOCKED",
    "choked": "CONCEPT_BLOCKED",
    "obstructed": "CONCEPT_BLOCKED",
    "stuck": "CONCEPT_BLOCKED",
    "bandh": "CONCEPT_BLOCKED",
    "band": "CONCEPT_BLOCKED",
    "jaam": "CONCEPT_BLOCKED",
    "jam": "CONCEPT_BLOCKED",
    "thapp": "CONCEPT_BLOCKED",
    "adakle": "CONCEPT_BLOCKED",
    "fasle": "CONCEPT_BLOCKED",
    "ruka": "CONCEPT_BLOCKED",
    "बंद": "CONCEPT_BLOCKED",
    "जाम": "CONCEPT_BLOCKED",
    "ठप्प": "CONCEPT_BLOCKED",
    "अडकले": "CONCEPT_BLOCKED",
    "अडकली": "CONCEPT_BLOCKED",
    "अवरुद्ध": "CONCEPT_BLOCKED",
    "फंस": "CONCEPT_BLOCKED",
    "फंसे": "CONCEPT_BLOCKED",

    # TREE
    "tree": "CONCEPT_TREE",
    "banyan": "CONCEPT_TREE",
    "gulmohar": "CONCEPT_TREE",
    "branch": "CONCEPT_TREE",
    "branches": "CONCEPT_TREE",
    "ped": "CONCEPT_TREE",
    "per": "CONCEPT_TREE",
    "jhad": "CONCEPT_TREE",
    "zaad": "CONCEPT_TREE",
    "vriksh": "CONCEPT_TREE",
    "झाड": "CONCEPT_TREE",
    "झाडे": "CONCEPT_TREE",
    "झाडाची": "CONCEPT_TREE",
    "झाडाच्या": "CONCEPT_TREE",
    "फांदी": "CONCEPT_TREE",
    "पेड़": "CONCEPT_TREE",
    "पेड": "CONCEPT_TREE",
    "वृक्ष": "CONCEPT_TREE",

    # FALL / COLLAPSE
    "fall": "CONCEPT_FALL",
    "fallen": "CONCEPT_FALL",
    "fell": "CONCEPT_FALL",
    "collapse": "CONCEPT_FALL",
    "collapsed": "CONCEPT_FALL",
    "uprooted": "CONCEPT_FALL",
    "gira": "CONCEPT_FALL",
    "giri": "CONCEPT_FALL",
    "padla": "CONCEPT_FALL",
    "padle": "CONCEPT_FALL",
    "kosalla": "CONCEPT_FALL",
    "kosalle": "CONCEPT_FALL",
    "पडले": "CONCEPT_FALL",
    "पडला": "CONCEPT_FALL",
    "कोसळले": "CONCEPT_FALL",
    "कोसळला": "CONCEPT_FALL",
    "उन्मुलित": "CONCEPT_FALL",
    "गिरा": "CONCEPT_FALL",
    "गिरी": "CONCEPT_FALL",
    "गिरे": "CONCEPT_FALL",

    # FLYOVER / BRIDGE
    "flyover": "CONCEPT_BRIDGE",
    "bridge": "CONCEPT_BRIDGE",
    "overpass": "CONCEPT_BRIDGE",
    "pul": "CONCEPT_BRIDGE",
    "pool": "CONCEPT_BRIDGE",
    "brij": "CONCEPT_BRIDGE",
    "पूल": "CONCEPT_BRIDGE",
    "पुल": "CONCEPT_BRIDGE",
    "पुलावर": "CONCEPT_BRIDGE",
    "पुलावरती": "CONCEPT_BRIDGE",
    "पूलावर": "CONCEPT_BRIDGE",
    "पुलाखाली": "CONCEPT_BRIDGE",
    "ब्रिज": "CONCEPT_BRIDGE",
    "फ्लायओव्हर": "CONCEPT_BRIDGE",

    # TRANSIT / PUBLIC TRANSPORT
    "bus": "CONCEPT_TRANSIT",
    "buses": "CONCEPT_TRANSIT",
    "local": "CONCEPT_TRANSIT",
    "train": "CONCEPT_TRANSIT",
    "depot": "CONCEPT_TRANSIT",
    "station": "CONCEPT_TRANSIT",
    "railway": "CONCEPT_TRANSIT",
    "st": "CONCEPT_TRANSIT",
    "गाडी": "CONCEPT_TRANSIT",
    "बस": "CONCEPT_TRANSIT",
    "ट्रेन": "CONCEPT_TRANSIT",
    "लोकल": "CONCEPT_TRANSIT",
    "रेल्वे": "CONCEPT_TRANSIT",
    "स्थानक": "CONCEPT_TRANSIT",
    "स्टेशन": "CONCEPT_TRANSIT",
    "आगार": "CONCEPT_TRANSIT",

    # TRAFFIC
    "traffic": "CONCEPT_TRAFFIC",
    "vahtuk": "CONCEPT_TRAFFIC",
    "vahan": "CONCEPT_TRAFFIC",
    "vehicular": "CONCEPT_TRAFFIC",
    "vehicles": "CONCEPT_TRAFFIC",
    "वाहतूक": "CONCEPT_TRAFFIC",
    "ट्रॅफिक": "CONCEPT_TRAFFIC",
    "ट्रैफिक": "CONCEPT_TRAFFIC",
    "गाड्या": "CONCEPT_TRAFFIC",
    "वाहने": "CONCEPT_TRAFFIC",

    # RAIN / STORM
    "rain": "CONCEPT_RAIN",
    "heavy rain": "CONCEPT_RAIN",
    "downpour": "CONCEPT_RAIN",
    "storm": "CONCEPT_RAIN",
    "barish": "CONCEPT_RAIN",
    "paus": "CONCEPT_RAIN",
    "varsha": "CONCEPT_RAIN",
    "पाऊस": "CONCEPT_RAIN",
    "मुसळधार": "CONCEPT_RAIN",
    "बारिश": "CONCEPT_RAIN",
    "वर्षा": "CONCEPT_RAIN",

    # LANDMARKS / LOCATIONS (Mumbai baseline)
    "dadar": "LOC_DADAR",
    "hindmata": "LOC_HINDMATA",
    "tt": "LOC_TT_CIRCLE",
    "circle": "LOC_TT_CIRCLE",
    "दादर": "LOC_DADAR",
    "हिंदमाता": "LOC_HINDMATA",
    "टीटी": "LOC_TT_CIRCLE",
    "सर्कल": "LOC_TT_CIRCLE",
    "bandra": "LOC_BANDRA",
    "वांद्रे": "LOC_BANDRA",
    "बांद्रा": "LOC_BANDRA",
    "kurla": "LOC_KURLA",
    "कुर्ला": "LOC_KURLA",
    "andheri": "LOC_ANDHERI",
    "अंधेरी": "LOC_ANDHERI",
    "bazaar": "LOC_MARKET",
    "bazar": "LOC_MARKET",
    "market": "LOC_MARKET",
    "बाजार": "LOC_MARKET",
    "मार्केट": "LOC_MARKET",
}


def normalize_text(text: str) -> str:
    """
    Applies Unicode NFKC normalization, strips punctuation, and standardizes casing.
    Preserves Devanagari script characters and Latin alphanumeric text.
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # 2. Lowercase (works across Latin and standard alphabets)
    text = text.lower()

    # 3. Replace punctuation and symbols with single space
    # Keep alphanumeric characters and Devanagari Unicode range (\u0900-\u097F)
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)

    # 4. Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str) -> List[str]:
    """Tokenizes normalized text into words."""
    norm = normalize_text(text)
    if not norm:
        return []
    return [w for w in norm.split() if w and w not in STOPWORDS]


def extract_canonical_concepts(text: str) -> Set[str]:
    """
    Extracts canonical concept keys and normalized content words from text.
    If a word maps to an EQUIVALENCE_MAP concept, the concept is emitted.
    Otherwise, the word itself is emitted (for named entities / landmarks).
    """
    tokens = tokenize(text)
    concepts: Set[str] = set()

    for token in tokens:
        if token in EQUIVALENCE_MAP:
            concepts.add(EQUIVALENCE_MAP[token])
        else:
            # Check prefix/suffix stripping for inflection (e.g. झाडाचे -> झाड, पुलावर -> पुल)
            matched = False
            for suffix in ["वरती", "वरून", "मध्ये", "खाली", "च्या", "चे", "ची", "चा", "वर", "ला", "ने", "par", "pe", "mein"]:
                if token.endswith(suffix) and len(token) > len(suffix) + 1:
                    base = token[:-len(suffix)]
                    if base in EQUIVALENCE_MAP:
                        concepts.add(EQUIVALENCE_MAP[base])
                        matched = True
                        break
            if not matched:
                for key, concept in EQUIVALENCE_MAP.items():
                    if len(key) >= 3 and (token.startswith(key) or key.startswith(token)):
                        concepts.add(concept)
                        matched = True
                        break
            if not matched:
                concepts.add(f"WORD_{token}")

    return concepts


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Computes Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    union = set_a.union(set_b)
    if not union:
        return 0.0
    intersection = set_a.intersection(set_b)
    return len(intersection) / len(union)
