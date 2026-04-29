export const RELATION_OPTIONS = [
  { value: 'FATHER', label: '아버지' },
  { value: 'MOTHER', label: '어머니' },
  { value: 'SON', label: '아들' },
  { value: 'DAUGHTER', label: '딸' },
  { value: 'HUSBAND', label: '남편' },
  { value: 'WIFE', label: '아내' },
  { value: 'OTHER', label: '기타' },
];

export const RELATION_MAP = {
  FATHER: '아버지',
  MOTHER: '어머니',
  SON: '아들',
  DAUGHTER: '딸',
  HUSBAND: '남편',
  WIFE: '아내',
  OTHER: '기타',
  SELF: '본인'
};

// 백엔드 (PARENT, CHILD, SPOUSE) + 성별 조합을 프론트엔드의 세부 관계(FATHER 등)로 변환
export const getSpecificRelation = (relationType, gender) => {
  if (relationType === 'PARENT') return gender === 'MALE' ? 'FATHER' : 'MOTHER';
  if (relationType === 'CHILD') return gender === 'MALE' ? 'SON' : 'DAUGHTER';
  if (relationType === 'SPOUSE') return gender === 'MALE' ? 'HUSBAND' : 'WIFE';
  if (relationType === 'SELF') return 'SELF';
  return 'OTHER';
};

// 프론트엔드의 세부 관계(FATHER 등)를 백엔드 형식(relation_type, gender)으로 변환
export const getBackendRelation = (specificRelation) => {
  if (['FATHER', 'MOTHER'].includes(specificRelation)) {
    return { relation_type: 'PARENT', gender: specificRelation === 'FATHER' ? 'MALE' : 'FEMALE' };
  }
  if (['SON', 'DAUGHTER'].includes(specificRelation)) {
    return { relation_type: 'CHILD', gender: specificRelation === 'SON' ? 'MALE' : 'FEMALE' };
  }
  if (['HUSBAND', 'WIFE'].includes(specificRelation)) {
    return { relation_type: 'SPOUSE', gender: specificRelation === 'HUSBAND' ? 'MALE' : 'FEMALE' };
  }
  if (specificRelation === 'SELF') {
    return { relation_type: 'SELF' };
  }
  return { relation_type: 'OTHER', gender: 'OTHER' };
};
