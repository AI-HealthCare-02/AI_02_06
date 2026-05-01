// Query key factory — 모든 도메인 hook 이 이 파일의 함수를 호출해 key 를 만든다.
// 같은 데이터에 대해 다른 곳에서 다른 key 를 쓰면 invalidate 가 안 통하므로 SSOT.

export const qk = {
  prescriptionGroups: {
    all: () => ['prescription-groups'],
    list: (profileId, search) => ['prescription-groups', 'list', profileId, search || ''],
    detail: (groupId) => ['prescription-groups', 'detail', groupId],
  },
  lifestyleGuides: {
    all: () => ['lifestyle-guides'],
    list: (profileId) => ['lifestyle-guides', 'list', profileId],
    detail: (guideId) => ['lifestyle-guides', 'detail', guideId],
    challenges: (guideId) => ['lifestyle-guides', 'challenges', guideId],
  },
  challenges: {
    all: () => ['challenges'],
    list: (profileId) => ['challenges', 'list', profileId],
  },
}
