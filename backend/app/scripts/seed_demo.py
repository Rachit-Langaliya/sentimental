"""
Demo data seeder — Phase A (Enhanced).

Populates the database with ~15 000 realistic posts, NLP results, topics,
trends, segments, and personas. Safe to run multiple times (idempotent).

Usage:
    python -m app.scripts.seed_demo
"""
from __future__ import annotations

import asyncio
import hashlib
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.models import (
    DemographicSegment,
    Persona,
    Platform,
    PostNLP,
    PostTopic,
    RawPost,
    Topic,
    Trend,
)

RNG = random.Random(2026)

# ── Topics ────────────────────────────────────────────────────────────────────

TOPICS = [
    "fuel_prices", "agriculture_msp", "ev_adoption", "education",
    "healthcare", "taxation_gst", "infrastructure", "environment",
    "ai_technology", "social_welfare", "employment", "digital_india",
]

_TOPIC_WEIGHTS = {
    "fuel_prices":     0.16,
    "agriculture_msp": 0.13,
    "ev_adoption":     0.09,
    "education":       0.11,
    "healthcare":      0.11,
    "taxation_gst":    0.07,
    "infrastructure":  0.09,
    "environment":     0.08,
    "ai_technology":   0.05,
    "social_welfare":  0.05,
    "employment":      0.04,
    "digital_india":   0.02,
}

_SENTIMENT_BIAS: dict[str, float] = {
    "fuel_prices":     -0.30,
    "agriculture_msp": +0.20,
    "ev_adoption":     +0.25,
    "education":       +0.15,
    "healthcare":      +0.18,
    "taxation_gst":    -0.20,
    "infrastructure":  +0.22,
    "environment":     -0.15,
    "ai_technology":   +0.10,
    "social_welfare":  +0.25,
    "employment":      -0.08,
    "digital_india":   +0.20,
}

# ── Content templates ─────────────────────────────────────────────────────────

