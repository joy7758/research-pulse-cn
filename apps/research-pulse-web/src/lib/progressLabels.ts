export function getReadingStatusLabel(status: string) {
  switch (status) {
    case "unread":
      return "待读";
    case "skimming":
      return "略读中";
    case "reading":
      return "精读中";
    case "read":
      return "已读";
    case "archived":
      return "已归档";
    default:
      return status;
  }
}

export function getResearchStageLabel(stage: string) {
  switch (stage) {
    case "inbox":
      return "收件箱";
    case "triage":
      return "待筛选";
    case "relevant":
      return "相关";
    case "reviewing":
      return "阅读分析中";
    case "cited":
      return "已引用";
    case "implemented":
      return "已转化";
    case "parked":
      return "暂停";
    default:
      return stage;
  }
}

export function getPriorityLabel(priority: string) {
  switch (priority) {
    case "urgent":
      return "紧急";
    case "high":
      return "高优先级";
    case "normal":
      return "普通";
    case "low":
      return "低优先级";
    default:
      return priority;
  }
}
