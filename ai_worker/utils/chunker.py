import json
from pathlib import Path


class DataChunker:
    @staticmethod
    def load_json(file_path: str) -> list[dict]:
        path = Path(file_path).resolve()
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def json_to_chunks(medicine_data: list[dict]) -> list[str]:
        """JSON 객체 리스트를 약품별 텍스트 청크 리스트로 변환"""
        chunks = []
        for med in medicine_data:
            text = (
                f"약 이름: {med['name']}\n"
                f"성분: {med['ingredient']}\n"
                f"용도: {med['usage']}\n"
                f"면책사항: {med['disclaimer']}\n"
                f"병용금기 약물: {', '.join(med['contraindicated_drugs'])}\n"
                f"금기 음식: {', '.join(med['contraindicated_foods'])}"
            )
            chunks.append(text)
        return chunks

    @staticmethod
    def json_to_text(medicine_data: list[dict]) -> str:
        """전체를 하나의 문자열로 반환 (호환용)"""
        return "\n---\n".join(DataChunker.json_to_chunks(medicine_data))