_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "fuel_prices": {
        "en": [
            "Petrol prices up again — when will it stop?",
            "Fuel hike is killing small businesses and daily commuters.",
            "Diesel prices at record high. Government must intervene now.",
            "Every week a new fuel price increase. Middle class is suffering.",
            "LPG cylinder cost has doubled in two years. Completely unacceptable.",
            "Rising fuel costs are driving up the price of everything we buy.",
            "Petrol at ₹105/litre in my city. Completely unsustainable for daily use.",
            "Auto drivers are struggling with rising CNG prices. Who will help them?",
            "Why does India have some of the highest fuel taxes in Asia?",
            "Fuel hike will push food inflation even higher. Brace yourselves.",
            "Reduce excise duty on petrol. It's that simple.",
            "Small transporters are shutting down because of diesel prices. #FuelHike",
            "International crude is down but domestic prices stay high. Explain this.",
            "Cooking gas at ₹950 — how is a daily wage worker supposed to manage?",
            "Petrol price hike reversed in election season, raised after. Classic cycle.",
            "Farmers hit double — high diesel for tractors, high transport costs for crops.",
            "EV adoption can't come fast enough given these fuel prices.",
            "If the government can subsidise rich companies, why not fuel for the poor?",
            "Real inflation = fuel prices × everything else. Fix this first.",
            "₹100+ petrol and ₹900+ LPG in the same month. My budget is destroyed.",
            "The VAT state governments collect on fuel is also a problem, not just Centre.",
            "Truck unions planning a strike over diesel prices. Supply chains at risk.",
        ],
        "hi": [
            "पेट्रोल की कीमतें फिर बढ़ीं, आम आदमी कहाँ जाए?",
            "डीजल इतना महंगा हो गया है कि ट्रकिंग कारोबार चौपट हो रहा है।",
            "एलपीजी सिलेंडर ₹900 पार — सरकार कब जागेगी?",
            "ईंधन की बढ़ती कीमतें महंगाई की असली वजह हैं।",
            "पेट्रोल-डीजल पर टैक्स कम करो, जनता राहत चाहती है।",
            "रोज़ की कमाई का बड़ा हिस्सा पेट्रोल में जा रहा है।",
            "खाना पकाने का गैस सिलेंडर ₹900 से ऊपर — गरीब परिवार क्या करें?",
            "किसान ट्रैक्टर चलाने के लिए डीजल नहीं खरीद पा रहे।",
            "सरकार को उत्पाद शुल्क कम करके राहत देनी चाहिए।",
            "दिल्ली में पेट्रोल ₹96 और मुंबई में ₹106 — यह कहाँ तक जाएगा?",
            "बस, ऑटो, टैक्सी वाले सभी परेशान हैं ईंधन महंगाई से।",
            "महंगाई कम करनी है तो पहले ईंधन की कीमत कम करो।",
            "चुनाव में सस्ता, चुनाव के बाद महंगा — यह खेल बंद होना चाहिए।",
            "इंटरनेशनल कच्चा तेल सस्ता होने पर भी भारत में कीमत नहीं घटती।",
            "मध्यम वर्ग बर्बाद हो रहा है पेट्रोल-डीजल की कीमतों से।",
        ],
        "ta": [
            "பெட்ரோல் விலை மீண்டும் உயர்ந்தது — மக்கள் கஷ்டப்படுகிறார்கள்.",
            "இந்த விலை உயர்வை அரசு கட்டுப்படுத்தணும்.",
            "எல்பிஜி சிலிண்டர் விலை ₹900 தாண்டியது, எல்லோரும் கஷ்டப்படுகிறோம்.",
            "பெட்ரோல் விலை குறைக்க வேண்டும், மக்கள் கோரிக்கை.",
            "டீசல் விலை அதிகரிப்பால் போக்குவரத்து கட்டணம் உயர்கிறது.",
            "அரசு உற்பத்தி வரி குறைத்தால் பெட்ரோல் விலை குறையும்.",
            "சிறு வணிகர்களுக்கு எரிபொருள் விலை உயர்வு பெரிய சுமை.",
            "சர்வதேச கச்சா எண்ணெய் விலை குறைந்தாலும் உள்நாட்டில் குறையவில்லை.",
        ],
        "te": [
            "పెట్రోల్ ధరలు మళ్ళీ పెరిగాయి — ప్రభుత్వం జోక్యం చేసుకోవాలి.",
            "వంట గ్యాస్ సిలిండర్ ₹900 దాటింది, సామాన్యులకు చాలా కష్టం.",
            "డీజిల్ ధర పెరగడంతో రవాణా ఖర్చులు పెరిగాయి.",
            "పెట్రోలు, డీజిల్ పై పన్ను తగ్గించాలని ప్రజలు కోరుతున్నారు.",
            "అంతర్జాతీయ చమురు ధర తగ్గినా మన దేశంలో తగ్గట్లేదు, ఎందుకు?",
            "ట్రక్కు డ్రైవర్లు డీజిల్ ధర పెరగడంతో నష్టపోతున్నారు.",
        ],
        "bn": [
            "পেট্রোলের দাম আবার বাড়ল — সাধারণ মানুষ কোথায় যাবে?",
            "রান্নার গ্যাসের দাম ৯০০ টাকা ছাড়াল, গরিবরা কী করবে?",
            "ডিজেলের দাম বাড়ায় পরিবহন ভাড়া বেড়েছে।",
            "সরকার উৎপাদন শুল্ক কমালে জ্বালানির দাম কমবে।",
            "আন্তর্জাতিক বাজারে দাম কমলেও দেশে কমে না — কেন?",
        ],
        "mr": [
            "पेट्रोलचे भाव पुन्हा वाढले — सामान्य माणसाची कंबर मोडली.",
            "एलपीजी सिलिंडर ₹९०० पार — सरकार लक्ष द्या.",
            "डिझेलच्या भाववाढीने वाहतूकदार त्रस्त आहेत.",
            "इंधन दरवाढ थांबवण्यासाठी सरकारने कर कमी करावेत.",
        ],
        "gu": [
            "પેટ્રોલ ફરી મોંઘું — ઘર ચલાવવું મુશ્કેલ થઈ ગયું.",
            "LPG સિલિન્ડર ₹900 થી વધ્યો, સરકારે ઘ્યાન આપવું જોઇએ.",
            "ડીઝલ મોંઘું હોવાથી ટ્રાન્સપોર્ટ ખર્ચ વધ્યો.",
            "ઈંધણ પર ટેક્સ ઘટાડો — સામાન્ય માણસ પ્રાર્થે છે.",
        ],
    },
    "agriculture_msp": {
        "en": [
            "Government increases MSP for wheat — good news for farmers.",
            "Kisan credit card scheme helping rural households access credit.",
            "PM-KISAN transfer received in my account. Thank you government.",
            "Farmer protests easing as MSP guarantee bill progresses.",
            "Crop insurance scheme coverage expanded to more districts.",
            "Direct benefit transfers reaching farmers faster now.",
            "MSP hike alone isn't enough — we need guaranteed procurement.",
            "Kisan sabha demanding legal guarantee for MSP. Completely justified.",
            "Procurement centres too far from villages. Last-mile connectivity needed.",
            "Cold storage infrastructure needs massive investment in rural areas.",
            "Pulses and oilseed MSP hike welcomed by farmers in Maharashtra.",
            "Drip irrigation subsidy scheme helping conserve water and improve yield.",
            "Soil health card scheme: farmers need more awareness about using it.",
            "Crop diversification incentives will help reduce farmer over-dependence on wheat.",
            "PM-KISAN ₹6000/year is not enough given rising input costs.",
            "Organic farming certification process is too slow. Needs to be simplified.",
            "Agri-tech startups working with farmers are a positive development.",
            "Mandi reform essential for farmers to get fair prices directly.",
            "Free power for agriculture should be replaced with direct subsidy to avoid waste.",
            "Kisan Drones scheme announcement is promising for precision farming.",
        ],
        "hi": [
            "एमएसपी बढ़ोतरी से किसानों को राहत मिलेगी।",
            "पीएम किसान योजना का पैसा खाते में आ गया।",
            "फसल बीमा योजना में सुधार का स्वागत है।",
            "किसान क्रेडिट कार्ड से खेती में मदद मिल रही है।",
            "सरकारी खरीद केंद्र गांव के पास खुले, सुविधा हुई।",
            "एमएसपी की कानूनी गारंटी मिलनी चाहिए, यही असली माँग है।",
            "ड्रिप सिंचाई सब्सिडी से पानी की बचत और उपज में सुधार।",
            "कोल्ड स्टोरेज सुविधाएं बढ़नी चाहिए गाँवों के पास।",
            "मंडी में बिचौलियों का राज खत्म होना चाहिए।",
            "डिजिटल मंडी से सीधे खरीदार मिल रहे हैं, अच्छी पहल।",
            "पीएम किसान की राशि ₹6000 से बढ़ानी चाहिए।",
            "ऑर्गेनिक खेती के लिए सर्टिफिकेशन आसान बनाएं।",
            "फसल बीमा का दावा जल्दी मिलना चाहिए।",
            "सोयाबीन और दलहन पर एमएसपी बढ़ाने से महाराष्ट्र के किसान खुश।",
        ],
        "ta": [
            "MSP உயர்வு விவசாயிகளுக்கு நல்ல செய்தி.",
            "பிரதம மந்திரி கிசான் திட்டம் கிராமங்களுக்கு உதவுகிறது.",
            "பயிர் காப்பீடு திட்டம் மேலும் மாவட்டங்களுக்கு விரிவாக்கப்பட்டது.",
            "நேரடி சேமிப்பு குளிர்பதனக் கிடங்கு விவசாயிகளுக்கு அவசியம்.",
            "MSP சட்டப் பாதுகாப்பு வேண்டும் என்பது நியாயமான கோரிக்கை.",
            "தொட்டு பாசன மானியம் தண்ணீர் சேமிக்க உதவுகிறது.",
            "மந்தி சீர்திருத்தம் விவசாயிகளுக்கு நேரடி விலை கிடைக்க உதவும்.",
        ],
        "te": [
            "వ్యవసాయదారులకు MSP పెంచడం మంచి నిర్ణయం.",
            "కిసాన్ పథకం ద్వారా రైతులకు ప్రత్యక్ష సహాయం.",
            "పంట బీమా పథకం మరింత జిల్లాలకు విస్తరించబడింది.",
            "MSP చట్టపరమైన హామీ కావాలి అని రైతులు డిమాండ్ చేస్తున్నారు.",
            "కోల్డ్ స్టోరేజ్ సౌకర్యాలు పల్లెలకు దగ్గరగా అవసరం.",
            "డ్రిప్ ఇరిగేషన్ సబ్సిడీ నీటి వినియోగం తగ్గించడంలో సహాయపడుతోంది.",
        ],
        "bn": [
            "MSP বৃদ্ধি কৃষকদের জন্য সুখবর।",
            "PM Kisan প্রকল্প গ্রামীণ পরিবারগুলিকে সাহায্য করছে।",
            "ফসল বীমা প্রকল্প আরও জেলায় প্রসারিত হয়েছে।",
            "কোল্ড স্টোরেজ সুবিধা গ্রামের কাছে প্রয়োজন।",
            "MSP আইনগত গ্যারান্টি দাবি ন্যায্য।",
        ],
        "mr": [
            "एमएसपी वाढ शेतकऱ्यांसाठी दिलासा आहे.",
            "पीएम किसान योजनेची रक्कम खात्यात जमा झाली.",
            "शेतमाल विमा योजना अधिक जिल्ह्यांमध्ये लागू होणे आवश्यक.",
            "एमएसपीची कायदेशीर हमी मिळावी ही रास्त मागणी.",
        ],
        "gu": [
            "MSP વધારો ખેડૂતો માટે રાહત.",
            "PM Kisan યોજનાની રકમ ખાતામાં આવી.",
            "પાક વીમા યોજના વધુ જિલ્લામાં વિસ્તૃત.",
            "MSP ની કાનૂની ગેરંટી જોઇએ — ખેડૂતોની ન્યાયી માગ.",
        ],
    },
    "ev_adoption": {
        "en": [
            "EV subsidies announced — great step towards clean transport.",
            "Charging infrastructure needs massive expansion in tier-2 cities.",
            "Electric scooter sales up 300% this year. India going green!",
            "Government PLI scheme boosting domestic EV manufacturing.",
            "Battery swapping stations rollout will accelerate EV adoption.",
            "Electric buses in city transport reducing pollution significantly.",
            "EV loan interest subsidy makes buying an EV more affordable now.",
            "Ola Electric IPO a sign of India's EV confidence. Exciting times.",
            "Range anxiety is real — more charging points needed on highways.",
            "EV two-wheelers are now competitive with petrol bikes on TCO.",
            "State govt offering ₹10k additional rebate on EV purchase. Smart move.",
            "Fleet operators switching to EVs for delivery. Good for environment.",
            "Battery recycling policy needed alongside EV push. Think full lifecycle.",
            "Green number plates for EVs is a good incentive for early adopters.",
            "FAME-III scheme should focus more on public transport EVs.",
            "Home charging overnight is the killer advantage of EV ownership.",
            "Tata Nexon EV now under ₹15L after subsidy. Very accessible.",
            "EV 2-wheeler running cost ₹0.5/km vs petrol ₹3/km. No contest.",
            "Need more EV-friendly apartment complex charging policies.",
            "100% EV target for government fleets by 2030 is ambitious but right.",
        ],
        "hi": [
            "इलेक्ट्रिक वाहन सब्सिडी से बाजार में तेजी आएगी।",
            "चार्जिंग स्टेशनों की संख्या बढ़ानी होगी टियर-2 शहरों में।",
            "ई-बस से शहरों की हवा साफ होगी।",
            "ओला इलेक्ट्रिक की बिक्री रिकॉर्ड स्तर पर — भारत आगे बढ़ रहा है।",
            "इलेक्ट्रिक स्कूटर की रनिंग कॉस्ट पेट्रोल से बहुत कम है।",
            "सरकारी PLI योजना से घरेलू EV उत्पादन बढ़ेगा।",
            "बैटरी स्वैपिंग से रेंज एंजाइटी खत्म होगी।",
            "राजमार्गों पर चार्जिंग स्टेशन जरूरी हैं।",
            "घर पर रात में चार्ज — यही EV की सबसे बड़ी सुविधा है।",
        ],
        "ta": [
            "EV மானியம் சுத்தமான போக்குவரத்துக்கு நல்ல அடி.",
            "நகர போக்குவரத்தில் மின்சார பேருந்துகள் மாசை குறைக்கும்.",
            "ஆண்டுக்கு 300% EV இரு சக்கர வாகன விற்பனை — இந்தியா முன்னேறுகிறது.",
            "சார்ஜிங் உள்கட்டமைப்பை இரண்டாம் நிலை நகரங்களில் விரிவாக்க வேண்டும்.",
            "EV இரு சக்கர வாகனங்கள் இப்போது மிகவும் மலிவானவை.",
        ],
        "te": [
            "EV సబ్సిడీలు స్వచ్ఛమైన రవాణా దిశలో మంచి అడుగు.",
            "ఎలక్ట్రిక్ బస్సులు నగరాల్లో కాలుష్యాన్ని తగ్గిస్తున్నాయి.",
            "చార్జింగ్ స్టేషన్ల సంఖ్య పెంచాలి.",
            "EV రన్నింగ్ కాస్ట్ పెట్రోల్ కంటే చాలా తక్కువ.",
        ],
    },
    "education": {
        "en": [
            "NEP 2020 implementation bringing multilingual learning opportunities.",
            "Digital classroom scheme reaching remote villages at last.",
            "School dropout rate falling under new education reforms.",
            "Scholarship scheme helping first-generation college students.",
            "STEM labs in government schools — a positive change.",
            "Mid-day meal improvement helping attendance rates rise.",
            "National education policy pushing skill-based learning is the right direction.",
            "Teacher training must keep pace with NEP reforms.",
            "CUET exam helping standardise college admissions across states.",
            "Rural schools need better infrastructure, not just policy changes.",
            "Higher education fee regulation needed to control costs.",
            "IIT expansion to more states is a welcome step.",
            "Board exam stress is killing curiosity. Reform needed urgently.",
            "Open schooling options for working youth are underpublicised.",
            "Coding in schools from Class 6 is a great move.",
            "Library access in government schools still woefully inadequate.",
            "PM-VIDYA scheme bridging digital divide in education.",
            "Quality of government school education varies too much state to state.",
            "Community college concept should be adopted in India.",
            "PhDs in India take too long. Structural reform needed.",
        ],
        "hi": [
            "नई शिक्षा नीति से बच्चों को मातृभाषा में पढ़ाई का मौका मिलेगा।",
            "डिजिटल शिक्षा दूरदराज के गांवों तक पहुँच रही है।",
            "छात्रवृत्ति योजना से गरीब परिवारों के बच्चों को फायदा।",
            "सरकारी स्कूलों में बुनियादी ढांचे में सुधार जरूरी है।",
            "मिड-डे मील सुधार से उपस्थिति बढ़ रही है।",
            "STEM लैब सरकारी स्कूलों में — बदलाव दिख रहा है।",
            "बोर्ड परीक्षा का तनाव कम होना चाहिए, NEP सही दिशा में है।",
            "शिक्षक प्रशिक्षण NEP के साथ कदम से कदम मिलाना चाहिए।",
            "IIT का विस्तार अधिक राज्यों में — स्वागतयोग्य कदम।",
            "सरकारी विश्वविद्यालयों में फीस नियंत्रण जरूरी।",
            "कोडिंग कक्षा 6 से शुरू — भविष्य के लिए सही कदम।",
        ],
        "bn": [
            "নতুন শিক্ষানীতিতে মাতৃভাষায় পড়াশোনার সুযোগ।",
            "ডিজিটাল শ্রেণীকক্ষ প্রকল্প গ্রামে পৌঁছাচ্ছে।",
            "বৃত্তি প্রকল্প প্রথম প্রজন্মের কলেজ পড়ুয়াদের সাহায্য করছে।",
            "সরকারি স্কুলে অবকাঠামো উন্নয়ন দরকার।",
            "স্টেম ল্যাব সরকারি স্কুলে — ইতিবাচক পরিবর্তন।",
        ],
        "ta": [
            "புதிய கல்வி கொள்கை மாதுரிமொழியில் கல்வி வாய்ப்பளிக்கிறது.",
            "டிஜிட்டல் வகுப்பறை திட்டம் தொலை கிராமங்களை எட்டுகிறது.",
            "உதவித்தொகை திட்டம் முதல் தலைமுறை மாணவர்களுக்கு உதவுகிறது.",
            "STEM ஆய்வகங்கள் அரசுப் பள்ளிகளில் — நல்ல மாற்றம்.",
            "ஆசிரியர் பயிற்சி NEP சீர்திருத்தங்களுடன் ஒத்துப்போக வேண்டும்.",
        ],
        "te": [
            "కొత్త విద్యా విధానం మాతృభాషలో చదువుకొనే అవకాశాన్ని అందిస్తోంది.",
            "డిజిటల్ తరగతి గది పథకం మారుమూల గ్రామాలను చేరుతోంది.",
            "స్కాలర్‌షిప్ పథకం మొదటి తరం కాలేజీ విద్యార్థులకు సహాయపడుతోంది.",
            "STEM ల్యాబ్‌లు ప్రభుత్వ పాఠశాలల్లో — మంచి మార్పు.",
        ],
        "mr": [
            "नवीन शिक्षण धोरण मातृभाषेतून शिक्षणाची संधी देते.",
            "डिजिटल वर्गखोली उपक्रम दुर्गम गावांपर्यंत पोहोचत आहे.",
            "शिष्यवृत्ती योजनेचा पहिल्या पिढीतील विद्यार्थ्यांना फायदा.",
            "STEM प्रयोगशाळा सरकारी शाळांमध्ये — सकारात्मक बदल.",
        ],
    },
    "healthcare": {
        "en": [
            "Ayushman Bharat coverage extended to 10 crore more families.",
            "Jan Aushadhi stores providing medicines at affordable prices.",
            "Mental health helpline usage increasing — awareness growing.",
            "New AIIMS in tier-2 cities will reduce medical travel burden.",
            "Vaccination drive successful — polio-free India milestone maintained.",
            "Generic medicines policy saving patients thousands annually.",
            "Primary health centres need more doctors, not just buildings.",
            "Cancer screening camps in rural areas — government initiative welcomed.",
            "Telemedicine usage surged. Keep investing in digital health.",
            "Medical college seats increasing but quality must not suffer.",
            "Health insurance portability needed so patients aren't stuck.",
            "Drug pricing regulations helping control costs of essential medicines.",
            "Ayushman Bharat hospitals turning away patients — fraud must stop.",
            "Blood bank shortages in tier-3 towns a serious problem.",
            "One Health Mission integrating human-animal-environment health. Smart.",
            "Free dialysis scheme for kidney patients is a life-saving step.",
            "Government should regulate private hospital billing aggressively.",
            "Maternal mortality rate declining. Health schemes working.",
            "Mobile health vans reaching tribal areas — great initiative.",
        ],
        "hi": [
            "आयुष्मान भारत योजना से गरीबों को इलाज मिल रहा है।",
            "जन औषधि केंद्र से सस्ती दवाएं मिल रही हैं।",
            "नए एम्स से इलाज के लिए दूर नहीं जाना पड़ेगा।",
            "मानसिक स्वास्थ्य हेल्पलाइन का उपयोग बढ़ रहा है।",
            "टेलीमेडिसिन सेवा गाँवों में डॉक्टर की कमी पूरी कर रही है।",
            "जेनेरिक दवाइयाँ मरीजों की लागत कम कर रही हैं।",
            "प्राथमिक स्वास्थ्य केंद्रों में और डॉक्टर चाहिए।",
            "कैंसर स्क्रीनिंग शिविर ग्रामीण क्षेत्रों में — अच्छी पहल।",
            "निशुल्क डायलिसिस योजना जीवन रक्षक कदम है।",
            "आयुष्मान भारत अस्पताल मरीज वापस भेज रहे — धोखाधड़ी रोको।",
        ],
        "ta": [
            "ஆயுஷ்மான் பாரத் திட்டம் ஏழை மக்களுக்கு உதவுகிறது.",
            "ஜன் ஔஷதி மையங்கள் மலிவு விலையில் மருந்து வழங்குகின்றன.",
            "புதிய AIIMS நகரங்களில் மருத்துவ பயணச்சுமை குறையும்.",
            "டெலிமெடிசின் கிராமங்களில் மருத்துவர் பற்றாக்குறையை நிவர்த்தி செய்கிறது.",
            "பொது சுகாதார மையங்களுக்கு மேலும் மருத்துவர்கள் தேவை.",
        ],
        "te": [
            "ఆయుష్మాన్ భారత్ పథకం పేదలకు చికిత్స అందిస్తోంది.",
            "జన్ ఔషధి కేంద్రాలు చవక ధరల్లో మందులు అందిస్తున్నాయి.",
            "కొత్త AIIMS టైర్-2 నగరాల్లో వైద్య ప్రయాణ భారాన్ని తగ్గిస్తుంది.",
            "టెలిమెడిసిన్ గ్రామాల్లో వైద్యుల కొరతను తీరుస్తోంది.",
            "ఉచిత డయాలసిస్ పథకం జీవన రక్షక చర్య.",
        ],
        "bn": [
            "আয়ুষ্মান ভারত প্রকল্প দরিদ্রদের চিকিৎসা পাচ্ছে।",
            "জন ঔষধি কেন্দ্র সস্তায় ওষুধ দিচ্ছে।",
            "টেলিমেডিসিন গ্রামে ডাক্তারের অভাব পূরণ করছে।",
            "নতুন AIIMS টায়ার-2 শহরে মেডিকেল ভ্রমণ কমাবে।",
        ],
    },
    "taxation_gst": {
        "en": [
            "GST on essential food items needs to be reduced immediately.",
            "Middle class is overtaxed while large corporations get exemptions.",
            "Income tax threshold should be raised to ₹10 lakh.",
            "GST compliance burden on small businesses is too high.",
            "Tax reform needed — simplify the slab structure.",
            "GST on health insurance premiums should be zero. It's healthcare.",
            "Capital gains tax hike will hurt retail investors who are just building wealth.",
            "TDS on freelancer income needs a threshold increase.",
            "Faceless assessment scheme reducing tax harassment. Keep improving it.",
            "GST on EV charging should be reduced to encourage adoption.",
            "STT (Securities Transaction Tax) hike will reduce market liquidity.",
            "Property tax reform in cities needed — outdated valuations everywhere.",
            "The 28% GST slab has too many items. Rationalise it.",
            "Simplified GST filing portal needed. Current one crashes too often.",
            "Direct tax code long overdue — unify and simplify the mess.",
            "Crypto taxation at 30% with no loss set-off is killing the industry.",
            "MSME tax relief needed — they are backbone of economy.",
        ],
        "hi": [
            "जीएसटी दरें जरूरी चीजों पर कम होनी चाहिए।",
            "मध्यम वर्ग पर टैक्स का बोझ बहुत ज्यादा है।",
            "इनकम टैक्स छूट सीमा बढ़ाई जाए।",
            "स्वास्थ्य बीमा पर जीएसटी शून्य होनी चाहिए।",
            "छोटे व्यवसायों पर जीएसटी अनुपालन का बोझ कम करें।",
            "पूंजीगत लाभ कर बढ़ाने से खुदरा निवेशक प्रभावित होंगे।",
            "फेसलेस असेसमेंट से टैक्स उत्पीड़न कम हुआ — अच्छी पहल।",
            "जीएसटी पोर्टल बार-बार क्रैश होता है — सुधार जरूरी।",
        ],
        "ta": [
            "அத்தியாவசிய உணவு பொருட்களில் GST குறைக்கப்பட வேண்டும்.",
            "நடுத்தர வர்க்கத்தினர் அதிக வரி செலுத்துகிறார்கள்.",
            "வருமான வரி விலக்கு வரம்பை ₹10 லட்சமாக உயர்த்த வேண்டும்.",
            "சிறு தொழில்களுக்கு GST இணக்கம் சுமை குறைக்க வேண்டும்.",
        ],
        "te": [
            "అవసరమైన ఆహార వస్తువులపై GST తగ్గించాలి.",
            "మధ్యతరగతి అధిక పన్ను భారం భరిస్తోంది.",
            "ఆదాయపు పన్ను మినహాయింపు పరిమితిని ₹10 లక్షలకు పెంచాలి.",
            "చిన్న వ్యాపారాలపై GST సమ్మతి భారం తగ్గించాలి.",
        ],
        "mr": [
            "अत्यावश्यक वस्तूंवरील जीएसटी कमी करा.",
            "मध्यमवर्गावर करांचा बोजा खूप जास्त आहे.",
            "आयकर सूट मर्यादा ₹१० लाखांपर्यंत वाढवावी.",
        ],
    },
    "infrastructure": {
        "en": [
            "New expressway cutting travel time between cities by half.",
            "Railway electrification project on schedule across all zones.",
            "Smart city mission improving urban infrastructure quality.",
            "Metro expansion bringing relief to commuters in large cities.",
            "Optical fibre reaching gram panchayats under BharatNet.",
            "National highway construction at record pace. Modi's biggest achievement?",
            "Dedicated freight corridors speeding up cargo movement significantly.",
            "Bullet train project: good for the long run but priority should be intercity trains.",
            "Airport expansion in tier-2 cities opening new connectivity options.",
            "Sagarmala port modernisation driving export growth.",
            "Urban flooding shows smart city investment needs to include drainage.",
            "Inland waterways as freight alternative — underused, needs more push.",
            "PM Gati Shakti for multimodal logistics — genuinely transformative.",
            "Hydrogen fuel cell buses pilot in Pune is exciting.",
            "Rural roads under PMGSY connecting villages to markets.",
            "Last-mile rail connectivity to ports critical for exports.",
        ],
        "hi": [
            "नया एक्सप्रेसवे यात्रा समय आधा कर देगा।",
            "रेलवे विद्युतीकरण से प्रदूषण कम होगा।",
            "स्मार्ट सिटी परियोजना से शहर बदल रहे हैं।",
            "भारतनेट से गाँवों में इंटरनेट पहुँचा।",
            "मेट्रो विस्तार बड़े शहरों के यात्रियों के लिए राहत।",
            "डेडिकेटेड फ्रेट कॉरिडोर माल ढुलाई को तेज कर रहा है।",
            "PM गति शक्ति से मल्टीमोडल लॉजिस्टिक्स में क्रांति।",
            "राष्ट्रीय राजमार्ग निर्माण रिकॉर्ड गति से — बड़ी उपलब्धि।",
        ],
        "ta": [
            "புதிய நெடுஞ்சாலை நகரங்கிடையிலான பயண நேரத்தை பாதியாக குறைக்கும்.",
            "ரயில்வே மின்மயமாக்கல் திட்டம் முன்னேறுகிறது.",
            "BharatNet கிராம பஞ்சாயத்துகளுக்கு இணையம் கொண்டு சேர்க்கிறது.",
            "மெட்ரோ விரிவாக்கம் நகர பயணிகளுக்கு நிவாரணம்.",
        ],
        "te": [
            "కొత్త ఎక్స్‌ప్రెస్‌వే నగరాల మధ్య ప్రయాణ సమయాన్ని సగానికి తగ్గిస్తుంది.",
            "రైల్వే విద్యుదీకరణ కాలుష్యాన్ని తగ్గిస్తుంది.",
            "BharatNet గ్రామ పంచాయతీలకు ఇంటర్నెట్ అందిస్తోంది.",
            "మెట్రో విస్తరణ నగర ప్రయాణికులకు ఊరట.",
        ],
    },
    "environment": {
        "en": [
            "Delhi AQI crossed 400 again. Emergency health alert issued.",
            "Forest fires increasing due to climate change. Need urgent action.",
            "Solar capacity target achieved ahead of schedule. Great news!",
            "Plastic ban enforcement improving coastal cleanliness visibly.",
            "River rejuvenation project showing some positive results.",
            "Stubble burning ban not enforced — same story every October.",
            "Climate commitments at COP need domestic policy follow-through.",
            "Green hydrogen mission could be India's next big industrial leap.",
            "National Clean Air Programme targets unmet in most cities.",
            "Wetlands under threat from urbanisation. Protect them now.",
            "Mangrove cover expansion announced — hope it's not greenwashing.",
            "Battery waste from growing EV sector needs a recycling policy now.",
            "Cheetah reintroduction at Kuno — too early to call success.",
            "Air purifiers now household items in Delhi. That's a crisis, not a solution.",
            "Carbon credit markets for Indian farmers — an idea worth exploring.",
            "Flooding in Chennai every monsoon. Urban drainage policy failing.",
        ],
        "hi": [
            "दिल्ली की हवा खतरनाक स्तर पर, प्रदूषण नियंत्रण जरूरी।",
            "सौर ऊर्जा का लक्ष्य समय से पहले हासिल — शानदार।",
            "प्लास्टिक प्रतिबंध से समुद्र तट साफ हो रहे हैं।",
            "पराली जलाने पर रोक लागू नहीं हो रही — हर साल यही दिखता है।",
            "हरित हाइड्रोजन मिशन भारत की अगली बड़ी छलांग हो सकती है।",
            "नदी पुनरुद्धार परियोजना में थोड़े अच्छे परिणाम आ रहे हैं।",
            "जंगलों में आग की घटनाएं बढ़ रही हैं — जलवायु परिवर्तन का असर।",
        ],
        "ta": [
            "டெல்லி AQI மீண்டும் 400 தாண்டியது — அவசர சுகாதார எச்சரிக்கை.",
            "காட்டுத் தீ அதிகரிக்கிறது — கடுமையான நடவடிக்கை தேவை.",
            "சூரிய ஆற்றல் இலக்கு முன்னதாக அடையப்பட்டது — நல்ல செய்தி.",
            "பிளாஸ்டிக் தடை கரையோரங்களை சுத்தமாக்குகிறது.",
        ],
        "te": [
            "ఢిల్లీ AQI మళ్ళీ 400 దాటింది — అత్యవసర ఆరోగ్య హెచ్చరిక.",
            "అడవి మంటలు పెరుగుతున్నాయి — వాతావరణ మార్పు ప్రభావం.",
            "సౌర విద్యుత్ లక్ష్యం ముందుగానే సాధించబడింది.",
            "ప్లాస్టిక్ నిషేధం తీరప్రాంత పరిశుభ్రతను మెరుగుపరుస్తోంది.",
        ],
    },
    "ai_technology": {
        "en": [
            "AI-powered crop advisory helping farmers make better decisions.",
            "Government deploying AI for faster document verification.",
            "India's AI startup ecosystem growing rapidly — unicorns incoming.",
            "AI in healthcare diagnostics could revolutionise rural care access.",
            "Digital India 2.0 integrating AI across governance services.",
            "Concerned about AI job displacement in IT sector — need policy.",
            "IndiaAI Mission: ₹10k crore allocation is a strong signal.",
            "Open-source AI models from India for Indian languages — needed now.",
            "AI regulation: balance innovation and safety carefully.",
            "AI tutors in government schools could transform learning outcomes.",
            "Deepfake regulation needed before elections are affected further.",
            "AI in judiciary for case management — promising if deployed right.",
            "India needs more GPU compute if it wants AI sovereignty.",
            "BharatGPT project promising but needs more open government data.",
            "AI chip design in India — PLI scheme should incentivise this.",
            "AI-based traffic management reducing congestion in pilot cities.",
        ],
        "hi": [
            "एआई से सरकारी सेवाएं तेज़ और पारदर्शी होंगी।",
            "किसानों के लिए एआई आधारित सलाह उपयोगी है।",
            "भारत AI मिशन में ₹10000 करोड़ — मजबूत संकेत।",
            "डीपफेक से चुनाव को खतरा — नियमन जरूरी।",
            "AI से आईटी क्षेत्र में नौकरियां जाने का डर — नीति चाहिए।",
            "हिंदी में AI मॉडल विकसित करना जरूरी है।",
        ],
        "ta": [
            "AI அரசு சேவைகளை வேகமாகவும் வெளிப்படையாகவும் ஆக்கும்.",
            "விவசாயிகளுக்கு AI ஆலோசனை பயனுள்ளது.",
            "IndiaAI திட்டம் ஒரு வலுவான சமிக்கை.",
            "தமிழ் மொழி AI மாதிரிகள் உருவாக்கப்பட வேண்டும்.",
        ],
        "te": [
            "AI ప్రభుత్వ సేవలను వేగంగా, పారదర్శకంగా చేస్తుంది.",
            "రైతులకు AI ఆధారిత సలహా ఉపయోగకరంగా ఉంది.",
            "IndiaAI మిషన్ ₹10,000 కోటి కేటాయింపు బలమైన సంకేతం.",
            "డీప్‌ఫేక్ నియంత్రణ ఎన్నికలకు ముందు అవసరం.",
        ],
    },
    "social_welfare": {
        "en": [
            "PM housing scheme: 3 crore houses under construction.",
            "Women self-help groups empowered through microfinance schemes.",
            "Free ration scheme extended — relief for poor families.",
            "MGNREGA wages increased to support rural livelihoods.",
            "Skill India programme helping youth find employment.",
            "PM Jan Dhan: financial inclusion milestone for unbanked households.",
            "Social security for gig workers long overdue — act now.",
            "Widow pension scheme amount woefully inadequate after 10 years.",
            "Anganwadi worker salaries need urgent revision.",
            "One Nation One Ration card working well for migrant workers.",
            "Scholarship portals should be merged and simplified.",
            "SC/ST scholarship disbursement delays must stop.",
            "Urban homeless shelter capacity needs tripling in major cities.",
            "Child labour laws must be enforced strictly.",
        ],
        "hi": [
            "पीएम आवास योजना से गरीब परिवारों को घर मिल रहा है।",
            "मनरेगा मजदूरी बढ़ाने से ग्रामीण आय बढ़ेगी।",
            "मुफ्त राशन योजना से जरूरतमंद परिवारों को राहत।",
            "एक राष्ट्र एक राशन कार्ड प्रवासी मजदूरों के लिए बड़ी राहत।",
            "महिला स्वयं सहायता समूह माइक्रोफाइनेंस से सशक्त हो रहे हैं।",
            "आंगनवाड़ी कार्यकर्ताओं का वेतन बढ़ाया जाना चाहिए।",
        ],
        "ta": [
            "PM வீட்டு திட்டம் 3 கோடி வீடுகளை கட்டுகிறது.",
            "பெண் சுய உதவிக் குழுக்கள் மைக்ரோ ஃபைனான்ஸ் மூலம் வலுப்பெறுகின்றன.",
            "இலவச ரேஷன் திட்டம் தொடர்கிறது — ஏழை குடும்பங்களுக்கு நிவாரணம்.",
            "ஒரே தேசம் ஒரே ரேஷன் அட்டை புலம்பெயர் தொழிலாளர்களுக்கு வரப்பிரசாதம்.",
        ],
        "te": [
            "PM గృహ పథకం 3 కోటి ఇళ్ళు నిర్మిస్తోంది.",
            "ఉచిత రేషన్ పథకం పేద కుటుంబాలకు ఊరట.",
            "MGNREGA వేతనాలు పెంచడం గ్రామీణ జీవికను మెరుగుపరుస్తుంది.",
            "ఒకే దేశం ఒకే రేషన్ కార్డు వలస కార్మికులకు వరం.",
        ],
    },
    "employment": {
        "en": [
            "Unemployment rate at 8-year high — government must act now.",
            "Gig workers need social security. Platform companies must pay.",
            "Internship scheme for 1 crore youth — promising if well implemented.",
            "Manufacturing PLI creating jobs but need 10x more.",
            "MSME sector employs 11 crore — protect it from GST overburden.",
            "Startup ecosystem creating quality jobs but need deeper reach beyond metros.",
            "Skill gap: too many BBA/MBA grads, too few skilled tradespeople.",
            "Contract workers being replaced by automation without retraining support.",
            "Defence manufacturing export potential can create lakhs of jobs.",
            "State employment exchanges are useless. Need a modern digital platform.",
            "Youth unemployment hitting small towns harder than big cities.",
            "Apprenticeship law reform could create millions of formal sector entry points.",
            "Women labour force participation is too low — fix the barriers.",
            "Agniveer scheme concerns valid. Job security for veterans post-service?",
        ],
        "hi": [
            "बेरोजगारी दर चिंताजनक स्तर पर — सरकार तुरंत कदम उठाए।",
            "गिग कार्यकर्ताओं के लिए सामाजिक सुरक्षा जरूरी है।",
            "1 करोड़ युवाओं के लिए इंटर्नशिप योजना — अगर सही से लागू हो।",
            "MSME 11 करोड़ लोगों को रोजगार देता है — इसे बचाओ।",
            "स्किल गैप की समस्या — डिग्री बहुत, हुनर कम।",
            "महिला श्रम बल भागीदारी बढ़ाने की जरूरत है।",
        ],
        "ta": [
            "வேலையின்மை விகிதம் உயர்ந்துள்ளது — அரசு நடவடிக்கை தேவை.",
            "கிக் தொழிலாளர்களுக்கு சமூக பாதுகாப்பு அவசியம்.",
            "1 கோடி இளைஞர்களுக்கு இன்டர்ன்ஷிப் திட்டம் — நல்ல அணுகுமுறை.",
            "MSME துறை 11 கோடி பேருக்கு வேலை தருகிறது — பாதுகாக்கணும்.",
        ],
        "te": [
            "నిరుద్యోగ రేటు పెరుగుతోంది — ప్రభుత్వం చర్యలు తీసుకోవాలి.",
            "గిగ్ కార్మికులకు సామాజిక భద్రత అవసరం.",
            "1 కోటి యువతకు ఇంటర్న్‌షిప్ పథకం — మంచి చొరవ.",
            "MSME 11 కోట్ల మందికి ఉపాధి కల్పిస్తోంది — రక్షించాలి.",
        ],
    },
    "digital_india": {
        "en": [
            "UPI transactions hit ₹20 trillion in a month. Incredible milestone.",
            "DigiLocker adoption rising among students and job seekers.",
            "Aadhaar-linked benefits working seamlessly now. DBT is a success.",
            "India Stack being adopted by other countries — proud moment.",
            "Digital rupee pilot expanding. Future of money is here.",
            "Cybersecurity awareness still very low in rural India — need campaigns.",
            "ONDC (Open Network for Digital Commerce) challenging e-commerce monopolies.",
            "Personal Data Protection Bill: strong privacy protections needed.",
            "5G rollout accelerating — real-world applications need to follow.",
            "e-Court system reducing case backlogs. Technology transforming judiciary.",
            "PM-WANI public WiFi scheme underutilised — needs better outreach.",
            "Digital literacy programmes must reach last mile.",
            "GeM portal saving government procurement costs. Transparency++.",
            "Umang app consolidating government services — needs UX improvement.",
        ],
        "hi": [
            "यूपीआई लेनदेन ₹20 ट्रिलियन प्रति माह — शानदार उपलब्धि।",
            "डिजिलॉकर का उपयोग बढ़ रहा है।",
            "आधार से जुड़े लाभ अब सुचारू रूप से मिल रहे हैं।",
            "5G रोलआउट तेज हो रहा है — असली अनुप्रयोग आने बाकी हैं।",
            "साइबर सुरक्षा जागरूकता ग्रामीण भारत में बहुत कम है।",
            "ONDC ई-कॉमर्स एकाधिकार को चुनौती दे रहा है।",
        ],
        "ta": [
            "UPI பரிவர்த்தனைகள் மாதத்திற்கு ₹20 ட்ரில்லியன் — அசாதாரண சாதனை.",
            "5G விரிவாக்கம் முடுகிவிடுகிறது.",
            "தனிப்பட்ட தரவு பாதுகாப்பு சட்டம் வலுவாக இருக்க வேண்டும்.",
        ],
        "te": [
            "UPI లావాదేవీలు నెలకు ₹20 ట్రిలియన్ — అద్భుత మైలురాయి.",
            "5G రోల్‌అవుట్ వేగవంతమవుతోంది.",
            "డిజిటల్ రూపాయి పైలట్ విస్తరిస్తోంది — డబ్బు భవిష్యత్తు ఇదే.",
        ],
    },
}

