"""
Shared content generation for all platform connectors.
Each connector imports this and applies platform-specific formatting + metadata.
"""
import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

# ── Topic bank ────────────────────────────────────────────────────────────────

TOPICS = [
    {
        "id": "fuel_prices",
        "display": "fuel price hike",
        "keywords": ["petrol", "diesel", "LPG", "fuel", "price hike", "oil"],
        "en": [
            "Petrol at ₹{price}/L now. Middle class is suffocating. #FuelPrice #India",
            "The {kw} situation is untenable. When does it end? #inflation",
            "₹{price} for a litre of petrol. How is a daily wage worker supposed to survive?",
            "New {kw} revision expected this week — markets watching closely 📊 #India",
            "Fuel prices up again. Public transport is the only way forward. #GreenIndia",
            "Does anyone else remember when {kw} was under ₹80? Asking for a friend 😬",
        ],
        "hi": [
            "पेट्रोल ₹{price} प्रति लीटर — आम आदमी पर बोझ बढ़ता जा रहा है। #MahangaiBadh",
            "{kw} की कीमत फिर बढ़ी। सरकार से सवाल — राहत कब मिलेगी?",
            "डीजल महंगा हो गया तो सब्जियां भी महंगी होंगी। किसान और ग्राहक दोनों परेशान।",
            "LPG सिलेंडर अब ₹{price2} का। खाना पकाना भी लग्जरी बन गया। #inflation",
            "तेल की कीमतें और रुपए की गिरावट — दोहरी मार पड़ रही है।",
        ],
        "ta": [
            "பெட்ரோல் விலை ₹{price} — சாமானியர்கள் கஷ்டப்படுகிறார்கள். #TamilNadu",
            "{kw} விலை உயர்வை நாங்கள் ஏற்க மாட்டோம். #protest",
            "டீசல் விலை ஏறினால் விவசாயிகளுக்கு பாதிப்பு அதிகம்.",
        ],
        "te": [
            "{kw} ధరలు పెరిగాయి. సామాన్య ప్రజలకు చాలా కష్టం. #Andhra",
            "పెట్రోల్ ₹{price} — ఇది భరించడం చాలా కష్టం.",
        ],
    },
    {
        "id": "ai_regulation",
        "display": "AI regulation",
        "keywords": ["AI policy", "artificial intelligence", "tech regulation", "data privacy", "deepfake"],
        "en": [
            "India's proposed AI regulation framework is ambitious but needs teeth. Thread 🧵 #AIPolicy",
            "The {kw} bill is missing key provisions on algorithmic accountability. #TechPolicy",
            "Should AI systems used in govt decisions be auditable? Absolutely yes. #AIGovernance",
            "Deepfake detection mandates in the new {kw} draft — finally. #DigitalIndia",
            "Global AI governance is fragmenting. India needs its own robust framework ASAP.",
            "Excited about India's AI compute initiative. This could be a game-changer for startups 🚀",
            "The {kw} consultation paper is out. Key ask: include civil society in the process.",
        ],
        "hi": [
            "AI नीति पर सरकार का नया मसौदा आया। क्या इसमें पर्याप्त सुरक्षा है? #AIPolicy",
            "{kw} से भारतीय IT क्षेत्र पर क्या असर पड़ेगा? विशेषज्ञों की राय जानिए।",
            "डीपफेक और AI का दुरुपयोग रोकने के लिए कड़े कानून जरूरी हैं।",
            "डेटा गोपनीयता और {kw} — दोनों एक साथ चाहिए।",
        ],
        "ta": [
            "AI கொள்கை வரைவு வந்தது. தமிழ்நாட்டின் IT துறைக்கு நன்மையா? #TechPolicy",
            "{kw} குறித்த கலந்தாய்வு தேவை. மக்கள் கருத்தை கேட்க வேண்டும்.",
        ],
        "te": [
            "AI విధానం పై చర్చ అవసరం. సాంకేతికత మరియు భద్రత రెండూ ముఖ్యం.",
            "{kw} నియంత్రణ — భారత్‌కు మంచి అవకాశం.",
        ],
    },
    {
        "id": "agriculture_msp",
        "display": "agriculture MSP",
        "keywords": ["MSP", "kisan", "farmer", "crop price", "procurement", "Rabi", "Kharif"],
        "en": [
            "MSP hike for {kw} — welcome but still below cost of production for many farmers.",
            "Farmer protest update: {kw} demands still unmet after 3 rounds of talks. #KisanAndolan",
            "The agriculture sector needs more than just MSP. Storage, credit, insurance — all broken.",
            "New procurement targets announced. Will they actually be met this season? #farmers",
            "Small and marginal farmers are left out of the {kw} system entirely. Fix this first.",
        ],
        "hi": [
            "{kw} बढ़ाने की मांग — किसानों को इससे कितना फायदा? 🌾 #KisanAndolan",
            "रबी फसल की MSP घोषणा हुई लेकिन असली समस्या खरीद की है। #annadata",
            "किसान कर्ज माफी और {kw} गारंटी — ये दोनों जरूरी हैं।",
            "सरकारी खरीद केंद्र समय पर नहीं खुले। किसान परेशान। #farming",
            "खेती की लागत बढ़ी, {kw} नहीं। यही असली संकट है।",
        ],
        "ta": [
            "விவசாயிகளுக்கு {kw} உறுதி வேண்டும். #Farmers #TamilNadu",
            "நெல் கொள்முதல் தாமதம் — விவசாயிகள் கஷ்டத்தில் உள்ளனர்.",
        ],
        "te": [
            "రైతులకు {kw} హామీ ఇవ్వాలి. #Farmers #Andhra",
            "పంట కొనుగోలు జాప్యం — రైతులు నష్టపోతున్నారు.",
        ],
    },
    {
        "id": "ev_policy",
        "display": "EV policy",
        "keywords": ["electric vehicle", "EV", "subsidy", "charging station", "green energy", "FAME"],
        "en": [
            "FAME III subsidy framework looks good but charging infra is still a bottleneck. #EV #GreenIndia",
            "My city has 3 EV charging stations for the entire district. The {kw} push needs matching infra.",
            "Two-wheeler EV adoption in India is genuinely impressive. 3.8M units this year 🔋",
            "Battery swapping vs. fast charging debate continues. {kw} policy needs to pick a lane.",
            "PLI scheme for EV batteries — this is how you build domestic manufacturing capacity. 🇮🇳",
            "The {kw} subsidy cut hurt small EV makers more than Chinese imports. Policy fail.",
        ],
        "hi": [
            "इलेक्ट्रिक वाहन नीति अच्छी है लेकिन चार्जिंग स्टेशन नहीं हैं। #EVIndia",
            "{kw} सब्सिडी से मध्यम वर्ग को सबसे ज्यादा फायदा होगा।",
            "दिल्ली में EV टैक्सी चलाना अब फायदेमंद है। बाकी शहरों में कब? #CleanAir",
            "FAME योजना का दूसरा चरण — क्या इसका लाभ आम आदमी को मिलेगा?",
        ],
        "ta": [
            "மின்சார வாகன கொள்கை சிறப்பாக உள்ளது. ஆனால் உள்கட்டமைப்பு தேவை. #EV",
            "{kw} மானியம் விரிவுபடுத்த வேண்டும்.",
        ],
        "te": [
            "ఎలక్ట్రిక్ వాహన విధానం మంచిది. కానీ చార్జింగ్ కేంద్రాలు అవసరం. #EV",
        ],
    },
    {
        "id": "education_reform",
        "display": "education reform",
        "keywords": ["NEP", "board exam", "university", "fee hike", "scholarship", "curriculum"],
        "en": [
            "NEP 2020 implementation is uneven across states. {kw} needs uniform execution. #Education",
            "Board exam results out. 40% pass rate in some districts — systemic failure, not student failure.",
            "University fee hike protest: students demand {kw} rollback and more scholarships. #StudentRights",
            "The new {kw} curriculum is strong on skills but light on critical thinking. Balance needed.",
            "Private school fees up 25% in 3 years. Education is becoming unaffordable. #edtech #India",
            "State board vs CBSE — the disparity in quality and recognition needs policy attention urgently.",
        ],
        "hi": [
            "NEP 2020 अच्छा है लेकिन सरकारी स्कूलों की हालत पहले सुधारनी होगी। #शिक्षा",
            "{kw} में बदलाव स्वागतयोग्य — लेकिन शिक्षकों को प्रशिक्षण दो पहले।",
            "परीक्षा परिणाम आए। कई बच्चे फेल — व्यवस्था पर सवाल उठाने का वक्त है।",
            "छात्रवृत्ति की राशि बहुत कम है। {kw} फीस के साथ तालमेल बिठाना जरूरी।",
            "सरकारी कॉलेज में फीस बढ़ोतरी के खिलाफ छात्रों का प्रदर्शन। #StudentProtest",
        ],
        "ta": [
            "NEP கல்வி சீர்திருத்தம் — தமிழ்நாட்டில் எப்படி நடைமுறைப்படுத்தப்படும்? #Education",
            "{kw} கட்டணம் உயர்வு — மாணவர்கள் எதிர்ப்பு தெரிவிக்கிறார்கள்.",
        ],
        "te": [
            "విద్యా సంస్కరణలు మంచివే. అమలు ముఖ్యం. #Education",
        ],
    },
    {
        "id": "healthcare",
        "display": "healthcare policy",
        "keywords": ["Ayushman Bharat", "hospital", "medicine price", "insurance", "PMJAY", "generic drugs"],
        "en": [
            "Ayushman Bharat coverage gap: 40% of beneficiaries can't find empanelled hospitals nearby.",
            "Generic drug pricing reform is long overdue. {kw} profiteering must be regulated. #Health",
            "PMJAY cashless claim rejections hit 23% — beneficiaries stranded at hospitals. Fix this.",
            "Mental health is still not covered under most {kw} schemes. This needs to change. #MentalHealth",
            "Rural primary health centres are understaffed by 62%. No amount of {kw} helps without doctors.",
        ],
        "hi": [
            "आयुष्मान भारत अच्छी योजना है लेकिन अस्पताल सहयोग नहीं करते। #Ayushman",
            "{kw} की कीमतें आसमान छू रही हैं। जेनेरिक दवाओं को बढ़ावा दो।",
            "सरकारी अस्पतालों में डॉक्टर नहीं। {kw} बीमा किस काम का?",
            "मानसिक स्वास्थ्य को भी बीमा में शामिल करो। #MentalHealth #India",
        ],
        "ta": [
            "ஆயுஷ்மான் பாரத் திட்டம் நல்லது. ஆனால் மருத்துவமனைகள் ஒத்துழைக்க வேண்டும். #Health",
            "{kw} விலை குறைக்க வேண்டும். ஏழை மக்களுக்கு அணுகல் தேவை.",
        ],
        "te": [
            "ఆయుష్మాన్ భారత్ మంచి పథకం. అమలులో సమస్యలు తొలగించాలి. #Health",
        ],
    },
    {
        "id": "employment",
        "display": "employment & jobs",
        "keywords": ["unemployment", "job vacancy", "skill India", "startup", "EPFO", "gig workers"],
        "en": [
            "Youth unemployment at 23.2% — no amount of {kw} spin changes this number. #Jobs",
            "Gig worker protections still absent in the new labour codes. Platform companies must be held accountable.",
            "Skill India mission: certificates issued, jobs not so much. Time for outcome-based {kw} metrics.",
            "Startup ecosystem looking strong — 115 unicorns but where are the jobs for non-engineers?",
            "EPFO data shows formal employment is growing but informal economy is still huge. Context matters.",
            "State govt recruitment freeze hits hundreds of thousands of aspirants. {kw} crisis is real.",
        ],
        "hi": [
            "युवा बेरोजगारी पर सरकार को गंभीर होना होगा। {kw} के आंकड़े चिंताजनक। #Rozgar",
            "गिग वर्कर्स को कोई सामाजिक सुरक्षा नहीं। नीति बनाओ।",
            "सरकारी नौकरी न हो तो क्या? {kw} में अवसर ढूंढने होंगे। #startupIndia",
            "EPFO पंजीकरण बढ़ा — रोजगार बढ़ा नहीं। फर्क समझना जरूरी।",
            "स्किल इंडिया प्रमाणपत्र मिले, नौकरी नहीं। {kw} की असली परीक्षा अब होगी।",
        ],
        "ta": [
            "வேலையின்மை சதவீதம் அதிகரிக்கிறது. {kw} திட்டங்கள் பலனளிக்கிறதா? #Jobs",
            "இளைஞர்களுக்கு தொழில் வாய்ப்புகள் தேவை. #YouthEmployment",
        ],
        "te": [
            "నిరుద్యోగ సమస్య తీవ్రంగా ఉంది. {kw} పరిష్కారాలు అవసరం. #Jobs",
        ],
    },
]

