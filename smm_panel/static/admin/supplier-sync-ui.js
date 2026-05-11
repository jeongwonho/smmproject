export function supplierSyncStatusLabel(status) {
  if (status === "success") return "동기화 정상";
  if (status === "syncing") return "동기화 중";
  if (status === "failed") return "동기화 실패";
  return "동기화 대기";
}

export function supplierSyncStatusTone(status) {
  if (status === "success") return "success";
  if (status === "syncing") return "warning";
  if (status === "failed") return "warning";
  return "neutral";
}

export function supplierNextSyncLabel(supplier) {
  const completedAt = supplier?.serviceSyncCompletedAt || supplier?.lastCheckedAt || "";
  const interval = Number(supplier?.serviceSyncIntervalMinutes || 30);
  if (!completedAt) return "동기화 이력 없음";
  const parsed = new Date(completedAt);
  if (Number.isNaN(parsed.getTime())) return "계산 불가";
  parsed.setMinutes(parsed.getMinutes() + Math.max(interval, 5));
  return parsed.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function supplierSyncInsight(supplier, status) {
  return {
    label: "자동 동기화",
    value: supplierSyncStatusLabel(status),
    description: status === "failed"
      ? (supplier?.serviceSyncMessage || "마지막 자동 동기화가 실패했습니다.")
      : `다음 예상 ${supplierNextSyncLabel(supplier)}`,
    tone: supplierSyncStatusTone(status),
  };
}