# Geo hints by language
_GEO: dict[str, list[str]] = {
    "en": ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Surat"],
    "hi": ["Delhi", "Lucknow", "Jaipur", "Bhopal", "Patna", "Varanasi", "Indore", "Agra", "Kanpur", "Meerut"],
    "ta": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli", "Tiruppur"],
    "te": ["Hyderabad", "Vijayawada", "Visakhapatnam", "Warangal", "Tirupati", "Kurnool"],
    "bn": ["Kolkata", "Durgapur", "Siliguri", "Asansol", "Howrah"],
    "mr": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur"],
    "gu": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Gandhinagar"],
    "pa": ["Chandigarh", "Amritsar", "Ludhiana", "Jalandhar", "Patiala"],
}

# Platform weights  [twitter, reddit, facebook, instagram, youtube, news]
_PLATFORM_WEIGHTS = [0.28, 0.14, 0.26, 0.16, 0.10, 0.06]

# Language distribution per platform
_PLATFORM_LANG_WEIGHTS: dict[str, dict[str, float]] = {
    "twitter":   {"en": 0.38, "hi": 0.32, "ta": 0.10, "te": 0.08, "bn": 0.05, "mr": 0.04, "gu": 0.02, "pa": 0.01},
    "reddit":    {"en": 0.72, "hi": 0.18, "ta": 0.04, "te": 0.03, "bn": 0.02, "mr": 0.01, "gu": 0.00, "pa": 0.00},
    "facebook":  {"en": 0.22, "hi": 0.40, "ta": 0.12, "te": 0.09, "bn": 0.08, "mr": 0.05, "gu": 0.03, "pa": 0.01},
    "instagram": {"en": 0.32, "hi": 0.38, "ta": 0.10, "te": 0.07, "bn": 0.06, "mr": 0.04, "gu": 0.02, "pa": 0.01},
    "youtube":   {"en": 0.38, "hi": 0.36, "ta": 0.10, "te": 0.08, "bn": 0.05, "mr": 0.02, "gu": 0.01, "pa": 0.00},
    "news":      {"en": 0.55, "hi": 0.28, "ta": 0.07, "te": 0.05, "bn": 0.03, "mr": 0.01, "gu": 0.01, "pa": 0.00},
}