GEO_HINTS = [
    "Delhi", "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Kolkata",
    "Lucknow", "Pune", "Jaipur", "Ahmedabad", "Bhopal", "Patna",
    "Surat", "Visakhapatnam", "Kochi", "Chandigarh", "Indore", "Nagpur",
    None, None, None,  # ~15% no geo
]

# Per-platform language distribution
LANG_DIST = {
    "twitter":   {"en": 0.55, "hi": 0.28, "ta": 0.09, "te": 0.08},
    "telegram":  {"en": 0.30, "hi": 0.45, "ta": 0.14, "te": 0.11},
    "instagram": {"en": 0.52, "hi": 0.30, "ta": 0.10, "te": 0.08},
    "reddit":    {"en": 0.82, "hi": 0.10, "ta": 0.04, "te": 0.04},
    "youtube":   {"en": 0.45, "hi": 0.38, "ta": 0.10, "te": 0.07},
    "facebook":  {"en": 0.28, "hi": 0.42, "ta": 0.16, "te": 0.14},
}

# Per-platform topic bias (weights for topic selection)
TOPIC_BIAS = {
    "twitter":   [0.20, 0.20, 0.12, 0.15, 0.16, 0.09, 0.08],  # news/political heavy
    "telegram":  [0.15, 0.15, 0.20, 0.10, 0.15, 0.14, 0.11],  # agricultural/health heavy
    "instagram": [0.18, 0.18, 0.08, 0.20, 0.18, 0.08, 0.10],  # EV/education/fuel heavy
    "reddit":    [0.14, 0.28, 0.10, 0.18, 0.16, 0.07, 0.07],  # AI/EV/education heavy
    "youtube":   [0.22, 0.14, 0.16, 0.12, 0.14, 0.12, 0.10],  # fuel/agriculture heavy
    "facebook":  [0.16, 0.08, 0.22, 0.10, 0.12, 0.20, 0.12],  # agriculture/health heavy
}


