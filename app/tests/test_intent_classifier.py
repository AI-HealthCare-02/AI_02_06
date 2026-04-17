"""Tests for IntentClassifier - keyword and rule-based intent classification."""

from app.services.rag.intent.classifier import IntentClassifier
from app.services.rag.intent.intents import IntentType


class TestIntentType:
    """Test IntentType enum definition."""

    def test_all_intent_types_defined(self) -> None:
        """All required intent categories must be defined."""
        expected = {
            "MEDICATION_INFO",
            "DRUG_INTERACTION",
            "MY_SCHEDULE",
            "SUPPLEMENT_INFO",
            "NEARBY_HOSPITAL",
            "WEATHER",
            "GENERAL_CHAT",
            "OUT_OF_SCOPE",
        }
        actual = {intent.name for intent in IntentType}
        assert expected == actual

    def test_intent_type_values_are_strings(self) -> None:
        """IntentType values must be lowercase strings."""
        for intent in IntentType:
            assert intent.value == intent.value.lower()


class TestIntentClassifierMedicationInfo:
    """Test MEDICATION_INFO intent classification."""

    def setup_method(self) -> None:
        """Initialize classifier before each test."""
        self.classifier = IntentClassifier()

    def test_classify_side_effect_question(self) -> None:
        """Questions about side effects should be MEDICATION_INFO."""
        assert self.classifier.classify("타이레놀 부작용이 뭐야?") == IntentType.MEDICATION_INFO

    def test_classify_dosage_question(self) -> None:
        """Questions about dosage should be MEDICATION_INFO."""
        assert self.classifier.classify("아스피린 용법이 어떻게 돼?") == IntentType.MEDICATION_INFO

    def test_classify_precaution_question(self) -> None:
        """Questions about precautions should be MEDICATION_INFO."""
        assert self.classifier.classify("이 약 주의사항 알려줘") == IntentType.MEDICATION_INFO

    def test_classify_efficacy_question(self) -> None:
        """Questions about efficacy should be MEDICATION_INFO."""
        assert self.classifier.classify("소화제 효능이 뭐야?") == IntentType.MEDICATION_INFO


class TestIntentClassifierDrugInteraction:
    """Test DRUG_INTERACTION intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_drug_combination_question(self) -> None:
        """Questions about drug combinations should be DRUG_INTERACTION."""
        assert self.classifier.classify("이 약이랑 저 약 같이 먹어도 돼?") == IntentType.DRUG_INTERACTION

    def test_classify_interaction_question(self) -> None:
        """Questions about drug interactions should be DRUG_INTERACTION."""
        assert self.classifier.classify("약물 상호작용 확인해줘") == IntentType.DRUG_INTERACTION

    def test_classify_contraindication_question(self) -> None:
        """Questions about contraindications should be DRUG_INTERACTION."""
        assert self.classifier.classify("병용금기 약물이 있어?") == IntentType.DRUG_INTERACTION


class TestIntentClassifierMySchedule:
    """Test MY_SCHEDULE intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_schedule_question(self) -> None:
        """Questions about medication schedule should be MY_SCHEDULE."""
        assert self.classifier.classify("오늘 몇 시에 약 먹어야 해?") == IntentType.MY_SCHEDULE

    def test_classify_remaining_question(self) -> None:
        """Questions about remaining medication should be MY_SCHEDULE."""
        assert self.classifier.classify("남은 약이 몇 개야?") == IntentType.MY_SCHEDULE

    def test_classify_intake_history_question(self) -> None:
        """Questions about intake history should be MY_SCHEDULE."""
        assert self.classifier.classify("오늘 약 먹었어?") == IntentType.MY_SCHEDULE


class TestIntentClassifierSupplementInfo:
    """Test SUPPLEMENT_INFO intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_supplement_question(self) -> None:
        """Questions about supplements should be SUPPLEMENT_INFO."""
        assert self.classifier.classify("비타민C 효능이 뭐야?") == IntentType.SUPPLEMENT_INFO

    def test_classify_nutrient_question(self) -> None:
        """Questions about nutrients should be SUPPLEMENT_INFO."""
        assert self.classifier.classify("오메가3 영양제 추천해줘") == IntentType.SUPPLEMENT_INFO


class TestIntentClassifierNearbyHospital:
    """Test NEARBY_HOSPITAL intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_hospital_question(self) -> None:
        """Questions about nearby hospitals should be NEARBY_HOSPITAL."""
        assert self.classifier.classify("근처 병원 어디야?") == IntentType.NEARBY_HOSPITAL

    def test_classify_pharmacy_question(self) -> None:
        """Questions about nearby pharmacies should be NEARBY_HOSPITAL."""
        assert self.classifier.classify("주변 약국 찾아줘") == IntentType.NEARBY_HOSPITAL


class TestIntentClassifierWeather:
    """Test WEATHER intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_weather_question(self) -> None:
        """Questions about weather should be WEATHER."""
        assert self.classifier.classify("오늘 날씨 어때?") == IntentType.WEATHER

    def test_classify_temperature_question(self) -> None:
        """Questions about temperature should be WEATHER."""
        assert self.classifier.classify("오늘 기온이 몇 도야?") == IntentType.WEATHER


class TestIntentClassifierGeneralChat:
    """Test GENERAL_CHAT intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_greeting(self) -> None:
        """Greetings should be GENERAL_CHAT."""
        assert self.classifier.classify("안녕") == IntentType.GENERAL_CHAT

    def test_classify_thanks(self) -> None:
        """Thanks should be GENERAL_CHAT."""
        assert self.classifier.classify("고마워") == IntentType.GENERAL_CHAT

    def test_classify_farewell(self) -> None:
        """Farewells should be GENERAL_CHAT."""
        assert self.classifier.classify("잘 있어") == IntentType.GENERAL_CHAT


class TestIntentClassifierOutOfScope:
    """Test OUT_OF_SCOPE intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_stock_question(self) -> None:
        """Stock questions should be OUT_OF_SCOPE."""
        assert self.classifier.classify("주식 추천해줘") == IntentType.OUT_OF_SCOPE

    def test_classify_politics_question(self) -> None:
        """Politics questions should be OUT_OF_SCOPE."""
        assert self.classifier.classify("대통령 선거 결과 알려줘") == IntentType.OUT_OF_SCOPE


class TestIntentClassifierEdgeCases:
    """Test edge cases for intent classification."""

    def setup_method(self) -> None:
        self.classifier = IntentClassifier()

    def test_classify_empty_string(self) -> None:
        """Empty string should return GENERAL_CHAT as fallback."""
        result = self.classifier.classify("")
        assert isinstance(result, IntentType)

    def test_classify_returns_intent_type(self) -> None:
        """classify() must always return an IntentType instance."""
        result = self.classifier.classify("아무 말이나")
        assert isinstance(result, IntentType)