# Max content length per platform (chars)
_PLATFORM_MAX_LEN = {
    "twitter": 280, "reddit": 800, "facebook": 500,
    "instagram": 300, "youtube": 400, "news": 1000,
}

# News event spikes: (days_ago_center, topic, multiplier, duration_days)
_NEWS_SPIKES = [
    (25, "fuel_prices",     3.5, 3),
    (20, "environment",     4.0, 2),
    (16, "agriculture_msp", 2.8, 3),
    (12, "ev_adoption",     3.2, 2),
    (8,  "taxation_gst",    2.5, 2),
    (5,  "ai_technology",   3.0, 2),
    (3,  "employment",      2.2, 2),
    (2,  "digital_india",   2.5, 1),
]

# Platform specs
_PLATFORM_SPECS = [
    {"name": "twitter",   "display_name": "X / Twitter",  "color": "#1DA1F2"},
    {"name": "reddit",    "display_name": "Reddit",       "color": "#FF4500"},
    {"name": "facebook",  "display_name": "Facebook",     "color": "#1877F2"},
    {"name": "instagram", "display_name": "Instagram",    "color": "#E1306C"},
    {"name": "youtube",   "display_name": "YouTube",      "color": "#FF0000"},
    {"name": "news",      "display_name": "News Sites",   "color": "#6B7280"},
]