def author_hash(platform: str, user_seed: str, daily_salt: str = "2026") -> str:
    raw = f"{daily_salt}:{platform}:{user_seed}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def pick_topic(platform: str, rng: random.Random) -> dict:
    weights = TOPIC_BIAS.get(platform, [1 / len(TOPICS)] * len(TOPICS))
    return rng.choices(TOPICS, weights=weights, k=1)[0]


def pick_language(platform: str, rng: random.Random) -> str:
    dist = LANG_DIST.get(platform, {"en": 0.6, "hi": 0.3, "ta": 0.1})
    return rng.choices(list(dist.keys()), weights=list(dist.values()), k=1)[0]


def render_template(template: str, topic: dict, rng: random.Random) -> str:
    price = rng.randint(94, 116)
    price2 = rng.randint(850, 1050)
    kw = rng.choice(topic["keywords"])
    return template.format(kw=kw, price=price, price2=price2)


def generate_content(platform: str, rng: random.Random) -> tuple[str, str, str]:
    """Returns (content, language, topic_id)."""
    topic = pick_topic(platform, rng)
    lang = pick_language(platform, rng)
    templates = topic.get(lang, topic.get("en", []))
    if not templates:
        templates = topic["en"]
    raw = render_template(rng.choice(templates), topic, rng)
    return raw, lang, topic["id"]