# ── Author persona bank ───────────────────────────────────────────────────────

def _build_personas(n: int = 2000) -> list[dict]:
    """Create n synthetic author personas with consistent behaviour."""
    personas = []
    for i in range(n):
        lang_pool = RNG.choices(
            ["en", "hi", "ta", "te", "bn", "mr", "gu"],
            weights=[0.22, 0.30, 0.12, 0.10, 0.08, 0.08, 0.10],
            k=1
        )[0]
        plat_pool = RNG.choices(
            ["twitter", "reddit", "facebook", "instagram", "youtube", "news"],
            weights=_PLATFORM_WEIGHTS,
            k=1
        )[0]
        # Primary topic preference (2–3 topics)
        n_topics = RNG.randint(2, 3)
        topic_names = list(_TOPIC_WEIGHTS.keys())
        topic_wts = list(_TOPIC_WEIGHTS.values())
        pref_topics = RNG.choices(topic_names, weights=topic_wts, k=n_topics)
        pref_topics = list(dict.fromkeys(pref_topics))  # dedup

        # Posting style
        style = RNG.choices(
            ["concise", "verbose", "emoji", "formal"],
            weights=[0.35, 0.25, 0.25, 0.15],
            k=1
        )[0]

        # Peak activity time
        peak = RNG.choices(
            ["morning", "afternoon", "evening", "night"],
            weights=[0.20, 0.30, 0.35, 0.15],
            k=1
        )[0]

        personas.append({
            "uid": i,
            "lang": lang_pool,
            "platform": plat_pool,
            "topics": pref_topics,
            "style": style,
            "peak": peak,
        })
    return personas


_PERSONAS = _build_personas(2000)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _pick(d: dict[str, float]) -> str:
    keys, weights = zip(*d.items())
    return RNG.choices(list(keys), weights=list(weights), k=1)[0]


def _sentiment(topic: str) -> tuple[str, float]:
    bias = _SENTIMENT_BIAS.get(topic, 0.0)
    base_pos = 0.33 + bias * 0.6
    base_neg = 0.33 - bias * 0.4
    base_neu = max(0.05, 1.0 - base_pos - base_neg)
    total = base_pos + base_neg + base_neu
    p, neg, n = base_pos / total, base_neg / total, base_neu / total
    s = RNG.choices(["positive", "negative", "neutral"], weights=[p, neg, n], k=1)[0]
    score = {
        "positive": RNG.uniform(0.55, 0.95),
        "negative": RNG.uniform(0.55, 0.92),
        "neutral":  RNG.uniform(0.48, 0.72),
    }[s]
    return s, round(score, 3)


def _author_hash(platform: str, uid: int) -> str:
    salt = "demo-salt-2026"
    return hashlib.sha256(f"{salt}{platform}{uid}".encode()).hexdigest()[:32]


def _spike_multiplier(days_ago: float, topic: str) -> float:
    for center, spike_topic, mult, dur in _NEWS_SPIKES:
        if spike_topic == topic and abs(days_ago - center) <= dur / 2:
            return mult
    return 1.0


def _post_time(now: datetime, persona: dict) -> datetime:
    """Generate a timestamp biased toward the persona's peak activity window."""
    peak_hours = {"morning": (6, 10), "afternoon": (12, 17), "evening": (18, 22), "night": (22, 26)}
    h_min, h_max = peak_hours[persona["peak"]]
    days_ago = RNG.uniform(0, 29)
    hour = RNG.randint(h_min, h_max - 1) % 24
    minute = RNG.randint(0, 59)
    ts = now - timedelta(days=days_ago, hours=now.hour - hour, minutes=minute)
    return min(ts, now)


def _enrich_content(content: str, style: str, platform: str, topic: str) -> str:
    """Vary content based on style and platform constraints."""
    max_len = _PLATFORM_MAX_LEN.get(platform, 500)
    if style == "emoji":
        emojis = {
            "fuel_prices": ["⛽", "💰", "😤", "📉"],
            "ev_adoption":  ["⚡", "🚗", "🌱", "✅"],
            "agriculture_msp": ["🌾", "👨‍🌾", "💚", "🇮🇳"],
            "environment":  ["🌍", "🌿", "😷", "⚠️"],
            "healthcare":   ["🏥", "💊", "❤️", "🙏"],
            "education":    ["📚", "🎓", "✏️", "🌟"],
        }
        pool = emojis.get(topic, ["🇮🇳", "💬", "📢"])
        emoji = RNG.choice(pool)
        content = f"{content} {emoji}"
    elif style == "formal":
        prefixes = ["Analysis: ", "Observation: ", "Policy note — "]
        content = RNG.choice(prefixes) + content
    elif style == "verbose" and platform in ("reddit", "facebook", "news"):
        suffixes = [
            " What are your thoughts on this?",
            " Share if you agree.",
            " This needs more discussion.",
            " The government needs to address this urgently.",
        ]
        content += RNG.choice(suffixes)
    hashtag_topics = {
        "fuel_prices": ["#FuelHike", "#PetrolPrice", "#IndiaFuel"],
        "ev_adoption": ["#EVIndia", "#CleanEnergy", "#ElectricVehicle"],
        "agriculture_msp": ["#KisanPolicy", "#MSPGuarantee", "#IndianFarmer"],
        "environment": ["#CleanAir", "#DelhiAQI", "#ClimateIndia"],
    }
    if platform == "twitter" and RNG.random() < 0.4:
        tags = hashtag_topics.get(topic, ["#India", "#Policy"])
        content += " " + RNG.choice(tags)
    return content[:max_len]


# ── Segment specs ─────────────────────────────────────────────────────────────

_SEGMENT_SPECS = [
    {
        "name": "Hindi-speaking Twitter users interested in Fuel & Energy Prices",
        "description": "Urban and semi-urban Hindi speakers on Twitter expressing strong opinions about fuel price hikes.",
        "dominant_language": "Hindi", "size_estimate": 4200, "confidence": 0.81,
        "topic_prefs": {"fuel_prices": 0.42, "taxation_gst": 0.28, "infrastructure": 0.15, "social_welfare": 0.15},
        "sentiment_profile": {"positive": 0.18, "neutral": 0.32, "negative": 0.50},
        "activity_profile": {"morning": 0.22, "afternoon": 0.28, "evening": 0.35, "night": 0.15},
        "geo_distribution": {"Delhi": 0.30, "UP": 0.22, "Bihar": 0.15, "MP": 0.12, "Rajasthan": 0.11, "Other": 0.10},
        "interests": ["fuel prices", "LPG cost", "inflation", "GST reform"],
        "summary": "Strongly negative voices discussing fuel & energy price hikes. Highly vocal on Twitter, respond quickly to petrol/diesel pricing announcements.",
        "reaction": {"support_policy": 0.18, "oppose_policy": 0.60, "neutral": 0.22},
    },
    {
        "name": "English-speaking Reddit users interested in AI & Technology",
        "description": "Educated urban professionals engaging in nuanced debate about AI and technology policy.",
        "dominant_language": "English", "size_estimate": 2800, "confidence": 0.87,
        "topic_prefs": {"ai_technology": 0.45, "infrastructure": 0.25, "education": 0.20, "ev_adoption": 0.10},
        "sentiment_profile": {"positive": 0.45, "neutral": 0.38, "negative": 0.17},
        "activity_profile": {"morning": 0.18, "afternoon": 0.32, "evening": 0.38, "night": 0.12},
        "geo_distribution": {"Bangalore": 0.28, "Hyderabad": 0.22, "Mumbai": 0.20, "Delhi": 0.15, "Pune": 0.10, "Other": 0.05},
        "interests": ["AI governance", "digital India", "EV technology", "startup ecosystem"],
        "summary": "Mostly positive voices on AI and technology policy. Analytical, engage with detailed policy documents.",
        "reaction": {"support_policy": 0.52, "oppose_policy": 0.18, "neutral": 0.30},
    },
    {
        "name": "Tamil-speaking Facebook users interested in Agriculture",
        "description": "Rural and semi-rural Tamil speakers discussing agricultural MSP and farmer welfare schemes.",
        "dominant_language": "Tamil", "size_estimate": 3100, "confidence": 0.76,
        "topic_prefs": {"agriculture_msp": 0.50, "social_welfare": 0.25, "environment": 0.15, "healthcare": 0.10},
        "sentiment_profile": {"positive": 0.38, "neutral": 0.35, "negative": 0.27},
        "activity_profile": {"morning": 0.30, "afternoon": 0.25, "evening": 0.30, "night": 0.15},
        "geo_distribution": {"Tamil Nadu (Rural)": 0.55, "Tamil Nadu (Urban)": 0.30, "Pondicherry": 0.10, "Other": 0.05},
        "interests": ["MSP policy", "crop insurance", "kisan credit", "farmer protests"],
        "summary": "Moderately positive voices on agricultural policy. Respond strongly to MSP announcements.",
        "reaction": {"support_policy": 0.42, "oppose_policy": 0.30, "neutral": 0.28},
    },
    {
        "name": "English-speaking YouTube users interested in EV Adoption",
        "description": "Tech-savvy urban consumers discussing EV policy, subsidies, and charging infrastructure.",
        "dominant_language": "English", "size_estimate": 1900, "confidence": 0.83,
        "topic_prefs": {"ev_adoption": 0.55, "environment": 0.25, "infrastructure": 0.12, "ai_technology": 0.08},
        "sentiment_profile": {"positive": 0.58, "neutral": 0.30, "negative": 0.12},
        "activity_profile": {"morning": 0.15, "afternoon": 0.25, "evening": 0.45, "night": 0.15},
        "geo_distribution": {"Bangalore": 0.25, "Delhi": 0.22, "Mumbai": 0.20, "Pune": 0.18, "Chennai": 0.10, "Other": 0.05},
        "interests": ["electric vehicles", "charging infrastructure", "battery tech", "clean transport"],
        "summary": "Strongly positive early adopters on EVs. Respond very positively to EV subsidies.",
        "reaction": {"support_policy": 0.65, "oppose_policy": 0.10, "neutral": 0.25},
    },
    {
        "name": "Hindi-speaking Instagram users interested in Education",
        "description": "Young students and parents discussing NEP 2020 and scholarship schemes.",
        "dominant_language": "Hindi", "size_estimate": 3600, "confidence": 0.79,
        "topic_prefs": {"education": 0.55, "social_welfare": 0.20, "ai_technology": 0.15, "healthcare": 0.10},
        "sentiment_profile": {"positive": 0.42, "neutral": 0.38, "negative": 0.20},
        "activity_profile": {"morning": 0.20, "afternoon": 0.15, "evening": 0.40, "night": 0.25},
        "geo_distribution": {"UP": 0.28, "Bihar": 0.18, "MP": 0.15, "Rajasthan": 0.15, "Delhi": 0.12, "Other": 0.12},
        "interests": ["NEP 2020", "scholarships", "digital education", "skill development"],
        "summary": "Aspirational mixed-to-positive voices on education. Respond well to scholarship announcements.",
        "reaction": {"support_policy": 0.48, "oppose_policy": 0.22, "neutral": 0.30},
    },
    {
        "name": "Telugu-speaking Facebook users interested in Healthcare",
        "description": "Telugu citizens discussing Ayushman Bharat and public health infrastructure.",
        "dominant_language": "Telugu", "size_estimate": 2200, "confidence": 0.74,
        "topic_prefs": {"healthcare": 0.55, "social_welfare": 0.25, "agriculture_msp": 0.12, "education": 0.08},
        "sentiment_profile": {"positive": 0.40, "neutral": 0.35, "negative": 0.25},
        "activity_profile": {"morning": 0.28, "afternoon": 0.22, "evening": 0.35, "night": 0.15},
        "geo_distribution": {"Andhra Pradesh": 0.45, "Telangana": 0.42, "Other": 0.13},
        "interests": ["Ayushman Bharat", "affordable medicines", "rural healthcare", "AIIMS expansion"],
        "summary": "Moderately positive voices on healthcare access. Strongly support policies reducing out-of-pocket expenses.",
        "reaction": {"support_policy": 0.45, "oppose_policy": 0.25, "neutral": 0.30},
    },
    {
        "name": "Gujarati-speaking users interested in Business & Economy",
        "description": "Gujarati entrepreneurs and traders discussing GST, digital commerce, and MSME policy.",
        "dominant_language": "Gujarati", "size_estimate": 1800, "confidence": 0.71,
        "topic_prefs": {"taxation_gst": 0.38, "digital_india": 0.28, "employment": 0.18, "infrastructure": 0.16},
        "sentiment_profile": {"positive": 0.35, "neutral": 0.38, "negative": 0.27},
        "activity_profile": {"morning": 0.30, "afternoon": 0.35, "evening": 0.25, "night": 0.10},
        "geo_distribution": {"Gujarat": 0.70, "Mumbai": 0.15, "Other": 0.15},
        "interests": ["GST reform", "MSME support", "UPI business", "ONDC"],
        "summary": "Pragmatic voices on business policy. Strong opinions on GST compliance and digital commerce.",
        "reaction": {"support_policy": 0.40, "oppose_policy": 0.32, "neutral": 0.28},
    },
    {
        "name": "Bengali-speaking users interested in Social Welfare",
        "description": "Bengali-speaking citizens discussing welfare schemes, ration access, and housing.",
        "dominant_language": "Bengali", "size_estimate": 2500, "confidence": 0.73,
        "topic_prefs": {"social_welfare": 0.42, "healthcare": 0.28, "education": 0.18, "employment": 0.12},
        "sentiment_profile": {"positive": 0.36, "neutral": 0.38, "negative": 0.26},
        "activity_profile": {"morning": 0.25, "afternoon": 0.28, "evening": 0.32, "night": 0.15},
        "geo_distribution": {"West Bengal": 0.65, "Bangladesh diaspora": 0.15, "Assam": 0.12, "Other": 0.08},
        "interests": ["ration card", "housing scheme", "MGNREGA", "healthcare access"],
        "summary": "Mixed voices on welfare coverage and delivery. Respond to announcements about ration, housing, healthcare.",
        "reaction": {"support_policy": 0.44, "oppose_policy": 0.24, "neutral": 0.32},
    },
]

# ── Trend specs ───────────────────────────────────────────────────────────────

_TREND_SPECS = [
    {"name": "Petrol Price Hike Backlash",     "topic": "fuel_prices",     "trend_score": 0.912, "velocity": 4.2, "acceleration": 0.8,  "unique_users": 18400, "platform_count": 5, "is_emerging": False, "platforms": ["twitter","facebook","reddit","youtube","news"], "sentiment_shift": -0.18, "baseline_7d": 3200.0, "community_spread": 0.82},
    {"name": "EV Subsidy Announcement Buzz",   "topic": "ev_adoption",     "trend_score": 0.874, "velocity": 6.8, "acceleration": 2.1,  "unique_users": 9200,  "platform_count": 4, "is_emerging": True,  "platforms": ["twitter","reddit","youtube","instagram"],       "sentiment_shift":  0.31, "baseline_7d": 1100.0, "community_spread": 0.68},
    {"name": "MSP Guarantee Bill Discussion",  "topic": "agriculture_msp", "trend_score": 0.821, "velocity": 2.9, "acceleration": 0.4,  "unique_users": 14100, "platform_count": 4, "is_emerging": False, "platforms": ["twitter","facebook","youtube","news"],           "sentiment_shift":  0.22, "baseline_7d": 2800.0, "community_spread": 0.75},
    {"name": "NEP 2020 Implementation Update", "topic": "education",       "trend_score": 0.763, "velocity": 1.8, "acceleration": 0.2,  "unique_users": 11200, "platform_count": 4, "is_emerging": False, "platforms": ["twitter","facebook","instagram","youtube"],     "sentiment_shift":  0.15, "baseline_7d": 1900.0, "community_spread": 0.61},
    {"name": "Delhi AQI Emergency Alert",      "topic": "environment",     "trend_score": 0.748, "velocity": 5.3, "acceleration": 1.9,  "unique_users": 16800, "platform_count": 5, "is_emerging": True,  "platforms": ["twitter","facebook","reddit","instagram","news"],"sentiment_shift": -0.28, "baseline_7d": 1400.0, "community_spread": 0.79},
    {"name": "Ayushman Bharat Expansion",      "topic": "healthcare",      "trend_score": 0.692, "velocity": 1.2, "acceleration": 0.1,  "unique_users": 8900,  "platform_count": 3, "is_emerging": False, "platforms": ["twitter","facebook","news"],                    "sentiment_shift":  0.19, "baseline_7d": 1600.0, "community_spread": 0.55},
    {"name": "GST on Essentials Debate",       "topic": "taxation_gst",    "trend_score": 0.671, "velocity": 3.1, "acceleration": 0.7,  "unique_users": 7400,  "platform_count": 3, "is_emerging": False, "platforms": ["twitter","reddit","facebook"],                  "sentiment_shift": -0.14, "baseline_7d": 1200.0, "community_spread": 0.58},
    {"name": "AI in Governance Initiative",    "topic": "ai_technology",   "trend_score": 0.634, "velocity": 4.5, "acceleration": 1.4,  "unique_users": 5800,  "platform_count": 3, "is_emerging": True,  "platforms": ["twitter","reddit","youtube"],                   "sentiment_shift":  0.12, "baseline_7d": 600.0,  "community_spread": 0.44},
    {"name": "New Expressway Network Launch",  "topic": "infrastructure",  "trend_score": 0.598, "velocity": 1.5, "acceleration": 0.3,  "unique_users": 6200,  "platform_count": 3, "is_emerging": False, "platforms": ["twitter","facebook","news"],                    "sentiment_shift":  0.20, "baseline_7d": 1100.0, "community_spread": 0.49},
    {"name": "PM Housing Scheme Milestone",    "topic": "social_welfare",  "trend_score": 0.561, "velocity": 0.9, "acceleration": 0.0,  "unique_users": 5100,  "platform_count": 3, "is_emerging": False, "platforms": ["twitter","facebook","news"],                    "sentiment_shift":  0.25, "baseline_7d": 900.0,  "community_spread": 0.43},
    {"name": "Youth Unemployment Crisis",      "topic": "employment",      "trend_score": 0.718, "velocity": 3.8, "acceleration": 1.1,  "unique_users": 12400, "platform_count": 4, "is_emerging": True,  "platforms": ["twitter","reddit","instagram","youtube"],       "sentiment_shift": -0.22, "baseline_7d": 1800.0, "community_spread": 0.67},
    {"name": "UPI ₹20T Monthly Record",        "topic": "digital_india",   "trend_score": 0.682, "velocity": 2.4, "acceleration": 0.6,  "unique_users": 8200,  "platform_count": 4, "is_emerging": True,  "platforms": ["twitter","reddit","facebook","news"],           "sentiment_shift":  0.35, "baseline_7d": 800.0,  "community_spread": 0.56},
]


# ── Main seeder ───────────────────────────────────────────────────────────────

async def seed(db_url: str) -> None:
    async_url = (
        db_url
        .replace("postgresql://", "postgresql+asyncpg://")
        .replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    )
    engine = create_async_engine(async_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        print("=== SIH Demo Seeder (Enhanced) ===")
        platform_ids = await _seed_platforms(db)
        topic_ids    = await _seed_topics(db)
        post_ids, post_topic_map = await _seed_posts(db, platform_ids, topic_ids)
        await _seed_nlp(db, post_ids, post_topic_map)
        await _seed_post_topics(db, post_ids, post_topic_map, topic_ids)
        await _seed_trends(db, topic_ids)
        await _seed_segments(db)

        print(f"\n✓ Seeding complete! Posts: {len(post_ids)}  Topics: {len(topic_ids)}  Segments: {len(_SEGMENT_SPECS)}")

    await engine.dispose()


async def _seed_platforms(db: AsyncSession) -> dict[str, int]:
    print("\n[1/7] Platforms...")
    result: dict[str, int] = {}
    for spec in _PLATFORM_SPECS:
        existing = await db.execute(select(Platform).where(Platform.name == spec["name"]))
        p = existing.scalar_one_or_none()
        if p is None:
            p = Platform(name=spec["name"], display_name=spec["display_name"], color=spec["color"])
            db.add(p)
            await db.flush()
            print(f"  + {spec['display_name']}")
        result[spec["name"]] = p.id
    await db.commit()
    return result


async def _seed_topics(db: AsyncSession) -> dict[str, int]:
    print("\n[2/7] Topics...")
    result: dict[str, int] = {}
    for topic_name in TOPICS:
        existing = await db.execute(select(Topic).where(Topic.name == topic_name))
        t = existing.scalar_one_or_none()
        if t is None:
            kws = _TEMPLATES.get(topic_name, {}).get("en", [""])[:3]
            t = Topic(
                name=topic_name,
                keywords={"terms": list(kws)},
                first_seen=datetime.now(timezone.utc) - timedelta(days=30),
                platform_ids=[1, 2, 3, 4, 5, 6],
            )
            db.add(t)
            await db.flush()
            print(f"  + {topic_name}")
        result[topic_name] = t.id
    await db.commit()
    return result


async def _seed_posts(
    db: AsyncSession,
    platform_ids: dict[str, int],
    topic_ids: dict[str, int],
) -> tuple[list[int], dict[int, str]]:
    print("\n[3/7] Posts (~15 000)...")

    existing_count_r = await db.execute(text("SELECT COUNT(*) FROM raw_posts"))
    existing = existing_count_r.scalar() or 0
    if existing >= 10000:
        print(f"  = {existing} posts already exist, skipping")
        all_ids_r = await db.execute(text("SELECT id FROM raw_posts ORDER BY id"))
        all_ids = [row[0] for row in all_ids_r.fetchall()]
        topic_names = list(_TOPIC_WEIGHTS.keys())
        topic_wts   = list(_TOPIC_WEIGHTS.values())
        post_topic_map = {pid: RNG.choices(topic_names, weights=topic_wts, k=1)[0] for pid in all_ids}
        return all_ids, post_topic_map

    platform_names = list(platform_ids.keys())
    now = datetime.now(timezone.utc)
    topic_names = list(_TOPIC_WEIGHTS.keys())
    topic_wts   = list(_TOPIC_WEIGHTS.values())

    TOTAL = 15000
    batch_size = 300
    all_ids: list[int] = []
    post_topic_map: dict[int, str] = {}

    for batch_start in range(0, TOTAL, batch_size):
        batch: list[RawPost] = []
        for j in range(min(batch_size, TOTAL - batch_start)):
            # Pick a persona to drive this post
            persona = _PERSONAS[RNG.randint(0, len(_PERSONAS) - 1)]

            # Topic: persona preference 60%, pure random 40%
            if RNG.random() < 0.60 and persona["topics"]:
                topic_name = RNG.choice(persona["topics"])
            else:
                topic_name = RNG.choices(topic_names, weights=topic_wts, k=1)[0]

            # Platform: persona preference 55%, pure random 45%
            if RNG.random() < 0.55:
                platform_name = persona["platform"]
            else:
                platform_name = RNG.choices(platform_names, weights=_PLATFORM_WEIGHTS, k=1)[0]

            platform_id = platform_ids[platform_name]

            # Language: persona lang 60%, platform distribution 40%
            if RNG.random() < 0.60:
                lang = persona["lang"]
            else:
                lang = _pick(_PLATFORM_LANG_WEIGHTS[platform_name])

            templates = _TEMPLATES.get(topic_name, {}).get(lang)
            if not templates:
                lang = "en"
                templates = _TEMPLATES.get(topic_name, {}).get("en", ["Policy discussion."])

            content = RNG.choice(templates)
            content = _enrich_content(content, persona["style"], platform_name, topic_name)

            author_hash = _author_hash(platform_name, persona["uid"])
            post_ts = _post_time(now, persona)

            # Apply news-event spike: more posts on spike days (we're building the
            # volume curve from scratch, so spikes are reflected in timestamps).
            # We already distributed timestamps; just nudge spike-topic posts
            # toward their spike center window.
            for center, spike_topic, _, dur in _NEWS_SPIKES:
                if spike_topic == topic_name and RNG.random() < 0.5:
                    jitter = RNG.uniform(-dur / 2 * 24 * 3600, dur / 2 * 24 * 3600)
                    spike_ts = now - timedelta(days=center) + timedelta(seconds=jitter)
                    post_ts = min(spike_ts, now)
                    break

            geo = RNG.choice(_GEO.get(lang, ["India"]))
            ext_id = f"demo_{platform_name}_{batch_start + j}_{RNG.randint(10000, 99999)}"

            # Engagement metadata
            likes = RNG.randint(0, 500) if platform_name in ("twitter", "instagram", "facebook") else 0
            shares = RNG.randint(0, 100) if platform_name in ("twitter", "facebook") else 0
            comments_count = RNG.randint(0, 80)
            has_media = RNG.random() < 0.22

            p = RawPost(
                platform_id=platform_id,
                external_id=ext_id,
                author_hash=author_hash,
                content=content,
                content_cleaned=content,
                language=lang,
                geo_hint=geo,
                post_ts=post_ts,
                expires_at=now + timedelta(days=30),
                metadata_={
                    "topic": topic_name,           # NOTE: "topic" (not "topic_hint") — simulation_engine uses this key
                    "demo": True,
                    "likes": likes,
                    "shares": shares,
                    "comments_count": comments_count,
                    "has_media": has_media,
                    "persona_id": persona["uid"],
                    "style": persona["style"],
                },
            )
            batch.append(p)
            db.add(p)

        await db.flush()
        for p in batch:
            all_ids.append(p.id)
            post_topic_map[p.id] = p.metadata_.get("topic", "fuel_prices")

        print(f"  + {min(batch_start + batch_size, TOTAL)}/{TOTAL} posts", end="\r")

    await db.commit()
    print(f"\n  = {TOTAL} posts written")
    return all_ids, post_topic_map


async def _seed_nlp(db: AsyncSession, post_ids: list[int], post_topic_map: dict[int, str]) -> None:
    print("\n[4/7] NLP results...")
    existing_r = await db.execute(text("SELECT post_id FROM post_nlp"))
    existing_set = {row[0] for row in existing_r.fetchall()}
    new_ids = [pid for pid in post_ids if pid not in existing_set]
    if not new_ids:
        print("  = NLP already complete")
        return

    emotions = ["neutral", "anger", "joy", "fear", "sadness", "surprise", "disgust"]
    emotion_weights_map = {
        "positive": [0.08, 0.04, 0.62, 0.05, 0.08, 0.10, 0.03],
        "negative": [0.08, 0.42, 0.04, 0.22, 0.14, 0.04, 0.06],
        "neutral":  [0.54, 0.10, 0.12, 0.09, 0.09, 0.04, 0.02],
    }

    batch_size = 500
    total_written = 0
    for i in range(0, len(new_ids), batch_size):
        chunk = new_ids[i:i + batch_size]
        for pid in chunk:
            topic = post_topic_map.get(pid, "fuel_prices")
            sentiment, score = _sentiment(topic)
            emotion_wts = emotion_weights_map[sentiment]
            emotion = RNG.choices(emotions, weights=emotion_wts, k=1)[0]
            emotion_score = round(RNG.uniform(0.45, 0.90), 3)
            intensity = round(abs(score - 0.5) * 2 + RNG.uniform(-0.05, 0.05), 3)
            intensity = max(0.0, min(1.0, intensity))
            sarcasm = RNG.random() < 0.05
            nlp = PostNLP(
                post_id=pid,
                sentiment=sentiment,
                sentiment_score=score,
                emotion=emotion,
                emotion_score=emotion_score,
                support_score=score if sentiment == "positive" else round(1.0 - score, 3),
                intensity=intensity,
                sarcasm_flag=sarcasm,
                sarcasm_conf=round(RNG.uniform(0.55, 0.85), 3) if sarcasm else round(RNG.uniform(0.02, 0.14), 3),
                model_version="rule-based-v2-demo",
            )
            db.add(nlp)
        await db.flush()
        total_written += len(chunk)
        print(f"  + NLP {total_written}/{len(new_ids)}", end="\r")
    await db.commit()
    print(f"\n  = {total_written} NLP rows written")


async def _seed_post_topics(
    db: AsyncSession,
    post_ids: list[int],
    post_topic_map: dict[int, str],
    topic_ids: dict[str, int],
) -> None:
    print("\n[5/7] Post-topic assignments...")
    existing_r = await db.execute(text("SELECT post_id FROM post_topics"))
    existing_set = {row[0] for row in existing_r.fetchall()}
    new_ids = [pid for pid in post_ids if pid not in existing_set]
    if not new_ids:
        print("  = Post-topic assignments already complete")
        return
    for pid in new_ids:
        topic_name = post_topic_map.get(pid, "fuel_prices")
        tid = topic_ids.get(topic_name)
        if tid is None:
            continue
        pt = PostTopic(post_id=pid, topic_id=tid, confidence=round(RNG.uniform(0.55, 0.95), 3))
        db.add(pt)
    await db.flush()
    await db.commit()
    print(f"  + {len(new_ids)} post-topic rows")


async def _seed_trends(db: AsyncSession, topic_ids: dict[str, int]) -> None:
    print("\n[6/7] Trends...")
    existing_r = await db.execute(text("SELECT name FROM trends"))
    existing_names = {row[0] for row in existing_r.fetchall()}
    now = datetime.now(timezone.utc)
    for spec in _TREND_SPECS:
        if spec["name"] in existing_names:
            continue
        tid = topic_ids.get(spec["topic"])
        t = Trend(
            topic_id=tid,
            name=spec["name"],
            trend_score=spec["trend_score"],
            volume_decay=spec["baseline_7d"] * spec["trend_score"],
            velocity=spec["velocity"],
            acceleration=spec["acceleration"],
            engagement=round(RNG.uniform(0.04, 0.22), 3),
            unique_users=spec["unique_users"],
            platform_count=spec["platform_count"],
            community_spread=spec["community_spread"],
            sentiment_shift=spec["sentiment_shift"],
            baseline_7d=spec["baseline_7d"],
            is_emerging=spec["is_emerging"],
            platforms=spec["platforms"],
            measured_at=now,
        )
        db.add(t)
        print(f"  + {spec['name']}")
    await db.commit()


async def _seed_segments(db: AsyncSession) -> None:
    print("\n[7/7] Segments & Personas...")
    existing_r = await db.execute(text("SELECT name FROM demographic_segments"))
    existing_names = {row[0] for row in existing_r.fetchall()}

    for spec in _SEGMENT_SPECS:
        if spec["name"] in existing_names:
            print(f"  = {spec['name'][:60]}... (exists)")
            continue
        seg = DemographicSegment(
            name=spec["name"],
            description=spec["description"],
            dominant_language=spec["dominant_language"],
            size_estimate=spec["size_estimate"],
            confidence=spec["confidence"],
            evidence_count=RNG.randint(200, 600),
            topic_prefs=spec["topic_prefs"],
            sentiment_profile=spec["sentiment_profile"],
            activity_profile=spec["activity_profile"],
            geo_distribution=spec["geo_distribution"],
            updated_at=datetime.now(timezone.utc),
        )
        db.add(seg)
        await db.flush()
        persona = Persona(
            segment_id=seg.id,
            summary=spec["summary"],
            interests={"tags": spec["interests"]},
            reaction=spec["reaction"],
            influence_score=round(RNG.uniform(0.3, 0.85), 3),
            confidence=spec["confidence"],
            evidence_json={"post_sample_count": RNG.randint(80, 300)},
        )
        db.add(persona)
        print(f"  + {spec['name'][:60]}...")
    await db.commit()


if __name__ == "__main__":
    db_url = settings.DATABASE_URL
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    asyncio.run(seed(db_url))
